"""
애플리케이션 설정 관리

Pydantic Settings를 사용한 타입 안전한 설정 관리
"""

import os
from typing import Optional, List
from pydantic import validator, Field
from pydantic.networks import AnyUrl
from pydantic_settings import BaseSettings


class DatabaseSettings(BaseSettings):
    """데이터베이스 설정"""

    host: str = Field(..., description="MySQL 호스트")
    port: int = Field(3306, description="MySQL 포트")
    user: str = Field(..., description="MySQL 사용자명")
    password: str = Field(..., description="MySQL 비밀번호")
    database: str = Field(..., description="데이터베이스 이름")

    @validator("password")
    def validate_password(cls, v):
        if not v:
            raise ValueError("데이터베이스 비밀번호는 필수입니다")
        if len(v) < 4:
            raise ValueError("데이터베이스 비밀번호는 최소 4자 이상이어야 합니다")
        return v

    @validator("port")
    def validate_port(cls, v):
        if not 1 <= v <= 65535:
            raise ValueError("포트는 1-65535 범위여야 합니다")
        return v

    @property
    def url(self) -> str:
        """SQLAlchemy 연결 URL 생성"""
        return f"mysql+pymysql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"

    model_config = {"env_prefix": "MYSQL_"}


class APISettings(BaseSettings):
    """외부 API 설정"""

    openai_api_key: str = Field(..., description="OpenAI API 키")
    yfinance_delay: float = Field(0.5, description="Yahoo Finance API 요청 간격(초)")

    @validator("openai_api_key")
    def validate_openai_key(cls, v):
        if not v:
            raise ValueError("OpenAI API 키는 필수입니다")
        if not v.startswith("sk-"):
            raise ValueError("올바른 OpenAI API 키 형식이 아닙니다 (sk-로 시작해야 함)")
        return v

    @validator("yfinance_delay")
    def validate_yfinance_delay(cls, v):
        if v < 0.1:
            raise ValueError("Yahoo Finance 지연 시간은 최소 0.1초 이상이어야 합니다")
        if v > 10.0:
            raise ValueError("Yahoo Finance 지연 시간은 최대 10초 이하여야 합니다")
        return v

    model_config = {"env_prefix": ""}


class TelegramSettings(BaseSettings):
    """텔레그램 봇 설정"""

    bot_token: str = Field(..., description="텔레그램 봇 토큰")
    chat_id: str = Field(..., description="텔레그램 채팅 ID")

    @validator("bot_token")
    def validate_bot_token(cls, v):
        if not v:
            raise ValueError("텔레그램 봇 토큰은 필수입니다")
        # 텔레그램 봇 토큰 형식: 숫자:문자열
        if ":" not in v:
            raise ValueError("올바른 텔레그램 봇 토큰 형식이 아닙니다")
        return v

    @validator("chat_id")
    def validate_chat_id(cls, v):
        if not v:
            raise ValueError("텔레그램 채팅 ID는 필수입니다")
        # 채팅 ID는 숫자 또는 -로 시작하는 숫자
        if not (v.isdigit() or (v.startswith("-") and v[1:].isdigit())):
            raise ValueError("올바른 텔레그램 채팅 ID 형식이 아닙니다")
        return v

    model_config = {"env_prefix": "TELEGRAM_"}


class LoggingSettings(BaseSettings):
    """로깅 설정"""

    level: str = Field("INFO", description="로그 레벨")
    format: str = Field("json", description="로그 포맷 (json/text)")
    file_enabled: bool = Field(True, description="파일 로깅 활성화")
    file_path: str = Field("logs/app.log", description="로그 파일 경로")
    file_max_size: str = Field("100MB", description="로그 파일 최대 크기")
    file_backup_count: int = Field(10, description="로그 파일 백업 개수")
    console_enabled: bool = Field(True, description="콘솔 로깅 활성화")

    @validator("level")
    def validate_level(cls, v):
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"로그 레벨은 {valid_levels} 중 하나여야 합니다")
        return v.upper()

    @validator("format")
    def validate_format(cls, v):
        valid_formats = ["json", "text"]
        if v.lower() not in valid_formats:
            raise ValueError(f"로그 포맷은 {valid_formats} 중 하나여야 합니다")
        return v.lower()

    @validator("file_backup_count")
    def validate_backup_count(cls, v):
        if v < 1 or v > 100:
            raise ValueError("로그 파일 백업 개수는 1-100 범위여야 합니다")
        return v

    model_config = {"env_prefix": "LOG_"}


class SecuritySettings(BaseSettings):
    """보안 설정"""

    secret_key: str = Field(..., description="애플리케이션 시크릿 키")
    encryption_key: Optional[str] = Field(None, description="데이터 암호화 키")
    allowed_hosts: List[str] = Field(["*"], description="허용된 호스트 목록")
    cors_origins: List[str] = Field(["*"], description="CORS 허용 오리진")

    @validator("secret_key")
    def validate_secret_key(cls, v):
        if not v:
            raise ValueError("시크릿 키는 필수입니다")
        if len(v) < 32:
            raise ValueError("시크릿 키는 최소 32자 이상이어야 합니다")
        return v

    @validator("encryption_key")
    def validate_encryption_key(cls, v):
        if v and len(v) != 44:  # Fernet 키는 44자
            raise ValueError("암호화 키는 44자여야 합니다 (Fernet 키 형식)")
        return v

    model_config = {"env_prefix": "SECURITY_"}


class AppSettings(BaseSettings):
    """애플리케이션 전체 설정"""

    # 환경 설정
    environment: str = Field("development", description="실행 환경")
    debug: bool = Field(False, description="디버그 모드")
    version: str = Field("1.0.0", description="애플리케이션 버전")

    # 서버 설정
    host: str = Field("0.0.0.0", description="서버 호스트")
    port: int = Field(8000, description="서버 포트")

    # 하위 설정들
    database: DatabaseSettings
    api: APISettings
    telegram: TelegramSettings
    logging: LoggingSettings
    security: SecuritySettings

    @validator("environment")
    def validate_environment(cls, v):
        valid_envs = ["development", "test", "production"]
        if v not in valid_envs:
            raise ValueError(f"환경은 {valid_envs} 중 하나여야 합니다")
        return v

    @validator("port")
    def validate_port(cls, v):
        if not 1 <= v <= 65535:
            raise ValueError("포트는 1-65535 범위여야 합니다")
        return v

    def __init__(self, **kwargs):
        # 하위 설정들을 자동으로 초기화
        if "database" not in kwargs:
            kwargs["database"] = DatabaseSettings()
        if "api" not in kwargs:
            kwargs["api"] = APISettings()
        if "telegram" not in kwargs:
            kwargs["telegram"] = TelegramSettings()
        if "logging" not in kwargs:
            kwargs["logging"] = LoggingSettings()
        if "security" not in kwargs:
            kwargs["security"] = SecuritySettings()

        super().__init__(**kwargs)

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


def get_settings() -> AppSettings:
    """설정 인스턴스 반환 (싱글톤 패턴)"""
    if not hasattr(get_settings, "_instance"):
        get_settings._instance = AppSettings()
    return get_settings._instance


def validate_settings() -> None:
    """설정 검증 (애플리케이션 시작 시 호출)"""
    try:
        settings = get_settings()
        print(f"✅ 설정 검증 완료 - 환경: {settings.environment}")
        return settings
    except Exception as e:
        print(f"❌ 설정 검증 실패: {e}")
        raise


# 편의를 위한 전역 설정 인스턴스
settings = get_settings()
