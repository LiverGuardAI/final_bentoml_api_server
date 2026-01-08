# LiverGuard CDSS - 최종 배포 패키지

## 📦 폴더 구조

```
final_deployment/
├── bentoml_service/           # BentoML AI 서비스
│   ├── artifacts/             # 모델 파일
│   │   ├── task1_model.joblib
│   │   ├── task2_model.joblib
│   │   ├── task3_model.joblib
│   │   ├── config.json
│   │   ├── results_summary.json
│   │   └── summary.json
│   ├── register_models.py     # Model Store 등록
│   ├── service.py             # BentoML 서비스
│   └── requirements.txt
│
├── django_ai_server/          # Django AI API
│   ├── feature_mapping.py
│   ├── serializers.py
│   ├── views.py
│   └── urls.py
│
└── react_frontend/            # React 컴포넌트
    └── prediction/
        ├── FeatureTables.tsx
        └── PredictionResults.tsx
    └── api/
        └── PredictionApi.ts
    └── pages/doctor/
        └── AIResult.tsx

```

---

## 🚀 설치 순서

### Step 1: BentoML 모델 등록

```bash
cd bentoml_service

# 의존성 설치
pip install -r requirements.txt

# Model Store에 등록
python register_models.py

# 등록 확인
bentoml models list
# 결과:
# liverguard_stage:xxxxx
# liverguard_relapse:xxxxx
# liverguard_survival:xxxxx
```

### Step 2: BentoML 서비스 실행

```bash
# 개발 모드
bentoml serve service:svc --reload --port 3001

# 헬스체크
curl http://localhost:3001/health
```

### Step 3: Django 설정

```python
# settings.py
BENTOML_SERVER_URL = 'http://localhost:3001'

INSTALLED_APPS = [
    ...
    'ai_model_server',
]
```

```python
# 프로젝트 urls.py
urlpatterns = [
    ...
    path('api/ai/', include('ai_model_server.urls')),
]
```

```bash
# 마이그레이션
python manage.py makemigrations ai_model_server
python manage.py migrate
```

### Step 4: React 컴포넌트 복사

```bash
# 컴포넌트 복사
cp -r react_components/prediction/* src/components/prediction/

# API 서비스 복사
cp react_components/prediction/predictionApi.ts src/services/
```

```tsx
// App.tsx 또는 라우터에 추가
import PredictionPage from './pages/prediction/PredictionPage';

<Route path="/patients/:patientId/prediction" element={<PredictionPage />} />
```

### Step 5: Vite Proxy 설정 (개발용)

```typescript
// vite.config.ts
export default defineConfig({
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});
```

---

## 🔌 API 엔드포인트

### Feature Vector APIs

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/ai/patients/{id}/radio-features/` | CT 특징 벡터 목록 |
| GET | `/api/ai/patients/{id}/clinical-features/` | 임상 특징 벡터 목록 |
| GET | `/api/ai/patients/{id}/genomic-features/` | 유전체 특징 벡터 목록 |

### Prediction APIs

| Method | Endpoint | 설명 |
|--------|----------|------|
| POST | `/api/ai/predict/all/` | 통합 예측 (병기+재발+생존) |
| POST | `/api/ai/predict/stage/` | 병기 예측만 (mRNA 불필요) |
| POST | `/api/ai/predict/by-ids/` | ID 기반 예측 |

### Analysis Result APIs

| Method | Endpoint | 설명 |
|--------|----------|------|
| POST | `/api/ai/analysis/save/` | 결과 저장 |
| GET | `/api/ai/patients/{id}/analysis-history/` | 분석 이력 |
| GET | `/api/ai/health/` | 헬스체크 |

---

## 📊 모델 성능

| Task | Metric | Value |
|------|--------|-------|
| Stage Prediction | F1 (macro) | 0.376 ± 0.114 |
| Relapse Prediction | AUC | 0.683 ± 0.045 |
| Survival Analysis | C-index | 0.713 (95% CI: 0.596-0.811) |

---

## ⚠️ 중요 사항

### 1. mRNA 사용 여부
- **Task 1 (Stage)**: mRNA 사용 안 함 (수술 전 시나리오)
- **Task 2 (Relapse)**: mRNA 필수
- **Task 3 (Survival)**: mRNA 필수

### 2. Survival 결과 해석
⚠️ **상대적 위험**입니다 (cohort-based estimate)
- 절대 생존 확률이 아님
- 동일 코호트 내 상대적 위험 수준

### 3. 날짜 불일치
- CT, Clinical, Genomic 데이터 수집일이 30일 이상 차이나면 경고 표시
- 서버에서도 검증하여 결과에 warnings 포함

---

## 🧪 테스트

### BentoML 직접 테스트

```bash
curl -X POST http://localhost:3001/predict \
  -H "Content-Type: application/json" \
  -d '{
    "clinical": [65, 1, 2, 1, 2, 100, 3.5, 1.2, 150],
    "ct_features": [0.1, 0.2, ...],  # 512개
    "mrna": [0.5, 0.3, ...],          # 20개
    "use_mrna": true
  }'
```

### Django API 테스트

```bash
curl -X POST http://localhost:8000/api/ai/predict/all/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "clinical_vector": [65, 1, 2, 1, 2, 100, 3.5, 1.2, 150],
    "ct_vector": [...],
    "mrna_vector": [...],
    "use_mrna": true
  }'
```

---

## 📝 요구사항 충족

| 요구사항 | 충족 |
|----------|------|
| BentoML API 연동 | ✅ Model Store + Runner |
| Radio feature 사용 | ✅ CT 512-dim |
| Genomic feature 사용 | ✅ mRNA 20 pathway |
| Genomic data 고려 | ✅ ssGSEA 변환 |
| Lab result 사용 | ✅ Clinical 9개 |

---
