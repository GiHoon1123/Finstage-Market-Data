import time
from datetime import datetime, timedelta
from sqlalchemy import text
from apscheduler.schedulers.background import BackgroundScheduler
from app.news_crawler.service.investing_news_crawler import InvestingNewsCrawler
from app.news_crawler.service.yahoo_news_crawler import YahooNewsCrawler
from app.market_price.service.price_high_record_service import PriceHighRecordService
from app.market_price.service.price_snapshot_service import PriceSnapshotService
from app.market_price.service.price_monitor_service import PriceMonitorService
from app.technical_analysis.service.technical_monitor_service import (
    TechnicalMonitorService,
)
from app.technical_analysis.service.outcome_tracking_service import (
    OutcomeTrackingService,
)
from app.technical_analysis.service.daily_data_collection_service import (
    DailyDataCollectionService,
)
from app.technical_analysis.service.historical_data_service import (
    HistoricalDataService,
)
from app.technical_analysis.service.signal_generator_service import (
    SignalGeneratorService,
)
from app.technical_analysis.service.backtesting_service import (
    BacktestingService,
)
from app.technical_analysis.service.pattern_analysis_service import (
    PatternAnalysisService,
)
from app.common.infra.database.config.database_config import (
    Base,
    engine,
    SessionLocal,
)
from app.technical_analysis.infra.model.entity.daily_prices import DailyPrice
from app.technical_analysis.infra.model.entity.technical_signals import (
    TechnicalSignal,
)
from app.technical_analysis.infra.model.entity.signal_outcomes import (
    SignalOutcome,
)
from app.technical_analysis.infra.model.entity.signal_patterns import (
    SignalPattern,
)
from app.technical_analysis.infra.model.repository.technical_signal_repository import (
    TechnicalSignalRepository,
)
from app.technical_analysis.infra.model.repository.technical_signal_repository import (
    TechnicalSignalRepository,
)
from app.technical_analysis.infra.model.entity.daily_prices import DailyPrice
from app.technical_analysis.infra.model.entity.technical_signals import (
    TechnicalSignal,
)
from app.technical_analysis.infra.model.entity.signal_outcomes import (
    SignalOutcome,
)
from app.technical_analysis.infra.model.entity.signal_patterns import (
    SignalPattern,
)
from app.common.constants.symbol_names import (
    INDEX_SYMBOLS,
    FUTURES_SYMBOLS,
    STOCK_SYMBOLS,
    SYMBOL_PRICE_MAP,
)
from app.common.constants.rss_feeds import (
    INVESTING_ECONOMIC_SYMBOLS,
    INVESTING_MARKET_SYMBOLS,
)
from app.common.utils.parallel_executor import (
    ParallelExecutor,
    measure_execution_time,
)
from app.common.infra.database.config.database_config import (
    Base,
    engine,
    SessionLocal,
)


def run_investing_economic_news():
    print("📡 Investing 경제 뉴스 크롤링 시작")

    for symbol in INVESTING_ECONOMIC_SYMBOLS:
        print(f"🔍 {symbol} 뉴스 처리 중...")
        InvestingNewsCrawler(symbol).process_all()

    print("✅ Investing 경제 뉴스 크롤링 완료")


def run_investing_market_news():
    print("📡 Investing 시장 뉴스 크롤링 시작")

    for symbol in INVESTING_MARKET_SYMBOLS:
        print(f"🔍 {symbol} 뉴스 처리 중...")
        InvestingNewsCrawler(symbol).process_all()

    print("✅ Investing 시장 뉴스 크롤링 완료")


def run_yahoo_futures_news():
    print("🕒 Yahoo 선물 뉴스 크롤링 시작")
    for symbol in FUTURES_SYMBOLS:
        print(f"🔍 {symbol} 뉴스 처리 중...")
        YahooNewsCrawler(symbol).process_all()

    print("✅ Yahoo 선물 뉴스 크롤링 완료")


def run_yahoo_index_news():
    print("🕒 Yahoo 지수 뉴스 크롤링 시작")
    for symbol in INDEX_SYMBOLS:
        print(f"🔍 {symbol} 뉴스 처리 중...")
        YahooNewsCrawler(symbol).process_all()

    print("✅ Yahoo 지수 뉴스 크롤링 완료")


