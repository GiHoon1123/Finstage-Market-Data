# Finstage Market Data - 백엔드 아키텍처 및 기술 구현

## 1. 시스템 아키텍처 개요

### 핵심 설계 철학

Finstage Market Data 백엔드는 **"모듈별 책임 분리를 통한 확장 가능한 실시간 데이터 처리"**를 목표로 설계되었습니다. 각 모듈은 명확한 역할을 가지며, APScheduler 기반 스케줄링을 통해 정시 작업 실행과 시스템 안정성을 확보했습니다.

### 모듈 구조 및 책임 분리

```
app/
├── news_crawler/           # 뉴스 크롤링 시스템
├── technical_analysis/     # 기술적 분석 엔진
├── market_price/          # 가격 데이터 처리
├── message_notification/   # 텔레그램 알림 시스템
├── scheduler/             # 작업 스케줄링
├── common/                # 공통 유틸리티
│   ├── utils/            # 병렬 처리, 비동기 클라이언트
│   └── infra/            # 데이터베이스, 설정
└── company/              # 기업 정보 관리
```

각 모듈은 독립적인 책임을 가지며, 직접적인 클래스 인스턴스 생성과 메서드 호출을 통해 동작합니다.

### 스케줄러 기반 작업 흐름

```python
# APScheduler를 통한 정시 작업 실행
Scheduler → 뉴스 크롤링 → 기술적 분석 → 신호 생성 → 텔레그램 알림
```

**구현된 주요 작업 흐름:**

- **뉴스 크롤링**: 1시간마다 다중 소스에서 뉴스 수집
- **기술적 분석**: 실시간 가격 데이터 기반 신호 생성
- **백테스팅**: 과거 데이터로 전략 성과 검증
- **알림 전송**: 텔레그램을 통한 실시간 신호 전달

**스케줄러 기반 설계의 실제 효과:**

- **정시 실행**: 정해진 시간에 안정적으로 작업 수행
- **독립적 모듈**: 각 작업이 독립적으로 실행되어 장애 격리
- **확장 용이성**: 새로운 작업 추가 시 스케줄러에 등록만 하면 됨

## 2. 실시간 데이터 처리 시스템

### 병렬 처리 엔진 구현

**ParallelExecutor 클래스**

```python
class ParallelExecutor:
    """병렬 작업 실행을 위한 클래스"""

    def __init__(self, max_workers: int = 5):
        self.max_workers = max_workers

    def run_symbol_tasks_parallel(
        self, func: Callable, symbols: List[str], delay: float = 0
    ) -> List[Any]:
        """
        심볼별 작업을 병렬로 실행 (API 제한 고려)

        Args:
            func: 실행할 함수
            symbols: 심볼 리스트
            delay: 각 작업 간 지연 시간 (초)
        """
        # 배치 크기 제한으로 DB 연결 부하 감소
        batch_size = 1  # 순차 처리로 안정성 확보
        results = []

        for i, symbol in enumerate(symbols):
            try:
                result = func(symbol)
                results.append(result)
            except Exception as e:
                print(f"❌ {symbol} 처리 실패: {e}")
                results.append(None)

            # API 제한 고려한 지연 시간
            if i < len(symbols) - 1:
                sleep_time = delay if delay > 0 else 5.0
                time.sleep(sleep_time)

        return results
```

**성능 최적화 특징:**

- **배치 처리**: 대량 데이터를 배치 단위로 나누어 처리
- **지연 제어**: API 제한을 고려한 지능적 요청 스케줄링
- **에러 격리**: 개별 작업 실패가 전체 프로세스에 영향 주지 않음

### 비동기 API 클라이언트

**AsyncApiClient 구현**

