# DDI 정보 맵핑 모듈 (ddi_map.py)
# V4 - 2025-11-06 최종 검증 완료
# V3의 점수 오류 (104번) 및 구문 오류 (주석 누락) 수정.
# 이 파일을 CDSS 백엔드의 최종 'Ground Truth'로 사용합니다.

# -----------------------------------------------------------
# 1. DDI KOREAN MAP (ID: [요약, 상세설명])
# - V2에서 검증 완료 (변경 없음)
# -----------------------------------------------------------
DDI_KOREAN_MAP = {
    1: ["심부전/저혈압 위험 증가", "두 약물 병용 시 심부전 및 저혈압의 위험 또는 심각도가 증가할 수 있습니다."],
    2: ["약물 농도 상승 (배설 감소)", "#Drug2가 #Drug1의 배설 속도를 감소시켜 #Drug1의 혈청 농도가 높아질 수 있습니다."],
    3: ["약물 농도 상승 (대사 억제)", "두 약물 병용 시 #Drug1의 대사 작용이 억제되어 혈청 농도가 증가할 수 있습니다."],
    4: ["빈혈/백혈구 감소증 위험", "#Drug2와 #Drug1 병용 시 빈혈 및 심각한 백혈구 감소증의 위험이 증가할 수 있습니다."],
    5: ["방실 차단(AV Block) 위험 증가", "#Drug1이 #Drug2의 방실 차단(AV block) 활동을 증가시킬 수 있습니다."],
    6: ["활성 대사체 농도 증가", "#Drug2와 #Drug1 병용 시 #Drug2의 활성 대사체 혈청 농도가 증가할 수 있습니다."],
    7: ["근육병증/횡문근융해증 위험", "두 약물 병용 시 근육병증 및 횡문근융해증의 위험 또는 심각도가 증가할 수 있습니다."],
    8: ["횡문근융해증/CPK 상승 위험", "#Drug2와 #Drug1 병용 시 횡문근융해증, 미오글로빈뇨 및 크레아틴 키나아제(CPK) 상승 위험이 증가할 수 있습니다."],
    9: ["QTc 연장/심장 마비 위험", "두 약물 병용 시 QTc 연장, Torsade de Pointes, 저칼륨혈증, 저마그네슘혈증, 심장 마비 위험이 증가할 수 있습니다."],
    10: ["약물 치료 효과 증가", "#Drug2와 병용 시 #Drug1의 치료 효과가 증가할 수 있습니다."],
    11: ["심장 독성 감소 (유익)", "#Drug2가 #Drug1의 심장 독성 활동을 감소시킬 수 있습니다."],
    12: ["고칼륨혈증 위험 증가", "#Drug2가 #Drug1의 고칼륨혈증 활동을 증가시킬 수 있습니다."],
    13: ["치료 효과 감소", "#Drug2와 병용 시 #Drug1의 치료 효과가 감소할 수 있습니다."],
    14: ["부종 형성 위험 증가", "#Drug1과 #Drug2 병용 시 부종 형성의 위험 또는 심각도가 증가할 수 있습니다."],
    15: ["진정 작용 감소 (유익)", "#Drug2가 #Drug1의 진정 작용을 감소시킬 수 있습니다."],
    16: ["혈관부종 위험 증가", "#Drug1과 #Drug2 병용 시 혈관부종의 위험 또는 심각도가 증가할 수 있습니다."],
    17: ["약물 농도 상승 (배설 감소)", "#Drug2와 병용 시 #Drug1의 배설이 감소할 수 있습니다."],
    18: ["과민 반응 위험 증가", "#Drug1과 #Drug2 병용 시 #Drug1에 대한 과민 반응 위험이 증가합니다."],
    19: ["체액 저류 위험 증가", "#Drug1이 #Drug2의 체액 저류 활동을 증가시킬 수 있습니다."],
    20: ["약물 농도 감소", "#Drug1과 병용 시 #Drug2의 혈청 농도가 감소할 수 있습니다."],
    21: ["고혈압 위험 증가", "#Drug2가 #Drug1의 고혈압 활동을 증가시킬 수 있습니다."],
    22: ["신장 독성 위험 증가", "#Drug2가 #Drug1의 신장 독성 활동을 증가시킬 수 있습니다."],
    23: ["약물 농도 상승 (단백결합 감소)", "#Drug2와 병용 시 #Drug1의 단백질 결합이 감소할 수 있습니다."],
    24: ["근육병증/횡문근융해증 위험", "두 약물 병용 시 근육병증, 횡문근융해증, 미오글로빈뇨의 위험 또는 심각도가 증가할 수 있습니다."],
    25: ["저혈압/CNS 억제 위험 증가", "#Drug1이 #Drug2의 저혈압 및 중추신경계(CNS) 억제 활동을 증가시킬 수 있습니다."],
    26: ["CNS 억제/고혈압 위험 증가", "#Drug1이 #Drug2의 중추신경계(CNS) 억제 및 고혈압 활동을 증가시킬 수 있습니다."],
    27: ["호흡 억제 위험 증가", "#Drug2가 #Drug1의 호흡 억제 활동을 증가시킬 수 있습니다."],
    28: ["횡문근융해증 위험 증가", "#Drug1과 #Drug2 병용 시 횡문근융해증의 위험 또는 심각도가 증가할 수 있습니다."],
    29: ["진통 효과 증가 (유익)", "#Drug2가 #Drug1의 진통 활동을 증가시킬 수 있습니다."],
    30: ["출혈 위험 증가", "#Drug1과 #Drug2 병용 시 출혈의 위험 또는 심각도가 증가할 수 있습니다."],
    31: ["저나트륨혈증 위험 증가", "#Drug2가 #Drug1의 저나트륨혈증 활동을 증가시킬 수 있습니다."],
    32: ["저혈압/Nitritoid 반응 위험", "#Drug1과 #Drug2 병용 시 저혈압 및 nitritoid 반응의 위험 또는 심각도가 증가할 수 있습니다."],
    33: ["활성 대사체 농도 감소", "#Drug1과 #Drug2 병용 시 #Drug1의 활성 대사체 혈청 농도가 감소할 수 있습니다."],
    34: ["CNS 억제 위험 증가", "#Drug1이 #Drug2의 중추신경계(CNS) 억제 활동을 증가시킬 수 있습니다."],
    35: ["심장 독성 위험 증가", "#Drug2가 #Drug1의 심장 독성 활동을 증가시킬 수 있습니다."],
    36: ["경련 위험 증가", "#Drug1과 #Drug2 병용 시 경련의 위험 또는 심각도가 증가할 수 있습니다."],
    37: ["흥분 작용 증가", "#Drug1이 #Drug2의 흥분 작용(stimulant activities)을 증가시킬 수 있습니다."],
    38: ["진정/졸음 위험 증가", "#Drug1과 #Drug2 병용 시 진정 및 졸음의 위험 또는 심각도가 증가할 수 있습니다."],
    39: ["혈관 수축 효과 증가", "#Drug1이 #Drug2의 혈관 수축 활동을 증가시킬 수 있습니다."],
    40: ["항혈소판 효과 감소", "#Drug2가 #Drug1의 항혈소판 활동을 감소시킬 수 있습니다."],
    41: ["신경근 부작용 위험 증가", "#Drug1과 #Drug2 병용 시 (신경근) 부작용의 위험 또는 심각도가 증가할 수 있습니다."],
    42: ["QTc 연장 위험 증가", "#Drug1이 #Drug2의 QTc 연장 활동을 증가시킬 수 있습니다."],
    43: ["면역 억제 위험 증가", "#Drug2가 #Drug1의 면역 억제 활동을 증가시킬 수 있습니다."],
    44: ["신경근 차단 효과 감소", "#Drug2가 #Drug1의 신경근 차단 활동을 감소시킬 수 있습니다."],
    45: ["항정신병 효과 증가", "#Drug1이 #Drug2의 항정신병 활동을 증가시킬 수 있습니다."],
    46: ["체액 저류 위험 증가", "#Drug2가 #Drug1의 체액 저류 활동을 증가시킬 수 있습니다."],
    47: ["항고혈압 효과 증가", "#Drug2가 #Drug1의 항고혈압 활동을 증가시킬 수 있습니다."],
    48: ["약물 흡수 감소", "#Drug2와 병용 시 #Drug1의 흡수가 감소할 수 있습니다."],
    49: ["기관지 확장 효과 감소", "#Drug2가 #Drug1의 기관지 확장 활동을 감소시킬 수 있습니다."],
    50: ["항응고 효과 감소", "#Drug2가 #Drug1의 항응고 활동을 감소시킬 수 있습니다."],
    51: ["골수 억제 위험 증가", "#Drug2가 #Drug1의 골수 억제 활동을 증가시킬 수 있습니다."],
    52: ["고혈압/혈관 수축 위험 증가", "#Drug2가 #Drug1의 고혈압 및 혈관 수축 활동을 증가시킬 수 있습니다."],
    53: ["QTc 연장 위험 증가", "#Drug1이 #Drug2의 QTc 연장 활동을 증가시킬 수 있습니다."],
    54: ["서맥 위험 증가", "#Drug1과 #Drug2 병용 시 서맥의 위험 또는 심각도가 증가할 수 있습니다."],
    55: ["저혈압/신경근 차단 위험 증가", "#Drug2가 #Drug1의 저혈압 및 신경근 차단 활동을 증가시킬 수 있습니다."],
    56: ["약물 흡수 증가", "#Drug2와 병용 시 #Drug1의 흡수가 증가할 수 있습니다."],
    57: ["기립성 저혈압 위험 증가", "#Drug1과 #Drug2 병용 시 기립성 저혈압의 위험 또는 심각도가 증가할 수 있습니다."],
    58: ["저혈당 위험 증가", "#Drug2가 #Drug1의 저혈당 활동을 증가시킬 수 있습니다."],
    59: ["광과민성 위험 증가", "#Drug2가 #Drug1의 광과민성 활동을 증가시킬 수 있습니다."],
    60: ["항고혈압 효과 감소", "#Drug2가 #Drug1의 항고혈압 활동을 감소시킬 수 있습니다."],
    61: ["변비 위험 증가", "#Drug2가 #Drug1의 변비 유발 활동을 증가시킬 수 있습니다."],
    62: ["기관지 수축 위험 증가", "#Drug1이 #Drug2의 기관지 수축 활동을 증가시킬 수 있습니다."],
    63: ["혈관 확장 효과 증가", "#Drug1이 #Drug2의 혈관 확장 활동을 증가시킬 수 있습니다."],
    64: ["고혈압 위험 증가", "#Drug1과 #Drug2 병용 시 고혈압의 위험 또는 심각도가 증가할 수 있습니다."],
    65: ["저혈압/신독성/고칼륨혈증 위험", "#Drug1과 #Drug2 병용 시 저혈압, 신독성, 고칼륨혈증의 위험 또는 심각도가 증가할 수 있습니다."],
    66: ["이뇨 효과 감소", "#Drug2가 #Drug1의 이뇨 활동을 감소시킬 수 있습니다."],
    67: ["저칼슘혈증 위험 증가", "#Drug1이 #Drug2의 저칼슘혈증 활동을 증가시킬 수 있습니다."],
    68: ["진단 효과 감소", "#Drug2가 #Drug1의 진단 활동을 감소시킬 수 있습니다."],
    69: ["신경 독성 위험 증가", "#Drug2가 #Drug1의 신경 독성 활동을 증가시킬 수 있습니다."],
    70: ["항혈소판 효과 증가", "#Drug2가 #Drug1의 항혈소판 활동을 증가시킬 수 있습니다."],
    71: ["피부 부작용 위험 증가", "#Drug1과 #Drug2 병용 시 (피부) 부작용의 위험 또는 심각도가 증가할 수 있습니다."],
    72: ["신경근 차단 효과 증가", "#Drug2가 #Drug1의 신경근 차단 활동을 증가시킬 수 있습니다."],
    73: ["궤양 유발 위험 증가", "#Drug2가 #Drug1의 궤양 유발 활동을 증가시킬 수 있습니다."],
    74: ["치료 효과 감소", "#Drug2와 병용 시 #Drug1의 치료 효과가 감소할 수 있습니다."],
    75: ["저혈압 위험 증가", "#Drug1과 #Drug2 병용 시 저혈압의 위험 또는 심각도가 증가할 수 있습니다."],
    76: ["흥분 작용 감소", "#Drug2가 #Drug1의 흥분 작용(stimulant activities)을 감소시킬 수 있습니다."],
    77: ["생체이용률 증가", "#Drug2와 병용 시 #Drug1의 생체이용률이 증가할 수 있습니다."],
    78: ["진통 효과 감소", "#Drug2가 #Drug1의 진통 활동을 감소시킬 수 있습니다."],
    79: ["저칼륨혈증 위험 증가", "#Drug1이 #Drug2의 저칼륨혈증 활동을 증가시킬 수 있습니다."],
    80: ["항응고 효과 증가", "#Drug2가 #Drug1의 항응고 활동을 증가시킬 수 있습니다."],
    81: ["혈관 수축 효과 감소", "#Drug2가 #Drug1의 혈관 수축 활동을 감소시킬 수 있습니다."],
    82: ["심각한 백혈구감소증 위험", "#Drug1과 #Drug2 병용 시 심각한 백혈구감소증의 위험 또는 심각도가 증가할 수 있습니다."],
    83: ["이독성/신독성 위험 증가", "#Drug1과 #Drug2 병용 시 이독성 및 신독성의 위험 또는 심각도가 증가할 수 있습니다."],
    84: ["근육병증/횡문근융해증 위험", "#Drug1과 #Drug2 병용 시 근육병증 및 횡문근융해증의 위험 또는 심각도가 증가할 수 있습니다."],
    85: ["항콜린 작용 증가", "#Drug1이 #Drug2의 항콜린 활동을 증가시킬 수 있습니다."],
    86: ["세로토닌 작용 증가", "#Drug1이 #Drug2의 세로토닌 활동을 증가시킬 수 있습니다."],
    87: ["약물 배설 증가", "#Drug2와 병용 시 #Drug1의 배설이 증가할 수 있습니다."],
    88: ["골수 억제 위험 증가", "#Drug2가 #Drug1의 골수 억제 활동을 증가시킬 수 있습니다."],
    89: ["약물 대사 감소", "#Drug2와 병용 시 #Drug1의 대사가 감소할 수 있습니다."],
    90: ["심실 부정맥 위험 증가", "#Drug1과 #Drug2 병용 시 심실 부정맥의 위험 또는 심각도가 증가할 수 있습니다."],
    91: ["신경 흥분 위험 증가", "#Drug1이 #Drug2의 신경 흥분 활동을 증가시킬 수 있습니다."],
    92: ["진정 작용 증가", "#Drug1이 #Drug2의 진정 활동을 증가시킬 수 있습니다."],
    93: ["이독성 위험 증가", "#Drug2가 #Drug1의 이독성 활동을 증가시킬 수 있습니다."],
    94: ["혈관 수축 효과 증가", "#Drug1이 #Drug2의 혈관 수축 활동을 증가시킬 수 있습니다."],
    95: ["저칼륨혈증 위험 증가", "#Drug1이 #Drug2의 저칼륨혈증 활동을 증가시킬 수 있습니다."],
    96: ["부정맥 유발 위험 증가", "#Drug2가 #Drug1의 부정맥 유발 활동을 증가시킬 수 있습니다."],
    97: ["혈전 생성 위험 증가", "#Drug2가 #Drug1의 혈전 생성 활동을 증가시킬 수 있습니다."],
    98: ["간 독성 위험 증가", "#Drug2가 #Drug1의 간 독성 활동을 증가시킬 수 있습니다."],
    99: ["고칼륨혈증 위험 증가", "#Drug1과 #Drug2 병용 시 고칼륨혈증의 위험 또는 심각도가 증가할 수 있습니다."],
    100: ["신경 독성 위험 증가", "#Drug1이 #Drug2의 신경 독성 활동을 증가시킬 수 있습니다."],
    101: ["근육병증 위험 증가", "#Drug2와 #Drug1 병용 시 근육병증의 위험 또는 심각도가 증가할 수 있습니다."],
    102: ["신부전/고칼륨혈증 위험 증가", "#Drug2와 #Drug1 병용 시 신부전 및 고칼륨혈증의 위험 또는 심각도가 증가할 수 있습니다."],
    103: ["빈맥 위험 증가", "#Drug1이 #Drug2의 빈맥 활동을 증가시킬 수 있습니다."],
    104: ["약물 대사 증가", "#Drug1과 병용 시 #Drug2의 대사가 증가할 수 있습니다."],
    105: ["생체이용률 감소", "#Drug1과 병용 시 #Drug2의 생체이용률이 감소할 수 있습니다."],
    106: ["고혈당 위험 증가", "#Drug2가 #Drug1의 고혈당 활동을 증가시킬 수 있습니다."],
    107: ["고칼슘혈증 위험 증가", "#Drug2가 #Drug1의 고칼슘혈증 활동을 증가시킬 수 있습니다."],
    108: ["저혈압 위험 증가", "#Drug1과 #Drug2 병용 시 저혈압의 위험 또는 심각도가 증가할 수 있습니다."],
    109: ["서맥 위험 증가", "#Drug1이 #Drug2의 서맥 활동을 증가시킬 수 있습니다."],
    110: ["심부전 위험 증가", "#Drug2와 #Drug1 병용 시 심부전의 위험 또는 심각도가 증가할 수 있습니다."],
    111: ["저나트륨혈증 위험 증가", "#Drug2가 #Drug1의 저나트륨혈증 활동을 증가시킬 수 있습니다."],
    112: ["세로토닌 작용 증가", "#Drug1이 #Drug2의 세로토닌 활동을 증가시킬 수 있습니다."],
    113: ["부작용 위험 증가 (일반)", "#Drug1과 #Drug2 병용 시 부작용의 위험 또는 심각도가 증가할 수 있습니다."],
}