def run_yahoo_stock_news():
    print("🕒 Yahoo 종목 뉴스 크롤링 시작")
    for symbol in STOCK_SYMBOLS:
        print(f"🔍 {symbol} 뉴스 처리 중...")
        YahooNewsCrawler(symbol).process_all()

    print("✅ Yahoo 종목 뉴스 크롤링 완료")


def run_high_price_update_job():
    print("📈 상장 후 최고가 갱신 시작")

    @measure_execution_time
    def process_symbol(symbol):
        service = PriceHighRecordService()
        return service.update_all_time_high(symbol)

    executor = ParallelExecutor(max_workers=5)
    results = executor.run_symbol_tasks_parallel(
        process_symbol, list(SYMBOL_PRICE_MAP), delay=1.0
    )

    success_count = sum(1 for r in results if r is not None)
    print(f"✅ 최고가 갱신 완료: {success_count}/{len(SYMBOL_PRICE_MAP)} 성공")


def run_previous_close_snapshot_job():
    print("🕓 전일 종가 저장 시작")

    @measure_execution_time
    def process_symbol(symbol):
        service = PriceSnapshotService()
        return service.save_previous_close_if_needed(symbol)

    executor = ParallelExecutor(max_workers=5)
    results = executor.run_symbol_tasks_parallel(
        process_symbol, list(SYMBOL_PRICE_MAP), delay=1.0
    )

    success_count = sum(1 for r in results if r is not None)
    print(f"✅ 전일 종가 저장 완료: {success_count}/{len(SYMBOL_PRICE_MAP)} 성공")


def run_previous_high_snapshot_job():
    print("🔺 전일 고점 저장 시작")

    @measure_execution_time
    def process_symbol(symbol):
        service = PriceSnapshotService()
        return service.save_previous_high_if_needed(symbol)

    executor = ParallelExecutor(max_workers=5)
    results = executor.run_symbol_tasks_parallel(
        process_symbol, list(SYMBOL_PRICE_MAP), delay=1.0
    )

    success_count = sum(1 for r in results if r is not None)
    print(f"✅ 전일 고점 저장 완료: {success_count}/{len(SYMBOL_PRICE_MAP)} 성공")


def run_previous_low_snapshot_job():
    print("🔻 전일 저점 저장 시작")
    service = PriceSnapshotService()
    for symbol in SYMBOL_PRICE_MAP:
        time.sleep(5.0)
        service.save_previous_low_if_needed(symbol)
    print("✅ 전일 저점 저장 완료")


def run_realtime_price_monitor_job():
    print("📡 실시간 가격 모니터링 시작")
    service = PriceMonitorService()
    for symbol in SYMBOL_PRICE_MAP:
        time.sleep(5.0)
        service.check_price_against_baseline(symbol)

    print("✅ 실시간 가격 모니터링 완료")


# =============================================================================
# 기술적 지표 모니터링 작업들
# =============================================================================


def run_daily_index_analysis():
    """
    주요 지수 상태 리포트 생성 및 전송
    - 나스닥 지수 (^IXIC): 기술주 중심
    - S&P 500 지수 (^GSPC): 전체 시장
    - 기존 임계점 돌파 알림 → 상태 리포트 형태로 변경
    - 1시간마다 실행하여 현재 상태 정보 제공
    """
    print("📊 주요 지수 상태 리포트 생성 시작")
    try:
        # 🆕 1단계: 최신 일봉 데이터 수집 및 저장

        collection_service = DailyDataCollectionService()
        collection_result = collection_service.collect_and_save_daily_data(
            ["^IXIC", "^GSPC"]
        )

        print(
            f"   💾 데이터 수집 결과: 수집 {collection_result.get('summary', {}).get('collected', 0)}개, "
            f"스킵 {collection_result.get('summary', {}).get('skipped', 0)}개"
        )

        # 🆕 2단계: 상태 리포트 생성 및 전송 (기존 + 신규 전략 통합)
        service = TechnicalMonitorService()

        # 한시간마다 상태 리포트 생성 (임계점 돌파 대신)
        service.run_hourly_status_report()

        print("✅ 주요 지수 상태 리포트 생성 완료")
    except Exception as e:
        print(f"❌ 주요 지수 상태 리포트 생성 실패: {e}")


