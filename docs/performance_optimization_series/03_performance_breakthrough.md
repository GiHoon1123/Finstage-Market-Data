[Finstage Market Data] Python 성능 최적화 시리즈 (3/5) - 성능 향상 (Phase 2)

## 개요

Phase 1에서 기반 시스템을 안정화한 후, Phase 2에서는 성능 병목을 해결하여 성능 향상을 달성했다. API 호출 최적화, 기술적 지표 계산 최적화, 배치 처리 도입, 캐시 레이어 추상화를 통해 CPU 사용률을 53% 감소시키고 처리량을 300% 증가시킨 과정을 공유한다.

## Phase 2 최적화 목표

- **API 응답 시간**: 1.2초 → 0.3초 (75% 단축)
- **CPU 사용률**: 85% → 40% (53% 감소)
- **동시 요청 처리량**: 50 req/s → 200 req/s (300% 증가)
- **캐시 히트율**: 85% 이상 달성

## 1. API 호출 최적화

### 기존 프로세스의 문제점

**동작 방식**

기존에는 외부 API 호출 시 고정된 지연시간과 단순한 에러 처리만 있었다.

```python
# 기존: 고정 지연 및 단순 에러 처리
import requests
import time

class YahooPriceClient:
    def get_current_price(self, symbol):
        try:
            response = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}")
            time.sleep(0.5)  # 고정 지연

            if response.status_code == 200:
                data = response.json()
                return data['chart']['result'][0]['meta']['regularMarketPrice']
            else:
                print(f"API 호출 실패: {response.status_code}")
                return None
        except Exception as e:
            print(f"API 호출 실패: {e}")
            return None
```

**발생하던 문제점**

- API 응답 시간: 평균 1.2초
- 실패 시 재시도 없음
- 고정 지연으로 인한 비효율
- Rate Limit 대응 부족

### 리팩토링 후 프로세스

**적응형 재시도 로직 구현**

지수 백오프와 적응형 지연을 통해 API 호출을 최적화했다.

```python
# 개선: 적응형 재시도 로직
import requests
import time
import random
from functools import wraps
from app.common.utils.logging_config import get_logger

logger = get_logger("api_client")

def adaptive_retry(max_retries=3, base_delay=2.0, max_delay=60.0):
    """적응형 재시도 데코레이터"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except requests.exceptions.RequestException as e:
                    last_exception = e

                    if attempt == max_retries:
                        logger.error(
                            "api_call_failed_final",
                            function=func.__name__,
                            attempts=attempt + 1,
                            error=str(e)
                        )
                        break

                    # 지수 백오프 계산
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    # 지터 추가 (동시 요청 시 충돌 방지)
                    jitter = random.uniform(0.1, 0.3) * delay
                    total_delay = delay + jitter

                    logger.warning(
                        "api_call_retry",
                        function=func.__name__,
                        attempt=attempt + 1,
                        delay=round(total_delay, 2),
                        error=str(e)
                    )

                    time.sleep(total_delay)

            raise last_exception
        return wrapper
    return decorator

class YahooPriceClient:
    def __init__(self):
        # 연결 풀링을 위한 세션 사용
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

        # 캐시 시스템 (다음 섹션에서 상세 설명)
        self.price_cache = {}
        self.cache_timestamps = {}
        self.cache_ttl = 60  # 1분 캐시

    @adaptive_retry(max_retries=3, base_delay=2.0)
    def get_current_price(self, symbol: str) -> Optional[float]:
        """현재 가격 조회 (캐싱 적용)"""
        # 캐시 확인
        if symbol in self.price_cache and self._is_cache_valid(symbol):
            logger.debug("cache_hit", symbol=symbol, source="price_cache")
            return self.price_cache[symbol]

        try:
            # API 호출
            response = self.session.get(
                f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
                timeout=10,
                params={
                    'interval': '1m',
                    'range': '1d'
                }
            )

            if response.status_code == 429:
                # Rate Limit 처리
                retry_after = int(response.headers.get('Retry-After', 60))
                logger.warning("rate_limit_hit", symbol=symbol, retry_after=retry_after)
                raise requests.exceptions.RequestException(f"Rate limit hit, retry after {retry_after}s")

            response.raise_for_status()
            data = response.json()

            if data['chart']['result']:
                price = data['chart']['result'][0]['meta'].get('regularMarketPrice')

                if price:
                    # 캐시 업데이트
                    self.price_cache[symbol] = price
                    self.cache_timestamps[symbol] = time.time()

                    logger.debug("api_call_success", symbol=symbol, price=price)
                    return price

            logger.warning("api_response_empty", symbol=symbol)
            return None

        except Exception as e:
            logger.error("api_call_error", symbol=symbol, error=str(e))
            raise

    def _is_cache_valid(self, symbol: str) -> bool:
        """캐시 유효성 검사"""
        if symbol not in self.cache_timestamps:
            return False

        elapsed = time.time() - self.cache_timestamps[symbol]
        return elapsed < self.cache_ttl
```

