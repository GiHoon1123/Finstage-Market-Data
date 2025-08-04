"""
인메모리 캐싱 시스템

Redis 대신 Python dict 기반 LRU 캐시를 구현합니다.
TTL 지원, 자동 만료 처리, 메모리 사용량 제한 기능을 제공합니다.
"""

import time
import threading
from typing import Dict, Any, Optional, Callable
from functools import wraps
from collections import OrderedDict
import gc

from app.common.utils.logging_config import get_logger

logger = get_logger(__name__)


class LRUCache:
    """LRU (Least Recently Used) 캐시 구현"""

    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        """
        Args:
            max_size: 최대 캐시 항목 수
            default_ttl: 기본 TTL (초)
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._lock = threading.RLock()
        self._hits = 0
        self._misses = 0

        logger.info("lru_cache_initialized", max_size=max_size, default_ttl=default_ttl)

    def get(self, key: str) -> Optional[Any]:
        """캐시에서 값 조회"""
        with self._lock:
            if key not in self.cache:
                self._misses += 1
                return None

            item = self.cache[key]

            # TTL 확인
            if time.time() > item["expires_at"]:
                del self.cache[key]
                self._misses += 1
                logger.debug("cache_expired", key=key)
                return None

            # LRU 업데이트 (최근 사용으로 이동)
            self.cache.move_to_end(key)
            item["accessed_at"] = time.time()
            item["access_count"] += 1

            self._hits += 1
            logger.debug("cache_hit", key=key, access_count=item["access_count"])
            return item["value"]

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """캐시에 값 저장"""
        with self._lock:
            ttl = ttl or self.default_ttl
            expires_at = time.time() + ttl

            # 기존 항목 업데이트
            if key in self.cache:
                self.cache[key].update(
                    {
                        "value": value,
                        "expires_at": expires_at,
                        "updated_at": time.time(),
                        "access_count": self.cache[key]["access_count"],
                    }
                )
                self.cache.move_to_end(key)
                logger.debug("cache_updated", key=key, ttl=ttl)
                return

            # 캐시 크기 제한 확인
            if len(self.cache) >= self.max_size:
                # 가장 오래된 항목 제거 (LRU)
                oldest_key, oldest_item = self.cache.popitem(last=False)
                logger.debug(
                    "cache_evicted",
                    evicted_key=oldest_key,
                    access_count=oldest_item["access_count"],
                )

            # 새 항목 추가
            self.cache[key] = {
                "value": value,
                "expires_at": expires_at,
                "created_at": time.time(),
                "updated_at": time.time(),
                "accessed_at": time.time(),
                "access_count": 1,
            }

            logger.debug("cache_set", key=key, ttl=ttl, cache_size=len(self.cache))

    def delete(self, key: str) -> bool:
        """캐시에서 항목 삭제"""
        with self._lock:
            if key in self.cache:
                del self.cache[key]
                logger.debug("cache_deleted", key=key)
                return True
            return False

    def clear(self) -> None:
        """캐시 전체 삭제"""
        with self._lock:
            cache_size = len(self.cache)
            self.cache.clear()
            self._hits = 0
            self._misses = 0
            logger.info("cache_cleared", cleared_items=cache_size)

    def cleanup_expired(self) -> int:
        """만료된 항목들 정리"""
        with self._lock:
            current_time = time.time()
            expired_keys = [
                key
                for key, item in self.cache.items()
                if current_time > item["expires_at"]
            ]

            for key in expired_keys:
                del self.cache[key]

            if expired_keys:
                logger.info(
                    "cache_cleanup_completed",
                    expired_count=len(expired_keys),
                    remaining_count=len(self.cache),
                )

            return len(expired_keys)

    def get_stats(self) -> Dict[str, Any]:
        """캐시 통계 조회"""
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0

            # 메모리 사용량 추정
            memory_usage = 0
            for item in self.cache.values():
                try:
                    import sys

                    memory_usage += sys.getsizeof(item["value"])
                except:
                    pass

            return {
                "cache_size": len(self.cache),
                "max_size": self.max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(hit_rate, 2),
                "memory_usage_bytes": memory_usage,
                "memory_usage_mb": round(memory_usage / 1024 / 1024, 2),
            }

    def get_top_accessed(self, limit: int = 10) -> list:
        """가장 많이 접근된 항목들 조회"""
        with self._lock:
            items = [
                {
                    "key": key,
                    "access_count": item["access_count"],
                    "created_at": item["created_at"],
                    "last_accessed": item["accessed_at"],
                }
                for key, item in self.cache.items()
            ]

            return sorted(items, key=lambda x: x["access_count"], reverse=True)[:limit]


class CacheManager:
    """캐시 매니저 - 여러 캐시 인스턴스 관리"""

    def __init__(self):
        self.caches: Dict[str, LRUCache] = {}
        self._lock = threading.Lock()

    def get_cache(
        self, name: str, max_size: int = 1000, default_ttl: int = 300
    ) -> LRUCache:
        """캐시 인스턴스 조회 또는 생성"""
        with self._lock:
            if name not in self.caches:
                self.caches[name] = LRUCache(max_size=max_size, default_ttl=default_ttl)
                logger.info("cache_instance_created", name=name)

            return self.caches[name]

    def cleanup_all_expired(self) -> Dict[str, int]:
        """모든 캐시의 만료된 항목 정리"""
        results = {}
        for name, cache in self.caches.items():
            expired_count = cache.cleanup_expired()
            results[name] = expired_count

        return results

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """모든 캐시의 통계 조회"""
        return {name: cache.get_stats() for name, cache in self.caches.items()}

    def clear_all(self) -> None:
        """모든 캐시 삭제"""
        for cache in self.caches.values():
            cache.clear()
        logger.info("all_caches_cleared", cache_count=len(self.caches))


# 전역 캐시 매니저
cache_manager = CacheManager()

# 주요 캐시 인스턴스들
technical_analysis_cache = cache_manager.get_cache(
    "technical_analysis", max_size=500, default_ttl=600
)  # 10분
news_cache = cache_manager.get_cache("news", max_size=1000, default_ttl=300)  # 5분
price_data_cache = cache_manager.get_cache(
    "price_data", max_size=200, default_ttl=3600
)  # 1시간
api_response_cache = cache_manager.get_cache(
    "api_response", max_size=2000, default_ttl=180
)  # 3분


def cache_result(
    cache_name: str = "default",
    ttl: Optional[int] = None,
    key_func: Optional[Callable] = None,
):
    """
    함수 결과 캐싱 데코레이터

    Args:
        cache_name: 사용할 캐시 이름
        ttl: TTL (초), None이면 캐시 기본값 사용
        key_func: 캐시 키 생성 함수, None이면 기본 키 생성
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 캐시 인스턴스 조회
            cache = cache_manager.get_cache(cache_name)

            # 캐시 키 생성
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # 기본 키 생성: 함수명 + 인자 해시
                import hashlib

                args_str = str(args) + str(sorted(kwargs.items()))
                args_hash = hashlib.md5(args_str.encode()).hexdigest()[:8]
                cache_key = f"{func.__name__}:{args_hash}"

            # 캐시에서 조회
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                logger.debug(
                    "cache_decorator_hit", function=func.__name__, cache_key=cache_key
                )
                return cached_result

            # 함수 실행
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time

                # 결과 캐싱
                cache.set(cache_key, result, ttl)

                logger.debug(
                    "cache_decorator_miss",
                    function=func.__name__,
                    cache_key=cache_key,
                    execution_time=execution_time,
                )

                return result

            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(
                    "cache_decorator_error",
                    function=func.__name__,
                    cache_key=cache_key,
                    execution_time=execution_time,
                    error=str(e),
                )
                raise

        return wrapper

    return decorator