def run_all_technical_analysis():
    """
    모든 기술적 지표 분석을 한번에 실행
    - 테스트용 또는 수동 실행용
    - 나스닥 지수 + S&P 500 지수 통합 분석
    """
    print("🚀 전체 기술적 지표 분석 시작")
    try:
        service = TechnicalMonitorService()
        service.run_all_technical_monitoring()
        print("✅ 전체 기술적 지표 분석 완료")
    except Exception as e:
        print(f"❌ 전체 기술적 지표 분석 실패: {e}")


def test_technical_alerts():
    """
    기술적 지표 알림 테스트 (장이 닫힌 시간에도 테스트 가능)
    - 가짜 데이터로 모든 알림 타입 테스트
    - 텔레그램 알림이 제대로 가는지 확인용
    """
    print("🧪 기술적 지표 알림 테스트 시작")
    try:
        service = TechnicalMonitorService()
        service.test_all_technical_alerts()
        print("✅ 기술적 지표 알림 테스트 완료")
    except Exception as e:
        print(f"❌ 기술적 지표 알림 테스트 실패: {e}")


"""
test_single_technical_alert("ma_breakout")    # 이동평균선 돌파
test_single_technical_alert("rsi")            # RSI 신호
test_single_technical_alert("bollinger")      # 볼린저 밴드
test_single_technical_alert("golden_cross")   # 골든크로스
test_single_technical_alert("dead_cross")     # 데드크로스
"""


def test_single_technical_alert(alert_type: str = "ma_breakout"):
    """
    단일 기술적 지표 알림 테스트

    Args:
        alert_type: 테스트할 알림 타입
    """
    print(f"🧪 {alert_type} 알림 테스트 시작")
    try:
        service = TechnicalMonitorService()
        service.test_single_alert(alert_type)
        print(f"✅ {alert_type} 알림 테스트 완료")
    except Exception as e:
        print(f"❌ {alert_type} 알림 테스트 실패: {e}")


# =============================================================================
# Phase 2: 결과 추적 작업들
# =============================================================================


def run_outcome_tracking_update():
    """
    신호 결과 추적 업데이트
    - 미완료된 신호들의 가격 및 수익률 업데이트
    - 1시간마다 실행하여 시간대별 성과 수집
    - Phase 2의 핵심 기능
    """
    print("📈 신호 결과 추적 업데이트 시작")
    try:
        service = OutcomeTrackingService()
        result = service.update_outcomes(hours_old=1)

        if "error" in result:
            print(f"❌ 결과 추적 업데이트 실패: {result['error']}")
        else:
            print(
                f"✅ 결과 추적 업데이트 완료: {result['updated']}개 업데이트, {result['completed']}개 완료"
            )

    except Exception as e:
        print(f"❌ 결과 추적 업데이트 실패: {e}")


def test_outcome_tracking():
    """
    결과 추적 기능 테스트 (개발용)
    - 최근 신호 중 하나를 선택하여 결과 추적 테스트
    - 가상의 가격 데이터로 전체 프로세스 검증
    """
    print("🧪 결과 추적 기능 테스트 시작")
    try:
        service = OutcomeTrackingService()

        # 테스트할 신호 ID (실제로는 최근 신호 중 하나를 선택해야 함)
        # 여기서는 ID 1을 예시로 사용
        test_signal_id = 1

        result = service.test_outcome_tracking(test_signal_id)

        if "error" in result:
            print(f"❌ 결과 추적 테스트 실패: {result['error']}")
        else:
            print(f"✅ 결과 추적 테스트 완료: 신호 ID {test_signal_id}")
            print(f"   - 원본 가격: ${result['test_data']['original_price']:.2f}")
            print(f"   - 1시간 후: ${result['test_data']['price_1h']:.2f}")
            print(f"   - 1일 후: ${result['test_data']['price_1d']:.2f}")
            print(f"   - 1주 후: ${result['test_data']['price_1w']:.2f}")
            print(f"   - 1개월 후: ${result['test_data']['price_1m']:.2f}")

    except Exception as e:
        print(f"❌ 결과 추적 테스트 실패: {e}")