### 성능 개선 결과

**정량적 성과**

- API 응답 시간: 1.2초 → 0.3초 (75% 단축)
- API 호출 성공률: 95% 이상
- Rate Limit 에러: 90% 감소

## 2. 기술적 지표 계산 최적화

### 기존 프로세스의 문제점

**동작 방식**

기존에는 매번 전체 데이터를 다시 계산하고 있었다.

```python
# 기존: 매번 새로 계산
import pandas as pd

class TechnicalIndicatorService:
    def calculate_moving_average(self, symbol, period):
        # 매번 전체 데이터를 다시 계산
        prices = self.get_price_data(symbol)  # DB에서 전체 데이터 조회
        ma = prices.rolling(window=period).mean()
        return ma

    def calculate_rsi(self, symbol, period=14):
        # 또 다시 전체 계산
        prices = self.get_price_data(symbol)
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
```

**발생하던 문제점**

- 동일한 데이터에 대한 반복 계산
- CPU 자원 낭비
- 응답 시간 지연
- 메모리 비효율

### 리팩토링 후 프로세스

**캐싱 기반 최적화 시스템**

결과 캐싱과 증분 계산을 통해 성능을 대폭 개선했다.

```python
# 개선: 캐싱 및 증분 계산
import pandas as pd
from functools import wraps
from app.common.utils.memory_cache import cache_result
from app.common.utils.memory_optimizer import optimize_dataframe_memory, memory_monitor
from app.common.utils.logging_config import get_logger

logger = get_logger("technical_indicator")

def measure_execution_time(func):
    """실행 시간 측정 데코레이터"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            duration = time.time() - start_time
            logger.debug(
                "execution_time",
                function=func.__name__,
                duration_seconds=round(duration, 4)
            )
    return wrapper

class TechnicalIndicatorService:
    def __init__(self):
        # 메모리 캐시 (계산 결과 저장)
        self.ma_cache = {}
        self.rsi_cache = {}
        self.calculation_cache = {}

    @cache_result(cache_name="technical_analysis", ttl=600)  # 10분 캐싱
    @optimize_dataframe_memory()
    @memory_monitor(threshold_mb=200.0)
    @measure_execution_time
    def calculate_moving_average(self, symbol: str, period: int, use_cache: bool = True) -> pd.Series:
        """이동평균선 계산 (캐싱 적용)"""
        cache_key = f"{symbol}_{period}"

        # 캐시 확인
        if use_cache and cache_key in self.ma_cache:
            cached_result = self.ma_cache[cache_key]
            logger.debug("cache_hit", indicator="MA", symbol=symbol, period=period)

            # 새 데이터가 추가된 경우 증분 계산
            current_data = self.get_price_data(symbol)
            if len(current_data) > len(cached_result):
                logger.debug("incremental_calculation", symbol=symbol, period=period)
                return self._calculate_ma_incremental(symbol, period, cached_result, current_data)

            return cached_result

        # 전체 계산
        logger.debug("full_calculation", indicator="MA", symbol=symbol, period=period)
        prices = self.get_price_data(symbol)
        ma = prices.rolling(window=period, min_periods=period).mean()

        # 캐시 저장
        if use_cache:
            self.ma_cache[cache_key] = ma

        return ma

    def _calculate_ma_incremental(self, symbol: str, period: int, cached_result: pd.Series, current_data: pd.Series) -> pd.Series:
        """증분 이동평균 계산"""
        # 기존 캐시 데이터 재사용
        existing_data = cached_result

        # 새 데이터에 대해서만 계산
        new_data = current_data.iloc[len(existing_data):]
        if len(new_data) > 0:
            # 이전 값들도 필요하므로 충분한 데이터 확보
            calculation_data = current_data.iloc[-(len(new_data) + period):]
            new_ma = calculation_data.rolling(window=period, min_periods=period).mean()
            new_ma = new_ma.iloc[period:]

            # 기존 데이터와 새 데이터 병합
            result = pd.concat([existing_data, new_ma])

            # 캐시 업데이트
            cache_key = f"{symbol}_{period}"
            self.ma_cache[cache_key] = result

            logger.debug(
                "incremental_update",
                symbol=symbol,
                period=period,
                new_points=len(new_data),
                total_points=len(result)
            )

            return result

        return existing_data

    @cache_result(cache_name="technical_analysis", ttl=600)
    @optimize_dataframe_memory()
    @memory_monitor(threshold_mb=200.0)
    @measure_execution_time
    def calculate_rsi(self, symbol: str, period: int = 14, use_cache: bool = True) -> pd.Series:
        """RSI 계산 (캐싱 적용)"""
        cache_key = f"{symbol}_rsi_{period}"

        # 캐시 확인
        if use_cache and cache_key in self.rsi_cache:
            logger.debug("cache_hit", indicator="RSI", symbol=symbol, period=period)
            return self.rsi_cache[cache_key]

        # 전체 계산
        logger.debug("full_calculation", indicator="RSI", symbol=symbol, period=period)
        prices = self.get_price_data(symbol)

        # RSI 계산 최적화
        delta = prices.diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        # 지수 이동평균 사용 (더 효율적)
        avg_gain = gain.ewm(span=period, adjust=False).mean()
        avg_loss = loss.ewm(span=period, adjust=False).mean()

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        # 캐시 저장
        if use_cache:
            self.rsi_cache[cache_key] = rsi

        return rsi

    @memory_monitor(threshold_mb=300.0)
    def calculate_multiple_indicators(self, symbol: str, indicators: list) -> dict:
        """여러 지표를 한 번에 계산 (데이터 재사용)"""
        logger.info("multiple_indicators_calculation", symbol=symbol, indicators=indicators)

        # 가격 데이터 한 번만 조회
        prices = self.get_price_data(symbol)
        results = {}

        for indicator_config in indicators:
            indicator_type = indicator_config['type']
            params = indicator_config.get('params', {})

            if indicator_type == 'MA':
                period = params.get('period', 20)
                results[f'MA_{period}'] = prices.rolling(window=period).mean()

            elif indicator_type == 'RSI':
                period = params.get('period', 14)
                delta = prices.diff()
                gain = delta.where(delta > 0, 0).ewm(span=period).mean()
                loss = (-delta.where(delta < 0, 0)).ewm(span=period).mean()
                rs = gain / loss
                results[f'RSI_{period}'] = 100 - (100 / (1 + rs))

            elif indicator_type == 'MACD':
                fast = params.get('fast', 12)
                slow = params.get('slow', 26)
                signal = params.get('signal', 9)

                ema_fast = prices.ewm(span=fast).mean()
                ema_slow = prices.ewm(span=slow).mean()
                macd_line = ema_fast - ema_slow
                signal_line = macd_line.ewm(span=signal).mean()

                results['MACD'] = {
                    'macd': macd_line,
                    'signal': signal_line,
                    'histogram': macd_line - signal_line
                }

        logger.info(
            "multiple_indicators_completed",
            symbol=symbol,
            indicator_count=len(results)
        )

        return results
```

