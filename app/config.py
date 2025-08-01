"""
레거시 설정 파일 (하위 호환성 유지)

새로운 코드에서는 app.common.config.settings를 사용하세요.
"""

import warnings
from app.common.config.settings import settings

# 하위 호환성을 위한 레거시 변수들
warnings.warn(
    "app.config는 deprecated입니다. app.common.config.settings를 사용하세요.",
    DeprecationWarning,
    stacklevel=2,
)

# 데이터베이스 설정 (레거시)
MYSQL_HOST = settings.database.host
MYSQL_PORT = settings.database.port
MYSQL_USER = settings.database.user
MYSQL_PASSWORD = settings.database.password
MYSQL_DATABASE = settings.database.database
MYSQL_URL = settings.database.url

# API 키 설정 (레거시)
OPENAI_API_KEY = settings.api.openai_api_key
YFINANCE_DELAY = settings.api.yfinance_delay

# 텔레그램 봇 설정 (레거시)
TELEGRAM_BOT_TOKEN = settings.telegram.bot_token
TELEGRAM_CHAT_ID = settings.telegram.chat_id

# 로그 설정 (레거시)
LOG_LEVEL = settings.logging.level