# =============================================================================
# 🆕 과거 데이터 분석 테스트 메서드들 (1,2,3,4번 실행)
# =============================================================================


def test_collect_historical_data():
    """
    테스트 메서드 1: 10년치 과거 데이터 수집
    - 나스닥 지수(^IXIC)와 S&P 500(^GSPC) 10년치 일봉 데이터 수집
    - daily_prices 테이블에 저장
    - 중복 데이터 자동 스킵
    """
    print("📊 1단계: 10년치 과거 데이터 수집 테스트 시작")
    try:

        service = HistoricalDataService()

        # 10년치 데이터 수집 (2015년부터)
        result = service.collect_10_years_data(
            symbols=["^IXIC", "^GSPC"], start_year=2015
        )

        if "error" in result:
            print(f"❌ 과거 데이터 수집 실패: {result['error']}")
        else:
            print(f"✅ 과거 데이터 수집 완료!")
            print(f"   - 총 저장: {result['summary']['total_saved']}개")
            print(f"   - 총 중복: {result['summary']['total_duplicates']}개")
            print(f"   - 총 오류: {result['summary']['total_errors']}개")

            for symbol, data in result["results"].items():
                print(
                    f"   - {symbol}: 저장 {data.get('saved', 0)}개, 중복 {data.get('duplicates', 0)}개"
                )

    except Exception as e:
        print(f"❌ 과거 데이터 수집 테스트 실패: {e}")


def test_generate_historical_signals():
    """
    테스트 메서드 2: 과거 데이터 기반 신호 생성
    - 저장된 10년치 데이터를 분석하여 모든 기술적 신호 생성
    - 이동평균선, RSI, 볼린저밴드, 골든크로스/데드크로스 신호
    - technical_signals 테이블에 저장
    """
    print("🔍 2단계: 과거 데이터 기반 신호 생성 테스트 시작")
    try:

        service = SignalGeneratorService()

        # 10년치 신호 생성
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=365 * 10)  # 10년 전

        result = service.generate_all_signals(
            symbols=["^IXIC", "^GSPC"], start_date=start_date, end_date=end_date
        )

        if "error" in result:
            print(f"❌ 신호 생성 실패: {result['error']}")
        else:
            print(f"✅ 신호 생성 완료!")
            print(f"   - 총 신호: {result['summary']['total_signals']}개")
            print(f"   - 저장됨: {result['summary']['total_saved']}개")

            for symbol, data in result["results"].items():
                print(f"   - {symbol}: {data.get('saved_signals', 0)}개 신호 저장")
                breakdown = data.get("signal_breakdown", {})
                print(f"     * MA: {breakdown.get('ma_signals', 0)}개")
                print(f"     * RSI: {breakdown.get('rsi_signals', 0)}개")
                print(f"     * 볼린저: {breakdown.get('bollinger_signals', 0)}개")
                print(f"     * 크로스: {breakdown.get('cross_signals', 0)}개")

    except Exception as e:
        print(f"❌ 신호 생성 테스트 실패: {e}")