def cache_technical_analysis(ttl: int = 600):
    """기술적 분석 결과 캐싱 데코레이터"""
    return cache_result(cache_name="technical_analysis", ttl=ttl)


def cache_news_data(ttl: int = 300):
    """뉴스 데이터 캐싱 데코레이터"""
    return cache_result(cache_name="news", ttl=ttl)


def cache_price_data(ttl: int = 3600):
    """가격 데이터 캐싱 데코레이터"""
    return cache_result(cache_name="price_data", ttl=ttl)


def cache_api_response(ttl: int = 180):
    """API 응답 캐싱 데코레이터"""
    return cache_result(cache_name="api_response", ttl=ttl)


# 캐시 정리 스케줄러
import asyncio
from datetime import datetime


async def cache_cleanup_scheduler():
    """주기적으로 만료된 캐시 항목 정리"""
    while True:
        try:
            await asyncio.sleep(300)  # 5분마다 실행

            results = cache_manager.cleanup_all_expired()
            total_expired = sum(results.values())

            if total_expired > 0:
                logger.info(
                    "scheduled_cache_cleanup",
                    total_expired=total_expired,
                    details=results,
                )

            # 메모리 정리
            gc.collect()

        except Exception as e:
            logger.error("cache_cleanup_scheduler_error", error=str(e))
            await asyncio.sleep(60)  # 에러 시 1분 후 재시도


