from apscheduler.schedulers.background import BackgroundScheduler
from app.news_crawler.service.investing_news_crawler import InvestingNewsCrawler
from app.news_crawler.service.yahoo_news_crawler import YahooNewsCrawler
from app.market_price.service.price_high_record_service import PriceHighRecordService
from app.market_price.service.price_snapshot_service import PriceSnapshotService
from app.market_price.service.price_monitor_service import PriceMonitorService
from app.market_price.service.technical_monitor_service import TechnicalMonitorService
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
import time


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
    service = PriceHighRecordService()
    for symbol in SYMBOL_PRICE_MAP:
        time.sleep(5.0)
        service.update_all_time_high(symbol)

    print("✅ 최고가 갱신 완료")


def run_previous_close_snapshot_job():
    print("🕓 전일 종가 저장 시작")
    service = PriceSnapshotService()
    for symbol in SYMBOL_PRICE_MAP:
        time.sleep(5.0)
        service.save_previous_close_if_needed(symbol)

    print("✅ 전일 종가 저장 완료")


def run_previous_high_snapshot_job():
    print("🔺 전일 고점 저장 시작")
    service = PriceSnapshotService()
    for symbol in SYMBOL_PRICE_MAP:
        time.sleep(5.0)
        service.save_previous_high_if_needed(symbol)
    print("✅ 전일 고점 저장 완료")


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


def run_technical_analysis_1min():
    """
    1분봉 기술적 지표 분석 (나스닥 선물)
    - 매우 단기적인 신호 포착
    - 스캘핑, 초단타 매매용
    - 1분마다 실행
    """
    print("📊 1분봉 기술적 지표 분석 시작")
    try:
        service = TechnicalMonitorService()
        service.check_nasdaq_futures_1min()
        print("✅ 1분봉 기술적 지표 분석 완료")
    except Exception as e:
        print(f"❌ 1분봉 기술적 지표 분석 실패: {e}")


def run_technical_analysis_15min():
    """
    15분봉 기술적 지표 분석 (나스닥 선물)
    - 단기 신호 포착 (1분봉보다 신뢰도 높음)
    - 단타매매, 스윙트레이딩용
    - 15분마다 실행
    """
    print("📊 15분봉 기술적 지표 분석 시작")
    try:
        service = TechnicalMonitorService()
        service.check_nasdaq_futures_15min()
        print("✅ 15분봉 기술적 지표 분석 완료")
    except Exception as e:
        print(f"❌ 15분봉 기술적 지표 분석 실패: {e}")


def run_technical_analysis_daily():
    """
    일봉 기술적 지표 분석 (나스닥 지수)
    - 장기 추세 분석 (가장 중요하고 신뢰도 높음)
    - 중장기 투자용
    - 1시간마다 실행 (중요한 신호라서 자주 체크)
    """
    print("📊 일봉 기술적 지표 분석 시작")
    try:
        service = TechnicalMonitorService()
        service.check_nasdaq_index_daily()
        print("✅ 일봉 기술적 지표 분석 완료")
    except Exception as e:
        print(f"❌ 일봉 기술적 지표 분석 실패: {e}")


def run_all_technical_analysis():
    """
    모든 기술적 지표 분석을 한번에 실행
    - 테스트용 또는 수동 실행용
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


def start_scheduler():
    scheduler = BackgroundScheduler()

    print("🔄 APScheduler 시작됨")

    # =============================================================================
    # 기존 작업들 (주석처리됨)
    # =============================================================================
    # scheduler.add_job(run_investing_economic_news, "interval", minutes=30)
    # scheduler.add_job(run_investing_market_news, "interval", minutes=30)
    # scheduler.add_job(run_yahoo_futures_news, "interval", minutes=10)
    # scheduler.add_job(run_yahoo_index_news, "interval", minutes=30)
    # scheduler.add_job(run_yahoo_stock_news, "interval", minutes=15)
    # scheduler.add_job(run_high_price_update_job, "interval", hours=1)
    # scheduler.add_job(run_previous_close_snapshot_job, "interval", hours=1)
    # scheduler.add_job(run_previous_high_snapshot_job, "interval", hours=1)
    # scheduler.add_job(run_previous_low_snapshot_job, "interval", hours=1)

    # =============================================================================
    # 현재 활성화된 작업들
    # =============================================================================

    # 실시간 가격 모니터링 (기존)
    # scheduler.add_job(run_realtime_price_monitor_job, "interval", minutes=1)

    # =============================================================================
    # 🆕 기술적 지표 모니터링 작업들 (새로 추가)
    # =============================================================================

    # 1분봉 기술적 지표 분석 (나스닥 선물)
    # - 매우 단기적인 신호 포착 (스캘핑용)
    # - 1분마다 실행
    # scheduler.add_job(run_technical_analysis_1min, "interval", minutes=1)

    # 15분봉 기술적 지표 분석 (나스닥 선물)
    # - 단기 신호 포착 (단타매매용)
    # - 15분마다 실행
    # scheduler.add_job(run_technical_analysis_15min, "interval", minutes=15)

    # 일봉 기술적 지표 분석 (나스닥 지수)
    # - 장기 추세 분석 (가장 중요!)
    # - 1시간마다 실행 (중요한 신호라서 자주 체크)
    # scheduler.add_job(run_technical_analysis_daily, "interval", hours=1)

    # =============================================================================
    # 서버 시작시 즉시 실행 (테스트용)
    # =============================================================================

    # print("🚀 서버 시작시 초기 분석 실행")

    # 기존 실시간 가격 모니터링 즉시 실행
    # run_realtime_price_monitor_job()

    # 🆕 기술적 지표 분석 즉시 실행
    # print("📊 기술적 지표 초기 분석 시작...")
    # run_all_technical_analysis()

    # 🧪 알림 테스트 (개발용)
    # print("🧪 기술적 지표 알림 테스트 실행...")
    # test_technical_alerts()

    # print("✅ 모든 초기 분석 완료, 스케줄러 시작")
    scheduler.start()
