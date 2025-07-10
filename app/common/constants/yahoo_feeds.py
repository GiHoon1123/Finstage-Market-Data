from app.common.constants.symbol_names import (
    INDEX_SYMBOLS,
    FUTURES_SYMBOLS,
    STOCK_SYMBOLS,)

YAHOO_NEWS_SYMBOLS = {
    # 지수
    "^IXIC": "나스닥 지수",
    "^GSPC": "S&P 500 지수",
    "^DJI": "다우존스 지수",

    # 선물
    "ES=F": "S&P 500 선물",
    "NQ=F": "나스닥 선물",
    "YM=F": "다우존스 선물",

    # 종목
    "AAPL": "애플",
    "AMZN": "아마존",
    "GOOGL": "구글",
    "TSLA": "테슬라",
    "MSFT": "마이크로소프트",
    "META": "메타",
    "NVDA": "엔비디아"
}

YAHOO_NEWS_CATEGORIES = {
    **{symbol: "지수" for symbol in INDEX_SYMBOLS},
    **{symbol: "선물" for symbol in FUTURES_SYMBOLS},
    **{symbol: "종목" for symbol in STOCK_SYMBOLS},
}