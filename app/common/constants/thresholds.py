# 카테고리별 기본 임계치
CATEGORY_THRESHOLDS = {
    "지수": {
        "price_rise": 1.0,         # 전일 종가 대비 상승 알림 기준 (%)
        "price_drop": -1.0,        # 전일 종가 대비 하락 알림 기준 (%)
        "drop_from_high": -2.0     # 최고가 대비 하락 알림 기준 (%)
    },
    "선물": {
        "price_rise": 5.0,
        "price_drop": -5.0,
        "drop_from_high": -10.0
    },
    "종목": {
        "price_rise": 3.0,
        "price_drop": -3.0,
        "drop_from_high": -5.0
    }
}

# 테스트용
# CATEGORY_THRESHOLDS = {
#     "지수": {
#         "price_rise": 0.0,         
#         "price_drop": 0.0,
#         "drop_from_high": 0.0,
#     },
#     "선물": {
#         "price_rise": 0.0,
#         "price_drop": 0.0,
#         "drop_from_high": 0.0,
#     },
#     "종목": {
#         "price_rise": 0.0,
#         "price_drop": 0.0,
#         "drop_from_high": 0.0,
#     }
# }

# 심볼별 개별 임계치 (카테고리보다 우선)
SYMBOL_THRESHOLDS = {
    # "TSLA": {
    #     "price_rise": 5.0,
    #     "price_drop": -5.0,
    #     "drop_from_high": -10.0
    # },
}