def test_run_backtesting():
    """
    테스트 메서드 3: 백테스팅 실행
    - 생성된 신호들의 실제 성과 분석
    - 신호별 승률, 평균 수익률, 최대 손실률 계산
    - 신호 품질 평가 (A~F 등급)
    """
    print("📈 3단계: 백테스팅 실행 테스트 시작")
    try:
        service = BacktestingService()

        # 전체 신호 성과 분석
        print("   📊 전체 신호 성과 분석 중...")
        overall_result = service.analyze_all_signals_performance(
            timeframe_eval="1d", min_samples=10  # 1일 기준 평가  # 최소 10개 샘플
        )

        if "error" in overall_result:
            print(f"❌ 전체 성과 분석 실패: {overall_result['error']}")
        else:
            summary = overall_result["summary"]
            print(f"✅ 전체 성과 분석 완료!")
            print(f"   - 분석된 신호 타입: {summary['total_signal_types']}개")
            print(f"   - 전체 평균 승률: {summary['overall_success_rate']:.1%}")
            print(f"   - 전체 평균 수익률: {summary['overall_avg_return']:.2f}%")
            print(f"   - 최고 승률: {summary['best_success_rate']:.1%}")
            print(f"   - 최고 수익률: {summary['best_avg_return']:.2f}%")

            # 우수한 신호들 출력
            excellent = overall_result.get("excellent_signals", [])
            if excellent:
                print(f"   🏆 우수한 신호들:")
                for signal in excellent[:3]:  # 상위 3개만
                    print(
                        f"     - {signal['signal_type']}: 승률 {signal['success_rate']:.1%}"
                    )

        # 주요 신호별 상세 분석
        important_signals = ["MA200_breakout_up", "golden_cross", "RSI_oversold"]
        for signal_type in important_signals:
            print(f"\n   🔍 {signal_type} 상세 분석 중...")
            detail_result = service.analyze_signal_type_performance(signal_type)

            if "error" not in detail_result:
                quality_score = detail_result.get("signal_quality_score", 0)
                print(f"     - 품질 점수: {quality_score:.1f}/100")

                timeframe_perf = detail_result.get("timeframe_performance", {})
                if "1d" in timeframe_perf:
                    perf_1d = timeframe_perf["1d"]
                    print(f"     - 1일 승률: {perf_1d.get('success_rate', 0):.1%}")
                    print(
                        f"     - 1일 평균 수익률: {perf_1d.get('avg_return', 0):.2f}%"
                    )

    except Exception as e:
        print(f"❌ 백테스팅 테스트 실패: {e}")


def test_run_pattern_analysis():
    """
    테스트 메서드 4: 패턴 분석 실행
    - 생성된 신호들의 조합 패턴 발견
    - 순차적/동시/선행 패턴 분류
    - 패턴별 성공률 및 신뢰도 분석
    """
    print("🔍 4단계: 패턴 분석 실행 테스트 시작")
    try:
        service = PatternAnalysisService()

        # 나스닥 지수 패턴 분석
        print("   📊 나스닥 지수 패턴 분석 중...")
        nasdaq_result = service.discover_patterns(symbol="^IXIC", timeframe="1day")

        if "error" in nasdaq_result:
            print(f"❌ 나스닥 패턴 분석 실패: {nasdaq_result['error']}")
        else:
            print(f"✅ 나스닥 패턴 분석 완료!")
            print(f"   - 발견된 패턴: {nasdaq_result.get('total_patterns', 0)}개")

            patterns = nasdaq_result.get("patterns", [])
            if patterns:
                print(f"   🎯 주요 패턴들:")
                for pattern in patterns[:3]:  # 상위 3개만
                    print(
                        f"     - {pattern.get('name', 'Unknown')}: 신뢰도 {pattern.get('confidence', 0):.1f}%"
                    )

        # S&P 500 패턴 분석
        print("\n   📊 S&P 500 패턴 분석 중...")
        sp500_result = service.discover_patterns(symbol="^GSPC", timeframe="1day")

        if "error" in sp500_result:
            print(f"❌ S&P 500 패턴 분석 실패: {sp500_result['error']}")
        else:
            print(f"✅ S&P 500 패턴 분석 완료!")
            print(f"   - 발견된 패턴: {sp500_result.get('total_patterns', 0)}개")

        # 성공적인 패턴 찾기
        print("\n   🏆 성공적인 패턴 검색 중...")
        successful_patterns = service.find_successful_patterns(
            success_threshold=0.7, min_occurrences=5  # 70% 이상 승률  # 최소 5번 발생
        )

        if "error" in successful_patterns:
            print(f"❌ 성공 패턴 검색 실패: {successful_patterns['error']}")
        else:
            patterns = successful_patterns.get("patterns", [])
            print(f"✅ 성공적인 패턴 {len(patterns)}개 발견!")

            for pattern in patterns[:5]:  # 상위 5개만
                print(f"   - {pattern.get('pattern_name', 'Unknown')}")
                print(f"     * 승률: {pattern.get('success_rate', 0):.1%}")
                print(f"     * 발생 횟수: {pattern.get('occurrences', 0)}회")

    except Exception as e:
        print(f"❌ 패턴 분석 테스트 실패: {e}")


