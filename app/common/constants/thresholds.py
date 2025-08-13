# 운영용 임계치
PRODUCTION_THRESHOLDS = {
    "지수": {"price_rise": 1.0, "price_drop": -1.0, "drop_from_high": -2.0},
    "선물": {"price_rise": 5.0, "price_drop": -5.0, "drop_from_high": -10.0},
    "종목": {"price_rise": 3.0, "price_drop": -3.0, "drop_from_high": -5.0},
    "ETF(Long)": {"price_rise": 3.0, "price_drop": -3.0, "drop_from_high": -5.0},
    "ETF(Short)": {"price_rise": 3.0, "price_drop": -3.0, "drop_from_high": -5.0},
}

# 테스트용 임계치 (모든 변화 감지)
TEST_THRESHOLDS = {
    "지수": {"price_rise": 0.0, "price_drop": 0.0, "drop_from_high": 0.0},
    "선물": {"price_rise": 0.0, "price_drop": 0.0, "drop_from_high": 0.0},
    "종목": {"price_rise": 0.0, "price_drop": 0.0, "drop_from_high": 0.0},
    "ETF(Long)": {"price_rise": 0.0, "price_drop": 0.0, "drop_from_high": 0.0},
    "ETF(Short)": {"price_rise": 0.0, "price_drop": 0.0, "drop_from_high": 0.0},
}

# 현재 사용 중인 임계치 (테스트/운영 전환용)
CATEGORY_THRESHOLDS = TEST_THRESHOLDS

# 심볼별 개별 임계치 (카테고리보다 우선)
SYMBOL_THRESHOLDS = {
    # "TSLA": {
    #     "price_rise": 5.0,
    #     "price_drop": -5.0,
    #     "drop_from_high": -10.0
    # },
}
