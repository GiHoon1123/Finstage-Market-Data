#!/usr/bin/env python3
"""
실시간 기술적 지표 모니터링 스크립트

실제 운영 환경에서 사용할 수 있는 실시간 모니터링 시스템
- 주기적으로 기술적 지표 체크
- 신호 발생시 즉시 알림
- 로그 기록 및 상태 추적
"""

import os
import sys
import time
import signal
from datetime import datetime, timedelta
from typing import Dict, List, Any

# 상위 디렉토리를 파이썬 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.technical_analysis.service.technical_monitor_service import (
    TechnicalMonitorService,
)


class RealtimeMonitor:
    """실시간 모니터링 클래스"""

    def __init__(self):
        self.monitor_service = TechnicalMonitorService()
        self.is_running = False
        self.last_signals = {}  # 마지막 신호 저장 (중복 방지용)

        # 모니터링 대상 심볼들
        self.symbols = {
            "^IXIC": "나스닥 종합지수",
            "^GSPC": "S&P 500",
            "^DJI": "다우존스",
            "QQQ": "나스닥 ETF",
            "SPY": "S&P 500 ETF",
        }

        # 신호 처리 함수 등록
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def signal_handler(self, signum, frame):
        """종료 신호 처리"""
        print(f"\n🛑 종료 신호 수신 (Signal: {signum})")
        self.stop_monitoring()

    def start_monitoring(self, interval_minutes: int = 15):
        """실시간 모니터링 시작"""
        print("🚀 실시간 기술적 지표 모니터링 시작")
        print(f"⏰ 모니터링 간격: {interval_minutes}분")
        print(f"📊 모니터링 대상: {len(self.symbols)}개 심볼")

        for symbol, name in self.symbols.items():
            print(f"  - {symbol}: {name}")

        print("\n" + "=" * 60)

        self.is_running = True
        cycle_count = 0

        try:
            while self.is_running:
                cycle_count += 1
                current_time = datetime.now()

                print(f"\n🔄 모니터링 사이클 #{cycle_count}")
                print(f"⏰ 시간: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
                print("-" * 50)

                # 각 심볼별 분석
                for symbol, name in self.symbols.items():
                    try:
                        self.analyze_symbol(symbol, name)
                        time.sleep(2)  # API 호출 간격 조절
                    except Exception as e:
                        print(f"❌ {symbol} 분석 실패: {e}")

                # 시장 전체 요약
                self.print_market_summary()

                if self.is_running:
                    print(f"\n😴 {interval_minutes}분 대기 중...")
                    print("   (Ctrl+C로 종료)")

                    # 인터벌 대기 (1분씩 체크하여 중단 신호 확인)
                    for _ in range(interval_minutes):
                        if not self.is_running:
                            break
                        time.sleep(60)

        except KeyboardInterrupt:
            print("\n🛑 사용자에 의한 모니터링 중단")
        except Exception as e:
            print(f"\n❌ 모니터링 중 오류 발생: {e}")
        finally:
            self.stop_monitoring()

    def analyze_symbol(self, symbol: str, name: str):
        """개별 심볼 분석"""
        print(f"\n📊 {symbol} ({name}) 분석 중...")

        # 종합 신호 분석
        comprehensive_result = self.monitor_service.monitor_comprehensive_signals(
            symbol
        )

        if comprehensive_result:
            current_price = comprehensive_result["current_price"]
            price_change_pct = comprehensive_result["price_change_pct"]
            signals = comprehensive_result.get("signals", {})

            # 가격 변화에 따른 이모지
            if price_change_pct > 1.0:
                price_emoji = "🚀"
            elif price_change_pct > 0:
                price_emoji = "📈"
            elif price_change_pct < -1.0:
                price_emoji = "💥"
            elif price_change_pct < 0:
                price_emoji = "📉"
            else:
                price_emoji = "🔄"

            print(
                f"  💰 현재가: {current_price:.2f} ({price_change_pct:+.2f}%) {price_emoji}"
            )

            # 신호 처리
            if signals:
                print(f"  🔔 신호 감지: {len(signals)}개")

                # 새로운 신호만 처리 (중복 방지)
                new_signals = self.filter_new_signals(symbol, signals)

                if new_signals:
                    print(f"  🆕 새로운 신호: {len(new_signals)}개")
                    for signal_type, signal_value in new_signals.items():
                        print(f"    - {signal_type.upper()}: {signal_value}")

                        # 실제 운영시에는 여기서 텔레그램/이메일 알림 전송
                        self.send_alert(
                            symbol, name, signal_type, signal_value, current_price
                        )

                    # 마지막 신호 업데이트
                    self.last_signals[symbol] = signals.copy()
                else:
                    print(f"  🔄 기존 신호 유지")
            else:
                print(f"  ✅ 특별한 신호 없음")

            # 시장 심리 분석
            sentiment_result = self.monitor_service.monitor_market_sentiment(symbol)
            if sentiment_result:
                sentiment = sentiment_result["sentiment"]
                emoji = sentiment_result["emoji"]
                ratio = sentiment_result["ratio"]
                print(f"  🧠 시장 심리: {sentiment} {emoji} ({ratio:.1%})")
        else:
            print(f"  ❌ 데이터 분석 실패")

    def filter_new_signals(
        self, symbol: str, current_signals: Dict[str, str]
    ) -> Dict[str, str]:
        """새로운 신호만 필터링 (중복 방지)"""
        if symbol not in self.last_signals:
            return current_signals

        last_signals = self.last_signals[symbol]
        new_signals = {}

        for signal_type, signal_value in current_signals.items():
            if (
                signal_type not in last_signals
                or last_signals[signal_type] != signal_value
            ):
                new_signals[signal_type] = signal_value

        return new_signals

    def send_alert(
        self,
        symbol: str,
        name: str,
        signal_type: str,
        signal_value: str,
        current_price: float,
    ):
        """알림 전송 (실제 운영시 텔레그램/이메일 등)"""
        timestamp = datetime.now().strftime("%H:%M:%S")

        alert_message = f"""
🚨 기술적 신호 알림

📊 종목: {symbol} ({name})
💰 현재가: {current_price:.2f}
🔔 신호: {signal_type.upper()}
📝 내용: {signal_value}
⏰ 시간: {timestamp}
        """.strip()

        print(f"  📨 알림 전송: {signal_type} - {signal_value}")

        # 실제 운영시에는 여기서 텔레그램 봇이나 이메일 전송
        # send_telegram_message(alert_message)
        # send_email_alert(alert_message)

        # 로그 파일에 기록
        self.log_alert(symbol, signal_type, signal_value, current_price)

    def log_alert(
        self, symbol: str, signal_type: str, signal_value: str, current_price: float
    ):
        """알림 로그 기록"""
        try:
            log_dir = "logs"
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)

            log_file = os.path.join(
                log_dir, f"alerts_{datetime.now().strftime('%Y%m%d')}.log"
            )

            with open(log_file, "a", encoding="utf-8") as f:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                log_entry = f"{timestamp},{symbol},{signal_type},{signal_value},{current_price:.2f}\n"
                f.write(log_entry)

        except Exception as e:
            print(f"  ⚠️  로그 기록 실패: {e}")

    def print_market_summary(self):
        """시장 전체 요약"""
        print(f"\n📈 시장 요약")
        print("-" * 30)

        total_symbols = len(self.symbols)
        symbols_with_signals = len([s for s in self.last_signals.values() if s])

        print(f"  📊 분석 종목: {total_symbols}개")
        print(f"  🔔 신호 발생: {symbols_with_signals}개")
        print(f"  ✅ 정상 상태: {total_symbols - symbols_with_signals}개")

    def stop_monitoring(self):
        """모니터링 중단"""
        self.is_running = False
        print("\n🛑 실시간 모니터링 중단")
        print("📊 모니터링 세션 종료")


def main():
    """메인 함수"""
    print("🚀 실시간 기술적 지표 모니터링 시스템")
    print("=" * 60)

    monitor = RealtimeMonitor()

    try:
        # 모니터링 간격 설정 (분 단위)
        interval = 15  # 15분마다 체크

        print(f"⚙️  설정:")
        print(f"  - 모니터링 간격: {interval}분")
        print(f"  - 대상 종목: {len(monitor.symbols)}개")
        print(f"  - 로그 저장: logs/ 디렉토리")

        # 초기 분석 한 번 실행
        print(f"\n🔍 초기 분석 실행...")
        for symbol, name in monitor.symbols.items():
            try:
                monitor.analyze_symbol(symbol, name)
                time.sleep(1)
            except Exception as e:
                print(f"❌ {symbol} 초기 분석 실패: {e}")

        # 실시간 모니터링 시작
        monitor.start_monitoring(interval)

    except Exception as e:
        print(f"❌ 시스템 오류: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
