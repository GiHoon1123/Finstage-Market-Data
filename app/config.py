import os

# 데이터베이스 설정
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "1234")  # 기본값을 1234로 설정
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "finstage_market_data")

# SQLAlchemy 연결 URL
MYSQL_URL = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}"

# API 키 설정
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# 텔레그램 봇 설정
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Yahoo Finance API 설정
YFINANCE_DELAY = float(os.getenv("YFINANCE_DELAY", "0.5"))

# 로그 설정
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
