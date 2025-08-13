# 지수 (Index)
INDEX_SYMBOLS = {
    "^IXIC": "나스닥 지수",
    "^GSPC": "S&P 500 지수",
}

# 선물 (Futures)
FUTURES_SYMBOLS = {
    "ES=F": "S&P 500 선물",
    "NQ=F": "나스닥 선물",
}

# 종목 (Stocks)
STOCK_SYMBOLS = {
    "AAPL": "애플",
    "AMZN": "아마존",
    "GOOGL": "구글",
    "TSLA": "테슬라",
    "MSFT": "마이크로소프트",
    "META": "메타",
    "NVDA": "엔비디아",
}

# LONG ETF
LONG_ETF_SYMBOLS = {
    "SOXL": "디렉시온 미국 반도체 3배 ETF",
    "TQQQ": "프로셰어즈 QQQ 3배 ETF",
    "TSLL": "디렉시온 테슬라 2배 ETF",
    "NVDL": "그래닛셰어즈 엔비디아 데일리 2배 롱 ETF",
}

# SHORT ETF
SHORT_ETF_SYMBOLS = {
    "SOXS": "디렉시온 미국 반도체 3배 인버스 ETF",
    "SQQQ": "프로셰어즈 QQQ 3배 인버스 ETF",
    "TSLQ": "TRADR 테슬라 2배 인버스 ETF",
    "NVD": "그래닛셰어즈 엔비디아 데일리 2배 인버스 ETF",
}

# 뉴스 심볼 (Investing RSS)
INVESTING_NEWS_SYMBOLS = {
    "INVESTING:ECONOMY": "인베스팅 경제 뉴스",
    "INVESTING:US": "인베스팅 미국 뉴스",
    "INVESTING:MARKET": "인베스팅 시장 분석",
    "INVESTING:COMMODITY": "인베스팅 원자재 뉴스",
    "INVESTING:FOREX": "인베스팅 외환 뉴스",
}

# ===== ML 모델 훈련을 위한 거시경제 지표들 =====

# 금리 관련 (Interest Rates)
INTEREST_RATE_SYMBOLS = {
    "^TNX": "10년 국채 수익률",
    "^TYX": "30년 국채 수익률", 
    "^IRX": "13주 국채 수익률",
}

# 달러 지수 (US Dollar)
DOLLAR_SYMBOLS = {
    "DX-Y.NYB": "달러 지수",
    "UUP": "PowerShares DB US Dollar Index Bullish Fund",
    "UDN": "PowerShares DB US Dollar Index Bearish Fund",
}

# 변동성 지수 (Volatility)
VOLATILITY_SYMBOLS = {
    "^VIX": "VIX 변동성 지수",
    "^VXN": "나스닥 변동성 지수",
}

# 원자재 (Commodities)
COMMODITY_SYMBOLS = {
    "GC=F": "금 선물",
    "SI=F": "은 선물",
    "CL=F": "원유 선물",
    "NG=F": "천연가스 선물",
    "ZC=F": "옥수수 선물",
    "ZS=F": "대두 선물",
}

# 섹터 ETF (Sector Rotation)
SECTOR_ETF_SYMBOLS = {
    "XLF": "금융 섹터 ETF",
    "XLK": "기술 섹터 ETF",
    "XLE": "에너지 섹터 ETF",
    "XLV": "헬스케어 섹터 ETF",
    "XLI": "산업재 섹터 ETF",
    "XLP": "필수소비재 섹터 ETF",
    "XLU": "유틸리티 섹터 ETF",
    "XLB": "소재 섹터 ETF",
    "XLRE": "부동산 섹터 ETF",
}

# 신용 시장 (Credit Market)
CREDIT_MARKET_SYMBOLS = {
    "LQD": "투자등급 기업채 ETF",
    "HYG": "하이일드 기업채 ETF",
    "JNK": "SPDR 하이일드 ETF",
    "VCIT": "중기 투자등급 기업채 ETF",
    "VCSH": "단기 투자등급 기업채 ETF",
}

# 글로벌 시장 (Global Market)
GLOBAL_MARKET_SYMBOLS = {
    "EFA": "선진국 ETF",
    "EEM": "신흥국 ETF",
    "IEFA": "선진국 ETF (iShares)",
    "IEMG": "신흥국 ETF (iShares)",
    "IWM": "러셀 2000 ETF",
    "IJR": "S&P 600 ETF",
    "VTI": "전체 시장 ETF",
    "VOO": "S&P 500 ETF (Vanguard)",
}

