"""
BentoML Client for LiverGuard CDSS
테스트 및 연동용 클라이언트

사용법:
    python client.py --test          # 기본 테스트
    python client.py --health        # 헬스체크 (정상 작동 체크)
    python client.py --stage-only    # 병기 예측만
"""

import argparse
import json
import requests
from typing import Dict, Any, List, Optional

# BentoML 서버 URL
BENTOML_URL = "http://localhost:3001"


class LiverGuardClient:
    """LiverGuard CDSS BentoML 클라이언트"""
    
    def __init__(self, base_url: str = BENTOML_URL):
        self.base_url = base_url.rstrip('/')
    
    def health_check(self) -> Dict[str, Any]:
        """헬스체크"""
        response = requests.get(f"{self.base_url}/health", timeout=5)
        response.raise_for_status()
        return response.json()
    
    def predict_all(
        self,
        clinical: List[float],
        ct_features: List[float],
        mrna: Optional[List[float]] = None,
        use_mrna: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        통합 예측 (병기 + 재발 + 생존)
        
        Args:
            clinical: 9개 임상 변수 [AGE, SEX, GRADE, VASCULAR_INVASION, ISHAK, AFP, ALBUMIN, BILIRUBIN, PLATELET]
            ct_features: 512차원 CT 특징 벡터
            mrna: 20개 pathway scores (선택)
            use_mrna: mRNA 사용 여부 (기본: mrna 존재 시 True)
        """
        payload = {
            "clinical": clinical,
            "ct_features": ct_features,
        }
        
        if mrna is not None and len(mrna) == 20:
            payload["mrna"] = mrna
            payload["use_mrna"] = use_mrna if use_mrna is not None else True
        else:
            payload["use_mrna"] = False
        
        response = requests.post(
            f"{self.base_url}/predict",
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    
    def predict_stage(
        self,
        clinical: List[float],
        ct_features: List[float]
    ) -> Dict[str, Any]:
        """
        병기 예측만 (mRNA 불필요)
        """
        response = requests.post(
            f"{self.base_url}/predict_stage",
            json={"clinical": clinical, "ct_features": ct_features},
            timeout=30
        )
        response.raise_for_status()
        return response.json()


def generate_dummy_data():
    """테스트용 더미 데이터 생성"""
    import random
    
    # Clinical: [AGE, SEX, GRADE, VASCULAR_INVASION, ISHAK, AFP, ALBUMIN, BILIRUBIN, PLATELET]
    clinical = [
        65,      # AGE
        1,       # SEX (1=Male)
        2,       # GRADE (G2)
        1,       # VASCULAR_INVASION (Micro)
        2,       # ISHAK (Fibrous Speta)
        150.5,   # AFP
        3.8,     # ALBUMIN
        1.2,     # BILIRUBIN
        180.0,   # PLATELET
    ]
    
    # CT features (512-dim, normalized)
    ct_features = [random.gauss(0, 1) for _ in range(512)]
    
    # mRNA (20 pathways)
    mrna = [random.gauss(0, 1) for _ in range(20)]
    
    return clinical, ct_features, mrna


def main():
    parser = argparse.ArgumentParser(description="LiverGuard CDSS Client")
    parser.add_argument("--url", default=BENTOML_URL, help="BentoML server URL")
    parser.add_argument("--health", action="store_true", help="Health check only")
    parser.add_argument("--test", action="store_true", help="Run test prediction")
    parser.add_argument("--stage-only", action="store_true", help="Stage prediction only")
    parser.add_argument("--no-mrna", action="store_true", help="Test without mRNA")
    args = parser.parse_args()
    
    client = LiverGuardClient(args.url)
    
    # 헬스체크
    if args.health:
        print("🔍 Health Check...")
        try:
            result = client.health_check()
            print(json.dumps(result, indent=2))
            print("✅ Server is healthy!")
        except Exception as e:
            print(f"❌ Health check failed: {e}")
        return
    
    # 테스트 예측
    if args.test or args.stage_only:
        print("🧪 Generating dummy data...")
        clinical, ct_features, mrna = generate_dummy_data()
        
        print(f"  Clinical: {clinical}")
        print(f"  CT features: [{ct_features[0]:.4f}, {ct_features[1]:.4f}, ... ({len(ct_features)} dims)]")
        print(f"  mRNA: [{mrna[0]:.4f}, {mrna[1]:.4f}, ... ({len(mrna)} pathways)]")
        print()
        
        if args.stage_only:
            print("📊 Running Stage Prediction (mRNA not used)...")
            try:
                result = client.predict_stage(clinical, ct_features)
                print(json.dumps(result, indent=2))
            except Exception as e:
                print(f"❌ Prediction failed: {e}")
        else:
            print("🔬 Running Full Prediction...")
            try:
                use_mrna = not args.no_mrna
                result = client.predict_all(
                    clinical, 
                    ct_features, 
                    mrna if use_mrna else None,
                    use_mrna
                )
                print(json.dumps(result, indent=2, ensure_ascii=False))
                
                # 결과 요약
                print("\n" + "="*50)
                print("📋 결과 요약")
                print("="*50)
                
                if 'stage_prediction' in result and 'predicted_stage' in result['stage_prediction']:
                    sp = result['stage_prediction']
                    print(f"  병기: {sp['predicted_stage']} (확신도: {sp['confidence']*100:.1f}%)")
                
                if 'relapse_prediction' in result and 'relapse_probability' in result['relapse_prediction']:
                    rp = result['relapse_prediction']
                    print(f"  재발 위험: {rp['relapse_probability']*100:.1f}% ({rp['risk_level']})")
                
                if 'survival_analysis' in result and 'risk_group' in result['survival_analysis']:
                    sa = result['survival_analysis']
                    print(f"  생존 위험군: {sa['risk_group']}")
                    if 'survival_probabilities' in sa:
                        probs = sa['survival_probabilities']
                        print(f"    - 12개월: {probs.get('months_12', 0)*100:.0f}%")
                        print(f"    - 24개월: {probs.get('months_24', 0)*100:.0f}%")
                        print(f"    - 36개월: {probs.get('months_36', 0)*100:.0f}%")
                
            except Exception as e:
                print(f"❌ Prediction failed: {e}")
        return
    
    # 기본: 헬스체크 + 간단한 테스트
    print("🏥 LiverGuard CDSS Client")
    print(f"   Server: {args.url}")
    print()
    
    print("🔍 Checking server health...")
    try:
        health = client.health_check()
        print(f"   Status: {health.get('status', 'unknown')}")
        print(f"   Models: {health.get('models', {})}")
        print("✅ Server is ready!")
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Is BentoML running?")
        print(f"   Try: bentoml serve service:svc --port 3001")
    except Exception as e:
        print(f"❌ Error: {e}")

@bentoml.api
def check_ddi(self, drug_a: Dict[str, str], drug_b: Dict[str, str]) -> Dict[str, Any]:
    # 병렬 분석 실행
    dur_res, ai_res = self.ddi_engine.check_pair(
        drug_a.get('name_kr'), drug_a.get('name_en'),
        drug_b.get('name_kr'), drug_b.get('name_en')
    )
    
    return {
        "prediction_timestamp": datetime.now().isoformat(),
        "status": "success",
        # 리액트가 Case 1, Case 2로 나누어 쓰기 좋게 분리해서 보냄
        "cases": {
            "standard_dur": dur_res,
            "ai_personalized": ai_res
        }
    }

if __name__ == "__main__":
    main()