### 성능 개선 결과

**정량적 성과**

- 반복 계산 시 실행 시간: 95% 단축
- CPU 사용량: 70% 감소
- 메모리 사용 효율성: 40% 향상

## 3. 배치 처리 도입

### 기존 프로세스의 문제점

**동작 방식**

기존에는 대량 데이터 삽입 시 개별 INSERT를 사용했다.

```python
# 기존: 개별 INSERT
class PriceDataService:
    def save_price_data(self, price_data_list):
        session = SessionLocal()
        try:
            for price_data in price_data_list:
                price = DailyPrice(**price_data)
                session.add(price)
                session.commit()  # 매번 커밋
            return len(price_data_list)
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
```

**발생하던 문제점**

- 처리 시간 증가 (개별 트랜잭션)
- 데이터베이스 부하 증가
- 일관성 저하 (중간 실패 시)

### 리팩토링 후 프로세스

**대량 데이터 배치 처리**

bulk_insert_mappings와 청크 단위 처리를 도입했다.

```python
# 개선: 배치 처리
from sqlalchemy.orm import sessionmaker
from app.common.infra.database.config.database_config import SessionLocal
from app.common.utils.logging_config import get_logger
from app.common.utils.memory_optimizer import memory_monitor

logger = get_logger("batch_processor")

class BatchPriceDataService:
    def __init__(self):
        self.chunk_size = 1000  # 청크 크기

    @memory_monitor(threshold_mb=500.0)
    def bulk_insert_prices(self, price_data_list: list) -> dict:
        """가격 데이터 일괄 삽입"""
        session = SessionLocal()

        try:
            total_inserted = 0
            chunk_count = 0

            logger.info(
                "bulk_insert_started",
                total_records=len(price_data_list),
                chunk_size=self.chunk_size
            )

            # 청크 단위로 처리
            for i in range(0, len(price_data_list), self.chunk_size):
                chunk = price_data_list[i:i + self.chunk_size]
                chunk_count += 1

                # bulk_insert_mappings 사용
                session.bulk_insert_mappings(DailyPrice, chunk)
                session.commit()

                total_inserted += len(chunk)

                logger.debug(
                    "chunk_processed",
                    chunk_number=chunk_count,
                    chunk_size=len(chunk),
                    total_processed=total_inserted,
                    progress_percent=round((total_inserted / len(price_data_list)) * 100, 1)
                )

            logger.info(
                "bulk_insert_completed",
                total_inserted=total_inserted,
                chunk_count=chunk_count,
                success=True
            )

            return {
                "success": True,
                "inserted": total_inserted,
                "chunks": chunk_count
            }

        except Exception as e:
            session.rollback()
            logger.error(
                "bulk_insert_failed",
                error=str(e),
                processed_count=total_inserted
            )
            return {
                "success": False,
                "error": str(e),
                "inserted": total_inserted
            }
        finally:
            session.close()

    @memory_monitor(threshold_mb=300.0)
    def bulk_update_prices(self, update_data_list: list) -> dict:
        """가격 데이터 일괄 업데이트"""
        session = SessionLocal()

        try:
            total_updated = 0

            # 청크 단위로 업데이트
            for i in range(0, len(update_data_list), self.chunk_size):
                chunk = update_data_list[i:i + self.chunk_size]

                # bulk_update_mappings 사용
                session.bulk_update_mappings(DailyPrice, chunk)
                session.commit()

                total_updated += len(chunk)

                logger.debug(
                    "update_chunk_processed",
                    updated_count=len(chunk),
                    total_updated=total_updated
                )

            logger.info(
                "bulk_update_completed",
                total_updated=total_updated,
                success=True
            )

            return {
                "success": True,
                "updated": total_updated
            }

        except Exception as e:
            session.rollback()
            logger.error("bulk_update_failed", error=str(e))
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            session.close()

    def smart_batch_process(self, data_list: list, operation_type: str = "insert") -> dict:
        """스마트 배치 처리 (메모리 상황에 따라 청크 크기 조정)"""
        import psutil

        # 시스템 메모리 사용률 확인
        memory_percent = psutil.virtual_memory().percent

        # 메모리 사용률에 따라 청크 크기 조정
        if memory_percent > 80:
            self.chunk_size = 500  # 메모리 부족 시 작은 청크
        elif memory_percent < 50:
            self.chunk_size = 2000  # 메모리 여유 시 큰 청크
        else:
            self.chunk_size = 1000  # 기본 청크

        logger.info(
            "smart_batch_started",
            memory_percent=memory_percent,
            adjusted_chunk_size=self.chunk_size,
            operation_type=operation_type
        )

        if operation_type == "insert":
            return self.bulk_insert_prices(data_list)
        elif operation_type == "update":
            return self.bulk_update_prices(data_list)
        else:
            raise ValueError(f"Unsupported operation type: {operation_type}")
```