# ML 모델 훈련 전용 심볼 (핵심 거시경제 지표들)
ML_TRAINING_SYMBOLS = {
    **INTEREST_RATE_SYMBOLS,      # 금리 환경
    **DOLLAR_SYMBOLS,             # 달러 강세/약세
    **VOLATILITY_SYMBOLS,         # 시장 불안감
    **SECTOR_ETF_SYMBOLS,         # 섹터 로테이션
    **CREDIT_MARKET_SYMBOLS,      # 신용 시장
    **GLOBAL_MARKET_SYMBOLS,      # 글로벌 시장
}

# ===== 뉴스 크롤링 대상 심볼들 =====

# Yahoo Finance 뉴스 크롤링 대상 (거시경제 지표들)
YAHOO_NEWS_SYMBOLS = {
    # 금리 관련 뉴스
    "^TNX": "10년 국채 수익률 뉴스",
    "^TYX": "30년 국채 수익률 뉴스",
    "^IRX": "13주 국채 수익률 뉴스",
    
    # 달러 관련 뉴스
    "DX-Y.NYB": "달러 지수 뉴스",
    "UUP": "달러 강세 ETF 뉴스",
    "UDN": "달러 약세 ETF 뉴스",
    
    # 변동성 관련 뉴스
    "^VIX": "VIX 변동성 지수 뉴스",
    "^VXN": "나스닥 변동성 지수 뉴스",
    
    # 주요 섹터 ETF 뉴스
    "XLF": "금융 섹터 ETF 뉴스",
    "XLK": "기술 섹터 ETF 뉴스",
    "XLE": "에너지 섹터 ETF 뉴스",
    "XLV": "헬스케어 섹터 ETF 뉴스",
    "XLI": "산업재 섹터 ETF 뉴스",
    
    # 신용 시장 뉴스
    "LQD": "투자등급 기업채 ETF 뉴스",
    "HYG": "하이일드 기업채 ETF 뉴스",
    "JNK": "SPDR 하이일드 ETF 뉴스",
    
    # 글로벌 시장 뉴스
    "EFA": "선진국 ETF 뉴스",
    "EEM": "신흥국 ETF 뉴스",
    "IWM": "러셀 2000 ETF 뉴스",
    "VTI": "전체 시장 ETF 뉴스",
}

# Investing.com 특화 뉴스 크롤링 대상
INVESTING_SPECIALIZED_NEWS = {
    # 금리 관련 특화 뉴스
    "INVESTING:TREASURY": "https://www.investing.com/rss/news_301.rss",  # 국채 뉴스
    "INVESTING:FED": "https://www.investing.com/rss/news_302.rss",       # 연준 뉴스
    
    # 섹터별 특화 뉴스
    "INVESTING:FINANCIAL": "https://www.investing.com/rss/news_303.rss", # 금융 섹터 뉴스
    "INVESTING:TECH": "https://www.investing.com/rss/news_304.rss",      # 기술 섹터 뉴스
    "INVESTING:ENERGY": "https://www.investing.com/rss/news_305.rss",    # 에너지 섹터 뉴스
    
    # 글로벌 시장 특화 뉴스
    "INVESTING:EMERGING": "https://www.investing.com/rss/news_306.rss",  # 신흥국 뉴스
    "INVESTING:EUROPE": "https://www.investing.com/rss/news_307.rss",    # 유럽 시장 뉴스
    "INVESTING:ASIA": "https://www.investing.com/rss/news_308.rss",      # 아시아 시장 뉴스
}

# 전체 뉴스 크롤링 대상 심볼 (기존 + 새로운 심볼들)
ALL_NEWS_SYMBOLS = {
    **INVESTING_NEWS_SYMBOLS,           # 기존 Investing.com 뉴스
    **YAHOO_NEWS_SYMBOLS,              # 새로운 Yahoo Finance 뉴스
    **INVESTING_SPECIALIZED_NEWS,      # 새로운 Investing.com 특화 뉴스
}