def test_run_all_historical_analysis():
    """
    테스트 메서드 통합: 1,2,3,4단계 순차 실행
    - 10년치 데이터 수집 → 신호 생성 → 백테스팅 → 패턴 분석
    - 전체 프로세스 한번에 실행
    """
    print("🚀 전체 과거 데이터 분석 프로세스 시작")
    print("=" * 60)

    try:
        # 1단계: 데이터 수집
        # print("\n1️⃣ 과거 데이터 수집")
        # test_collect_historical_data()

        # 2단계: 신호 생성
        print("\n2️⃣ 과거 데이터 기반 신호 생성")
        test_generate_historical_signals()

        # 3단계: 백테스팅
        print("\n3️⃣ 백테스팅 실행")
        test_run_backtesting()

        # 4단계: 패턴 분석
        print("\n4️⃣ 패턴 분석 실행")
        test_run_pattern_analysis()

        print("\n" + "=" * 60)
        print("🎉 전체 과거 데이터 분석 프로세스 완료!")
        print("   - 이제 백테스팅 결과와 패턴 분석 결과를 확인할 수 있습니다.")
        print("   - 실시간 모니터링을 시작하면 새로운 신호와 비교 분석이 가능합니다.")

    except Exception as e:
        print(f"❌ 전체 분석 프로세스 실패: {e}")


def test_recreate_tables():
    """
    테스트 메서드: 테이블 재생성
    - 기존 테이블 삭제 후 새로 생성
    - 스키마 불일치 문제 해결
    - 주의: 모든 데이터가 삭제됨!
    """
    print("⚠️ 테이블 재생성 테스트 시작 (모든 데이터 삭제됨!)")
    try:
        session = SessionLocal()

        try:
            # 1. 기존 테이블 삭제
            print("🗑️ 기존 테이블 삭제 중...")

            # 외래 키 제약 조건 때문에 삭제 순서 중요
            tables = [
                "signal_patterns",
                "signal_outcomes",
                "technical_signals",
                "daily_prices",
            ]

            for table in tables:
                try:
                    session.execute(text(f"DROP TABLE IF EXISTS {table}"))
                    print(f"   ✅ {table} 테이블 삭제 완료")
                except Exception as e:
                    print(f"   ❌ {table} 테이블 삭제 실패: {e}")

            session.commit()

            # 2. 테이블 재생성
            print("\n🏗️ 테이블 재생성 중...")
            Base.metadata.create_all(engine)
            print("   ✅ 모든 테이블 생성 완료")

            # 3. 테이블 확인
            print("\n🔍 생성된 테이블 확인 중...")
            result = session.execute(text("SHOW TABLES"))
            tables = [row[0] for row in result]

            for table in tables:
                print(f"   - {table}")

            print("\n🎉 테이블 재생성 완료!")

        except Exception as e:
            print(f"❌ 테이블 재생성 실패: {e}")
            session.rollback()
        finally:
            session.close()

    except Exception as e:
        print(f"❌ 테이블 재생성 테스트 실패: {e}")


