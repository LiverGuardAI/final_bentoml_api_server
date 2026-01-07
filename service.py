"""
BentoML Service for LiverGuard CDSS
Model Store 연동 방식

실행:
    bentoml serve service:svc --reload --port 3001
    
엔드포인트:
    POST /predict       - 통합 예측 (병기 + 재발 + 생존)
    POST /predict_stage - 병기 예측만 (mRNA 불필요)
    GET  /health        - 헬스체크 (정상적으로 동작 중인지 확인하기 위한 간단한 API)
"""

import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, Any, List, Optional

import bentoml
from bentoml.io import JSON

# ============================================================
# Model Store에서 모델 로드
# ============================================================

# Task 1: Stage (sklearn - XGBoost)
try:
    stage_ref = bentoml.sklearn.get("liverguard_stage:latest")
    stage_runner = stage_ref.to_runner()
    stage_objs = stage_ref.custom_objects
    HAS_STAGE = True
    print(f"✅ Stage model loaded: {stage_ref.tag}")
except bentoml.exceptions.NotFound:
    HAS_STAGE = False
    print("⚠️ Stage model not found in BentoML store")

# Task 2: Relapse (sklearn - RandomForest)
try:
    relapse_ref = bentoml.sklearn.get("liverguard_relapse:latest")
    relapse_runner = relapse_ref.to_runner()
    relapse_objs = relapse_ref.custom_objects
    HAS_RELAPSE = True
    print(f"✅ Relapse model loaded: {relapse_ref.tag}")
except bentoml.exceptions.NotFound:
    HAS_RELAPSE = False
    print("⚠️ Relapse model not found in BentoML store")

# Task 3: Survival (picklable - CoxPH)
try:
    survival_ref = bentoml.picklable_model.get("liverguard_survival:latest")
    survival_runner = survival_ref.to_runner()
    survival_objs = survival_ref.custom_objects
    HAS_SURVIVAL = True
    print(f"✅ Survival model loaded: {survival_ref.tag}")
except bentoml.exceptions.NotFound:
    HAS_SURVIVAL = False
    print("⚠️ Survival model not found in BentoML store")

# ============================================================
# Service 정의
# ============================================================

runners = []
if HAS_STAGE: runners.append(stage_runner)
if HAS_RELAPSE: runners.append(relapse_runner)
if HAS_SURVIVAL: runners.append(survival_runner)

svc = bentoml.Service("liverguard_cdss", runners=runners)

# ============================================================
# 입력 검증
# ============================================================

def validate_input(clinical: List, ct: List, mrna: List = None, 
                   require_mrna: bool = False) -> Optional[str]:
    """통일된 입력 검증"""
    if not clinical or len(clinical) < 5:
        return "clinical must have at least 5 features"
    
    if not ct or len(ct) != 512:
        return f"ct_features must be 512-dimensional, got {len(ct) if ct else 0}"
    
    if require_mrna and (not mrna or len(mrna) != 20):
        return f"mrna must have 20 pathways, got {len(mrna) if mrna else 0}"
    
    return None

# ============================================================
# 전처리 함수
# ============================================================

def preprocess_stage(clinical: List, ct: List) -> np.ndarray:
    """Task 1 전처리 (mRNA 없음)"""
    clinical = np.array(clinical).reshape(1, -1)
    ct = np.array(ct).reshape(1, -1)
    
    # Clinical: feature selection → impute → scale
    clinical = clinical[:, stage_objs['clinical_idx']]
    clinical = stage_objs['scaler_clin'].transform(
        stage_objs['imputer_clin'].transform(clinical)
    )
    
    # CT: impute → scale → PCA
    ct = stage_objs['pca'].transform(
        stage_objs['scaler_ct'].transform(
            stage_objs['imputer_ct'].transform(ct)
        )
    )
    
    return np.hstack([clinical, ct])


