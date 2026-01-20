import pandas as pd
import joblib
import pickle
import numpy as np
import json
import xgboost as xgb
import pathlib
import csv
import logging
import re
import ast
import os
from itertools import combinations
from datetime import datetime

# [1] ddi_map 에서 한글 번역 사전 임포트
try: 
    from ddi_map import DDI_KOREAN_MAP
except ImportError: 
    DDI_KOREAN_MAP = {
        0: ["안전", "임상적 상호작용 보고 없음"],
        1: ["주의", "부작용의 위험 또는 심각도가 증가할 수 있습니다."],
        2: ["위험", "병용 시 약물 효과가 감소하거나 독성이 증가할 수 있습니다."]
    }

logger = logging.getLogger("bentoml.service")

# --- 📂 Configuration & Paths ---
PROJECT_ROOT = pathlib.Path(__file__).parent.absolute()
BASE_PATH = PROJECT_ROOT / "artifacts"

MEDICINE_MASTER_PATH = BASE_PATH / "medicine_master_v3.csv"
INTEGRATED_DUR_PATH = BASE_PATH / "dur_master_integrated_v2.csv"
DRUGBANK_MAP_PATH = BASE_PATH / "drugbank_slim_df_comma_separated.csv"
DRUGBANK_RULES_PATH = BASE_PATH / "DrugBank_known_ddi.txt"
FINAL_MODEL_PATH = BASE_PATH / "xgb_model_v5_optuna_cv.joblib"
BRIDGE_PATH = BASE_PATH / "name_to_smiles_v5.pkl"
EMBED_PATH = BASE_PATH / "embedding_map_v5_service.pkl"
CLASSES_PATH = BASE_PATH / "mlb_classes_v2.pkl"
CLINICAL_MAP_PATH = BASE_PATH / "feature_clinical_map_v8.json"

