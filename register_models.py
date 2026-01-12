"""
BentoML Model Store 등록 스크립트
LiverGuard CDSS

사용법:
    cd bentoml_service
    python register_models.py
    
    # 등록 확인
    bentoml models list
"""

import joblib
from pathlib import Path

# BentoML import
try:
    import bentoml
    from bentoml.exceptions import NotFound
except ImportError:
    print("Error: bentoml not installed. Run: pip install bentoml")
    exit(1)


def register_models(artifacts_dir: str = "./artifacts"):
    """ 모델들을 BentoML Model Store에 등록"""
    
    artifacts_path = Path(artifacts_dir)
    
    if not artifacts_path.exists():
        print(f"Error: artifacts directory not found: {artifacts_path}")
        return False
    
    print("=" * 60)
    print("LiverGuard CDSS - BentoML Model Registration")
    print("=" * 60)
    
    success_count = 0
    
    # ===== Task 1: Stage Prediction (XGBoost/sklearn) =====
    task1_path = artifacts_path / "task1_model.joblib"
    if task1_path.exists():
        try:
            task1 = joblib.load(task1_path)
            
            saved = bentoml.sklearn.save_model(
                "liverguard_stage",
                task1['model'],
                signatures={"predict": {"batchable": True}, "predict_proba": {"batchable": True}},
                custom_objects={
                    "imputer_clin": task1['imputer_clin'],
                    "scaler_clin": task1['scaler_clin'],
                    "imputer_ct": task1['imputer_ct'],
                    "scaler_ct": task1['scaler_ct'],
                    "pca": task1['pca'],
                    "clinical_idx": task1['clinical_idx'],
                    "clinical_cols": task1['clinical_cols'],
                    "n_clinical": task1['n_clinical'],
                    "n_ct_pca": task1['n_ct_pca'],
                    "uses_mrna": task1['uses_mrna'],
                },
                metadata={
                    "task": "stage_prediction",
                    "description": "HCC Stage Prediction (I/II/III+)",
                    "uses_mrna": False,
                    "input_dims": {"clinical": task1['n_clinical'], "ct_pca": task1['n_ct_pca']}
                }
            )
            print(f"✅ Task 1 (Stage): {saved.tag}")
            success_count += 1
        except Exception as e:
            print(f"❌ Task 1 failed: {e}")
    else:
        print(f"⚠️ Task 1 model not found: {task1_path}")
    
    # ===== Task 2: Relapse Prediction (RandomForest) =====
    task2_path = artifacts_path / "task2_model.joblib"
    if task2_path.exists():
        try:
            task2 = joblib.load(task2_path)
            
            saved = bentoml.sklearn.save_model(
                "liverguard_relapse",
                task2['model'],
                signatures={"predict": {"batchable": True}, "predict_proba": {"batchable": True}},
                custom_objects={
                    "imputer_clin": task2['imputer_clin'],
                    "scaler_clin": task2['scaler_clin'],
                    "imputer_mrna": task2['imputer_mrna'],
                    "scaler_mrna": task2['scaler_mrna'],
                    "imputer_ct": task2['imputer_ct'],
                    "scaler_ct": task2['scaler_ct'],
                    "pca": task2['pca'],
                    "clinical_idx": task2['clinical_idx'],
                    "clinical_cols": task2['clinical_cols'],
                    "mrna_cols": task2['mrna_cols'],
                    "n_clinical": task2['n_clinical'],
                    "n_mrna": task2['n_mrna'],
                    "n_ct_pca": task2['n_ct_pca'],
                    "threshold": task2['threshold'],
                    "uses_mrna": task2['uses_mrna'],
                },
                metadata={
                    "task": "relapse_prediction",
                    "description": "Early Relapse Prediction (24 months)",
                    "uses_mrna": True,
                    "threshold": task2['threshold'],
                    "input_dims": {"clinical": task2['n_clinical'], "mrna": task2['n_mrna'], "ct_pca": task2['n_ct_pca']}
                }
            )
            print(f"✅ Task 2 (Relapse): {saved.tag}")
            success_count += 1
        except Exception as e:
            print(f"❌ Task 2 failed: {e}")
    else:
        print(f"⚠️ Task 2 model not found: {task2_path}")
    
    # ===== Task 3: Survival Analysis (CoxPH - lifelines) =====
    task3_path = artifacts_path / "task3_model.joblib"
    if task3_path.exists():
        try:
            task3 = joblib.load(task3_path)
            
            # CoxPHFitter는 picklable_model 사용
            saved = bentoml.picklable_model.save_model(
                "liverguard_survival",
                task3['model'],
                signatures={"predict_partial_hazard": {"batchable": False}},
                custom_objects={
                    "imputer_clin": task3['imputer_clin'],
                    "scaler_clin": task3['scaler_clin'],
                    "imputer_mrna": task3['imputer_mrna'],
                    "scaler_mrna": task3['scaler_mrna'],
                    "imputer_ct": task3['imputer_ct'],
                    "scaler_ct": task3['scaler_ct'],
                    "pca": task3['pca'],
                    "clinical_cols": task3['clinical_cols'],
                    "mrna_cols": task3['mrna_cols'],
                    "n_clinical": task3['n_clinical'],
                    "n_mrna": task3['n_mrna'],
                    "n_ct_pca": task3['n_ct_pca'],
                    "risk_cutoffs": task3['risk_cutoffs'],
                    "feature_names": task3['feature_names'],
                    "uses_mrna": task3['uses_mrna'],
                },
                metadata={
                    "task": "survival_analysis",
                    "description": "Overall Survival Risk Prediction (Cox PH)",
                    "uses_mrna": True,
                    "risk_cutoff_method": "percentile_33_66",
                    "note": "Relative risk within cohort",
                    "input_dims": {"clinical": task3['n_clinical'], "mrna": task3['n_mrna'], "ct_pca": task3['n_ct_pca']}
                }
            )
            print(f"✅ Task 3 (Survival): {saved.tag}")
            success_count += 1
        except Exception as e:
            print(f"❌ Task 3 failed: {e}")
    else:
        print(f"⚠️ Task 3 model not found: {task3_path}")
    # ===== Task 4: DDI Hybrid Engine (XGBoost) [NEW] =====
    ddi_model_path = artifacts_path / "xgb_model_v5_optuna_cv.joblib"
    if ddi_model_path.exists():
        try:
            # XGBoost 전용 저장 방식 사용
            saved = bentoml.xgboost.save_model(
                "ddi_v5_model",
                joblib.load(ddi_model_path),
                labels={"owner": "user", "version": "v5.5"},
                metadata={
                    "description": "Hybrid DDI Engine with MFDS DUR Filter",
                    "task": "ddi_prediction"
                }
            )
            print(f"✅ Task 4 (DDI): {saved.tag}")
            success_count += 1
        except Exception as e:
            print(f"❌ Task 4 (DDI) failed: {e}")
    else:
        print(f"⚠️ Task 4 model not found: {ddi_model_path}")
    
    print()
    print("=" * 60)
    print(f"Registration Complete: {success_count}/4 models")
    print("=" * 60)
    print()
    print("Next steps:")
    print("  1. Verify: bentoml models list")
    print("  2. Start service: bentoml serve service:svc --reload --port 3001")
    print("  3. Test: curl http://localhost:3001/health")
    
    
    return success_count == 4


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Register models to BentoML Store")
    parser.add_argument("--artifacts-dir", type=str, default="./artifacts",
                       help="Path to artifacts directory")
    args = parser.parse_args()
    
    register_models(args.artifacts_dir)
