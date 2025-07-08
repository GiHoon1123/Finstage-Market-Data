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

# ✅ 종목 (Stocks)
STOCK_SYMBOLS = {
    "AAPL": "애플",
    "AMZN": "아마존",
    "GOOGL": "구글",
    "TSLA": "테슬라",
    "GRYP": "그리폰 디지털 마이닝",
    "MSFT": "마이크로소프트",
    "META": "메타",
    "PLTR": "팔란티어",
    "BTBT": "비트 디지털"
}

# ✅ 커뮤니티 (Community)
COMMUNITY_SYMBOLS = {
    "DC_US": "디시 미국주식 갤러리"
}


# ✅ 뉴스 공급자 (Investing RSS 카테고리)
INVESTING_SYMBOLS = {
    "INVESTING:ECONOMY": "인베스팅 경제 뉴스",
    "INVESTING:US": "인베스팅 미국 뉴스",
    "INVESTING:MARKET": "인베스팅 시장 분석",
    "INVESTING:COMMODITY": "인베스팅 원자재 뉴스",
    "INVESTING:FOREX": "인베스팅 외환 뉴스"
}

SYMBOL_NAME_MAP = {
    **INDEX_SYMBOLS,
    **FUTURES_SYMBOLS,
    **STOCK_SYMBOLS,
    **COMMUNITY_SYMBOLS,
    **INVESTING_SYMBOLS
}

SYMBOL_PRICE_MAP = {
    **INDEX_SYMBOLS,
    **FUTURES_SYMBOLS,
    **STOCK_SYMBOLS,
}

SYMBOL_CATEGORY_MAP = {
    **{symbol: "지수" for symbol in INDEX_SYMBOLS},
    **{symbol: "선물" for symbol in FUTURES_SYMBOLS},
    **{symbol: "종목" for symbol in STOCK_SYMBOLS},
    **{symbol: "커뮤니티" for symbol in COMMUNITY_SYMBOLS},
    **{symbol: "국제뉴스" for symbol in INVESTING_SYMBOLS}
}