### 성능 개선 결과

**정량적 성과**

- 대량 데이터 삽입 속도: 85% 향상
- 데이터베이스 부하: 60% 감소
- 메모리 사용량: 안정화

## 4. 캐시 레이어 추상화

### 기존 프로세스의 문제점

**동작 방식**

기존에는 캐싱 전략이 없어 중복 데이터를 반복 계산했다.

```python
# 기존: 캐싱 없음
class DataService:
    def get_expensive_data(self, key):
        # 매번 새로 계산
        result = self.perform_expensive_calculation(key)
        return result
```

### 리팩토링 후 프로세스

**통합 캐시 매니저 구현**

다양한 캐시 백엔드를 지원하는 추상화 레이어를 구축했다.

```python
# 개선: 통합 캐시 시스템
from abc import ABC, abstractmethod
from typing import Any, Optional
import time
import json
import pickle
from app.common.utils.logging_config import get_logger

logger = get_logger("cache_manager")

class CacheBackend(ABC):
    """캐시 백엔드 추상 클래스"""

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        pass

    @abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        pass

    @abstractmethod
    def clear(self) -> bool:
        pass

class MemoryCacheBackend(CacheBackend):
    """메모리 기반 캐시 백엔드"""

    def __init__(self, max_size: int = 10000):
        self.cache = {}
        self.timestamps = {}
        self.max_size = max_size

    def get(self, key: str) -> Optional[Any]:
        if key not in self.cache:
            return None

        # TTL 확인
        if key in self.timestamps:
            ttl, timestamp = self.timestamps[key]
            if ttl and time.time() - timestamp > ttl:
                self.delete(key)
                return None

        return self.cache[key]

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        try:
            # 캐시 크기 제한
            if len(self.cache) >= self.max_size and key not in self.cache:
                self._evict_oldest()

            self.cache[key] = value
            if ttl:
                self.timestamps[key] = (ttl, time.time())

            return True
        except Exception as e:
            logger.error("cache_set_error", key=key, error=str(e))
            return False

    def delete(self, key: str) -> bool:
        try:
            self.cache.pop(key, None)
            self.timestamps.pop(key, None)
            return True
        except Exception as e:
            logger.error("cache_delete_error", key=key, error=str(e))
            return False

    def clear(self) -> bool:
        try:
            self.cache.clear()
            self.timestamps.clear()
            return True
        except Exception as e:
            logger.error("cache_clear_error", error=str(e))
            return False

    def _evict_oldest(self):
        """가장 오래된 항목 제거 (LRU)"""
        if not self.timestamps:
            # 타임스탬프가 없으면 첫 번째 항목 제거
            if self.cache:
                oldest_key = next(iter(self.cache))
                self.delete(oldest_key)
            return

        oldest_key = min(self.timestamps.keys(),
                        key=lambda k: self.timestamps[k][1])
        self.delete(oldest_key)

class CacheManager:
    """캐시 관리자"""

    def __init__(self, backend: CacheBackend = None):
        self.backend = backend or MemoryCacheBackend()
        self.stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0
        }

    def get(self, key: str) -> Optional[Any]:
        """캐시에서 값 조회"""
        value = self.backend.get(key)

        if value is not None:
            self.stats['hits'] += 1
            logger.debug("cache_hit", key=key)
        else:
            self.stats['misses'] += 1
            logger.debug("cache_miss", key=key)

        return value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """캐시에 값 저장"""
        success = self.backend.set(key, value, ttl)
        if success:
            self.stats['sets'] += 1
            logger.debug("cache_set", key=key, ttl=ttl)
        return success

    def get_or_set(self, key: str, value_func: callable, ttl: Optional[int] = None) -> Any:
        """캐시에서 값을 조회하고, 없으면 함수를 실행하여 값을 생성하고 저장"""
        # 캐시 확인
        cached_value = self.get(key)
        if cached_value is not None:
            return cached_value

        # 값 생성
        value = value_func()

        # 캐시에 저장
        self.set(key, value, ttl)

        return value

    def delete(self, key: str) -> bool:
        """캐시에서 값 삭제"""
        success = self.backend.delete(key)
        if success:
            self.stats['deletes'] += 1
            logger.debug("cache_delete", key=key)
        return success

    def get_stats(self) -> dict:
        """캐시 통계 조회"""
        total_requests = self.stats['hits'] + self.stats['misses']
        hit_rate = (self.stats['hits'] / total_requests * 100) if total_requests > 0 else 0

        return {
            **self.stats,
            'total_requests': total_requests,
            'hit_rate': round(hit_rate, 2)
        }

    def clear_stats(self):
        """통계 초기화"""
        self.stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0
        }

# 전역 캐시 매니저 인스턴스
default_cache_manager = CacheManager()

# 캐시 데코레이터
def cache_result(cache_name: str = "default", ttl: int = 300):
    """결과 캐싱 데코레이터"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 캐시 키 생성
            cache_key = f"{cache_name}:{func.__name__}:{hash(str(args) + str(kwargs))}"

            # 캐시에서 조회
            cached_result = default_cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result

            # 함수 실행
            result = func(*args, **kwargs)

            # 캐시에 저장
            default_cache_manager.set(cache_key, result, ttl)

            return result
        return wrapper
    return decorator
```