# 전체 심볼 이름 매핑
SYMBOL_NAME_MAP = {
    **INDEX_SYMBOLS,
    **FUTURES_SYMBOLS,
    **STOCK_SYMBOLS,
    **LONG_ETF_SYMBOLS,
    **SHORT_ETF_SYMBOLS,
    **INVESTING_NEWS_SYMBOLS,
    **INTEREST_RATE_SYMBOLS,
    **DOLLAR_SYMBOLS,
    **VOLATILITY_SYMBOLS,
    **COMMODITY_SYMBOLS,
    **SECTOR_ETF_SYMBOLS,
    **CREDIT_MARKET_SYMBOLS,
    **GLOBAL_MARKET_SYMBOLS,
    **YAHOO_NEWS_SYMBOLS,
    **INVESTING_SPECIALIZED_NEWS,
}

# 가격 모니터링 대상 심볼
SYMBOL_PRICE_MAP = {
    **INDEX_SYMBOLS,
    **STOCK_SYMBOLS,
    **LONG_ETF_SYMBOLS,
    **SHORT_ETF_SYMBOLS,
    **INTEREST_RATE_SYMBOLS,
    **DOLLAR_SYMBOLS,
    **VOLATILITY_SYMBOLS,
    **COMMODITY_SYMBOLS,
    **SECTOR_ETF_SYMBOLS,
    **CREDIT_MARKET_SYMBOLS,
    **GLOBAL_MARKET_SYMBOLS,
}

# ML 모델 훈련 전용 심볼 (핵심 거시경제 지표들)
ML_TRAINING_SYMBOLS = {
    **INTEREST_RATE_SYMBOLS,      # 금리 환경
    **DOLLAR_SYMBOLS,             # 달러 강세/약세
    **VOLATILITY_SYMBOLS,         # 시장 불안감
    **SECTOR_ETF_SYMBOLS,         # 섹터 로테이션
    **CREDIT_MARKET_SYMBOLS,      # 신용 시장
    **GLOBAL_MARKET_SYMBOLS,      # 글로벌 시장
}

# 심볼별 카테고리 매핑
SYMBOL_CATEGORY_MAP = {
    **{symbol: "지수" for symbol in INDEX_SYMBOLS},
    **{symbol: "선물" for symbol in FUTURES_SYMBOLS},
    **{symbol: "종목" for symbol in STOCK_SYMBOLS},
    **{symbol: "ETF(Long)" for symbol in LONG_ETF_SYMBOLS},
    **{symbol: "ETF(Short)" for symbol in SHORT_ETF_SYMBOLS},
    **{symbol: "국제뉴스" for symbol in INVESTING_NEWS_SYMBOLS},
    **{symbol: "금리" for symbol in INTEREST_RATE_SYMBOLS},
    **{symbol: "달러" for symbol in DOLLAR_SYMBOLS},
    **{symbol: "변동성" for symbol in VOLATILITY_SYMBOLS},
    **{symbol: "원자재" for symbol in COMMODITY_SYMBOLS},
    **{symbol: "섹터ETF" for symbol in SECTOR_ETF_SYMBOLS},
    **{symbol: "신용시장" for symbol in CREDIT_MARKET_SYMBOLS},
    **{symbol: "글로벌시장" for symbol in GLOBAL_MARKET_SYMBOLS},
}

# 모니터링용 카테고리 매핑 (가격 모니터링 대상만)
SYMBOL_MONITORING_CATEGORY_MAP = {
    **{symbol: "지수" for symbol in INDEX_SYMBOLS},
    **{symbol: "종목" for symbol in STOCK_SYMBOLS},
    **{symbol: "ETF(Long)" for symbol in LONG_ETF_SYMBOLS},
    **{symbol: "ETF(Short)" for symbol in SHORT_ETF_SYMBOLS},
    **{symbol: "금리" for symbol in INTEREST_RATE_SYMBOLS},
    **{symbol: "달러" for symbol in DOLLAR_SYMBOLS},
    **{symbol: "변동성" for symbol in VOLATILITY_SYMBOLS},
    **{symbol: "원자재" for symbol in COMMODITY_SYMBOLS},
    **{symbol: "섹터ETF" for symbol in SECTOR_ETF_SYMBOLS},
    **{symbol: "신용시장" for symbol in CREDIT_MARKET_SYMBOLS},
    **{symbol: "글로벌시장" for symbol in GLOBAL_MARKET_SYMBOLS},
}
