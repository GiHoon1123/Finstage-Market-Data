#!/usr/bin/env python3
"""
신호 가격 데이터 확인 스크립트
"""

import os
import sys

# 환경 변수 설정
os.environ["DB_HOST"] = "localhost"
os.environ["DB_PORT"] = "5432"
os.environ["DB_NAME"] = "finstage_dev"
os.environ["DB_USER"] = "postgres"
os.environ["DB_PASSWORD"] = "password"

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.technical_analysis.service.enhanced_outcome_tracking_service import (
    EnhancedOutcomeTrackingService,
)
from sqlalchemy import text


def main():
    print("🔍 신호 가격 데이터 확인")
    print("=" * 50)

    service = EnhancedOutcomeTrackingService()

    try:
        # 데이터베이스 연결 및 리포지토리 준비
        session, outcome_repo, signal_repo = service._get_session_and_repositories()

        # 최근 신호들의 가격 확인
        print("📋 최근 신호들의 가격 확인:")
        print("-" * 60)

        recent_signals_query = """
        SELECT 
            id,
            symbol,
            signal_type,
            current_price,
            created_at,
            triggered_at
        FROM technical_signals
        ORDER BY created_at DESC
        LIMIT 10
        """

        result = session.execute(text(recent_signals_query))
        signals = result.fetchall()

        for signal in signals:
            signal_id, symbol, signal_type, current_price, created_at, triggered_at = (
                signal
            )
            print(f"ID: {signal_id}")
            print(f"  심볼: {symbol}")
            print(f"  신호: {signal_type}")
            print(f"  가격: ${float(current_price or 0):.2f}")
            print(f"  생성: {created_at}")
            print(f"  트리거: {triggered_at}")
            print()

        # 심볼별 가격 범위 확인
        print("📊 심볼별 가격 범위 확인:")
        print("-" * 40)

        price_range_query = """
        SELECT 
            symbol,
            COUNT(*) as signal_count,
            MIN(current_price) as min_price,
            MAX(current_price) as max_price,
            AVG(current_price) as avg_price,
            MIN(created_at) as first_signal,
            MAX(created_at) as last_signal
        FROM technical_signals
        WHERE current_price IS NOT NULL
        GROUP BY symbol
        ORDER BY symbol
        """

        range_result = session.execute(text(price_range_query))
        ranges = range_result.fetchall()

        for range_data in ranges:
            (
                symbol,
                count,
                min_price,
                max_price,
                avg_price,
                first_signal,
                last_signal,
            ) = range_data
            print(f"{symbol}:")
            print(f"  신호 개수: {count}개")
            print(f"  가격 범위: ${float(min_price):.2f} ~ ${float(max_price):.2f}")
            print(f"  평균 가격: ${float(avg_price):.2f}")
            print(f"  기간: {first_signal} ~ {last_signal}")
            print()

        # 특정 시점의 가격 변화 확인
        print("🕐 2025-07-18 시점의 가격 변화:")
        print("-" * 40)

        price_change_query = """
        SELECT 
            symbol,
            signal_type,
            current_price,
            created_at
        FROM technical_signals
        WHERE DATE(created_at) = '2025-07-18'
        ORDER BY symbol, created_at
        LIMIT 20
        """

        change_result = session.execute(text(price_change_query))
        changes = change_result.fetchall()

        current_symbol = None
        for change in changes:
            symbol, signal_type, current_price, created_at = change
            if symbol != current_symbol:
                print(f"\n{symbol}:")
                current_symbol = symbol
            print(f"  {created_at}: ${float(current_price):.2f} ({signal_type})")

        # 현재 실제 가격과 비교
        print("\n💰 현재 실제 가격 확인:")
        print("-" * 30)

        try:
            from app.common.infra.client.yahoo_price_client import YahooPriceClient

            yahoo_client = YahooPriceClient()

            symbols = ["^IXIC", "^GSPC"]
            for symbol in symbols:
                try:
                    current_data = yahoo_client.get_latest_minute_price(symbol)
                    if current_data:
                        print(
                            f"{symbol}: ${current_data['price']:.2f} @ {current_data['timestamp']}"
                        )
                    else:
                        print(f"{symbol}: 데이터 없음")
                except Exception as e:
                    print(f"{symbol}: 오류 - {e}")
        except Exception as e:
            print(f"야후 클라이언트 오류: {e}")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback

        traceback.print_exc()
    finally:
        # 세션 정리
        if "session" in locals():
            session.close()


if __name__ == "__main__":
    main()