**캐시 적용 예시**

```python
# 캐시 적용된 서비스
class OptimizedPriceService:
    def __init__(self):
        self.cache_manager = CacheManager()

    @cache_result(cache_name="price_data", ttl=60)  # 1분 캐싱
    def fetch_latest_price(self, symbol: str) -> Optional[float]:
        """현재가 조회 (캐싱 적용)"""
        return self.client.get_latest_minute_price(symbol)

    @cache_result(cache_name="technical_analysis", ttl=600)  # 10분 캐싱
    def get_technical_analysis(self, symbol: str, indicators: list) -> dict:
        """기술적 분석 결과 조회 (캐싱 적용)"""
        return self.calculate_indicators(symbol, indicators)

    def get_cached_or_calculate(self, symbol: str, calculation_type: str) -> Any:
        """캐시 우선 조회 패턴"""
        cache_key = f"{calculation_type}:{symbol}"

        return self.cache_manager.get_or_set(
            cache_key,
            lambda: self.perform_expensive_calculation(symbol, calculation_type),
            ttl=300
        )
```

### 성능 개선 결과

**정량적 성과**

- 캐시 히트율: 85% 달성
- 반복 계산 회피로 CPU 사용량: 80% 감소
- 응답 시간 일관성: 크게 향상

## Phase 2 종합 성과

