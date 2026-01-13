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
    POST /predict_survival_detail - 생존/위험도 곡선 + HR
    POST /health           - 헬스체크
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

import numpy as np
import pandas as pd
import bentoml
from bentoml.io import JSON
from hybrid_dur_model import HybridDUREngine



# 한국 시간대 (UTC+9)
KST = timezone(timedelta(hours=9))

def _safe_float(value) -> Optional[float]:
    if value is None:
        return None
    try:
        num = float(value)
    except (TypeError, ValueError):
        return None
    if np.isfinite(num):
        return num
    return None


# ============================================================
# Model Loading (BentoML Model Store)
# ============================================================

HAS_STAGE = HAS_RELAPSE = HAS_SURVIVAL = False
stage_runner = None
relapse_runner = None

# Task 1: Stage (sklearn - XGBoost)
try:
    stage_ref = bentoml.sklearn.get("liverguard_stage:latest")
    stage_runner = stage_ref.to_runner()
    if hasattr(stage_runner, "init_local"):
        stage_runner.init_local()
    stage_objs = stage_ref.custom_objects
    HAS_STAGE = True
    print(f"✅ Stage model loaded: {stage_ref.tag}")
except Exception as e:
    print(f"⚠️ Stage model load failed: {e}")

# Task 2: Relapse (sklearn - RandomForest)
try:
    relapse_ref = bentoml.sklearn.get("liverguard_relapse:latest")
    relapse_runner = relapse_ref.to_runner()
    if hasattr(relapse_runner, "init_local"):
        relapse_runner.init_local()
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
    traffic={"timeout": 60},
    runners=[
        *([stage_runner] if HAS_STAGE and stage_runner is not None else []),
        *([relapse_runner] if HAS_RELAPSE and relapse_runner is not None else []),
    ]
)
class LiverGuardService:
    # 1. Runner 선언 (Class attributes for auto-collection)
    stage_runner = stage_runner
    relapse_runner = relapse_runner

    def __init__(self):
        print("Initializing LiverGuardService...")
        
        # 1. DDI Engine initialization
        print("Initializing HybridDUREngine...")
        self.ddi_engine = HybridDUREngine()

        # 2. Stage Custom Objects
        self.has_stage = False
        try:
            stage_ref = bentoml.sklearn.get("liverguard_stage:latest")
            self.stage_objs = stage_ref.custom_objects
            self.has_stage = True
            print(f"✅ Stage model objects loaded: {stage_ref.tag}")
        except Exception as e:
            print(f"⚠️ Stage objects load failed: {e}")

        # 3. Relapse Custom Objects
        self.has_relapse = False
        try:
            relapse_ref = bentoml.sklearn.get("liverguard_relapse:latest")
            self.relapse_objs = relapse_ref.custom_objects
            self.has_relapse = True
            print(f"✅ Relapse model objects loaded: {relapse_ref.tag}")
        except Exception as e:
            print(f"⚠️ Relapse objects load failed: {e}")

        # 4. Survival Custom Objects & Model (Picklable models are not runners by default)
        self.has_survival = False
        try:
            self.survival_ref = bentoml.picklable_model.get("liverguard_survival:latest")
            self.survival_objs = self.survival_ref.custom_objects
            self.has_survival = True
            print(f"✅ Survival model objects loaded: {self.survival_ref.tag}")
        except Exception as e:
            print(f"⚠️ Survival objects load failed: {e}")

    # ============================================================
    # 입력 검증
    # ============================================================

    def validate_input(
        self,
        clinical: List,
        ct: List,
        mrna: Optional[List] = None,
        require_mrna: bool = False
    ) -> Optional[str]:
        if clinical is None or len(clinical) != 11:
            return f"clinical must have 11 features, got {len(clinical) if clinical is not None else 0}"
        if ct is None or len(ct) != 512:
            return f"ct_features must be 512-dimensional, got {len(ct) if ct is not None else 0}"
        if require_mrna and (mrna is None or len(mrna) != 20):
            return f"mrna must have 20 pathways, got {len(mrna) if mrna is not None else 0}"
        return None

    # ============================================================
    # 전처리 함수 (Instance methods accessing self.*_objs)
    # ============================================================

    def preprocess_stage(self, clinical, ct):
        clinical = np.array(clinical).reshape(1, -1)
        ct = np.array(ct).reshape(1, -1)
    
        # Clinical: feature selection → impute → scale
        clinical = clinical[:, self.stage_objs["clinical_idx"]]
        clinical = self.stage_objs["scaler_clin"].transform(
            self.stage_objs["imputer_clin"].transform(clinical)
        )
    
        # CT: impute → scale → PCA
        ct = self.stage_objs["pca"].transform(
                self.stage_objs["scaler_ct"].transform(
                    self.stage_objs["imputer_ct"].transform(ct)
                )
            )
    
        return np.hstack([clinical, ct])

    def preprocess_relapse(self, clinical, mrna, ct):
        """Task 2 전처리 (mRNA 필수)"""
        clinical = np.array(clinical).reshape(1, -1)
        mrna = np.array(mrna).reshape(1, -1)
        ct = np.array(ct).reshape(1, -1)
    
        # Clinical: feature selection → impute → scale
        clinical = clinical[:, self.relapse_objs["clinical_idx"]]
        clinical = self.relapse_objs["scaler_clin"].transform(
            self.relapse_objs["imputer_clin"].transform(clinical)
        )
        
        # mRNA: impute → scale
        mrna = self.relapse_objs["scaler_mrna"].transform(
            self.relapse_objs["imputer_mrna"].transform(mrna)
        )
        
        # CT: impute → scale → PCA
        ct = self.relapse_objs["pca"].transform(
            self.relapse_objs["scaler_ct"].transform(
                self.relapse_objs["imputer_ct"].transform(ct)
            )
        )
        
        return np.hstack([clinical, mrna, ct])

    def preprocess_survival(self, clinical, mrna, ct):
        """Task 3 전처리 (mRNA 필수)"""
        clinical = np.array(clinical).reshape(1, -1)
        mrna = np.array(mrna).reshape(1, -1)
        ct = np.array(ct).reshape(1, -1)
        
        # Clinical: feature selection → impute → scale
        clinical_idx = survival_objs.get("clinical_idx")
        if clinical_idx is None:
            n_clinical = survival_objs.get("n_clinical")
            if isinstance(n_clinical, int) and n_clinical > 0:
                clinical_idx = list(range(n_clinical))
        if clinical_idx is not None:
            clinical = clinical[:, clinical_idx]

        clinical = survival_objs["scaler_clin"].transform(
            survival_objs["imputer_clin"].transform(clinical)
        )
        
        # mRNA
        mrna = self.survival_objs["scaler_mrna"].transform(
            self.survival_objs["imputer_mrna"].transform(mrna)
        )
        
        # CT
        ct = self.survival_objs["pca"].transform(
            self.survival_objs["scaler_ct"].transform(
                self.survival_objs["imputer_ct"].transform(ct)
            )
        )
        
        X = np.hstack([clinical, mrna, ct])
        return pd.DataFrame(X, columns=self.survival_objs["feature_names"])

    # ============================================================
    # Helper 함수
    # ============================================================

    def get_risk_level(self, prob):
        if prob > 0.6:
            return "High"
        elif prob > 0.4:
            return "Medium"
        return "Low"

    def get_risk_group(self, score, cutoffs):
        if score <= cutoffs[0]:
            return "Low"
        elif score <= cutoffs[1]:
            return "Medium"
        return "High"
    
    @staticmethod
    def calculate_percentile(score: float, distribution: list[float]) -> float:
        if not distribution:
            return 0.0
        count = sum(1 for v in distribution if v <= score)
        return round(count / len(distribution) * 100, 1)

    @staticmethod
    def build_survival_curves(cox_model, df_input):
        timeline = []
        if hasattr(cox_model, "baseline_survival_") and cox_model.baseline_survival_ is not None:
            timeline = [float(t) for t in cox_model.baseline_survival_.index.tolist()]
        elif hasattr(cox_model, "baseline_cumulative_hazard_") and cox_model.baseline_cumulative_hazard_ is not None:
            timeline = [float(t) for t in cox_model.baseline_cumulative_hazard_.index.tolist()]
        if not timeline:
            timeline = [float(t) for t in range(1, 366)]

        survival_df = cox_model.predict_survival_function(df_input, times=timeline)
        hazard_df = cox_model.predict_cumulative_hazard(df_input, times=timeline)

        survival_curve = [float(v) for v in survival_df.iloc[:, 0].tolist()]
        hazard_curve = [float(v) for v in hazard_df.iloc[:, 0].tolist()]

        return timeline, survival_curve, hazard_curve

    @staticmethod
    def build_hr_table(cox_model):
        if not hasattr(cox_model, "summary"):
            return []
        summary = cox_model.summary
        features = summary.index.tolist()
        coef_series = summary["coef"] if "coef" in summary.columns else None
        hr_series = summary["exp(coef)"] if "exp(coef)" in summary.columns else None
        p_series = summary["p"] if "p" in summary.columns else None

        hr_table = []
        for idx, feature in enumerate(features):
            coef_val = coef_series.iloc[idx] if coef_series is not None else None
            hr_val = hr_series.iloc[idx] if hr_series is not None else None
            p_val = p_series.iloc[idx] if p_series is not None else None
            hr_table.append({
                "feature": str(feature),
                "coef": _safe_float(coef_val),
                "hazard_ratio": _safe_float(hr_val),
                "p_value": _safe_float(p_val),
            })
        return hr_table

    # ============================================================
    # API Endpoints
    # ============================================================

    @bentoml.api
    async def predict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        통합 AI 예측 (병기 + 재발 + 생존)
        
        Input:
        {
            "clinical": [11개 값],
            "ct_features": [512개 값],
            "mrna": [20개 값],       # 선택, Task2/3용
            "use_mrna": true/false   # 선택, 기본값은 mrna 존재 여부
        }
        """
        payload = data.get("data", data)
        clinical = payload.get("clinical", [])
        ct = payload.get("ct_features", [])
        mrna = payload.get("mrna")
        use_mrna = payload.get("use_mrna", mrna is not None and len(mrna) == 20)

        # 입력 검증
        error = self.validate_input(clinical, ct)
        if error:
            return {"error": error, "status": "validation_failed"}

        result = {
            "prediction_timestamp": datetime.now(KST).isoformat(),
            "input_validation": {
                "clinical_dim": len(clinical),
                "ct_dim": len(ct),
                "mrna_provided": mrna is not None and len(mrna) == 20,
                "use_mrna": use_mrna
            }
        }
        
        # ===== Task 1: Stage (mRNA 사용 안 함) =====
        if self.has_stage:
            X = self.preprocess_stage(clinical, ct)
            proba = (await self.stage_runner.predict_proba.async_run(X))[0]
            pred = int(np.argmax(proba))
            labels = ["Stage I", "Stage II", "Stage III+"]

            result["stage_prediction"] = {
                "predicted_stage": labels[pred],
                "stage_code": pred,
                "confidence": float(np.max(proba).item()),
                "probabilities": {labels[i]: float(proba[i].item()) for i in range(3)},
                "uses_mrna": False,
                "model_version": "v11.6",
                "prediction_timestamp": datetime.now(KST).isoformat()
            }
            
        # ===== Task 2: Relapse (mRNA 필요) =====
        if HAS_RELAPSE:
            if use_mrna and mrna is not None and len(mrna) > 0:
                X = self.preprocess_relapse(clinical, mrna, ct)
                prob = float((await relapse_runner.predict_proba.async_run(X))[0, 1].item())

                result["relapse_prediction"] = {
                    "relapse_probability": prob,
                    "risk_level": self.get_risk_level(prob),
                    "prediction": int(prob >= self.relapse_objs["threshold"]),
                    "uses_mrna": True,
                }
            else:
                result["relapse_prediction"] = {
                    "error": "mRNA required",
                    "uses_mrna": True,
                }
                
        # ===== Task 3: Survival (mRNA 필요) =====
        if HAS_SURVIVAL:
            if use_mrna and mrna is not None and len(mrna) == 20:
                try:
                    df_input = self.preprocess_survival(clinical, mrna, ct)
                    cox_model = bentoml.picklable_model.load_model(survival_ref.tag)
                    risk_score = float(cox_model.predict_partial_hazard(df_input).values[0].item())

                    cutoffs = survival_objs["risk_cutoffs"]
                    distribution = survival_objs.get("risk_score_distribution") or []
                    percentile = self.calculate_percentile(risk_score, distribution) # ← 학습 시 저장

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
            "clinical": [11개 값],
            "ct_features": [512개 값]
        }
        """
        payload = data.get("data", data)
        clinical = payload.get("clinical", [])
        ct = payload.get("ct_features", [])

        error = self.validate_input(clinical, ct)
        if error:
            return {"error": error}

        if not HAS_STAGE:
            return {"error": "Stage model not loaded", "status": "model_not_loaded"}
        
        X = self.preprocess_stage(clinical, ct)
        proba = (await self.stage_runner.predict_proba.async_run(X))[0]
        pred = int(np.argmax(proba))
        labels = ["Stage I", "Stage II", "Stage III+"]

        return {
            "predicted_stage": labels[pred],
            "stage_code": pred,
            "confidence": float(np.max(proba).item()),
            "probabilities": {labels[i]: float(proba[i].item()) for i in range(3)},
            "uses_mrna": False,
            "model_version": "v11.6",
            "prediction_timestamp": datetime.now(KST).isoformat()
        }

    @bentoml.api
    async def predict_relapse(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        재발 예측 전용 (mRNA 필수)

        Input:
        {
            "clinical": [11개 값],
            "ct_features": [512개 값],
            "mrna": [20개 값]
        }
        """
        payload = data.get("data", data)
        clinical = payload.get('clinical', [])
        ct = payload.get('ct_features', [])
        mrna = payload.get('mrna', [])

        error = self.validate_input(clinical, ct, mrna, require_mrna=True)
        if error:
            return {"error": error, "status": "validation_failed"}

        if not self.has_relapse:
            return {"error": "Relapse model not loaded"}

        try:
            X = self.preprocess_relapse(clinical, mrna, ct)
            proba = await relapse_runner.predict_proba.async_run(X)
            prob = float(proba[0, 1].item())
            threshold = relapse_objs['threshold']

            return {
                "relapse_probability": prob,
                "risk_level": self.get_risk_level(prob),
                "prediction": int(prob >= threshold),
                "threshold_used": float(threshold) if isinstance(threshold, (np.floating, np.integer)) else threshold,
                "uses_mrna": True,
                "model_version": "v11.6",
                "prediction_timestamp": datetime.now(KST).isoformat()
            }
        except Exception as e:
            return {"error": str(e)}

    @bentoml.api
    async def predict_survival(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        생존 분석 전용 (mRNA 필수)

        Input:
        {
            "clinical": [11개 값],
            "ct_features": [512개 값],
            "mrna": [20개 값]
        }
        """
        payload = data.get("data", data)
        clinical = payload.get('clinical', [])
        ct = payload.get('ct_features', [])
        mrna = payload.get('mrna', [])

        error = self.validate_input(clinical, ct, mrna, require_mrna=True)
        if error:
            return {"error": error, "status": "validation_failed"}

        if not self.has_survival:
            return {"error": "Survival model not loaded"}

        try:
            df_input = self.preprocess_survival(clinical, mrna, ct)
            cox_model = bentoml.picklable_model.load_model(survival_ref.tag)
            risk_score = float(cox_model.predict_partial_hazard(df_input).values[0].item())

            cutoffs = self.survival_objs['risk_cutoffs']
            risk_group = self.get_risk_group(risk_score, cutoffs)

            # Calculate percentile for better interpretation
            distribution = survival_objs.get("risk_score_distribution") or []
            percentile = self.calculate_percentile(risk_score, distribution)
            timeline, survival_curve, hazard_curve = self.build_survival_curves(cox_model, df_input)
            hr_table = self.build_hr_table(cox_model)

            return {
                "risk_score": risk_score,
                "risk_group": risk_group,
                "risk_percentile": percentile,
                "survival_curve": {
                    "timeline": timeline,
                    "survival": survival_curve
                },
                "hazard_curve": {
                    "timeline": timeline,
                    "hazard": hazard_curve
                },
                "hazard_ratio": hr_table,
                "uses_mrna": True,
                "interpretation": "relative_risk",
                "warning": (
                    "This result represents RELATIVE survival risk"
                    "within the training cohort."
                    "It is NOT an absolute survival probability."
                ),
                "risk_cutoff_method": "percentile_33_66",
                "model_version": "v11.6",
                "prediction_timestamp": datetime.now(KST).isoformat()
            }
        except Exception as e:
            return {"error": str(e)}

    @bentoml.api
    async def predict_survival_detail(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        생존 분석 상세 (곡선 + HR)

        Input:
        {
            "clinical": [11개 값],
            "ct_features": [512개 값],
            "mrna": [20개 값]
        }
        """
        payload = data.get("data", data)
        clinical = payload.get('clinical', [])
        ct = payload.get('ct_features', [])
        mrna = payload.get('mrna', [])

        error = self.validate_input(clinical, ct, mrna, require_mrna=True)
        if error:
            return {"error": error, "status": "validation_failed"}

        if not HAS_SURVIVAL:
            return {"error": "Survival model not loaded"}

        try:
            df_input = self.preprocess_survival(clinical, mrna, ct)
            cox_model = bentoml.picklable_model.load_model(survival_ref.tag)
            risk_score = float(cox_model.predict_partial_hazard(df_input).values[0].item())

            cutoffs = survival_objs['risk_cutoffs']
            risk_group = self.get_risk_group(risk_score, cutoffs)
            distribution = survival_objs.get("risk_score_distribution") or []
            percentile = self.calculate_percentile(risk_score, distribution)

            timeline, survival_curve, hazard_curve = self.build_survival_curves(cox_model, df_input)
            hr_table = self.build_hr_table(cox_model)

            return {
                "risk_score": risk_score,
                "risk_group": risk_group,
                "risk_percentile": percentile,
                "survival_curve": {
                    "timeline": timeline,
                    "survival": survival_curve
                },
                "hazard_curve": {
                    "timeline": timeline,
                    "hazard": hazard_curve
                },
                "hazard_ratio": hr_table,
                "uses_mrna": True,
                "interpretation": "relative_risk",
                "warning": (
                    "This result represents RELATIVE survival risk "
                    "within the training cohort. "
                    "It is NOT an absolute survival probability."
                ),
                "risk_cutoff_method": "percentile_33_66",
                "model_version": "v11.6",
                "prediction_timestamp": datetime.now(KST).isoformat()
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
                "stage": self.has_stage,
                "relapse": self.has_relapse,
                "survival": self.has_survival
            },
            "timestamp": datetime.now(KST).isoformat()
        }

    @bentoml.api
    def check_ddi(self, drug_a: Dict[str, str], drug_b: Dict[str, str]) -> Dict[str, Any]:
        """
        DDI 하이브리드 검사 (기존 타임스탬프 및 메타데이터 규격 준수)
        """
        level, message, detail = self.ddi_engine.check_pair(
            drug_a.get('name_kr'), drug_a.get('name_en'),
            drug_b.get('name_kr'), drug_b.get('name_en')
        )
        
        return {
            "prediction_timestamp": datetime.now().isoformat(),
            "level": level,
            "message": message,
            "detail": detail,
            "status": "success"
        }
