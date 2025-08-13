# 기술적 지표 설정

TECHNICAL_SYMBOLS = {
    "^IXIC": {
        "name": "나스닥 지수",
        "category": "지수",
        "timeframes": ["1day"],
        "indicators": [
            "MA50",
            "MA200",
            "RSI",
            "BOLLINGER",
            "GOLDEN_CROSS",
            "DEAD_CROSS",
        ],
    },
    "^GSPC": {
        "name": "S&P 500 지수",
        "category": "지수",
        "timeframes": ["1day"],
        "indicators": [
            "MA50",
            "MA200",
            "RSI",
            "BOLLINGER",
            "GOLDEN_CROSS",
            "DEAD_CROSS",
        ],
    },
}

# 이동평균선 설정
MA_PERIODS = {
    "MA5": {"period": 5, "type": "SMA", "name": "5일선"},
    "MA20": {"period": 20, "type": "SMA", "name": "20일선"},
    "MA50": {"period": 50, "type": "SMA", "name": "50일선"},
    "MA60": {"period": 60, "type": "SMA", "name": "60일선"},
    "MA200": {"period": 200, "type": "SMA", "name": "200일선"},
    "MA300": {"period": 300, "type": "SMA", "name": "300일선"},
    "EMA9": {"period": 9, "type": "EMA", "name": "EMA 9일선"},
    "EMA21": {"period": 21, "type": "EMA", "name": "EMA 21일선"},
    "EMA50": {"period": 50, "type": "EMA", "name": "EMA 50일선"},
    "VWAP": {"period": 1, "type": "VWAP", "name": "VWAP"},
}

# RSI 설정
RSI_SETTINGS = {
    "period": 14,
    "overbought": 70,
    "oversold": 30,
    "neutral": 50,
}

# 볼린저 밴드 설정
BOLLINGER_SETTINGS = {
    "period": 20,
    "std_dev": 2,
}

# MACD 설정
MACD_SETTINGS = {
    "fast_period": 12,
    "slow_period": 26,
    "signal_period": 9,
}

# 스토캐스틱 설정
STOCHASTIC_SETTINGS = {
    "k_period": 14,
    "d_period": 3,
    "overbought": 80,
    "oversold": 20,
}

# 거래량 지표 설정
VOLUME_SETTINGS = {
    "sma_period": 20,
    "surge_threshold": 2.0,
    "low_threshold": 0.5,
    "price_change_threshold": 1.0,
}

# 크로스 신호 설정
CROSS_SIGNALS = {
    "GOLDEN_CROSS": {"short_ma": 50, "long_ma": 200, "signal": "상승"},
    "DEAD_CROSS": {"short_ma": 50, "long_ma": 200, "signal": "하락"},
}

# 알림 주기 설정 (분 단위)
ALERT_INTERVALS = {
    "MA_BREAKOUT": {"1min": 30, "15min": 120, "1day": 1440},
    "RSI_ALERT": {"1min": 60, "15min": 240, "1day": 1440},
    "BOLLINGER_ALERT": {"1min": 60, "15min": 180, "1day": 720},
    "CROSS_SIGNAL": {"1day": 60},
}

# 시간대별 설정
TIMEFRAME_INFO = {
    "1min": {"name": "1분봉", "suitable_for": "데이트레이딩"},
    "15min": {"name": "15분봉", "suitable_for": "스윙트레이딩"},
    "1day": {"name": "일봉", "suitable_for": "중장기 투자"},
}