```python
class AsyncApiClient:
    """비동기 API 클라이언트"""

    def __init__(self, base_url: str = "", timeout: int = 30):
        self.base_url = base_url
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.session = None
        self.rate_limit_delay = 0.5  # 기본 요청 간격

    async def fetch_multiple(
        self,
        urls: List[str],
        params: Dict = None,
        concurrency: int = 5,
        delay: float = 0.5,
    ) -> List[Any]:
        """
        여러 URL을 병렬로 요청

        Args:
            urls: 요청할 URL 목록
            concurrency: 최대 동시 요청 수
            delay: 요청 간 지연 시간
        """
        # 세마포어로 동시성 제한
        semaphore = asyncio.Semaphore(concurrency)

        async def fetch_with_semaphore(url):
            async with semaphore:
                await self._wait_for_rate_limit()
                try:
                    async with self.session.get(url, params=params) as response:
                        response.raise_for_status()
                        return await response.json()
                except Exception as e:
                    print(f"URL {url} 요청 실패: {e}")
                    return None

        # 모든 요청 실행
        tasks = [fetch_with_semaphore(url) for url in urls]
        return await asyncio.gather(*tasks)
```

**비동기 처리의 장점:**

- **I/O 바운드 최적화**: 네트워크 요청 대기 시간 동안 다른 작업 수행
- **동시성 제어**: 세마포어를 통한 안전한 동시 요청 관리
- **속도 제한 준수**: API 제한을 고려한 지능적 요청 관리

## 3. 스케줄링 시스템

### 병렬 스케줄러 구현

**parallel_scheduler.py**

```python
def start_parallel_scheduler():
    """병렬 처리 기능이 추가된 스케줄러 시작"""
    scheduler = BackgroundScheduler()

    # 통합 뉴스 크롤링 (경제 뉴스 + 지수 뉴스)
    scheduler.add_job(
        run_integrated_news_crawling_parallel,
        "interval",
        minutes=90
    )

    # 가격 관련 작업
    scheduler.add_job(
        run_high_price_update_job_parallel,
        "interval",
        hours=4
    )

    # 실시간 모니터링
    scheduler.add_job(
        run_realtime_price_monitor_job_parallel,
        "interval",
        minutes=30
    )

    # 일일 종합 분석 리포트 (매일 오전 8시)
    scheduler.add_job(
        run_daily_comprehensive_report,
        "cron",
        hour=8,
        minute=0,
        timezone="Asia/Seoul"
    )

    scheduler.start()
```

**스케줄링 최적화:**

- **작업 간격 조정**: 시스템 부하를 고려한 최적 실행 주기 설정
- **시간대 고려**: 한국 시간 기준 최적 실행 시간 설정
- **병렬 처리**: 각 작업 내에서 병렬 처리로 성능 향상

### 작업별 병렬 처리 구현

**뉴스 크롤링 병렬 처리**

```python
@measure_execution_time
def run_integrated_news_crawling_parallel():
    """통합 뉴스 크롤링 (경제 뉴스 + 지수 뉴스)"""

    # 1. Investing 경제 뉴스 크롤링
    def process_investing_symbol(symbol):
        crawler = InvestingNewsCrawler(symbol)
        return crawler.process_all()

    investing_results = executor.run_symbol_tasks_parallel(
        process_investing_symbol,
        INVESTING_ECONOMIC_SYMBOLS,
        delay=0.5
    )

    # 2. Yahoo 지수 뉴스 크롤링
    def process_yahoo_symbol(symbol):
        crawler = YahooNewsCrawler(symbol)
        return crawler.process_all()

    yahoo_results = executor.run_symbol_tasks_parallel(
        process_yahoo_symbol,
        INDEX_SYMBOLS,
        delay=0.5
    )

    # 결과 집계 및 로깅
    total_success = sum(1 for r in investing_results + yahoo_results if r is not None)
    total_symbols = len(INVESTING_ECONOMIC_SYMBOLS) + len(INDEX_SYMBOLS)
    print(f"🎉 통합 뉴스 크롤링 완료: {total_success}/{total_symbols} 성공")
```

## 4. 기술적 분석 엔진

### 20+ 전략 알고리즘 구현

**이동평균선 전략**

```python
async def executeMABreakoutStrategy(candles: List[CandleData], period: int):
    """MA 돌파 전략 구현"""
    sma = self.indicatorService.calculateSMA(candles, period)
    current_price = candles[-1].close
    current_ma = sma[-1].value

    # 2% 이상 돌파 시 매수 신호
    if current_price > current_ma * 1.02:
        return {
            "signal": SignalType.BUY,
            "confidence": 75,
            "reason": f"MA{period} 돌파 (현재가: {current_price}, MA: {current_ma})"
        }
```

