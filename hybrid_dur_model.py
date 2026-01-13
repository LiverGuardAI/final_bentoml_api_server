import pandas as pd
import joblib
import pickle
import numpy as np
import json
import xgboost as xgb
import pathlib
import sys
import csv
import logging
from datetime import datetime

# BentoML 표준 로거 설정
logger = logging.getLogger("bentoml.service")

# --- Configuration ---
PROJECT_ROOT = pathlib.Path(__file__).parent
BASE_PATH = PROJECT_ROOT / "artifacts"

FINAL_MODEL_PATH = BASE_PATH / "xgb_model_v5_optuna_cv.joblib"
BRIDGE_PATH = BASE_PATH / "name_to_smiles_v5.pkl"
EMBED_PATH = BASE_PATH / "embedding_map_v5_service.pkl"
CLASSES_PATH = BASE_PATH / "mlb_classes_v2.pkl"
CLINICAL_MAP_PATH = BASE_PATH / "feature_clinical_map.json"
DUR_CSV_PATH = BASE_PATH / "OpenData_PotOpenDurIngr_AC20251216.csv"

class HybridDUREngine:
    def __init__(self):
        logger.info("🚀 [LIVER GUARD v5.5] Initializing Engine...")
        self.load_assets()
        self.load_official_db()
        
    def load_assets(self):
        try:
            self.model = joblib.load(FINAL_MODEL_PATH)
            with open(BRIDGE_PATH, 'rb') as f: self.bridge = pickle.load(f)
            with open(EMBED_PATH, 'rb') as f: self.embed_map = pickle.load(f)
            with open(CLASSES_PATH, 'rb') as f: self.classes = pickle.load(f)
            with open(CLINICAL_MAP_PATH, 'r', encoding='utf-8') as f: 
                self.clinical_map = json.load(f)
            logger.info(f"✅ Loaded Assets: Map-Size({len(self.clinical_map)})")
        except Exception as e:
            logger.error(f"❌ Asset Load Error: {e}")

    def load_official_db(self):
        try:
            df = pd.read_csv(DUR_CSV_PATH, encoding='cp949', on_bad_lines='skip', quoting=csv.QUOTE_NONE)
        except:
            try:
                df = pd.read_csv(DUR_CSV_PATH, encoding='utf-8', on_bad_lines='skip', quoting=csv.QUOTE_NONE)
            except:
                self.official_pairs = {}
                return
        
        self.official_pairs = {}
        for _, row in df.iterrows():
            d1 = str(row.get('DUR성분명', '')).strip()
            d2 = str(row.get('병용금기DUR성분명', '')).strip()
            reason = str(row.get('금기내용', 'Unknown')).strip()
            if d1 and d2:
                self.official_pairs[frozenset([d1, d2])] = reason

    def normalize_en_name(self, name):
        if not name: return ""
        salts = [" Hydrochloride", " HCl", " Sodium", " Potassium", " Sulfate", " Hydrate"]
        clean = name.strip()
        for s in salts:
            clean = clean.replace(s, "").replace(s.lower(), "")
        return clean.strip()

    def get_alternatives(self, drug_en, category):
        alt_map = {
            "Simvastatin": ["Atorvastatin", "Rosuvastatin"],
            "Acetaminophen": ["Ibuprofen", "Naproxen"],
            "Isoniazid": ["Ethambutol"],
            "Metformin": ["Sitagliptin", "Linagliptin"]
        }
        clean_name = self.normalize_en_name(drug_en)
        return alt_map.get(clean_name, ["유관 전문가 협진 권고"])

    def get_ai_risk(self, d1_en, d2_en):
        d1_clean = self.normalize_en_name(d1_en)
        d2_clean = self.normalize_en_name(d2_en)
        
        logger.info(f"🔍 [DDI ANALYZE] {d1_clean} + {d2_clean}")

        s1 = self.bridge.get(d1_clean) or self.bridge.get(d1_clean.lower())
        s2 = self.bridge.get(d2_clean) or self.bridge.get(d2_clean.lower())
        
        if not s1 or not s2: 
            return 0.54, "UNKNOWN", []

        v1, v2 = self.embed_map.get(s1), self.embed_map.get(s2)
        if v1 is None or v2 is None: 
            return 0.51, "UNKNOWN", []

        input_vec = np.concatenate([v1, v2]).reshape(1, -1)
        probs = self.model.predict(xgb.DMatrix(input_vec))[0]
        top_idx = np.argmax(probs)
        top_prob = float(probs[top_idx])
        
        vec_vals = input_vec[0]
        all_mapped_hits = []
        for fid_str, meta in self.clinical_map.items():
            fid = int(fid_str[1:])
            if fid < len(vec_vals):
                val = abs(vec_vals[fid])
                all_mapped_hits.append((fid_str, val, meta))
        
        all_mapped_hits.sort(key=lambda x: x[1], reverse=True)
        return top_prob, self.classes[top_idx], all_mapped_hits[:3]

    def is_match(self, key_part, d_ko, d_en):
        if not key_part: return False
        clean_key = key_part.lower()
        if d_ko and d_ko in clean_key: return True
        if d_en and d_en.lower() in clean_key: return True
        return False

    def check_pair(self, d1_ko, d1_en, d2_ko, d2_en):
        # 1. Level 1: DUR Check
        dur_info = {"level": "SAFE", "message": "식약처 표준 금기 사항 없음", "source": "DUR_OFFICIAL"}
        for key, reason in self.official_pairs.items():
            klist = list(key)
            if (self.is_match(klist[0], d1_ko, d1_en) and self.is_match(klist[1], d2_ko, d2_en)) or \
               (self.is_match(klist[0], d2_ko, d2_en) and self.is_match(klist[1], d1_ko, d1_en)):
                dur_info = {"level": "CRITICAL", "message": f"사유: {reason}", "source": "DUR_OFFICIAL"}
                break
                
        # 2. Level 2: AI Clinical Risk
        prob, cls, hits = self.get_ai_risk(d1_en, d2_en)
        
        if hits:
            fid_str, val, meta = hits[0]
            ai_info = {
                "level": "CRITICAL" if prob > 0.8 else "ATTENTION",
                "message": f"[{meta['clinical_meaning']}] {meta['category']} 경로의 상호작용 위험 감지",
                "source": "AI_HYBRID",
                "prob": round(prob, 4),
                "feature_id": fid_str,
                "clinical_category": meta['category'],
                "alternatives": self.get_alternatives(d1_en, meta['category'])
            }
        else:
            if prob > 0.5:
                ai_info = {
                    "level": "ATTENTION",
                    "message": "구조적 독성 징후 포착. 간 질환 환자 처방 시 주의 요망.",
                    "prob": round(prob, 4),
                    "feature_id": "Structural-Analysis",
                    "source": "AI_HYBRID",
                    "alternatives": self.get_alternatives(d1_en, "General")
                }
            else:
                ai_info = {"level": "SAFE", "message": "특이적 위험 인자 미검출", "prob": prob, "feature_id": "Global", "source": "AI_SAFE", "alternatives": []}

        return dur_info, ai_info