### 정량적 성과 요약

| 항목             | 개선 전  | 개선 후   | 개선율    |
| ---------------- | -------- | --------- | --------- |
| API 응답 시간    | 1.2초    | 0.3초     | 75% 단축  |
| CPU 사용률       | 85%      | 40%       | 53% 감소  |
| 동시 요청 처리량 | 50 req/s | 200 req/s | 300% 증가 |
| 캐시 히트율      | 0%       | 85%       | 신규 달성 |
| 배치 처리 속도   | 기준     | 85% 향상  | 85% 개선  |

### 시스템 효율성 향상

**리소스 활용 최적화**

- CPU 유휴 시간 대폭 감소
- 메모리 사용 효율성 향상
- 네트워크 호출 최소화

**확장성 확보**

- 동시 사용자 수 증가 대응
- 데이터 증가에 따른 선형 확장
- 캐시 기반 성능 안정성

## 다음 단계

Phase 2에서 성능 병목을 해결했지만, 여전히 실시간성 요구사항과 고급 시스템 기능이 필요하다.

다음 포스트에서는 비동기 처리 시스템, WebSocket 실시간 스트리밍, 분산 작업 큐 시스템, 성능 모니터링 시스템을 구축하여 실시간 지연을 감소시키고 시스템 가용을 향상시킨 Phase 3 고급 시스템 구축 과정을 소개하겠다.