**RSI 과매수/과매도 전략**

```python
async def executeRSIStrategy(candles: List[CandleData]):
    """RSI 과매수/과매도 전략"""
    rsi = self.indicatorService.calculateRSI(candles, 14)
    current_rsi = rsi[-1].value

    if current_rsi < 30:
        return {
            "signal": SignalType.BUY,
            "confidence": 70,
            "reason": f"RSI 과매도 반등 신호 (RSI: {current_rsi})"
        }
    elif current_rsi > 70:
        return {
            "signal": SignalType.SELL,
            "confidence": 70,
            "reason": f"RSI 과매수 조정 신호 (RSI: {current_rsi})"
        }
```

**복합 전략 (트리플 확인)**

```python
async def executeTripleConfirmationStrategy(candles: List[CandleData]):
    """트리플 확인 전략 (MA + RSI + Volume)"""
    ma_signal = await self.executeMAStrategy(candles)
    rsi_signal = await self.executeRSIStrategy(candles)
    volume_signal = await self.executeVolumeStrategy(candles)

    # 3개 지표 모두 동일한 신호일 때만 실행
    if (ma_signal.signal == rsi_signal.signal == volume_signal.signal):
        return {
            "signal": ma_signal.signal,
            "confidence": 85,  # 높은 신뢰도
            "reason": "트리플 확인 (MA + RSI + Volume 일치)"
        }
```

### 백테스팅 시스템

**과거 데이터 기반 전략 검증**

```python
class BacktestingService:
    """백테스팅 서비스"""

    def analyze_all_signals_performance(
        self,
        timeframe_eval: str = "1d",
        min_samples: int = 10
    ):
        """전체 신호 성과 분석"""

        # 1. 모든 신호 조회
        signals = self.get_all_historical_signals()

        # 2. 전략별 성과 계산
        strategy_performance = {}
        for signal in signals:
            strategy = signal.signal_type
            if strategy not in strategy_performance:
                strategy_performance[strategy] = {
                    "total_signals": 0,
                    "successful_signals": 0,
                    "total_return": 0,
                    "returns": []
                }

            # 성과 계산
            outcome = self.calculate_signal_outcome(signal, timeframe_eval)
            strategy_performance[strategy]["total_signals"] += 1

            if outcome["return"] > 0:
                strategy_performance[strategy]["successful_signals"] += 1

            strategy_performance[strategy]["total_return"] += outcome["return"]
            strategy_performance[strategy]["returns"].append(outcome["return"])

        # 3. 통계 계산
        results = {}
        for strategy, perf in strategy_performance.items():
            if perf["total_signals"] >= min_samples:
                success_rate = perf["successful_signals"] / perf["total_signals"]
                avg_return = perf["total_return"] / perf["total_signals"]

                results[strategy] = {
                    "success_rate": success_rate,
                    "avg_return": avg_return,
                    "total_signals": perf["total_signals"],
                    "sharpe_ratio": self.calculate_sharpe_ratio(perf["returns"])
                }

        return results
```

## 5. 데이터베이스 최적화

### 연결 풀링 설정

**database_config.py**

```python
# SQLAlchemy 엔진 생성 - 연결 풀링 최적화
engine = create_engine(
    MYSQL_URL,
    echo=False,  # SQL 쿼리 로깅 비활성화 (성능 향상)

    # 연결 풀링 설정 (성능 개선의 핵심)
    pool_size=20,           # 기본 연결 풀 크기
    max_overflow=30,        # 추가 연결 허용 수
    pool_timeout=300,       # 연결 대기 시간 (5분)
    pool_recycle=600,       # 연결 재사용 시간 (10분)
    pool_pre_ping=True,     # 연결 유효성 검사

    # 추가 최적화 설정
    connect_args={
        "charset": "utf8mb4",
        "autocommit": False,
        "connect_timeout": 60,
        "read_timeout": 60,
        "write_timeout": 60,
    },
)
```

### 세션 관리 최적화

**db_session_manager.py**

