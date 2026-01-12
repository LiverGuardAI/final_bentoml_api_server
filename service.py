"""
BentoML Service for LiverGuard CDSS (v1.4+ compatible)
Model Store 연동 방식

실행:
    bentoml serve service:LiverGuardService --reload --port 3001

엔드포인트:
    POST /predict          - 통합 예측 (병기 + 재발 + 생존)
    POST /predict_stage    - 병기 예측만 (mRNA 불필요)
    POST /predict_relapse  - 재발 예측만 (mRNA 필수)
    POST /predict_survival - 생존 분석만 (mRNA 필수)
    POST /health           - 헬스체크
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, Any, List, Optional

import numpy as np
import pandas as pd
import bentoml
from bentoml.io import JSON


# ============================================================
# Model Loading (BentoML Model Store)
# ============================================================

HAS_STAGE = HAS_RELAPSE = HAS_SURVIVAL = False

# Task 1: Stage (sklearn - XGBoost)
try:
    stage_ref = bentoml.sklearn.get("liverguard_stage:latest")
    stage_runner = stage_ref.to_runner()
    stage_objs = stage_ref.custom_objects
    HAS_STAGE = True
    print(f"✅ Stage model loaded: {stage_ref.tag}")
except Exception as e:
    print(f"⚠️ Stage model load failed: {e}")

# Task 2: Relapse (sklearn - RandomForest)
try:
    relapse_ref = bentoml.sklearn.get("liverguard_relapse:latest")
    relapse_runner = relapse_ref.to_runner()
    relapse_objs = relapse_ref.custom_objects
    HAS_RELAPSE = True
    print(f"✅ Relapse model loaded: {relapse_ref.tag}")
except Exception as e:
    print(f"⚠️ Relapse model load failed: {e}")

# Task 3: Survival (picklable - CoxPH)
try:
    survival_ref = bentoml.picklable_model.get("liverguard_survival:latest")
    survival_objs = survival_ref.custom_objects
    HAS_SURVIVAL = True
    print(f"✅ Survival model loaded: {survival_ref.tag}")
except Exception as e:
    print(f"⚠️ Survival model load failed: {e}")

# ============================================================
# Service 정의
# ============================================================

@bentoml.service(
    name="liverguard_cdss",
    runners=[
        *( [stage_runner] if HAS_STAGE else [] ),
        *( [relapse_runner] if HAS_RELAPSE else [] ),
    ]
)
class LiverGuardService:

    # ============================================================
    # 입력 검증
    # ============================================================

    @staticmethod
    def validate_input(
        clinical: List,
        ct: List,
        mrna: Optional[List] = None,
        require_mrna: bool = False
    ) -> Optional[str]:
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

    @staticmethod
    def preprocess_stage(clinical, ct):
        clinical = np.array(clinical).reshape(1, -1)
        ct = np.array(ct).reshape(1, -1)
    
        # Clinical: feature selection → impute → scale
        clinical = clinical[:, stage_objs["clinical_idx"]]
        clinical = stage_objs["scaler_clin"].transform(
            stage_objs["imputer_clin"].transform(clinical)
        )
    
        # CT: impute → scale → PCA
        ct = stage_objs["pca"].transform(
                stage_objs["scaler_ct"].transform(
                    stage_objs["imputer_ct"].transform(ct)
                )
            )
    
        return np.hstack([clinical, ct])

    @staticmethod
    def preprocess_relapse(clinical, mrna, ct):
        """Task 2 전처리 (mRNA 필수)"""
        clinical = np.array(clinical).reshape(1, -1)
        mrna = np.array(mrna).reshape(1, -1)
        ct = np.array(ct).reshape(1, -1)
    
        # Clinical: feature selection → impute → scale
        clinical = clinical[:, relapse_objs["clinical_idx"]]
        clinical = relapse_objs["scaler_clin"].transform(
            relapse_objs["imputer_clin"].transform(clinical)
        )
        
        # mRNA: impute → scale
        mrna = relapse_objs["scaler_mrna"].transform(
            relapse_objs["imputer_mrna"].transform(mrna)
        )
        
        # CT: impute → scale → PCA
        ct = relapse_objs["pca"].transform(
            relapse_objs["scaler_ct"].transform(
                relapse_objs["imputer_ct"].transform(ct)
            )
        )
        
        return np.hstack([clinical, mrna, ct])

    @staticmethod
    def preprocess_survival(clinical, mrna, ct):
        """Task 3 전처리 (mRNA 필수)"""
        clinical = np.array(clinical).reshape(1, -1)
        mrna = np.array(mrna).reshape(1, -1)
        ct = np.array(ct).reshape(1, -1)
        
        # Clinical: 전체 사용 (Task3는 모든 clinical feature 사용)
        clinical = survival_objs["scaler_clin"].transform(
            survival_objs["imputer_clin"].transform(clinical)
        )
        
        # mRNA
        mrna = survival_objs["scaler_mrna"].transform(
            survival_objs["imputer_mrna"].transform(mrna)
        )
        
        # CT
        ct = survival_objs["pca"].transform(
            survival_objs["scaler_ct"].transform(
                survival_objs["imputer_ct"].transform(ct)
            )
        )
        
        X = np.hstack([clinical, mrna, ct])
        return pd.DataFrame(X, columns=survival_objs["feature_names"])

    # ============================================================
    # Helper 함수
    # ============================================================

    @staticmethod
    def get_risk_level(prob):
        if prob > 0.6:
            return "High"
        elif prob > 0.4:
            return "Medium"
        return "Low"

    @staticmethod
    def get_risk_group(score, cutoffs):
        if score <= cutoffs[0]:
            return "Low"
        elif score <= cutoffs[1]:
            return "Medium"
        return "High"
    
    @staticmethod
    def calculate_percentile(score: float, distribution: list[float]) -> float:
        count = sum(1 for v in distribution if v <= score)
        return round(count / len(distribution) * 100, 1)

    # ============================================================
    # API Endpoints
    # ============================================================

    @bentoml.api
    async def predict(self, data: Dict[str, Any]) -> Dict[str, Any]:
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
        clinical = data.get("clinical", [])
        ct = data.get("ct_features", [])
        mrna = data.get("mrna")
        use_mrna = data.get("use_mrna", mrna is not None and len(mrna) == 20)

        # 입력 검증
        error = self.validate_input(clinical, ct)
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
            X = self.preprocess_stage(clinical, ct)
            proba = (await stage_runner.predict_proba.async_run(X))[0]
            pred = int(np.argmax(proba))
            labels = ["Stage I", "Stage II", "Stage III+"]

            result["stage_prediction"] = {
                "predicted_stage": labels[pred],
                "stage_code": pred,
                "confidence": float(np.max(proba)),
                "probabilities": {labels[i]: float(proba[i]) for i in range(3)},
                "uses_mrna": False,
            }
            
        # ===== Task 2: Relapse (mRNA 필요) =====
        if HAS_RELAPSE:
            if use_mrna and mrna:
                X = self.preprocess_relapse(clinical, mrna, ct)
                prob = float((await relapse_runner.predict_proba.async_run(X))[0, 1])

                result["relapse_prediction"] = {
                    "relapse_probability": prob,
                    "risk_level": self.get_risk_level(prob),
                    "prediction": int(prob >= relapse_objs["threshold"]),
                    "uses_mrna": True,
                }
            else:
                result["relapse_prediction"] = {
                    "error": "mRNA required",
                    "uses_mrna": True,
                }
                
        # ===== Task 3: Survival (mRNA 필요) =====
        if HAS_SURVIVAL:
            if use_mrna and mrna and len(mrna) == 20:
                try:
                    df_input = self.preprocess_survival(clinical, mrna, ct)
                    cox_model = survival_ref.load()
                    risk_score = float(cox_model.predict_partial_hazard(df_input).values[0])

                    cutoffs = survival_objs["risk_cutoffs"]
                    percentile = self.calculate_percentile(risk_score, survival_objs["risk_score_distribution"]) # ← 학습 시 저장

                    result["survival_analysis"] = {
                        "risk_score": risk_score,
                        "risk_group": self.get_risk_group(risk_score, cutoffs),
                        "risk_percentile": percentile,
                        "uses_mrna": True,
                        "interpretation": "relative_risk",
                        "warning": (
                            "This result represents RELATIVE survival risk "
                            "within the training cohort. "
                            "It is NOT an absolute survival probability."
                        ),
                    }
                    
                except Exception as e:
                    result["survival_analysis"] = {
                        "error": str(e),
                        "uses_mrna": True
                    }
            else:
                result["survival_analysis"] = {
                    "error": "mRNA required for survival analysis",
                    "uses_mrna": True
                }

        return result
    

    @bentoml.api
    async def predict_stage(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        병기 예측 전용 (mRNA 불필요)
        
        Input:
        {
            "clinical": [9개 값],
            "ct_features": [512개 값]
        }
        """
        clinical = data.get("clinical", [])
        ct = data.get("ct_features", [])

        error = self.validate_input(clinical, ct)
        if error:
            return {"error": error}
        
        X = self.preprocess_stage(clinical, ct)
        proba = (await stage_runner.predict_proba.async_run(X))[0]
        pred = int(np.argmax(proba))
        labels = ["Stage I", "Stage II", "Stage III+"]

        return {
            "predicted_stage": labels[pred],
            "stage_code": pred,
            "confidence": float(np.max(proba)),
            "probabilities": {labels[i]: float(proba[i]) for i in range(3)},
            "uses_mrna": False,
        }

    @bentoml.api
    async def predict_relapse(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        재발 예측 전용 (mRNA 필수)

        Input:
        {
            "clinical": [값],
            "ct_features": [512개 값],
            "mrna": [20개 값]
        }
        """
        clinical = data.get('clinical', [])
        ct = data.get('ct_features', [])
        mrna = data.get('mrna', [])

        error = self.validate_input(clinical, ct, mrna, require_mrna=True)
        if error:
            return {"error": error, "status": "validation_failed"}

        if not HAS_RELAPSE:
            return {"error": "Relapse model not loaded"}

        try:
            X = self.preprocess_relapse(clinical, mrna, ct)
            proba = await relapse_runner.predict_proba.async_run(X)
            prob = float(proba[0, 1])
            threshold = relapse_objs['threshold']

            return {
                "relapse_probability": prob,
                "risk_level": self.get_risk_level(prob),
                "prediction": int(prob >= threshold),
                "threshold_used": float(threshold),
                "uses_mrna": True,
                "model_version": "v11.6",
                "prediction_timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {"error": str(e)}

    @bentoml.api
    async def predict_survival(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        생존 분석 전용 (mRNA 필수)

        Input:
        {
            "clinical": [값],
            "ct_features": [512개 값],
            "mrna": [20개 값]
        }
        """
        clinical = data.get('clinical', [])
        ct = data.get('ct_features', [])
        mrna = data.get('mrna', [])

        error = self.validate_input(clinical, ct, mrna, require_mrna=True)
        if error:
            return {"error": error, "status": "validation_failed"}

        if not HAS_SURVIVAL:
            return {"error": "Survival model not loaded"}

        try:
            df_input = self.preprocess_survival(clinical, mrna, ct)
            cox_model = survival_ref.load()
            risk_score = float(cox_model.predict_partial_hazard(df_input).values[0])

            cutoffs = survival_objs['risk_cutoffs']
            risk_group = self.get_risk_group(risk_score, cutoffs)

            # Calculate percentile for better interpretation
            percentile = self.calculate_percentile(risk_score, survival_objs.get("risk_score_distribution", []))

            return {
                "risk_score": risk_score,
                "risk_group": risk_group,
                "risk_percentile": percentile,
                "uses_mrna": True,
                "interpretation": "relative_risk",
                "warning": (
                    "This result represents RELATIVE survival risk "
                    "within the training cohort. "
                    "It is NOT an absolute survival probability."
                ),
                "risk_cutoff_method": "percentile_33_66",
                "model_version": "v11.6",
                "prediction_timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {"error": str(e)}

    @bentoml.api
    async def health(self, data: Dict = None) -> Dict[str, Any]:
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
