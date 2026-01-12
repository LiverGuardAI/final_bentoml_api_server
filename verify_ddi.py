import asyncio
import json
from hybrid_dur_model import HybridDUREngine
from service import LiverGuardService

def test_ddi_verification():
    print("=" * 60)
    print("[Verification] DDI Hybrid Engine Integration Test")
    print("=" * 60)

    # 1. Initialize Service (loads engine)
    print("\n1. Initializing LiverGuardService...")
    try:
        service = LiverGuardService()
        print("✅ Service initialized successfully.")
    except Exception as e:
        print(f"❌ Service initialization failed: {e}")
        return

    # 2. Prepare Test Data
    # Scenario: 삐콤정 (Thiamine) + Itraconazole -> Expected ATTENTION (Level 2)
    # Thiamine is essentially harmless, Itraconazole has many interactions.
    # The AI model often flags this combination due to interaction features.
    drug_a = {"name_kr": "삐콤정", "name_en": "Thiamine"}
    drug_b = {"name_kr": "이트라코나졸", "name_en": "Itraconazole"}

    print(f"\n2. Testing Pair: {drug_a['name_kr']} + {drug_b['name_kr']}")

    # 3. Call endpoint method directly
    try:
        result = service.check_ddi(drug_a, drug_b)
        print("\n3. Result:")
        print(json.dumps(result, indent=2, ensure_ascii=False))

        if result.get('status') == 'success' and 'prediction_timestamp' in result:
            print(f"✅ Response Format Valid: status={result['status']}, timestamp={result['prediction_timestamp']}")
        else:
            print(f"❌ Response Format Invalid: keys={result.keys()}")

        if result['level'] == 'ATTENTION':
            print("\n✅ Verification PASSED: Level is ATTENTION")
        elif result.get('level') == 'CRITICAL':
            print("\n⚠️ Verification NOTE: Level is CRITICAL (Official DB hit?)")
        else:
            print(f"\n❌ Verification FAILED: Level is {result.get('level')} (Expected ATTENTION or CRITICAL)")
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"\n❌ Verification Error: {e}")

if __name__ == "__main__":
    test_ddi_verification()