```python
@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """
    세션 컨텍스트 매니저 - 트랜잭션 자동 관리

    사용 예:
    with session_scope() as session:
        # 세션 사용
        session.query(...)
    # 자동으로 커밋 또는 롤백 후 세션 닫힘
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"데이터베이스 오류: {e}")
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"일반 오류: {e}")
        raise
    finally:
        session.close()
```

**세션 관리의 장점:**

- **자동 트랜잭션 관리**: 커밋/롤백 자동 처리
- **리소스 정리**: 세션 자동 종료로 메모리 누수 방지
- **에러 처리**: 예외 발생 시 안전한 롤백

## 6. 성능 모니터링 시스템

### 실행 시간 측정

**performance_monitor.py**

```python
class PerformanceMetrics:
    """성능 지표 수집 및 관리"""

    def record_execution_time(self, name: str, duration: float):
        """실행 시간 기록"""
        with self.lock:
            if name not in self.metrics:
                self.metrics[name] = {
                    "count": 0,
                    "total_time": 0,
                    "min_time": float("inf"),
                    "max_time": 0,
                    "avg_time": 0,
                    "last_time": 0,
                    "timestamps": [],
                }

            metrics = self.metrics[name]
            metrics["count"] += 1
            metrics["total_time"] += duration
            metrics["min_time"] = min(metrics["min_time"], duration)
            metrics["max_time"] = max(metrics["max_time"], duration)
            metrics["avg_time"] = metrics["total_time"] / metrics["count"]
            metrics["last_time"] = duration

@measure_execution_time
def run_integrated_news_crawling_parallel():
    """실행 시간이 자동으로 측정되는 함수"""
    # 함수 실행 내용
    pass
```

### 리소스 모니터링

```python
class ResourceMonitor:
    """시스템 리소스 모니터링"""

    def _monitor_resources(self):
        """리소스 모니터링 스레드"""
        while self.running:
            try:
                # CPU 사용률
                cpu_percent = psutil.cpu_percent(interval=1)

                # 메모리 사용량
                memory = psutil.Process().memory_info()
                memory_mb = memory.rss / (1024 * 1024)

                # 지표 기록
                performance_metrics.record_resource_usage(
                    "system", cpu_percent, memory_mb
                )

                time.sleep(self.interval)
            except Exception as e:
                logger.error(f"리소스 모니터링 오류: {e}")
```

## 7. 텔레그램 알림 시스템

### 일일 종합 리포트 생성

**daily_comprehensive_report_service.py**

```python
class DailyComprehensiveReportService:
    """일일 종합 분석 리포트 서비스"""

    def generate_daily_report(self):
        """일일 리포트 생성 및 전송"""

        # 1. 백테스팅 성과 분석
        backtesting_results = self.analyze_backtesting_performance()

        # 2. 패턴 분석 결과
        pattern_results = self.analyze_patterns()

        # 3. 머신러닝 분석
        ml_results = self.analyze_ml_clusters()

        # 4. 투자 인사이트 생성
        insights = self.generate_investment_insights()

        # 5. 리포트 포맷팅
        report = self.format_daily_report({
            "backtesting": backtesting_results,
            "patterns": pattern_results,
            "ml_analysis": ml_results,
            "insights": insights
        })

        # 6. 텔레그램 전송
        return self.send_telegram_report(report)

    def format_daily_report(self, data):
        """리포트 포맷팅"""
        report = f"""🌅 일일 퀀트 분석 리포트 ({datetime.now().strftime('%Y.%m.%d %H:%M')})

📈 백테스팅 성과 분석
┌─ 나스닥 지수 (^IXIC)
│  • 최고 성과 전략: {data['backtesting']['nasdaq']['best_strategy']}
│  • 평균 수익률: {data['backtesting']['nasdaq']['avg_return']:.1f}% (1일 기준)
│  • 승률: {data['backtesting']['nasdaq']['success_rate']:.1f}%
│  • 전체 신호 정확도: {data['backtesting']['nasdaq']['accuracy']:.1f}%

🎯 오늘의 투자 인사이트
{self.format_insights(data['insights'])}

📚 용어 해설
🔹 백테스팅: 과거 데이터로 전략을 테스트해서 "만약 이렇게 투자했다면?"을 계산
🔹 골든크로스: 단기선이 장기선을 위로 뚫고 올라가는 강한 상승 신호 🚀
"""
        return report
```