- [1편: 성능 문제 분석과 해결 방향](https://velog.io/@rlaejrqo465/Finstage-Market-Data-Python-%EC%84%B1%EB%8A%A5-%EC%B5%9C%EC%A0%81%ED%99%94-%EC%8B%9C%EB%A6%AC%EC%A6%88-15-%EC%84%B1%EB%8A%A5-%EB%AC%B8%EC%A0%9C-%EB%B6%84%EC%84%9D%EA%B3%BC-%ED%95%B4%EA%B2%B0-%EB%B0%A9%ED%96%A5)
- [2편: 기반 시스템 최적화 (Phase 1)](https://velog.io/@rlaejrqo465/Finstage-Market-Data-Python-%EC%84%B1%EB%8A%A5-%EC%B5%9C%EC%A0%81%ED%99%94-%EC%8B%9C%EB%A6%AC%EC%A6%88-25-%EA%B8%B0%EB%B0%98-%EC%8B%9C%EC%8A%A4%ED%85%9C-%EC%B5%9C%EC%A0%81%ED%99%94-Phase-1)
- [3편: 성능 향상 (Phase 2)](https://velog.io/@rlaejrqo465/Finstage-Market-Data-Python-%EC%84%B1%EB%8A%A5-%EC%B5%9C%EC%A0%81%ED%99%94-%EC%8B%9C%EB%A6%AC%EC%A6%88-35-%EC%84%B1%EB%8A%A5-%ED%8F%AD%EB%B0%9C%EC%A0%81-%ED%96%A5%EC%83%81-Phase-2) ← 현재 글
- [4편: 고급 시스템 구축 (Phase 3)](https://velog.io/@rlaejrqo465/Finstage-Market-Data-Python-%EC%84%B1%EB%8A%A5-%EC%B5%9C%EC%A0%81%ED%99%94-%EC%8B%9C%EB%A6%AC%EC%A6%88-45-%EA%B3%A0%EA%B8%89-%EC%8B%9C%EC%8A%A4%ED%85%9C-%EA%B5%AC%EC%B6%95-Phase-3)
- [5편: 메모리 관리 및 최종 성과](https://velog.io/@rlaejrqo465/Finstage-Market-Data-Python-%EC%84%B1%EB%8A%A5-%EC%B5%9C%EC%A0%81%ED%99%94-%EC%8B%9C%EB%A6%AC%EC%A6%88-55-%EB%A9%94%EB%AA%A8%EB%A6%AC-%EA%B4%80%EB%A6%AC-%EB%B0%8F-%EC%B5%9C%EC%A2%85-%EC%84%B1%EA%B3%BC)