def test_data_status_check():
    """
    테스트 메서드 보조: 데이터 상태 확인
    - 저장된 일봉 데이터 현황 확인
    - 생성된 신호 통계 확인
    - 데이터 품질 검증
    """
    print("📋 데이터 상태 확인 테스트 시작")
    try:
        service = HistoricalDataService()

        # 데이터 상태 확인
        status = service.get_data_status(["^IXIC", "^GSPC"])

        if "error" in status:
            print(f"❌ 데이터 상태 확인 실패: {status['error']}")
        else:
            print(f"✅ 데이터 상태 확인 완료!")
            print(f"   - 총 레코드: {status['total_records']}개")

            for symbol, data in status["symbols"].items():
                print(f"   - {symbol}:")
                print(f"     * 데이터 개수: {data['count']}개")
                print(
                    f"     * 기간: {data['date_range']['start']} ~ {data['date_range']['end']}"
                )
                if data["latest_data"]["date"]:
                    print(
                        f"     * 최신: {data['latest_data']['date']} (${data['latest_data']['close_price']:.2f})"
                    )

        # 데이터 품질 검증
        for symbol in ["^IXIC", "^GSPC"]:
            print(f"\n   🔍 {symbol} 데이터 품질 검증 중...")
            quality = service.validate_data_quality(symbol, days=30)

            if "error" not in quality:
                print(
                    f"     - 품질 점수: {quality['quality_score']:.1f}% ({quality['status']})"
                )
                print(
                    f"     - 유효 레코드: {quality['valid_records']}/{quality['total_records']}"
                )
                if quality["issues"]:
                    print(f"     - 이슈: {len(quality['issues'])}개")

    except Exception as e:
        print(f"❌ 데이터 상태 확인 테스트 실패: {e}")


def initialize_recent_signals_tracking():
    """
    최근 신호들에 대한 결과 추적 초기화
    - 아직 추적이 시작되지 않은 최근 신호들을 찾아서 추적 시작
    - 서버 시작시 또는 수동으로 실행
    """
    print("🎯 최근 신호들 결과 추적 초기화 시작")
    try:
        # 최근 24시간 내 신호들 조회
        session = SessionLocal()
        signal_repo = TechnicalSignalRepository(session)

        end_date = datetime.utcnow()
        start_date = end_date - timedelta(hours=24)

        recent_signals = signal_repo.find_by_date_range(
            start_date=start_date, end_date=end_date, limit=50
        )

        session.close()

        # 각 신호에 대해 결과 추적 초기화
        service = OutcomeTrackingService()
        initialized_count = 0

        for signal in recent_signals:
            try:
                result = service.initialize_outcome_tracking(signal.id)
                if result:
                    initialized_count += 1
                    print(f"   ✅ 신호 ID {signal.id} 추적 시작: {signal.signal_type}")
            except Exception as e:
                print(f"   ⚠️ 신호 ID {signal.id} 추적 시작 실패: {e}")

        print(f"✅ 결과 추적 초기화 완료: {initialized_count}개 신호 추적 시작")

    except Exception as e:
        print(f"❌ 결과 추적 초기화 실패: {e}")


