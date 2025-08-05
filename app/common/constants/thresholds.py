# 카테고리별 기본 임계치
CATEGORY_THRESHOLDS = {
    "지수": {
        "price_rise": 1.0,  # 전일 종가 대비 상승 알림 기준 (%)
        "price_drop": -1.0,  # 전일 종가 대비 하락 알림 기준 (%)
        "drop_from_high": -2.0,  # 최고가 대비 하락 알림 기준 (%)
    },
    "선물": {"price_rise": 5.0, "price_drop": -5.0, "drop_from_high": -10.0},
    "종목": {"price_rise": 3.0, "price_drop": -3.0, "drop_from_high": -5.0},
}

# 테스트용 - 낮은 임계값으로 알림 테스트
CATEGORY_THRESHOLDS = {
    "지수": {
        "price_rise": 0.01,  # 0.01% 이상 상승 시 알림
        "price_drop": -0.01,  # 0.01% 이상 하락 시 알림
        "drop_from_high": -0.1,  # 최고가 대비 0.1% 이상 하락 시 알림
    },
    "선물": {
        "price_rise": 0.01,
        "price_drop": -0.01,
        "drop_from_high": -0.1,
    },
    "종목": {
        "price_rise": 0.01,
        "price_drop": -0.01,
        "drop_from_high": -0.1,
    },
}

# 심볼별 개별 임계치 (카테고리보다 우선)
SYMBOL_THRESHOLDS = {
    # "TSLA": {
    #     "price_rise": 5.0,
    #     "price_drop": -5.0,
    #     "drop_from_high": -10.0
    # },
}