def preprocess_relapse(clinical: List, mrna: List, ct: List) -> np.ndarray:
    """Task 2 전처리 (mRNA 필수)"""
    clinical = np.array(clinical).reshape(1, -1)
    mrna = np.array(mrna).reshape(1, -1)
    ct = np.array(ct).reshape(1, -1)
    
    # Clinical: feature selection → impute → scale
    clinical = clinical[:, relapse_objs['clinical_idx']]
    clinical = relapse_objs['scaler_clin'].transform(
        relapse_objs['imputer_clin'].transform(clinical)
    )
    
    # mRNA: impute → scale
    mrna = relapse_objs['scaler_mrna'].transform(
        relapse_objs['imputer_mrna'].transform(mrna)
    )
    
    # CT: impute → scale → PCA
    ct = relapse_objs['pca'].transform(
        relapse_objs['scaler_ct'].transform(
            relapse_objs['imputer_ct'].transform(ct)
        )
    )
    
    return np.hstack([clinical, mrna, ct])


def preprocess_survival(clinical: List, mrna: List, ct: List) -> pd.DataFrame:
    """Task 3 전처리 (mRNA 필수)"""
    clinical = np.array(clinical).reshape(1, -1)
    mrna = np.array(mrna).reshape(1, -1)
    ct = np.array(ct).reshape(1, -1)
    
    # Clinical: 전체 사용 (Task3는 모든 clinical feature 사용)
    clinical = survival_objs['scaler_clin'].transform(
        survival_objs['imputer_clin'].transform(clinical)
    )
    
    # mRNA
    mrna = survival_objs['scaler_mrna'].transform(
        survival_objs['imputer_mrna'].transform(mrna)
    )
    
    # CT
    ct = survival_objs['pca'].transform(
        survival_objs['scaler_ct'].transform(
            survival_objs['imputer_ct'].transform(ct)
        )
    )
    
    X = np.hstack([clinical, mrna, ct])
    return pd.DataFrame(X, columns=survival_objs['feature_names'])

# ============================================================
# Helper 함수
# ============================================================

def get_risk_level(prob: float) -> str:
    if prob > 0.6: return "High"
    elif prob > 0.4: return "Medium"
    return "Low"


def get_risk_group(score: float, cutoffs: List[float]) -> str:
    if score <= cutoffs[0]: return "Low"
    elif score <= cutoffs[1]: return "Medium"
    return "High"


def get_relative_survival(group: str) -> Dict[str, float]:
    """
    상대적 생존 확률 (cohort-based estimate)
    NOTE: 절대 생존 확률이 아님!
    """
    estimates = {
        "Low": {"months_12": 0.95, "months_24": 0.88, "months_36": 0.82},
        "Medium": {"months_12": 0.85, "months_24": 0.72, "months_36": 0.60},
        "High": {"months_12": 0.70, "months_24": 0.50, "months_36": 0.35},
    }
    return estimates.get(group, estimates["Medium"])

# ============================================================
# API Endpoints
# ============================================================