# -----------------------------------------------------------
# 2. DDI RISK MAP (ID: {severity, score, category})
# - 연구원님이 제공한 RISK_SEVERITY 맵 원본을 그대로 사용 (V4 수정)
# - DDI 104번을 원본(LOW, 30)으로 수정, V3의 주석 오류 수정
# -----------------------------------------------------------
DDI_RISK_MAP = {
    # 🔴 HIGH RISK (80-100) - 생명 위협적
    1: {"severity": "HIGH", "score": 90, "category": "cardiac"},  # 심부전, 저혈압
    7: {"severity": "HIGH", "score": 95, "category": "muscle"},  # 횡문근융해증, 근육병증
    8: {"severity": "HIGH", "score": 95, "category": "muscle"},  # 횡문근융해증, 근육글로불린뇨
    9: {"severity": "HIGH", "score": 100, "category": "cardiac"},  # QTc 연장, torsade de pointes, 심정지
    24: {"severity": "HIGH", "score": 95, "category": "muscle"},  # 근육병증, 횡문근융해증
    27: {"severity": "HIGH", "score": 90, "category": "respiratory"},  # 호흡억제
    28: {"severity": "HIGH", "score": 95, "category": "muscle"},  # 횡문근융해증
    30: {"severity": "HIGH", "score": 85, "category": "bleeding"},  # 출혈 위험
    42: {"severity": "HIGH", "score": 90, "category": "cardiac"},  # QTc 연장
    53: {"severity": "HIGH", "score": 90, "category": "cardiac"},  # QTc 연장 활동
    54: {"severity": "HIGH", "score": 85, "category": "cardiac"},  # 서맥
    83: {"severity": "HIGH", "score": 85, "category": "renal"},  # 이독성, 신독성
    84: {"severity": "HIGH", "score": 90, "category": "muscle"},  # 근육병증 횡문근융해증
    90: {"severity": "HIGH", "score": 85, "category": "cardiac"},  # 심실 부정맥
    101: {"severity": "HIGH", "score": 85, "category": "muscle"},  # 근육병증
    102: {"severity": "HIGH", "score": 90, "category": "renal"},  # 신부전, 고칼륨혈증
    110: {"severity": "HIGH", "score": 90, "category": "cardiac"},  # 심부전
    112: {"severity": "HIGH", "score": 85, "category": "neurological"},  # 세로토닌 증후군

    # 🟠 MODERATE RISK (50-79) - 심각한 부작용, 관리 필요
    4: {"severity": "MODERATE", "score": 75, "category": "hematologic"},  # 빈혈, 백혈구감소증
    12: {"severity": "MODERATE", "score": 65, "category": "metabolic"},  # 고칼륨혈증
    16: {"severity": "MODERATE", "score": 70, "category": "allergic"},  # 혈관부종
    18: {"severity": "MODERATE", "score": 60, "category": "allergic"},  # 과민반응
    22: {"severity": "MODERATE", "score": 70, "category": "renal"},  # 신독성
    31: {"severity": "MODERATE", "score": 65, "category": "metabolic"},  # 저나트륨혈증
    32: {"severity": "MODERATE", "score": 70, "category": "cardiac"},  # 저혈압, nitritoid 반응
    35: {"severity": "MODERATE", "score": 75, "category": "cardiac"},  # 심장독성
    36: {"severity": "MODERATE", "score": 75, "category": "neurological"},  # 경련
    51: {"severity": "MODERATE", "score": 70, "category": "hematologic"},  # 골수억제
    55: {"severity": "MODERATE", "score": 70, "category": "neuromuscular"},  # 저혈압, 신경근차단
    58: {"severity": "MODERATE", "score": 75, "category": "metabolic"},  # 저혈당
    64: {"severity": "MODERATE", "score": 65, "category": "cardiac"},  # 고혈압
    65: {"severity": "MODERATE", "score": 70, "category": "multi"},  # 저혈압, 신독성, 고칼륨혈증
    69: {"severity": "MODERATE", "score": 65, "category": "neurological"},  # 중추신경독성
    79: {"severity": "MODERATE", "score": 65, "category": "metabolic"},  # 저칼륨혈증
    80: {"severity": "MODERATE", "score": 70, "category": "bleeding"},  # 항응고 증가
    82: {"severity": "MODERATE", "score": 70, "category": "hematologic"},  # 심각한 백혈구감소증
    88: {"severity": "MODERATE", "score": 65, "category": "hematologic"},  # 골수억제
    96: {"severity": "MODERATE", "score": 65, "category": "cardiac"},  # 부정맥
    97: {"severity": "MODERATE", "score": 70, "category": "thrombotic"},  # 혈전 생성
    98: {"severity": "MODERATE", "score": 75, "category": "hepatic"},  # 간독성
    99: {"severity": "MODERATE", "score": 70, "category": "metabolic"},  # 고칼륨혈증
    100: {"severity": "MODERATE", "score": 65, "category": "neurological"},  # 신경독성
    106: {"severity": "MODERATE", "score": 60, "category": "metabolic"},  # 고혈당
    107: {"severity": "MODERATE", "score": 60, "category": "metabolic"},  # 고칼슘혈증
    108: {"severity": "MODERATE", "score": 70, "category": "cardiac"},  # 저혈압
    111: {"severity": "MODERATE", "score": 65, "category": "metabolic"},  # 저나트륨혈증
    # [V4 수정] MODERATE로 분류되었으나 점수가 LOW인 항목들 (89, 103, 109, 113)
    # 원본 맵(RISK_SEVERITY) 기준으로 89, 103, 109, 113은 LOW가 맞습니다. MODERATE에서 제외합니다.
    # 89: (LOW, 35)
    # 103: (LOW, 35)
    # 109: (LOW, 35)
    # 113: (LOW, 40)
    
    # 🟡 LOW RISK (20-49) - 경미한 부작용 또는 약동학적 변화
    2: {"severity": "LOW", "score": 40, "category": "pharmacokinetic"},  # 배설 감소 → 혈청농도 증가
    3: {"severity": "LOW", "score": 40, "category": "pharmacokinetic"},  # 혈청농도 증가
    5: {"severity": "LOW", "score": 45, "category": "cardiac"},  # AV 차단
    6: {"severity": "LOW", "score": 35, "category": "pharmacokinetic"},  # 활성대사물 농도 증가
    14: {"severity": "LOW", "score": 30, "category": "mild"},  # 부종
    17: {"severity": "LOW", "score": 35, "category": "pharmacokinetic"},  # 배설 감소
    19: {"severity": "LOW", "score": 30, "category": "mild"},  # 체액 저류
    20: {"severity": "LOW", "score": 35, "category": "pharmacokinetic"},  # 혈청농도 감소
    21: {"severity": "LOW", "score": 45, "category": "cardiovascular"},  # 고혈압
    23: {"severity": "LOW", "score": 30, "category": "pharmacokinetic"},  # 단백결합 감소
    25: {"severity": "LOW", "score": 45, "category": "cns"},  # 저혈압, CNS 억제
    26: {"severity": "LOW", "score": 45, "category": "cns"},  # CNS 억제, 고혈압
    33: {"severity": "LOW", "score": 30, "category": "pharmacokinetic"},  # 활성대사물 감소 → 효과 감소
    34: {"severity": "LOW", "score": 45, "category": "cns"},  # CNS 억제
    37: {"severity": "LOW", "score": 30, "category": "cns"},  # 자극 활동 증가
    38: {"severity": "LOW", "score": 40, "category": "sedation"},  # 진정, 졸림
    39: {"severity": "LOW", "score": 35, "category": "cardiovascular"},  # 혈관수축
    40: {"severity": "LOW", "score": 35, "category": "antiplatelet"},  # 항혈소판 감소
    41: {"severity": "LOW", "score": 40, "category": "neuromuscular"},  # 신경근 부작용
    43: {"severity": "LOW", "score": 35, "category": "immunologic"},  # 면역억제
    44: {"severity": "LOW", "score": 25, "category": "neuromuscular"},  # 신경근차단 감소
    45: {"severity": "LOW", "score": 30, "category": "psychiatric"},  # 항정신병 활동
    46: {"severity": "LOW", "score": 30, "category": "mild"},  # 체액 저류
    47: {"severity": "LOW", "score": 35, "category": "cardiovascular"},  # 항고혈압
    48: {"severity": "LOW", "score": 25, "category": "pharmacokinetic"},  # 흡수 감소
    49: {"severity": "LOW", "score": 30, "category": "respiratory"},  # 기관지확장 감소
    50: {"severity": "LOW", "score": 35, "category": "anticoagulant"},  # 항응고 감소
    52: {"severity": "LOW", "score": 40, "category": "cardiovascular"},  # 고혈압, 혈관수축
    56: {"severity": "LOW", "score": 30, "category": "pharmacokinetic"},  # 흡수 증가
    57: {"severity": "LOW", "score": 40, "category": "cardiovascular"},  # 기립성 저혈압
    59: {"severity": "LOW", "score": 30, "category": "dermatologic"},  # 광과민성
    60: {"severity": "LOW", "score": 30, "category": "antihypertensive"},  # 항고혈압 감소
    61: {"severity": "LOW", "score": 30, "category": "gastrointestinal"},  # 변비
    62: {"severity": "LOW", "score": 35, "category": "respiratory"},  # 기관지수축
    63: {"severity": "LOW", "score": 30, "category": "cardiovascular"},  # 혈관확장
    66: {"severity": "LOW", "score": 30, "category": "diuretic"},  # 이뇨 감소
    67: {"severity": "LOW", "score": 35, "category": "metabolic"},  # 저칼슘혈증
    68: {"severity": "LOW", "score": 20, "category": "diagnostic"},  # 진단제 효과 감소
    70: {"severity": "LOW", "score": 35, "category": "bleeding"},  # 항혈소판
    71: {"severity": "LOW", "score": 35, "category": "dermatologic"},  # 피부 부작용
    72: {"severity": "LOW", "score": 40, "category": "neuromuscular"},  # 신경근차단
    73: {"severity": "LOW", "score": 30, "category": "gastrointestinal"},  # 궤양 생성
    74: {"severity": "LOW", "score": 35, "category": "therapeutic"},  # 치료 효과 감소
    75: {"severity": "LOW", "score": 40, "category": "cardiovascular"},  # 저혈압
    76: {"severity": "LOW", "score": 25, "category": "stimulant"},  # 자극 감소
    77: {"severity": "LOW", "score": 25, "category": "pharmacokinetic"},  # 생체이용률 증가
    78: {"severity": "LOW", "score": 25, "category": "analgesic"},  # 진통 감소
    81: {"severity": "LOW", "score": 30, "category": "vasoconstrictor"},  # 혈관수축 감소
    85: {"severity": "LOW", "score": 35, "category": "anticholinergic"},  # 항콜린성
    86: {"severity": "LOW", "score": 40, "category": "serotonergic"},  # 세로토닌성
    87: {"severity": "LOW", "score": 30, "category": "pharmacokinetic"},  # 배설 증가 → 농도 감소
    89: {"severity": "LOW", "score": 35, "category": "pharmacokinetic"},  # 대사 감소 (V4: MODERATE에서 LOW로 원복)
    91: {"severity": "LOW", "score": 30, "category": "neurological"},  # 신경흥분
    92: {"severity": "LOW", "score": 35, "category": "sedation"},  # 진정
    93: {"severity": "LOW", "score": 35, "category": "ototoxicity"},  # 이독성
    94: {"severity": "LOW", "score": 35, "category": "cardiovascular"},  # 혈관수축
    95: {"severity": "LOW", "score": 35, "category": "metabolic"},  # 저칼륨혈증
    103: {"severity": "LOW", "score": 35, "category": "cardiac"},  # 빈맥 (V4: MODERATE에서 LOW로 원복)
    104: {"severity": "LOW", "score": 30, "category": "pharmacokinetic"}, # 약물 대사 증가 (V4: HIGH 80 -> LOW 30 원복)
    105: {"severity": "LOW", "score": 25, "category": "pharmacokinetic"},  # 생체이용률 감소
    109: {"severity": "LOW", "score": 35, "category": "cardiac"},  # 서맥 (V4: MODERATE에서 LOW로 원복)
    113: {"severity": "LOW", "score": 40, "category": "general"},  # 일반 부작용 (V4: MODERATE에서 LOW로 원복)

    # 🟢 BENEFICIAL (0-19) - 치료 효과 증가, 독성 감소
    10: {"severity": "BENEFICIAL", "score": 10, "category": "therapeutic"},  # 치료 효과 증가
    11: {"severity": "BENEFICIAL", "score": 10, "category": "therapeutic"},  # 심장독성 감소
    15: {"severity": "BENEFICIAL", "score": 15, "category": "therapeutic"},  # 진정 감소
    29: {"severity": "BENEFICIAL", "score": 10, "category": "therapeutic"},  # 진통 효과 증가
    
    # --- 누락된 ID (원본 CSV에 없음) ---
    13: {"severity": "LOW", "score": 35, "category": "therapeutic"}, # 13번: 치료 효과 감소 (원본 74와 유사)
}


def get_ddi_info(ddi_id: int):
    """DDI ID에 해당하는 정보 (제목, 설명, 위험 수준, 점수, 카테고리)를 반환합니다."""
    kor_info = DDI_KOREAN_MAP.get(ddi_id)
    if not kor_info:
        # Fallback for undefined DDI (Model predicted a class not in Map)
        kor_info = ["상호작용 위험 (미분류)", "이 약물들의 병용은 주의가 필요합니다. 의사와 상담하십시오."]

    risk_info = DDI_RISK_MAP.get(ddi_id)
    
    if risk_info:
        risk_level = risk_info.get("severity", "UNKNOWN")
        risk_score = risk_info.get("score")
        risk_category = risk_info.get("category")
    else:
        # DDI_RISK_MAP에 누락된 ID가 있을 경우(매우 드묾) UNKNOWN으로 처리
        risk_level = "UNKNOWN"
        risk_score = None
        risk_category = None

    return {
        "id": ddi_id,
        "risk_level": risk_level,
        "score": risk_score,
        "category": risk_category,
        "title": kor_info[0],
        "description": kor_info[1]
    }