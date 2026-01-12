
import pandas as pd
import joblib
import pickle
import numpy as np
import json
import xgboost as xgb
import pathlib
import sys
import csv

# --- Configuration ---
import pathlib
PROJECT_ROOT = pathlib.Path(__file__).parent
BASE_PATH = PROJECT_ROOT / "artifacts"

# 모든 경로를 artifacts 폴더 안으로 강제 지정
FINAL_MODEL_PATH = BASE_PATH / "xgb_model_v5_optuna_cv.joblib"
BRIDGE_PATH = BASE_PATH / "name_to_smiles_v5.pkl"
EMBED_PATH = BASE_PATH / "embedding_map_v5_service.pkl"
CLASSES_PATH = BASE_PATH / "mlb_classes_v2.pkl"
CLINICAL_MAP_PATH = BASE_PATH / "feature_clinical_map.json"
DUR_CSV_PATH = BASE_PATH / "OpenData_PotOpenDurIngr_AC20251216.csv"

class HybridDUREngine:
    def __init__(self):
        print("Initializing Hybrid DUR Engine (Production Mode)...")
        self.load_assets()
        self.load_official_db()
        
    def load_assets(self):
        self.model = joblib.load(FINAL_MODEL_PATH)
        with open(BRIDGE_PATH, 'rb') as f: self.bridge = pickle.load(f)
        with open(EMBED_PATH, 'rb') as f: self.embed_map = pickle.load(f)
        with open(CLASSES_PATH, 'rb') as f: self.classes = pickle.load(f)
        with open(CLINICAL_MAP_PATH, 'r', encoding='utf-8') as f: self.clinical_map = json.load(f)
        
    def load_official_db(self):
        print(f"Loading Official DUR DB from {DUR_CSV_PATH}...")
        try:
            # Disable QUOTING to avoid EOF errors if quotes are unbalanced
            df = pd.read_csv(DUR_CSV_PATH, encoding='cp949', on_bad_lines='skip', quoting=csv.QUOTE_NONE)
        except Exception as e_cp949:
            try:
                df = pd.read_csv(DUR_CSV_PATH, encoding='utf-8', on_bad_lines='skip', quoting=csv.QUOTE_NONE)
            except Exception as e:
                print(f"Error loading DUR CSV: {e}")
                self.official_pairs = {}
                return
            
        self.official_pairs = {}
        
        # Heuristic Column Selection
        cols = df.columns
        col_main = next((c for c in cols if 'DUR성분명' in c and '병용' not in c), None)
        col_mix = next((c for c in cols if '병용금기DUR성분명' in c), None)
        
        if not col_main: col_main = next((c for c in cols if '성분명' in c and '병용' not in c), df.columns[0])
        if not col_mix: col_mix = next((c for c in cols if '병용' in c and '성분명' in c), df.columns[1])
        col_reason = next((c for c in cols if '금기내용' in c), '금기내용')
        
        for _, row in df.iterrows():
            d1 = str(row[col_main]).strip()
            d2 = str(row[col_mix]).strip()
            reason = str(row.get(col_reason, "Unknown Reason")).strip()
            self.official_pairs[frozenset([d1, d2])] = reason
            
        print(f"Indexed {len(self.official_pairs)} Official DUR Pairs.")
        
    def get_ai_risk(self, d1_en, d2_en):
        s1 = self.bridge.get(d1_en) or self.bridge.get(d1_en.lower())
        s2 = self.bridge.get(d2_en) or self.bridge.get(d2_en.lower())
        
        if not s1 or not s2: return 0.0, "SMILES_NOT_FOUND", []
        
        v1 = self.embed_map.get(s1)
        v2 = self.embed_map.get(s2)
        
        if v1 is None or v2 is None: return 0.0, "EMBED_NOT_FOUND", []
        
        input_vec = np.concatenate([v1, v2]).reshape(1, -1)
        dmat = xgb.DMatrix(input_vec)
        probs = self.model.predict(dmat)[0]
        
        top_idx = np.argmax(probs)
        top_prob = float(probs[top_idx])
        top_class = self.classes[top_idx]
        
        vec_vals = input_vec[0]
        hits = []
        for fid_str, meta in self.clinical_map.items():
            fid = int(fid_str[1:])
            val = vec_vals[fid]
            if abs(val) > 0.5:
                 hits.append((fid, val, meta))
        
        hits.sort(key=lambda x: abs(x[1]) * abs(x[2]['correlation']), reverse=True)
        return top_prob, top_class, hits

    def normalize_ko_name(self, name):
        salts = ["염산염", "말레산염", "황산염", "브롬화수소산염", "나트륨", "칼륨", "수화물", "무수물", "타르타르산염"]
        clean = name.strip()
        for s in salts:
            clean = clean.replace(s, "")
        return clean.strip()
        
    def normalize_en_name(self, name):
        salts = [" Hydrochloride", " HCl", " Tartrate", " Mesylate", " Maleate", " Sodium", " Potassium", " Sulfate", " Hydrate", " Anhydrous"]
        clean = name.strip()
        for s in salts:
            clean = clean.replace(s, "")
            clean = clean.replace(s.lower(), "")
        return clean.strip()
        
    def is_match(self, key_part, d_ko, d_en):
        norm_key = self.normalize_ko_name(key_part)
        norm_key = self.normalize_en_name(norm_key)
        
        # Check against Korean Input
        if d_ko:
            norm_ko = self.normalize_ko_name(d_ko)
            # Exact or Substring match (User request for robust salt handling)
            if norm_ko and (norm_ko == norm_key or norm_ko in norm_key or norm_key in norm_ko):
                return True
                
        # Check against English Input
        if d_en:
            norm_en = self.normalize_en_name(d_en)
            if norm_en and (norm_en.lower() == norm_key.lower() or norm_en.lower() in norm_key.lower() or norm_key.lower() in norm_en.lower()):
                return True
                
        return False

    def get_clinical_message(self, category, fid, meaning):
        if category == "QT Prolongation":
            monitor_guide = "심장 기저 질환(부정맥) 및 심전도(ECG)"
        elif category == "PD Synergism":
            monitor_guide = "기저 질환(출혈 소인, 위장 장애 등)"
        elif category == "Renal Competition":
            monitor_guide = "신장 기능(Creatinine 수치)"
        elif category == "Enzyme Inhibition":
            monitor_guide = "약물 농도 변동 및 독성 징후"
        else:
            monitor_guide = "기저 질환 및 이상 반응"
            
        return f"임상 참고: 본 조합은 식약처 금기는 아니나, AI 분석 결과 **{meaning} (f{fid})**이(가) 감지됩니다. 환자의 {monitor_guide}에 따른 모니터링을 권장합니다."

    def check_pair(self, d1_ko, d1_en, d2_ko, d2_en):
        """
        Returns: (Level, Reason/Message, DetailedDetail)
        Level: 'CRITICAL', 'ATTENTION', 'SAFE', 'UNKNOWN'
        """
        # Level 1: Official DB
        for key in self.official_pairs:
            k1, k2 = list(key)
            match_1 = self.is_match(k1, d1_ko, d1_en) and self.is_match(k2, d2_ko, d2_en)
            match_2 = self.is_match(k1, d2_ko, d2_en) and self.is_match(k2, d1_ko, d1_en)
            
            if match_1 or match_2:
                reason = self.official_pairs[key]
                return "CRITICAL", f"사유: {reason}", {"source": "DUR_OFFICIAL", "reason": reason}
        
        # Level 2: AI Risk
        prob, cls, hits = self.get_ai_risk(d1_en, d2_en)
        
        if hits:
            top_hit = hits[0]
            meta = top_hit[2]
            risk_cat = meta['category']
            msg = self.get_clinical_message(risk_cat, top_hit[0], meta['clinical_meaning'])
            return "ATTENTION", msg, {"source": "AI_HYBRID", "prob": prob, "feature": meta, "fid": top_hit[0]}
            
        # Level 3: Safe
        return "SAFE", "특이적 위험 인자 미검출", {"source": "AI_SAFE", "prob": prob}