@svc.api(input=JSON(), output=JSON())
async def predict(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    통합 AI 예측 (병기 + 재발 + 생존)
    
    Input:
    {
        "clinical": [9개 값],
        "ct_features": [512개 값],
        "mrna": [20개 값],       # 선택, Task2/3용
        "use_mrna": true/false   # 선택, 기본값은 mrna 존재 여부
    }
    """
    clinical = data.get('clinical', [])
    ct = data.get('ct_features', [])
    mrna = data.get('mrna')
    use_mrna = data.get('use_mrna', mrna is not None and len(mrna) == 20)
    
    # 입력 검증
    error = validate_input(clinical, ct)
    if error:
        return {"error": error, "status": "validation_failed"}
    
    result = {
        "prediction_timestamp": datetime.now().isoformat(),
        "input_validation": {
            "clinical_dim": len(clinical),
            "ct_dim": len(ct),
            "mrna_provided": mrna is not None and len(mrna) == 20,
            "use_mrna": use_mrna
        }
    }
    
    # ===== Task 1: Stage (mRNA 사용 안 함) =====
    if HAS_STAGE:
        try:
            X = preprocess_stage(clinical, ct)
            proba = await stage_runner.predict_proba.async_run(X)
            proba = proba[0]
            pred = int(np.argmax(proba))
            
            labels = ["Stage I", "Stage II", "Stage III+"]
            result['stage_prediction'] = {
                "predicted_stage": labels[pred],
                "stage_code": pred,
                "probabilities": {labels[i]: float(proba[i]) for i in range(3)},
                "confidence": float(np.max(proba)),
                "uses_mrna": False
            }
        except Exception as e:
            result['stage_prediction'] = {"error": str(e), "uses_mrna": False}
    else:
        result['stage_prediction'] = {"error": "Model not loaded", "uses_mrna": False}
    
    # ===== Task 2: Relapse (mRNA 필요) =====
    if HAS_RELAPSE:
        if use_mrna and mrna and len(mrna) == 20:
            try:
                X = preprocess_relapse(clinical, mrna, ct)
                proba = await relapse_runner.predict_proba.async_run(X)
                prob = float(proba[0, 1])
                threshold = relapse_objs['threshold']
                
                result['relapse_prediction'] = {
                    "relapse_probability": prob,
                    "risk_level": get_risk_level(prob),
                    "prediction": int(prob >= threshold),
                    "threshold_used": float(threshold),
                    "uses_mrna": True
                }
            except Exception as e:
                result['relapse_prediction'] = {"error": str(e), "uses_mrna": True}
        else:
            result['relapse_prediction'] = {
                "error": "mRNA data required for relapse prediction",
                "uses_mrna": True,
                "mrna_provided": mrna is not None and len(mrna) == 20
            }
    else:
        result['relapse_prediction'] = {"error": "Model not loaded", "uses_mrna": True}
    
    # ===== Task 3: Survival (mRNA 필요) =====
    if HAS_SURVIVAL:
        if use_mrna and mrna and len(mrna) == 20:
            try:
                df_input = preprocess_survival(clinical, mrna, ct)
                cox_model = survival_ref.load()  # 직접 로드 (Cox는 async 미지원)
                risk_score = float(cox_model.predict_partial_hazard(df_input).values[0])
                
                cutoffs = survival_objs['risk_cutoffs']
                risk_group = get_risk_group(risk_score, cutoffs)
                
                result['survival_analysis'] = {
                    "risk_score": risk_score,
                    "risk_group": risk_group,
                    "survival_probabilities": get_relative_survival(risk_group),
                    "uses_mrna": True,
                    "note": "RELATIVE risk within cohort. Not absolute survival probability.",
                    "risk_cutoff_method": "percentile_33_66"
                }
            except Exception as e:
                result['survival_analysis'] = {"error": str(e), "uses_mrna": True}
        else:
            result['survival_analysis'] = {
                "error": "mRNA data required for survival analysis",
                "uses_mrna": True,
                "mrna_provided": mrna is not None and len(mrna) == 20
            }
    else:
        result['survival_analysis'] = {"error": "Model not loaded", "uses_mrna": True}
    
    return result


@svc.api(input=JSON(), output=JSON())
async def predict_stage(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    병기 예측 전용 (mRNA 불필요)
    
    Input:
    {
        "clinical": [9개 값],
        "ct_features": [512개 값]
    }
    """
    clinical = data.get('clinical', [])
    ct = data.get('ct_features', [])
    
    error = validate_input(clinical, ct)
    if error:
        return {"error": error, "status": "validation_failed"}
    
    if not HAS_STAGE:
        return {"error": "Stage model not loaded"}
    
    try:
        X = preprocess_stage(clinical, ct)
        proba = await stage_runner.predict_proba.async_run(X)
        proba = proba[0]
        pred = int(np.argmax(proba))
        
        labels = ["Stage I", "Stage II", "Stage III+"]
        return {
            "predicted_stage": labels[pred],
            "stage_code": pred,
            "probabilities": {labels[i]: float(proba[i]) for i in range(3)},
            "confidence": float(np.max(proba)),
            "uses_mrna": False,
            "model_version": "v11.6",
            "prediction_timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {"error": str(e)}


@svc.api(input=JSON(), output=JSON())
async def health(_: Dict = None) -> Dict[str, Any]:
    """헬스체크"""
    return {
        "status": "healthy",
        "service": "liverguard_cdss",
        "models": {
            "stage": HAS_STAGE,
            "relapse": HAS_RELAPSE,
            "survival": HAS_SURVIVAL
        },
        "timestamp": datetime.now().isoformat()
    }
