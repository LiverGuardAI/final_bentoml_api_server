"""
LiverGuard CDSS - BentoML API Service (Final)

3개의 AI Task를 제공하는 BentoML 서비스:
- Task 1: 병기 예측 (Stage Prediction)
- Task 2: 조기 재발 예측 (Early Relapse Prediction)  
- Task 3: 생존 분석 (Survival Analysis)

실행:
    bentoml serve service:LiverGuardService --port 3001
"""

import bentoml
import numpy as np
import pandas as pd
import joblib
import json
from pathlib import Path
from typing import Dict, List
import logging
import warnings

warnings.filterwarnings('ignore')
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ARTIFACTS_DIR = Path(__file__).parent / "models" / "artifacts"


@bentoml.service(
    name="liverguard_cdss",
    traffic={"timeout": 300},
    resources={"cpu": "2", "memory": "4Gi"}
)
class LiverGuardService:
    """LiverGuard CDSS BentoML 서비스"""
    
    def __init__(self):
        logger.info("Loading LiverGuard CDSS models...")
        
        # Config 로드
        config_path = ARTIFACTS_DIR / "config.json"
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        else:
            logger.warning("config.json not found, using defaults")
            self.config = {}
        
        # 모델 로드
        try:
            self.task1 = joblib.load(ARTIFACTS_DIR / "task1_model.joblib")
            self.task2 = joblib.load(ARTIFACTS_DIR / "task2_model.joblib")
            self.task3 = joblib.load(ARTIFACTS_DIR / "task3_model.joblib")
            logger.info("All models loaded successfully!")
        except Exception as e:
            logger.error(f"Failed to load models: {e}")
            raise
        
        self.clinical_features = self.config.get('data', {}).get('clinical_features', [])
        self.version = self.config.get('version', '11.3')
    
    @bentoml.api
    def health(self) -> Dict:
        """서비스 상태 확인"""
        return {
            "status": "ok",
            "service": "LiverGuard CDSS",
            "version": self.version,
            "tasks": ["predict_stage", "predict_relapse", "predict_survival"]
        }
    
    @bentoml.api
    def predict_stage(self, clinical: List[float], ct: List[float]) -> Dict:
        """
        Task 1: 병기 예측
        
        Args:
            clinical: Clinical features (11-dim)
            ct: CT features (512-dim)
        
        Returns:
            stage_class: 0=Stage I, 1=Stage II, 2=Stage III+
            probabilities: 각 병기 확률
        """
        try:
            # 입력 검증
            if len(clinical) != 11:
                return {"success": False, "error": f"clinical must have 11 features, got {len(clinical)}"}
            if len(ct) != 512:
                return {"success": False, "error": f"ct must have 512 features, got {len(ct)}"}
            
            clinical_arr = np.array(clinical).reshape(1, -1)
            ct_arr = np.array(ct).reshape(1, -1)
            
            # 전처리 (학습 시 fit된 객체 사용)
            X_clin = self.task1['clin_scaler'].transform(
                self.task1['clin_imputer'].transform(clinical_arr))
            X_ct = self.task1['ct_pca'].transform(
                self.task1['ct_scaler'].transform(
                    self.task1['ct_imputer'].transform(ct_arr)))
            X = np.hstack([X_clin, X_ct])
            
            # 예측
            pred = int(self.task1['model'].predict(X)[0])
            proba = self.task1['model'].predict_proba(X)[0].tolist()
            labels = ['Stage I', 'Stage II', 'Stage III+']
            
            return {
                "success": True,
                "task": "stage_prediction",
                "stage_class": pred,
                "stage_label": labels[pred],
                "probabilities": {labels[i]: round(p, 4) for i, p in enumerate(proba)}
            }
        except Exception as e:
            logger.error(f"predict_stage error: {e}")
            return {"success": False, "error": str(e)}
    
    @bentoml.api
    def predict_relapse(self, clinical: List[float], mrna: List[float], ct: List[float]) -> Dict:
        """
        Task 2: 조기 재발 예측
        
        Args:
            clinical: Clinical features (11-dim)
            mrna: mRNA features (20-dim)
            ct: CT features (512-dim)
        
        Returns:
            probability: 재발 확률
            risk_level: Low/Medium/High
        """
        try:
            # 입력 검증
            if len(clinical) != 11:
                return {"success": False, "error": f"clinical must have 11 features"}
            if len(mrna) != 20:
                return {"success": False, "error": f"mrna must have 20 features"}
            if len(ct) != 512:
                return {"success": False, "error": f"ct must have 512 features"}
            
            clinical_arr = np.array(clinical).reshape(1, -1)
            mrna_arr = np.array(mrna).reshape(1, -1)
            ct_arr = np.array(ct).reshape(1, -1)
            
            # 전처리
            X_clin = self.task2['clin_scaler'].transform(
                self.task2['clin_imputer'].transform(clinical_arr))
            X_mrna = self.task2['mrna_scaler'].transform(
                self.task2['mrna_imputer'].transform(mrna_arr))
            X_ct = self.task2['ct_pca'].transform(
                self.task2['ct_scaler'].transform(
                    self.task2['ct_imputer'].transform(ct_arr)))
            X = np.hstack([X_clin, X_mrna, X_ct])
            
            # 예측
            proba = float(self.task2['model'].predict_proba(X)[0, 1])
            threshold = self.task2['optimal_threshold']
            
            # Risk level 결정
            if proba >= threshold:
                risk_level = "High"
            elif proba >= threshold * 0.7:
                risk_level = "Medium"
            else:
                risk_level = "Low"
            
            return {
                "success": True,
                "task": "relapse_prediction",
                "probability": round(proba, 4),
                "risk_level": risk_level,
                "threshold": round(threshold, 4),
                "prediction": int(proba >= threshold)
            }
        except Exception as e:
            logger.error(f"predict_relapse error: {e}")
            return {"success": False, "error": str(e)}
    
    @bentoml.api
    def predict_survival(self, clinical: List[float], mrna: List[float], ct: List[float]) -> Dict:
        """
        Task 3: 생존 분석
        
        Args:
            clinical: Clinical features (11-dim)
            mrna: mRNA features (20-dim)
            ct: CT features (512-dim)
        
        Returns:
            risk_score: 위험 점수
            risk_group: Low/Medium/High
        """
        try:
            # 입력 검증
            if len(clinical) != 11:
                return {"success": False, "error": f"clinical must have 11 features"}
            if len(mrna) != 20:
                return {"success": False, "error": f"mrna must have 20 features"}
            if len(ct) != 512:
                return {"success": False, "error": f"ct must have 512 features"}
            
            clinical_arr = np.array(clinical).reshape(1, -1)
            mrna_arr = np.array(mrna).reshape(1, -1)
            ct_arr = np.array(ct).reshape(1, -1)
            
            # 전처리
            X_clin = self.task3['clin_scaler'].transform(
                self.task3['clin_imputer'].transform(clinical_arr))
            X_mrna = self.task3['mrna_scaler'].transform(
                self.task3['mrna_imputer'].transform(mrna_arr))
            X_ct = self.task3['ct_pca'].transform(
                self.task3['ct_scaler'].transform(
                    self.task3['ct_imputer'].transform(ct_arr)))
            X = np.hstack([X_clin, X_mrna, X_ct])
            
            # Cox 모델 예측
            n_feat = X.shape[1]
            df = pd.DataFrame(X, columns=[f'f{j}' for j in range(n_feat)])
            risk_score = float(self.task3['model'].predict_partial_hazard(df).values[0])
            
            # Risk group 결정
            cutoffs = self.task3['risk_cutoffs']
            if risk_score <= cutoffs[0]:
                risk_group = "Low"
            elif risk_score <= cutoffs[1]:
                risk_group = "Medium"
            else:
                risk_group = "High"
            
            return {
                "success": True,
                "task": "survival_analysis",
                "risk_score": round(risk_score, 4),
                "risk_group": risk_group,
                "note": "Risk score is relative and intended for stratification only."
            }
        except Exception as e:
            logger.error(f"predict_survival error: {e}")
            return {"success": False, "error": str(e)}
    
    @bentoml.api
    def predict_all(self, clinical: List[float], mrna: List[float], ct: List[float]) -> Dict:
        """전체 예측 (Task 1, 2, 3)"""
        return {
            "task1_stage": self.predict_stage(clinical, ct),
            "task2_relapse": self.predict_relapse(clinical, mrna, ct),
            "task3_survival": self.predict_survival(clinical, mrna, ct)
        }
    
    @bentoml.api
    def get_feature_info(self) -> Dict:
        """Feature 정보 반환"""
        return {
            "clinical_features": self.clinical_features,
            "expected_dims": {"clinical": 11, "mrna": 20, "ct": 512},
            "task1_inputs": ["clinical", "ct"],
            "task2_inputs": ["clinical", "mrna", "ct"],
            "task3_inputs": ["clinical", "mrna", "ct"]
        }
