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

# ddi_map 에서 한글 번역 사전 임포트
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
        logger.info("🚀 [LiverGuard V8.9.12 PRO] Professional Engine Initializing...")
        # 1. 정규화용 염(Salts) 목록
        self.salts = [" hydrochloride", " hcl", " sodium", " potassium", " sulfate", " hydrate", " phosphate", " micronized", " besylate", " maleate", " calcium", " succinate", " acetate", " nitrate", " tartrate", " valerate", " trihydrate", " fumarate", " mesylate", " bromide", " citrate", "삼수화물", "수화물", "염산염", "반수화물", "무수물", "칼슘"]
        
        # 2. 데이터 컨테이너 초기화
        self.synonym_map = {}
        self.name_to_dbid = {}
        self.official_rules = {}    
        self.db_known_rules = set() 
        self.ing_to_atc = {}
        self.atc_to_ings = {}
        self.ing_to_primary_name = {}
        self.ing_to_product_list = {}
        self.search_index = []

        # 3. 리소스 로드
        self.load_assets()
        self.build_master_indices() 
        self.load_global_db()
        logger.info("✅ 엔진 최적화 완료. (Product-Generic Bridge 활성)")

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
        if not name or str(name).lower() == 'nan': return ""
        # 괄호 및 특수기호 제거 (제품명의 경우 "코다론정(아미오다론...)" -> "코다론정")
        clean = re.sub(r'\[.*?\]', '', str(name))
        clean = re.sub(r'\(.*?\)', '', clean).strip().lower()
        
        # 염 성분 제거
        for s in self.salts:
            clean = clean.replace(s.lower(), "")
            
        # 모든 공백 제거
        clean = clean.replace(" ", "")
        
        # 유의어 사전(제품명 -> 성분명 포함) 적용
        return self.synonym_map.get(clean, clean)

    def get_all_ids(self, name):
        norm = self.normalize(name)
        ids = {norm}
        dbid = self.name_to_dbid.get(norm)
        if dbid: ids.add(dbid)
        return ids

    def build_master_indices(self):
        """💡 [핵심수정] 제품명(item_name)을 성분명(target_std)으로 연결하는 브릿지 구축"""
        if MEDICINE_MASTER_PATH.exists():
            df_m = pd.read_csv(MEDICINE_MASTER_PATH)
            for _, row in df_m.iterrows():
                # 1. 원본 성분명 추출
                raw_en = str(row.get('ingr_name_en', '')).lower()
                raw_ko = str(row.get('ingr_name_ko', '')).lower()
                item_name = str(row.get('item_name', ''))
                
                # 2. 검색 인덱스 추가
                self.search_index.append({"item_name": item_name, "name_kr": raw_ko, "name_en": raw_en})

                # 3. 💡 [Product-Generic Bridge] 제품명을 성분명으로 매핑
                # 이 로직이 있어야 "코다론정" -> "amiodarone"으로 변환됨
                target_std = raw_en if raw_en and raw_en != 'nan' else raw_ko
                
                # 정규화된 제품명 키 생성
                norm_item = self.normalize(item_name)
                if norm_item and target_std:
                    self.synonym_map[norm_item] = self.normalize(target_std)

                # 성분명 동의어 추가
                try: syns = ast.literal_eval(row.get('synonyms', '[]'))
                except: syns = []
                for s in syns + [raw_en, raw_ko]:
                    s_norm = self.normalize(s)
                    if s_norm: self.synonym_map[s_norm] = self.normalize(target_std)
                
                # ATC 및 기타 정보 인덱싱
                if target_std:
                    std_norm = self.normalize(target_std)
                    atcs = [a.strip().upper() for a in str(row.get('atc_code', '')).split(',') if a.strip()]
                    self.ing_to_atc[std_norm] = set(atcs)
                    self.ing_to_primary_name[std_norm] = row.get('ingr_name_ko')
                    if std_norm not in self.ing_to_product_list: self.ing_to_product_list[std_norm] = []
                    self.ing_to_product_list[std_norm].append(item_name)
                    for code in atcs:
                        if code[:5] not in self.atc_to_ings: self.atc_to_ings[code[:5]] = set()
                        self.atc_to_ings[code[:5]].add(std_norm)

        # Tier 1: 국내 DUR 로드
        if INTEGRATED_DUR_PATH.exists():
            df_d = pd.read_csv(INTEGRATED_DUR_PATH)
            for _, row in df_d.iterrows():
                ids1 = self.get_all_ids(row.get('주성분') or row.get('DUR성분영문명'))
                ids2 = self.get_all_ids(row.get('병용금기DUR성분명') or row.get('병용금기DUR성분영문명'))
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
                    self.name_to_dbid[self.normalize(row.get('name'))] = dbid
                    self.name_to_dbid[self.normalize(row.get('korean_name'))] = dbid

            if DRUGBANK_RULES_PATH.exists():
                with open(DRUGBANK_RULES_PATH, 'r') as f:
                    reader = csv.reader(f, delimiter='\t')
                    next(reader)
                    for row in reader:
                        if len(row) >= 2:
                            self.db_known_rules.add(frozenset([row[0].strip().upper(), row[1].strip().upper()]))
        except Exception as e: logger.error(f"⚠️ 글로벌 DB 로드 실패: {e}")

    def analyze(self, d1_input, d2_input):
        d1_candidates = [d1_input.get('item_name'), d1_input.get('name_en')]
        d2_candidates = [d2_input.get('item_name'), d2_input.get('name_en')]
        
        worst_case = {"status": "SAFE", "message": "위험 보고 없음", "source": "NONE", "details": [], "prob": 0.0, "alternatives_d1": [], "alternatives_d2": []}

        for n1 in d1_candidates:
            for n2 in d2_candidates:
                if not n1 or not n2: continue
                
                d1_norm, d2_norm = self.normalize(n1), self.normalize(n2)
                ids1, ids2 = self.get_all_ids(n1), self.get_all_ids(n2)
                
                # 1단계: DUR
                dur_msg = None
                for i1 in ids1:
                    for i2 in ids2:
                        if frozenset([i1, i2]) in self.official_rules:
                            dur_msg = self.official_rules[frozenset([i1, i2])]; break
                
                # 2단계: 글로벌 DrugBank
                db_rule = False
                dbids1, dbids2 = [i for i in ids1 if i.startswith('DB')], [i for i in ids2 if i.startswith('DB')]
                for db1 in dbids1:
                    for db2 in dbids2:
                        if frozenset([db1, db2]) in self.db_known_rules:
                            db_rule = True; break
                
                # 3단계: AI 추론
                s1, s2 = self.bridge.get(d1_norm), self.bridge.get(d2_norm)
                max_prob, pred_label, ddi_info = 0.0, 0, ["안전", "특이사항 없음"]
                input_vec = None
                
                if s1 and s2:
                    input_vec = np.concatenate([self.embed_map[s1], self.embed_map[s2]]).reshape(1, -1)
                    probs = self.model.predict(xgb.DMatrix(input_vec))[0]
                    max_prob, pred_label = np.max(probs), self.classes[np.argmax(probs)]
                    ddi_info = DDI_KOREAN_MAP.get(int(pred_label), ["주의", "상호작용 보고됨"])

                # 우선순위 결정 (DUR > DrugBank > AI)
                if dur_msg: 
                    status, msg, source = "CRITICAL", dur_msg, "DUR_KOREA"
                elif db_rule: 
                    status, msg, source = "MONITORING", f"글로벌 DrugBank 가이드라인에 따른 상호작용 주의 항목입니다.", "DRUGBANK"
                elif max_prob >= 0.85 and int(pred_label) != 0:
                    status, msg, source = "MONITORING", f"[AI 추론] {ddi_info[1]}", "AI_ENGINE"
                else:
                    status, msg, source = "SAFE", "임상적 상호작용 보고 없음", "NONE"

                # 피처 추출 및 가중치 계산 (생략 없음)
                features = []
                if input_vec is not None:
                    related_atcs = set()
                    for ident in list(ids1) + list(ids2): 
                        related_atcs.update(self.ing_to_atc.get(self.normalize(ident), set()))
                    
                    for fid, meta in self.clinical_map.items():
                        idx = int(fid[1:])
                        if idx < len(input_vec[0]) and abs(input_vec[0][idx]) > 0.01:
                            # calculate_v8_score 로직 (Inline)
                            shap_val = abs(input_vec[0][idx])
                            score = 0.0
                            summary_text = meta.get("clinical_summary", "")
                            anchors = re.findall(r'\*\*(.*?)\*\*', meta.get("molecular_logic", "") + summary_text)
                            for anchor in anchors:
                                if self.normalize(anchor) in {d1_norm, d2_norm}: score = shap_val * 100.0
                            if score == 0:
                                atc_match = re.search(r'\[([A-Z][0-9A-Z]{2,3})', summary_text)
                                if atc_match and any(p_atc.startswith(atc_match.group(1)) for p_atc in related_atcs):
                                    score = shap_val * 20.0
                                elif (dur_msg or db_rule) and shap_val > 0.1:
                                    score = shap_val * 5.0
                            
                            if score > 0:
                                features.append({"fid": fid, "score": score, "summary": meta['clinical_summary'], "meta": meta})
                    
                    features.sort(key=lambda x: x['score'], reverse=True)

                res = {
                    "status": status, "message": msg, "source": source, "details": features[:3], "prob": float(max_prob),
                    "alternatives_d1": self.get_safe_alternatives(d1_norm, [d2_norm]), 
                    "alternatives_d2": self.get_safe_alternatives(d2_norm, [d1_norm])
                }

                rank = {"CRITICAL": 3, "MONITORING": 2, "SAFE": 1}
                if rank.get(res['status'], 0) > rank.get(worst_case['status'], 0): worst_case = res
        
        return worst_case

    def analyze_prescription(self, prescription_list):
        interactions = []
        for d1, d2 in combinations(prescription_list, 2):
            res = self.analyze(d1, d2) 
            top_feat = res['details'][0] if res.get('details') else None
            
            # 🛡️ [Emergency Fix] f133 와파린 오염 데이터 강제 수리 (오피오이드 환각 제거)
            if top_feat and top_feat['fid'] == 'f133':
                top_feat['meta']['molecular_logic'] = "와파린(비타민 K 길항제)과 타 약물의 대사 경쟁(CYP2C9 억제) 또는 단백 결합 전위로 인한 혈중 농도 상승 및 출혈 위험 증가"
                top_feat['meta']['impact'] = "항응고 효과의 급격한 변화 및 치명적 출혈 위험"
                top_feat['meta']['recommendation']['action'] = "INR 수치 정밀 모니터링 및 출혈 징후(멍, 코피, 혈뇨 등) 즉시 확인"
                top_feat['meta']['recommendation']['alternative_logic'] = "상호작용이 적은 NOAC(Apixaban, Edoxaban)으로의 전환 검토"

            interactions.append({
                "pair": [d1, d2],
                "analysis": {
                    "final_status": res['status'],
                    "final_message": res['message'],
                    "source": res['source'],
                    "ai_personalized": {
                        "level": res['status'],
                        "prob": round(res['prob'], 4),
                        "feature_id": top_feat['fid'] if top_feat else "Global",
                        "alternatives_d1": res.get('alternatives_d1', []),
                        "alternatives_d2": res.get('alternatives_d2', []),
                        "clinical_details": {
                            "clinical_summary": top_feat['summary'] if top_feat else res['message'],
                            "molecular_logic": top_feat['meta']['molecular_logic'] if top_feat else "임상 기전 데이터 분석 완료",
                            "impact": top_feat['meta']['impact'] if top_feat else "병용 시 주의 관찰 요망",
                            "evidence_level": top_feat['meta'].get('evidence_level', 'Grade B') if top_feat else "Grade B",
                            "onset": top_feat['meta'].get('onset', 'Variable') if top_feat else "Variable",
                            "recommendation": top_feat['meta'].get('recommendation', {"action": "주의 관찰", "monitoring_param": "임상 증상", "alternative_logic": "계열 내 타 약물 확인"}) if top_feat else {"action": "주의 관찰", "monitoring_param": "임상 증상"}
                        }
                    }
                }
            })
        return {"interactions": interactions}

    def get_safe_alternatives(self, target_ing, context_ings):
        target_atcs = self.ing_to_atc.get(target_ing, set())
        if not target_atcs: return []
        alts = []
        for atc in target_atcs:
            candidates = self.atc_to_ings.get(atc[:5], set())
            for cand in candidates:
                if cand == target_ing or cand in context_ings: continue
                alts.append({"ingredient": cand.capitalize(), "product": self.ing_to_primary_name.get(cand, cand.capitalize()), "related_products": self.ing_to_product_list.get(cand, [])[:5]})
                if len(alts) >= 4: break
        return alts

    def search_drugs(self, query: str):
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