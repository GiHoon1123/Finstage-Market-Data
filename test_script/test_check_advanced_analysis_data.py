#!/usr/bin/env python3
"""
고급 기술 분석 데이터 확인 스크립트
signal_patterns, price_snapshots, signal_outcomes 테이블 데이터 확인
"""

from sqlalchemy import create_engine, text
from app.config import MYSQL_URL
import pandas as pd


def check_table_data():
    """각 테이블의 데이터 상태 확인"""
    try:
        engine = create_engine(MYSQL_URL)

        tables = [
            "technical_signals",
            "signal_outcomes",
            "signal_patterns",
            "price_snapshots",
        ]

        print("=== 고급 기술 분석 테이블 데이터 확인 ===\n")

        for table in tables:
            try:
                # 테이블 존재 여부 확인
                with engine.connect() as conn:
                    result = conn.execute(text(f"SHOW TABLES LIKE '{table}'"))
                    if not result.fetchone():
                        print(f"❌ {table}: 테이블이 존재하지 않음")
                        continue

                # 데이터 개수 확인
                with engine.connect() as conn:
                    result = conn.execute(
                        text(f"SELECT COUNT(*) as count FROM {table}")
                    )
                    count = result.fetchone()[0]
                    print(f"📊 {table}: {count}개 레코드")

                # 최근 데이터 확인 (created_at 또는 triggered_at 컬럼이 있는 경우)
                if table in ["technical_signals", "signal_outcomes"]:
                    date_col = (
                        "triggered_at" if table == "technical_signals" else "created_at"
                    )
                    try:
                        with engine.connect() as conn:
                            result = conn.execute(
                                text(
                                    f"""
                                SELECT {date_col} 
                                FROM {table} 
                                ORDER BY {date_col} DESC 
                                LIMIT 1
                            """
                                )
                            )
                            latest = result.fetchone()
                            if latest:
                                print(f"   📅 최신 데이터: {latest[0]}")
                    except Exception as e:
                        print(f"   ⚠️ 최신 데이터 확인 실패: {e}")

                # 샘플 데이터 확인
                if count > 0 and count < 10:
                    try:
                        with engine.connect() as conn:
                            df = pd.read_sql(f"SELECT * FROM {table} LIMIT 3", conn)
                            print(f"   📋 샘플 데이터:")
                            for col in df.columns[:5]:  # 처음 5개 컬럼만
                                print(
                                    f"      {col}: {df[col].iloc[0] if len(df) > 0 else 'N/A'}"
                                )
                    except Exception as e:
                        print(f"   ⚠️ 샘플 데이터 확인 실패: {e}")

                print()

            except Exception as e:
                print(f"❌ {table} 확인 실패: {e}\n")

        # 관계 확인
        print("=== 테이블 간 관계 확인 ===")
        try:
            with engine.connect() as conn:
                # technical_signals와 signal_outcomes 관계
                result = conn.execute(
                    text(
                        """
                    SELECT 
                        COUNT(ts.id) as total_signals,
                        COUNT(so.signal_id) as tracked_signals,
                        ROUND(COUNT(so.signal_id) * 100.0 / COUNT(ts.id), 2) as tracking_rate
                    FROM technical_signals ts
                    LEFT JOIN signal_outcomes so ON ts.id = so.signal_id
                """
                    )
                )
                row = result.fetchone()
                if row:
                    print(f"📈 신호 추적률: {row[1]}/{row[0]} ({row[2]}%)")

        except Exception as e:
            print(f"❌ 관계 확인 실패: {e}")

        engine.dispose()

    except Exception as e:
        print(f"❌ 데이터 확인 실패: {e}")


def check_recent_activity():
    """최근 활동 확인"""
    try:
        engine = create_engine(MYSQL_URL)

        print("\n=== 최근 24시간 활동 확인 ===")

        # 최근 신호 생성
        with engine.connect() as conn:
            result = conn.execute(
                text(
                    """
                SELECT COUNT(*) as count
                FROM technical_signals 
                WHERE triggered_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
            """
                )
            )
            recent_signals = result.fetchone()[0]
            print(f"📊 최근 24시간 신호: {recent_signals}개")

        # 최근 결과 추적
        with engine.connect() as conn:
            result = conn.execute(
                text(
                    """
                SELECT COUNT(*) as count
                FROM signal_outcomes 
                WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
            """
                )
            )
            recent_outcomes = result.fetchone()[0]
            print(f"📊 최근 24시간 결과 추적: {recent_outcomes}개")

        # 최근 가격 스냅샷
        with engine.connect() as conn:
            result = conn.execute(
                text(
                    """
                SELECT COUNT(*) as count
                FROM price_snapshots 
                WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
            """
                )
            )
            recent_snapshots = result.fetchone()[0]
            print(f"📊 최근 24시간 가격 스냅샷: {recent_snapshots}개")

        engine.dispose()

    except Exception as e:
        print(f"❌ 최근 활동 확인 실패: {e}")


if __name__ == "__main__":
    check_table_data()
    check_recent_activity()