def start_cache_cleanup_scheduler():
    """캐시 정리 스케줄러 시작"""
    try:
        loop = asyncio.get_event_loop()
        loop.create_task(cache_cleanup_scheduler())
        logger.info("cache_cleanup_scheduler_started")
    except Exception as e:
        logger.error("cache_cleanup_scheduler_start_failed", error=str(e))


class CacheMetrics:
    """캐시 성능 메트릭 수집"""

    def __init__(self):
        self.metrics = {
            "total_requests": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "cache_sets": 0,
            "cache_deletes": 0,
            "cache_evictions": 0,
            "memory_saved_mb": 0.0,
            "avg_response_time_ms": 0.0,
        }
        self._response_times = []
        self._lock = threading.Lock()

    def record_hit(self, response_time_ms: float = 0):
        """캐시 히트 기록"""
        with self._lock:
            self.metrics["total_requests"] += 1
            self.metrics["cache_hits"] += 1
            if response_time_ms > 0:
                self._response_times.append(response_time_ms)
                self._update_avg_response_time()

    def record_miss(self, response_time_ms: float = 0):
        """캐시 미스 기록"""
        with self._lock:
            self.metrics["total_requests"] += 1
            self.metrics["cache_misses"] += 1
            if response_time_ms > 0:
                self._response_times.append(response_time_ms)
                self._update_avg_response_time()

    def record_set(self):
        """캐시 설정 기록"""
        with self._lock:
            self.metrics["cache_sets"] += 1

    def record_delete(self):
        """캐시 삭제 기록"""
        with self._lock:
            self.metrics["cache_deletes"] += 1

    def record_eviction(self):
        """캐시 축출 기록"""
        with self._lock:
            self.metrics["cache_evictions"] += 1

    def record_memory_saved(self, mb: float):
        """메모리 절약량 기록"""
        with self._lock:
            self.metrics["memory_saved_mb"] += mb

    def _update_avg_response_time(self):
        """평균 응답 시간 업데이트"""
        if self._response_times:
            # 최근 1000개 응답 시간만 유지
            if len(self._response_times) > 1000:
                self._response_times = self._response_times[-1000:]

            self.metrics["avg_response_time_ms"] = sum(self._response_times) / len(
                self._response_times
            )

    def get_hit_rate(self) -> float:
        """캐시 히트율 계산"""
        if self.metrics["total_requests"] == 0:
            return 0.0
        return (self.metrics["cache_hits"] / self.metrics["total_requests"]) * 100

    def get_summary(self) -> Dict[str, Any]:
        """메트릭 요약 조회"""
        with self._lock:
            return {
                **self.metrics,
                "hit_rate_percent": round(self.get_hit_rate(), 2),
                "miss_rate_percent": round(100 - self.get_hit_rate(), 2),
            }

    def reset(self):
        """메트릭 초기화"""
        with self._lock:
            self.metrics = {
                "total_requests": 0,
                "cache_hits": 0,
                "cache_misses": 0,
                "cache_sets": 0,
                "cache_deletes": 0,
                "cache_evictions": 0,
                "memory_saved_mb": 0.0,
                "avg_response_time_ms": 0.0,
            }
            self._response_times = []


# 전역 캐시 메트릭
cache_metrics = CacheMetrics()


def get_cache_stats() -> Dict[str, Any]:
    """캐시 통계 조회 (간단 버전)"""
    return cache_manager.get_all_stats()


def get_cache_health_report() -> Dict[str, Any]:
    """캐시 시스템 건강 상태 보고서"""
    all_stats = cache_manager.get_all_stats()
    metrics_summary = cache_metrics.get_summary()

    # 전체 메모리 사용량 계산
    total_memory_mb = sum(stats["memory_usage_mb"] for stats in all_stats.values())
    total_items = sum(stats["cache_size"] for stats in all_stats.values())

    # 평균 히트율 계산
    hit_rates = [
        stats["hit_rate"] for stats in all_stats.values() if stats["hit_rate"] > 0
    ]
    avg_hit_rate = sum(hit_rates) / len(hit_rates) if hit_rates else 0

    return {
        "timestamp": time.time(),
        "overall_health": (
            "healthy"
            if avg_hit_rate > 70
            else "warning" if avg_hit_rate > 50 else "critical"
        ),
        "cache_instances": len(all_stats),
        "total_cached_items": total_items,
        "total_memory_usage_mb": round(total_memory_mb, 2),
        "average_hit_rate": round(avg_hit_rate, 2),
        "global_metrics": metrics_summary,
        "instance_details": all_stats,
    }