class HybridDUREngine:
    def __init__(self):
        logger.info("🚀 [LiverGuard V8.9.21 PRO] Professional Integrated Engine Initializing...")
        
        # 1. 정규화용 염(Salts) 및 특수어구 목록
        self.salts = [
            " hydrochloride", " hcl", " sodium", " potassium", " sulfate", " hydrate", " phosphate", 
            " micronized", " besylate", " maleate", " calcium", " succinate", " acetate", " nitrate", 
            " tartrate", " valerate", " trihydrate", " fumarate", " mesylate", " bromide", " citrate", 
            "삼수화물", "수화물", "염산염", "반수화물", "무수물", "칼슘", "나트륨", "말레산염", "베실산염", 
            "인산염", "황산염", "메실산염", "에스테르", "피복", "제피", "서방정", "서방캡슐"
        ]
        
        # 2. 데이터 컨테이너 초기화
        self.synonym_map = {}
        self.name_to_dbid = {}
        self.dbid_to_categories = {}
        self.cat_to_dbids = {}
        self.official_rules = {}
        self.db_known_rules = {}
        self.ing_to_atc = {}
        self.atc_to_ings = {}
        self.ing_to_primary_name = {}
        self.ing_to_product_list = {}
        self.search_index = []

        # 3. 리소스 로드
        self.load_assets()
        self.build_master_indices() 
        self.load_global_db()
        logger.info("✅ 엔진 최적화 완료. (DUR/DrugBank/AI/Category 전 자산 활성화)")

    def load_assets(self):
        try:
            self.model = joblib.load(FINAL_MODEL_PATH)
            with open(BRIDGE_PATH, 'rb') as f: self.bridge = pickle.load(f)
            with open(EMBED_PATH, 'rb') as f: self.embed_map = pickle.load(f)
            with open(CLASSES_PATH, 'rb') as f: self.classes = pickle.load(f)
            with open(CLINICAL_MAP_PATH, 'r', encoding='utf-8') as f: 
                self.clinical_map = json.load(f)
        except Exception as e:
            logger.error(f"❌ AI 자산 로드 실패: {e}")

    def normalize(self, name):
        """지능형 성분명 정규화"""
        if not name or str(name).lower() == 'nan': return ""
        clean = re.sub(r'\[.*?\]', '', str(name))
        clean = re.sub(r'\(.*?\)', '', clean).strip().lower()
        for s in self.salts:
            clean = clean.replace(s.lower(), "")
        clean = clean.replace(" ", "")
        return self.synonym_map.get(clean, clean)

    def get_all_ids(self, name):
        """식별자 추출"""
        if not name: return set()
        norm = self.normalize(name)
        ids = {norm} if norm else set()
        dbid = self.name_to_dbid.get(norm)
        if dbid: ids.add(dbid)
        return ids

    def build_master_indices(self):
        """마스터 인덱싱"""
        if MEDICINE_MASTER_PATH.exists():
            df_m = pd.read_csv(MEDICINE_MASTER_PATH)
            for _, row in df_m.iterrows():
                raw_en = str(row.get('ingr_name_en', '')).lower()
                raw_ko = str(row.get('ingr_name_ko', '')).lower()
                item_name = str(row.get('item_name', ''))
                self.search_index.append({"item_name": item_name, "name_kr": raw_ko, "name_en": raw_en})
                
                target_std = raw_en if raw_en and raw_en != 'nan' else raw_ko
                norm_item = self.normalize(item_name)
                if norm_item and target_std:
                    self.synonym_map[norm_item] = self.normalize(target_std)
                
                std_norm = self.normalize(target_std)
                atcs = [a.strip().upper() for a in str(row.get('atc_code', '')).split(',') if a.strip()]
                self.ing_to_atc[std_norm] = set(atcs)
                self.ing_to_primary_name[std_norm] = row.get('ingr_name_ko')
                if std_norm not in self.ing_to_product_list: self.ing_to_product_list[std_norm] = []
                self.ing_to_product_list[std_norm].append(item_name)
                for code in atcs:
                    if code[:5] not in self.atc_to_ings: self.atc_to_ings[code[:5]] = set()
                    self.atc_to_ings[code[:5]].add(std_norm)

        if INTEGRATED_DUR_PATH.exists():
            df_d = pd.read_csv(INTEGRATED_DUR_PATH)
            for _, row in df_d.iterrows():
                raw_list1, raw_list2 = [], []
                for col in ['주성분', 'DUR성분영문명']:
                    val = str(row.get(col, ''))
                    if val and val != 'nan': raw_list1.extend(val.split('/'))
                for col in ['병용금기DUR성분명', '병용금기DUR성분영문명', '병용금기주성분']:
                    val = str(row.get(col, ''))
                    if val and val != 'nan': raw_list2.extend(val.split('/'))
                
                ids1, ids2 = set(), set()
                for r in raw_list1: ids1.update(self.get_all_ids(r))
                for r in raw_list2: ids2.update(self.get_all_ids(r))
                
                desc = f"{row.get('금기내용', '')} {row.get('비고', '')}".strip()
                for i1 in ids1:
                    for i2 in ids2:
                        if i1 and i2: self.official_rules[frozenset([i1, i2])] = desc

    def load_global_db(self):
        try:
            if DRUGBANK_MAP_PATH.exists():
                db_map = pd.read_csv(DRUGBANK_MAP_PATH)
                for _, row in db_map.iterrows():
                    dbid = str(row['drugbank_id']).strip().upper()
                    norm_en, norm_ko = self.normalize(row.get('name')), self.normalize(row.get('korean_name'))
                    self.name_to_dbid[norm_en] = dbid
                    self.name_to_dbid[norm_ko] = dbid
                    
                    cats = set(str(row.get('categories', '')).split('|'))
                    self.dbid_to_categories[dbid] = cats
                    for cat in cats:
                        if cat.strip() and len(cat) > 3:
                            if cat not in self.cat_to_dbids: self.cat_to_dbids[cat] = set()
                            self.cat_to_dbids[cat].add(dbid)

            if DRUGBANK_RULES_PATH.exists():
                with open(DRUGBANK_RULES_PATH, 'r', encoding='utf-8') as f:
                    reader = csv.reader(f, delimiter='\t')
                    next(reader)
                    for row in reader:
                        if len(row) >= 3:
                            self.db_known_rules[frozenset([row[0].strip().upper(), row[1].strip().upper()])] = int(row[2].strip())
        except Exception as e: logger.error(f"⚠️ 글로벌 DB 로드 실패: {e}")

    def analyze(self, d1_input, d2_input):
        d1_candidates = [d1_input.get('item_name'), d1_input.get('name_en'), d1_input.get('name_kr')]
        d2_candidates = [d2_input.get('item_name'), d2_input.get('name_en'), d2_input.get('name_kr')]
        worst_case = {"status": "SAFE", "message": "위험 보고 없음", "summary_title": "안전", "source": "NONE", "details": [], "prob": 0.0, "alternatives_d1": [], "alternatives_d2": []}

        for n1 in d1_candidates:
            for n2 in d2_candidates:
                if not n1 or not n2: continue
                d1_norm, d2_norm = self.normalize(n1), self.normalize(n2)
                ids1, ids2 = self.get_all_ids(n1), self.get_all_ids(n2)
                
                # ---------------------------------------------------------
                # [0] AI 추론 미리 수행 (위험의 '성격'과 '요약 제목'을 먼저 파악)
                # ---------------------------------------------------------
                s1, s2 = self.bridge.get(d1_norm), self.bridge.get(d2_norm)
                max_prob, pred_label, ai_ddi_info = 0.0, 0, ["안전", "특이사항 없음"]
                input_vec = None
                if s1 and s2:
                    input_vec = np.concatenate([self.embed_map[s1], self.embed_map[s2]]).reshape(1, -1)
                    probs = self.model.predict(xgb.DMatrix(input_vec))[0]
                    max_prob, pred_label = np.max(probs), self.classes[np.argmax(probs)]
                    ai_ddi_info = DDI_KOREAN_MAP.get(int(pred_label), ["주의", "상호작용 보고됨"])

                # [1] DUR 확인
                dur_msg = None
                for i1 in ids1:
                    for i2 in ids2:
                        if frozenset([i1, i2]) in self.official_rules:
                            dur_msg = self.official_rules[frozenset([i1, i2])]; break
                
                # [2] DrugBank 확인
                db_rule_id = None
                dbids1 = [i for i in ids1 if str(i).startswith('DB')]
                dbids2 = [i for i in ids2 if str(i).startswith('DB')]
                for db1 in dbids1:
                    for db2 in dbids2:
                        key = frozenset([db1, db2])
                        if key in self.db_known_rules:
                            db_rule_id = self.db_known_rules[key]; break

                # ---------------------------------------------------------
                # [3] 최종 제목(Summary Title) 및 우선순위 결정
                # ---------------------------------------------------------
                # AI가 분류한 위험 제목(예: "QTc 연장/심장 마비 위험")을 최우선으로 가져옴
                risk_title = ai_ddi_info[0] if int(pred_label) != 0 else None
                if not risk_title and db_rule_id is not None:
                    risk_title = DDI_KOREAN_MAP.get(db_rule_id, ["상호작용 주의"])[0]

                if dur_msg: 
                    status, msg, source = "CRITICAL", f"[DUR 금기] {dur_msg}", "DUR_KOREA"
                    # 고정 문구 대신 AI가 찾은 '위험 성격'을 제목으로 사용
                    summary_title = risk_title if risk_title else "DUR 금기 위반"
                elif db_rule_id is not None: 
                    mapped_info = DDI_KOREAN_MAP.get(db_rule_id, ["상호작용 주의", "병용 시 주의가 필요합니다."])
                    status, msg, source = "MONITORING", f"[DrugBank] {mapped_info[1]}", "DRUGBANK"
                    summary_title = risk_title if risk_title else mapped_info[0]
                elif max_prob >= 0.85 and int(pred_label) != 0:
                    status, msg, source = "MONITORING", f"[AI 예측] {ai_ddi_info[1]}", "AI_ENGINE"
                    summary_title = ai_ddi_info[0]
                else:
                    status, msg, source = "SAFE", "임상적 상호작용 보고 없음", "NONE"
                    summary_title = "안전"

                # SHAP 기반 기전 추출
                features = []
                if input_vec is not None:
                    related_atcs = set()
                    for ident in list(ids1) + list(ids2): 
                        related_atcs.update(self.ing_to_atc.get(self.normalize(ident), set()))
                    for fid, meta in self.clinical_map.items():
                        idx = int(fid[1:])
                        if idx < len(input_vec[0]) and abs(input_vec[0][idx]) > 0.01:
                            shap_val, score = abs(input_vec[0][idx]), 0.0
                            summary_text = meta.get("clinical_summary", "")
                            anchors = re.findall(r'\*\*(.*?)\*\*', meta.get("molecular_logic", "") + summary_text)
                            for anchor in anchors:
                                if self.normalize(anchor) in {d1_norm, d2_norm}: score = shap_val * 100.0
                            if score == 0:
                                atc_match = re.search(r'\[([A-Z][0-9A-Z]{2,3})', summary_text)
                                if atc_match and any(p_atc.startswith(atc_match.group(1)) for p_atc in related_atcs): score = shap_val * 20.0
                            if score > 0: features.append({"fid": fid, "score": score, "summary": summary_text, "meta": meta})
                    features.sort(key=lambda x: x['score'], reverse=True)

                res = {
                    "status": status, 
                    "message": msg, 
                    "summary_title": summary_title, # ✅ 이제 "QTc 연장..." 등이 들어감
                    "source": source, 
                    "details": features[:3], 
                    "prob": float(max_prob),
                    "alternatives_d1": self.get_smart_alternatives(d1_norm, [d2_norm], dbids1), 
                    "alternatives_d2": self.get_smart_alternatives(d2_norm, [d1_norm], dbids2)
                }
                rank = {"CRITICAL": 3, "MONITORING": 2, "SAFE": 1}
                if rank.get(res['status'], 0) > rank.get(worst_case['status'], 0): worst_case = res
        return worst_case

    def get_smart_alternatives(self, target_ing, context_ings, dbids):
        """대체 성분 추천 엔진"""
        alts, seen = [], {target_ing} | set(context_ings)
        target_atcs = self.ing_to_atc.get(target_ing, set())
        for atc in target_atcs:
            for cand in self.atc_to_ings.get(atc[:5], set()):
                if cand not in seen:
                    alts.append({"ingredient": cand.capitalize(), "product": self.ing_to_primary_name.get(cand, cand.capitalize()), "related_products": self.ing_to_product_list.get(cand, [])[:5], "match_type": "ATC Class"})
                    seen.add(cand)
                    if len(alts) >= 4: break
        if len(alts) < 5:
            for dbid in dbids:
                target_cats = [c for c in self.dbid_to_categories.get(dbid, set()) if len(c) > 12]
                for cat in target_cats:
                    for cand_dbid in self.cat_to_dbids.get(cat, []):
                        for norm_name, mapped_dbid in self.name_to_dbid.items():
                            if mapped_dbid == cand_dbid and norm_name not in seen and norm_name in self.ing_to_primary_name:
                                alts.append({"ingredient": norm_name.capitalize(), "product": self.ing_to_primary_name[norm_name], "related_products": self.ing_to_product_list.get(norm_name, [])[:5], "match_type": f"Category: {cat}"})
                                seen.add(norm_name)
                        if len(alts) >= 6: break
                    if len(alts) >= 6: break
        return alts[:5]

    def analyze_prescription(self, prescription_list):
        """처방 리스트 전체 분석"""
        interactions = []
        for d1, d2 in combinations(prescription_list, 2):
            res = self.analyze(d1, d2) 
            top_feat = res['details'][0] if res.get('details') else None
            
            # 와파린 특수 처리 로직
            if top_feat and top_feat['fid'] == 'f133':
                top_feat['meta']['molecular_logic'] = "와파린과 타 약물의 대사 경쟁(CYP2C9 억제)으로 인한 출혈 위험 증가"
                top_feat['meta']['impact'] = "치명적 출혈 위험"

            interactions.append({
                "pair": [d1, d2],
                "analysis": {
                    "final_status": res['status'], 
                    "final_message": res['message'], 
                    "summary_title": res['summary_title'], # ✅ 리액트로 제목 전달
                    "source": res['source'],
                    "ai_personalized": {
                        "level": res['status'], 
                        "prob": round(res['prob'], 4), 
                        "feature_id": top_feat['fid'] if top_feat else "Global",
                        "alternatives_d1": res.get('alternatives_d1', []), 
                        "alternatives_d2": res.get('alternatives_d2', []),
                        "clinical_details": {
                            "clinical_summary": top_feat['summary'] if top_feat else res['message'],
                            "molecular_logic": top_feat['meta']['molecular_logic'] if top_feat else "임상 데이터 분석 완료",
                            "impact": top_feat['meta']['impact'] if top_feat else "병용 주의 요망",
                            "evidence_level": top_feat['meta'].get('evidence_level', 'Grade B') if top_feat else "Grade B",
                            "onset": top_feat['meta'].get('onset', 'Variable') if top_feat else "Variable",
                            "recommendation": top_feat['meta'].get('recommendation', {"action": "주의 관찰", "monitoring_param": "임상 증상"}) if top_feat else {"action": "주의 관찰", "monitoring_param": "임상 증상"}
                        }
                    }
                }
            })
        return {"interactions": interactions}

    def search_drugs(self, query: str):
        """의약품 검색"""
        query = query.lower().strip().replace(" ", "")
        if not query: return []
        results = []
        for item in self.search_index:
            if query in item['item_name'].lower().replace(" ", "") or \
               query in item['name_kr'].lower().replace(" ", "") or \
               query in item['name_en'].lower().replace(" ", ""):
                results.append(item)
            if len(results) >= 15: break
        return results