# Investing.com RSS 피드 설정

INVESTING_RSS_FEEDS = {
    "INVESTING:ECONOMY": "https://www.investing.com/rss/news.rss",
    "INVESTING:US": "https://www.investing.com/rss/news_25.rss",
    "INVESTING:MARKET": "https://www.investing.com/rss/market_overview.rss",
    "INVESTING:COMMODITY": "https://www.investing.com/rss/commodities.rss",
    "INVESTING:FOREX": "https://www.investing.com/rss/forex.rss",
    
    # ===== 새로 추가한 거시경제 지표 특화 뉴스 =====
    
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

# 경제 관련 심볼
INVESTING_ECONOMIC_SYMBOLS = ["INVESTING:ECONOMY", "INVESTING:US"]

# 시장 관련 심볼
INVESTING_MARKET_SYMBOLS = [
    "INVESTING:MARKET",
    "INVESTING:COMMODITY",
    "INVESTING:FOREX",
]

# 새로 추가한 거시경제 지표 관련 심볼
INVESTING_MACRO_SYMBOLS = [
    "INVESTING:TREASURY",    # 국채/금리
    "INVESTING:FED",         # 연준
    "INVESTING:FINANCIAL",   # 금융 섹터
    "INVESTING:TECH",        # 기술 섹터
    "INVESTING:ENERGY",      # 에너지 섹터
    "INVESTING:EMERGING",    # 신흥국
    "INVESTING:EUROPE",      # 유럽
    "INVESTING:ASIA",        # 아시아
]

# 전체 Investing.com 뉴스 심볼
ALL_INVESTING_NEWS_SYMBOLS = [
    *INVESTING_ECONOMIC_SYMBOLS,
    *INVESTING_MARKET_SYMBOLS,
    *INVESTING_MACRO_SYMBOLS,
]
