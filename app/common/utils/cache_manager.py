"""
캐시 관리 시스템

다양한 캐시 백엔드(메모리, Redis 등)를 추상화하여 일관된 인터페이스 제공
"""

import time
import json
import pickle
from abc import ABC, abstractmethod
from typing import Any, Optional, Dict, Union
from datetime import datetime, timedelta


class CacheBackend(ABC):
    """캐시 백엔드 추상 클래스"""

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """
        캐시에서 값 조회

        Args:
            key: 캐시 키

        Returns:
            저장된 값 또는 None (없는 경우)
        """
        pass

    @abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        캐시에 값 저장

        Args:
            key: 캐시 키
            value: 저장할 값
            ttl: 유효 시간 (초)

        Returns:
            성공 여부
        """
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """
        캐시에서 값 삭제

        Args:
            key: 캐시 키

        Returns:
            성공 여부
        """
        pass

    @abstractmethod
    def clear(self) -> bool:
        """
        캐시 전체 삭제

        Returns:
            성공 여부
        """
        pass


class MemoryCacheBackend(CacheBackend):
    """메모리 기반 캐시 백엔드"""

    def __init__(self, default_ttl: int = 3600, max_size: int = 1000):
        """
        Args:
            default_ttl: 기본 유효 시간 (초)
            max_size: 최대 캐시 항목 수
        """
        self.cache = {}  # {key: (value, expires_at)}
        self.default_ttl = default_ttl
        self.max_size = max_size

    def get(self, key: str) -> Optional[Any]:
        """캐시에서 값 조회"""
        if key not in self.cache:
            return None

        value, expires_at = self.cache[key]

        # 만료 확인
        if expires_at and time.time() > expires_at:
            del self.cache[key]
            return None

        return value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """캐시에 값 저장"""
        # 캐시 크기 제한 확인
        if len(self.cache) >= self.max_size and key not in self.cache:
            # 가장 오래된 항목 삭제
            oldest_key = min(
                self.cache.keys(), key=lambda k: self.cache[k][1] or float("inf")
            )
            del self.cache[oldest_key]

        # 만료 시간 계산
        ttl = ttl if ttl is not None else self.default_ttl
        expires_at = time.time() + ttl if ttl > 0 else None

        # 캐시에 저장
        self.cache[key] = (value, expires_at)
        return True

    def delete(self, key: str) -> bool:
        """캐시에서 값 삭제"""
        if key in self.cache:
            del self.cache[key]
            return True
        return False

    def clear(self) -> bool:
        """캐시 전체 삭제"""
        self.cache.clear()
        return True


class RedisCacheBackend(CacheBackend):
    """Redis 기반 캐시 백엔드"""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        default_ttl: int = 3600,
        prefix: str = "cache:",
    ):
        """
        Args:
            host: Redis 호스트
            port: Redis 포트
            db: Redis DB 번호
            password: Redis 비밀번호
            default_ttl: 기본 유효 시간 (초)
            prefix: 캐시 키 접두사
        """
        self.default_ttl = default_ttl
        self.prefix = prefix
        self.client = None
        self.connection_params = {
            "host": host,
            "port": port,
            "db": db,
            "password": password,
        }

    def _get_client(self):
        """Redis 클라이언트 가져오기 (지연 초기화)"""
        if self.client is None:
            try:
                import redis

                self.client = redis.Redis(**self.connection_params)
            except ImportError:
                raise ImportError(
                    "Redis 사용을 위해 'pip install redis' 명령으로 패키지를 설치하세요."
                )
        return self.client

    def _get_full_key(self, key: str) -> str:
        """접두사가 포함된 전체 키 생성"""
        return f"{self.prefix}{key}"

    def get(self, key: str) -> Optional[Any]:
        """캐시에서 값 조회"""
        try:
            client = self._get_client()
            full_key = self._get_full_key(key)
            data = client.get(full_key)

            if data is None:
                return None

            # 직렬화된 데이터 역직렬화
            return pickle.loads(data)
        except Exception as e:
            print(f"Redis 캐시 조회 실패: {e}")
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """캐시에 값 저장"""
        try:
            client = self._get_client()
            full_key = self._get_full_key(key)

            # 직렬화
            data = pickle.dumps(value)

            # TTL 설정
            ttl = ttl if ttl is not None else self.default_ttl

            if ttl > 0:
                client.setex(full_key, ttl, data)
            else:
                client.set(full_key, data)

            return True
        except Exception as e:
            print(f"Redis 캐시 저장 실패: {e}")
            return False

    def delete(self, key: str) -> bool:
        """캐시에서 값 삭제"""
        try:
            client = self._get_client()
            full_key = self._get_full_key(key)
            client.delete(full_key)
            return True
        except Exception as e:
            print(f"Redis 캐시 삭제 실패: {e}")
            return False

    def clear(self) -> bool:
        """캐시 전체 삭제 (접두사로 시작하는 키만)"""
        try:
            client = self._get_client()
            pattern = f"{self.prefix}*"

            # 스캔을 통해 키 찾기
            cursor = 0
            while True:
                cursor, keys = client.scan(cursor, match=pattern, count=100)
                if keys:
                    client.delete(*keys)

                if cursor == 0:
                    break

            return True
        except Exception as e:
            print(f"Redis 캐시 전체 삭제 실패: {e}")
            return False


class CacheManager:
    """캐시 관리자"""

    def __init__(self, backend: CacheBackend = None):
        """
        Args:
            backend: 사용할 캐시 백엔드 (기본: 메모리 캐시)
        """
        self.backend = backend or MemoryCacheBackend()

    def get(self, key: str) -> Optional[Any]:
        """캐시에서 값 조회"""
        return self.backend.get(key)

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """캐시에 값 저장"""
        return self.backend.set(key, value, ttl)

    def delete(self, key: str) -> bool:
        """캐시에서 값 삭제"""
        return self.backend.delete(key)

    def clear(self) -> bool:
        """캐시 전체 삭제"""
        return self.backend.clear()

    def get_or_set(
        self, key: str, value_func: callable, ttl: Optional[int] = None
    ) -> Any:
        """
        캐시에서 값을 조회하고, 없으면 함수를 실행하여 값을 생성하고 저장

        Args:
            key: 캐시 키
            value_func: 값을 생성할 함수
            ttl: 유효 시간 (초)

        Returns:
            캐시된 값 또는 새로 생성된 값
        """
        # 캐시 확인
        cached_value = self.get(key)
        if cached_value is not None:
            return cached_value

        # 값 생성
        value = value_func()

        # 캐시에 저장
        self.set(key, value, ttl)

        return value


# 기본 캐시 매니저 인스턴스 (메모리 캐시)
default_cache_manager = CacheManager(MemoryCacheBackend())


# Redis 캐시 매니저 생성 함수
def create_redis_cache_manager(
    host: str = "localhost",
    port: int = 6379,
    db: int = 0,
    password: Optional[str] = None,
    prefix: str = "cache:",
) -> CacheManager:
    """
    Redis 기반 캐시 매니저 생성

    Args:
        host: Redis 호스트
        port: Redis 포트
        db: Redis DB 번호
        password: Redis 비밀번호
        prefix: 캐시 키 접두사

    Returns:
        Redis 캐시 매니저
    """
    backend = RedisCacheBackend(host, port, db, password, prefix=prefix)
    return CacheManager(backend)
