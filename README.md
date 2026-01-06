# LiverGuard CDSS v11.3 - Final Release

## 📊 성능 결과

| Task | Metric | 결과 | 설정 |
|------|--------|------|------|
| **Task 1** (병기) | F1 macro | **0.31** | XGBoost + CT PCA 20 + seed=42 |
| **Task 2** (재발) | AUC | **0.65** | RandomForest + CT PCA 20 + seed=7 |
| **Task 3** (생존) | C-index | **0.71** | Lasso Cox + CT PCA 10 |

---

## 📁 폴더 구조

```
liverguard_final_release/
├── liverguard_pipeline/           # 모델 학습용
│   ├── config.json
│   ├── multimodel_pipeline.py
│   └── artifacts/                 # 학습된 모델 ✅
│       ├── task1_model.joblib
│       ├── task2_model.joblib
│       ├── task3_model.joblib
│       └── config.json
│
├── final_bentoml_api_server/      # BentoML 서버 ✅
│   ├── bentofile.yaml
│   ├── service.py
│   ├── client.py
│   └── models/artifacts/          # 모델 파일 포함
│
├── django_integration/            # Django 연동
│   ├── views.py
│   ├── urls.py
│   └── settings_snippet.py
│
└── README.md
```

---

## 🚀 BentoML 서버 실행

### 1. 의존성 설치
```bash
pip install bentoml numpy pandas scikit-learn xgboost lifelines joblib
```

### 2. 서버 실행
```bash
cd final_bentoml_api_server
bentoml serve service:LiverGuardService --port 3001
```

### 3. API 테스트
```bash
curl -X POST http://localhost:3001/health
```

---

## 🔗 Django 연동

### settings.py
```python
BENTOML_SERVER_URL = "http://localhost:3001"
```

### views.py / urls.py
`django_integration/` 폴더의 파일을 `ai_model_server/` 앱으로 복사

---

## 📡 API Endpoints

| Endpoint | Method | 입력 |
|----------|--------|------|
| `/health` | POST | - |
| `/predict_stage` | POST | clinical(11), ct(512) |
| `/predict_relapse` | POST | clinical(11), mrna(20), ct(512) |
| `/predict_survival` | POST | clinical(11), mrna(20), ct(512) |
| `/predict_all` | POST | clinical(11), mrna(20), ct(512) |

---

## 🐳 Docker 배포

```bash
cd final_bentoml_api_server
bentoml build
bentoml containerize liverguard_cdss:latest
docker run -p 3001:3000 liverguard_cdss:latest
```
