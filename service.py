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
from hybrid_dur_model import HybridDUREngine


@bentoml.service(
    name="liverguard_cdss",
    traffic={"timeout": 60}
)
class LiverGuardService:
    # 1. Runner 선언 (Class attributes for auto-collection)
    stage_runner = bentoml.sklearn.get("liverguard_stage:latest").to_runner()
    relapse_runner = bentoml.sklearn.get("liverguard_relapse:latest").to_runner()

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
        if not clinical or len(clinical) < 5:
            return "clinical must have at least 5 features"
        if not ct or len(ct) != 512:
            return f"ct_features must be 512-dimensional, got {len(ct) if ct else 0}"
        if require_mrna and (not mrna or len(mrna) != 20):
            return f"mrna must have 20 pathways, got {len(mrna) if mrna else 0}"
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
        
        # Clinical: 전체 사용 (Task3는 모든 clinical feature 사용)
        clinical = self.survival_objs["scaler_clin"].transform(
            self.survival_objs["imputer_clin"].transform(clinical)
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
    
    def calculate_percentile(self, score: float, distribution: list[float]) -> float:
        count = sum(1 for v in distribution if v <= score)
        return round(count / len(distribution) * 100, 1)

    # ============================================================
    # API Endpoints
    # ============================================================

    @bentoml.api
    async def predict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        통합 AI 예측 (병기 + 재발 + 생존)
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
        if self.has_stage:
            X = self.preprocess_stage(clinical, ct)
            proba = (await self.stage_runner.predict_proba.async_run(X))[0]
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
        if self.has_relapse:
            if use_mrna and mrna:
                X = self.preprocess_relapse(clinical, mrna, ct)
                prob = float((await self.relapse_runner.predict_proba.async_run(X))[0, 1])

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
        if self.has_survival:
            if use_mrna and mrna and len(mrna) == 20:
                try:
                    df_input = self.preprocess_survival(clinical, mrna, ct)
                    cox_model = self.survival_ref.load()
                    risk_score = float(cox_model.predict_partial_hazard(df_input).values[0])

                    cutoffs = self.survival_objs["risk_cutoffs"]
                    percentile = self.calculate_percentile(risk_score, self.survival_objs["risk_score_distribution"]) 

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
        """
        clinical = data.get("clinical", [])
        ct = data.get("ct_features", [])

        error = self.validate_input(clinical, ct)
        if error:
            return {"error": error}
        
        X = self.preprocess_stage(clinical, ct)
        proba = (await self.stage_runner.predict_proba.async_run(X))[0]
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
        """
        clinical = data.get('clinical', [])
        ct = data.get('ct_features', [])
        mrna = data.get('mrna', [])

        error = self.validate_input(clinical, ct, mrna, require_mrna=True)
        if error:
            return {"error": error, "status": "validation_failed"}

        if not self.has_relapse:
            return {"error": "Relapse model not loaded"}

        try:
            X = self.preprocess_relapse(clinical, mrna, ct)
            proba = await self.relapse_runner.predict_proba.async_run(X)
            prob = float(proba[0, 1])
            threshold = self.relapse_objs['threshold']

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
        """
        clinical = data.get('clinical', [])
        ct = data.get('ct_features', [])
        mrna = data.get('mrna', [])

        error = self.validate_input(clinical, ct, mrna, require_mrna=True)
        if error:
            return {"error": error, "status": "validation_failed"}

        if not self.has_survival:
            return {"error": "Survival model not loaded"}

        try:
            df_input = self.preprocess_survival(clinical, mrna, ct)
            cox_model = self.survival_ref.load()
            risk_score = float(cox_model.predict_partial_hazard(df_input).values[0])

            cutoffs = self.survival_objs['risk_cutoffs']
            risk_group = self.get_risk_group(risk_score, cutoffs)

            # Calculate percentile for better interpretation
            percentile = self.calculate_percentile(risk_score, self.survival_objs.get("risk_score_distribution", []))

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
                "stage": self.has_stage,
                "relapse": self.has_relapse,
                "survival": self.has_survival
            },
            "timestamp": datetime.now().isoformat()
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
