# app/common/constants/symbol_names.py

# ✅ 지수 (Index)
INDEX_SYMBOLS = {
    "^IXIC": "나스닥 지수",
    "^GSPC": "S&P 500 지수",
    "^DJI": "다우존스 지수"
}

# ✅ 선물 (Futures)
FUTURES_SYMBOLS = {
    "ES=F": "S&P 500 선물",
    "NQ=F": "나스닥 선물",
    "YM=F": "다우존스 선물"
}

# ✅ 종목 (Stocks) - 한글 명칭
STOCK_SYMBOLS = {
    "AAPL": "애플",
    "AMZN": "아마존",
    "GOOGL": "구글",
    "TSLA": "테슬라",
    "GRYP": "그리폰 디지털 마이닝",
    "MSFT": "마이크로소프트",
    "META": "메타",
    "PLTR": "팔란티어"
}

# ✅ 디시인사이드 미국 주식 갤러리 추가
COMMUNITY_SYMBOLS = {
    "DC_US": "디시 미국주식 갤러리"
}

SYMBOL_NAME_MAP = {
    **INDEX_SYMBOLS,
    **FUTURES_SYMBOLS,
    **STOCK_SYMBOLS,
    **COMMUNITY_SYMBOLS
}


# ✅ 전체 심볼 → 이름 매핑 (옵션)
SYMBOL_CATEGORY_MAP = {
    **{symbol: "지수" for symbol, _ in INDEX_SYMBOLS.items()},
    **{symbol: "선물" for symbol, _ in FUTURES_SYMBOLS.items()},
    **{symbol: "종목" for symbol, _ in STOCK_SYMBOLS.items()},
    **{symbol: "커뮤니티" for symbol, _ in COMMUNITY_SYMBOLS.items()}
}