def start_scheduler():
    scheduler = BackgroundScheduler()

    print("🔄 APScheduler 시작됨")

    # =============================================================================
    # 뉴스 크롤링 작업들 (빈도 최적화)
    # 기존: 10분~30분마다 → 신규: 1시간마다 통일 (텔레그램 스팸 방지)
    # =============================================================================
    scheduler.add_job(run_investing_economic_news, "interval", hours=1)
    scheduler.add_job(run_investing_market_news, "interval", hours=1)
    scheduler.add_job(run_yahoo_futures_news, "interval", hours=1)
    scheduler.add_job(run_yahoo_index_news, "interval", hours=1)
    scheduler.add_job(run_yahoo_stock_news, "interval", hours=1)
    # 가격 스냅샷 작업들 (1시간마다 → 하루 1번으로 최적화)
    # 일봉 기준에서는 하루 1번이면 충분함
    scheduler.add_job(
        run_high_price_update_job, "cron", hour=6, minute=0, timezone="Asia/Seoul"
    )
    scheduler.add_job(
        run_previous_close_snapshot_job,
        "cron",
        hour=6,
        minute=10,
        timezone="Asia/Seoul",
    )
    scheduler.add_job(
        run_previous_high_snapshot_job, "cron", hour=6, minute=20, timezone="Asia/Seoul"
    )
    scheduler.add_job(
        run_previous_low_snapshot_job, "cron", hour=6, minute=30, timezone="Asia/Seoul"
    )

    # =============================================================================
    # 현재 활성화된 작업들
    # =============================================================================

    # 실시간 가격 모니터링 (1분 → 15분으로 변경)
    # 일봉 기준 투자에서는 15분 간격이면 충분함
    scheduler.add_job(run_realtime_price_monitor_job, "interval", minutes=15)

    # =============================================================================
    # 🆕 주요 지수 기술적 지표 모니터링 작업들
    # =============================================================================

    # 주요 지수 일봉 기술적 지표 분석 (나스닥 + S&P 500)
    # - 나스닥 지수 (^IXIC): 기술주 중심 분석
    # - S&P 500 지수 (^GSPC): 전체 시장 분석
    # - 장기 투자 관점에서 가장 중요한 신호들
    # - 매일 오전 7시 KST 실행 (한국 시간 기준)
    scheduler.add_job(
        run_daily_index_analysis, "cron", hour=7, minute=0, timezone="Asia/Seoul"
    )

    # =============================================================================
    # 서버 시작시 즉시 실행 (테스트용)
    # =============================================================================

    # print("🚀 서버 시작시 초기 분석 실행")

    # 기존 실시간 가격 모니터링 즉시 실행
    # run_realtime_price_monitor_job()

    # 🆕 기술적 지표 분석 즉시 실행
    # print("📊 기술적 지표 초기 분석 시작...")
    # run_all_technical_analysis()

    # =============================================================================
    # 🆕 Phase 2: 결과 추적 스케줄러 작업들
    # =============================================================================

    # 신호 결과 추적 업데이트 (1시간마다)
    # - 미완료된 신호들의 가격 및 수익률 업데이트
    # - Phase 2의 핵심 기능
    scheduler.add_job(run_outcome_tracking_update, "interval", hours=1)

    # 최근 신호들 결과 추적 초기화 (6시간마다)
    # - 아직 추적이 시작되지 않은 신호들을 찾아서 추적 시작
    scheduler.add_job(initialize_recent_signals_tracking, "interval", hours=6)

    # =============================================================================
    # 서버 시작시 즉시 실행 (테스트 및 초기화)
    # =============================================================================

    # =============================================================================
    # 🆕 과거 데이터 분석 프로세스 실행 (1,2,3,4단계)
    # =============================================================================

    # ⚠️ 테이블 재생성 (스키마 불일치 문제 해결)
    # print("⚠️ 테이블 재생성 실행...")
    # test_recreate_tables()

    # 🚀 전체 과거 데이터 분석 프로세스 실행 (주석 해제하면 서버 시작시 자동 실행)
    # print("🚀 데이터 상태 확인부터 시작...")
    # test_data_status_check()

    # print("\n🚀 전체 과거 데이터 분석 프로세스 실행...")
    # test_run_all_historical_analysis()

    # 개별 단계별 실행 (필요시 주석 해제)
    # print("📊 1단계: 10년치 과거 데이터 수집...")
    # test_collect_historical_data()

    # print("🔍 2단계: 과거 데이터 기반 신호 생성...")
    # test_generate_historical_signals()

    # print("📈 3단계: 백테스팅 실행...")
    # test_run_backtesting()

    # print("🔍 4단계: 패턴 분석 실행...")
    # test_run_pattern_analysis()

    # 데이터 상태 확인 (필요시 주석 해제)
    # print("📋 데이터 상태 확인...")
    # test_data_status_check()

    # =============================================================================
    # 기존 테스트들 (주석 처리)
    # =============================================================================

    # 🧪 알림 테스트 (개발용) - 주석 해제하면 서버 시작시 12개 테스트 알림 전송
    # print("🧪 기술적 지표 알림 테스트 실행...")
    # test_technical_alerts()  # 나스닥 + S&P 500 테스트 알림

    # 🎯 Phase 2: 결과 추적 초기화 (서버 시작시)
    # print("🎯 최근 신호들 결과 추적 초기화...")
    # initialize_recent_signals_tracking()

    # 📈 Phase 2: 결과 추적 테스트 (개발용)
    # print("🧪 결과 추적 기능 테스트...")
    # test_outcome_tracking()

    print("✅ 모든 초기 분석 및 과거 데이터 분석 완료, 스케줄러 시작")
    scheduler.start()
