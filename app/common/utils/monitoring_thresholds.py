from app.common.constants.symbol_names import SYMBOL_MONITORING_CATEGORY_MAP
from app.common.constants.thresholds import CATEGORY_THRESHOLDS, SYMBOL_THRESHOLDS

def get_monitoring_thresholds(symbol: str) -> dict:
    """
    해당 심볼의 모니터링 임계값 반환
    우선순위: SYMBOL_THRESHOLDS > CATEGORY_THRESHOLDS > DEFAULT
    """
    # 1. 개별 심볼 기준 임계값이 있으면 우선 사용
    if symbol in SYMBOL_THRESHOLDS:
        return SYMBOL_THRESHOLDS[symbol]

    # 2. 해당 심볼이 속한 카테고리 기준 임계값 사용
    category = SYMBOL_MONITORING_CATEGORY_MAP.get(symbol)
    if category and category in CATEGORY_THRESHOLDS:
        return CATEGORY_THRESHOLDS[category]