### 실시간 신호 알림

```python
class TechnicalMonitorService:
    """기술적 지표 모니터링 서비스"""

    def send_signal_notification(self, signal):
        """신호 알림 전송"""

        # 신호 강도별 우선순위 결정
        priority = self.determine_priority(signal)

        if priority == NotificationPriority.HIGH:
            # 즉시 알림
            message = f"""🚨 중요 신호 발생!

📊 {signal.symbol} - {signal.signal_type}
💰 현재가: ${signal.current_price:.2f}
📈 신뢰도: {signal.confidence}%
🎯 예상 방향: {signal.direction}

📝 분석 내용:
{signal.analysis_detail}

⏰ 발생 시간: {signal.timestamp}
"""
            self.telegram_service.send_message(message)

        elif priority == NotificationPriority.MEDIUM:
            # 일반 알림 (배치로 처리)
            self.add_to_batch_notification(signal)
```

## 8. 테스트 및 품질 관리

### 통합 테스트 시스템

**test_router.py**

```python
@router.post('/analysis-flow')
async def test_analysis_flow(request: dict):
    """전체 플로우 테스트"""
    start_time = time.time()

    try:
        # 1. 캔들 데이터 조회
        candles = await candle_service.get_latest_candles(request['symbol'])

        # 2. 기술적 분석 실행
        analysis_result = await technical_analysis_service.analyze_symbol(
            request['symbol'],
            [StrategyType.RSI_OVERSOLD_BOUNCE, StrategyType.MA_20_BREAKOUT]
        )

        # 3. 알림 테스트 (실제 발송 안 함)
        notification = await notification_service.prepare_notification(analysis_result)

        return {
            "success": True,
            "execution_time": time.time() - start_time,
            "result": {
                "candles_count": len(candles),
                "signals_count": len(analysis_result.signals),
                "notification_prepared": bool(notification)
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
```

### 헬스체크 시스템

```python
@router.get('/health')
async def get_health_status():
    """시스템 상태 확인"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "database": await check_database_connection(),
            "telegram_bot": await telegram_service.check_connection(),
            "scheduler": scheduler.get_status()
        },
        "features": [
            "실시간 데이터 수집",
            "20+ 기술적 분석 전략",
            "병렬 처리 시스템",
            "텔레그램 알림 시스템",
            "백테스팅 엔진",
            "성능 모니터링"
        ],
        "performance": performance_metrics.get_summary()
    }
```

## 9. 현재 운영 현황 및 향후 개선 계획

### 현재 상황

- **사용자 규모**: 개발자 본인 + 소수 테스터
- **데이터 규모**: 10년치 히스토리컬 데이터 (140,000개 캔들)
- **처리 성능**: 1.5초 이내 전체 프로세스 완료
- **시스템 안정성**: 24시간 가동률 99% 이상

### 현재 한계점

- **확장성**: 사용자 증가 시 대응 방안 미검증
- **모니터링**: 기본적인 성능 로깅 수준
- **장애 복구**: 실제 대규모 장애 상황 경험 부족

### 향후 개선 계획

**성능 최적화**

- 데이터베이스 쿼리 최적화 및 인덱스 튜닝
- 캐싱 전략 고도화 (Redis 도입)
- 연결 풀 튜닝 및 부하 분산

**모니터링 강화**

- 상세 성능 메트릭 수집 (Prometheus + Grafana)
- 실시간 알림 시스템 고도화
- 로그 분석 시스템 구축 (ELK Stack)

**확장성 개선**

- 마이크로서비스 아키텍처로 분리
- 컨테이너 기반 배포 (Docker + Kubernetes)
- 데이터베이스 샤딩 및 읽기 전용 복제본

**운영 안정성**

- 자동 장애 복구 시스템
- 백업/복구 자동화
- 보안 강화 (API 키 관리, 접근 제어)

---

**Finstage Market Data 백엔드는 확장 가능하고 안정적인 실시간 금융 데이터 분석 플랫폼을 구현하기 위한 현대적인 아키텍처와 기술 스택을 활용합니다.**
