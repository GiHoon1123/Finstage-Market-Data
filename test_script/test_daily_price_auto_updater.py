#!/usr/bin/env python3
"""
일봉 데이터 자동 업데이트 테스트

주요 기능:
1. 현재 데이터 현황 확인
2. 누락된 데이터 자동 감지 및 채우기
3. 최신 데이터 업데이트
4. 데이터 품질 검증
"""

import os
import sys
from datetime import datetime, date, timedelta

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.market_price.service.daily_price_auto_updater import DailyPriceAutoUpdater


def test_data_status():
    """현재 데이터 현황 확인"""
    print("📊 현재 일봉 데이터 현황 확인")
    print("-" * 60)

    updater = DailyPriceAutoUpdater()
    status = updater.get_data_status()

    if status.get("status") == "success":
        for symbol, info in status["symbols"].items():
            print(f"\n🔹 {info['symbol_name']} ({symbol})")
            print(f"  📈 총 레코드: {info['total_records']:,}개")
            print(f"  📅 데이터 기간: {info['first_date']} ~ {info['last_date']}")
            print(f"  📊 최근 7일: {info['recent_7days_count']}개")
            print(
                f"  🕐 마지막 업데이트: {info['days_behind']}일 전"
                if info["days_behind"]
                else "  ✅ 최신 상태"
            )
            print(f"  📉 예상 누락: {info['estimated_gaps']}개")
            print(
                f"  🎯 상태: {'✅ 최신' if info['is_up_to_date'] else '⚠️ 업데이트 필요'}"
            )
    else:
        print(f"❌ 데이터 현황 확인 실패: {status.get('error')}")

    return status


def test_update_data():
    """데이터 업데이트 테스트"""
    print("\n🔄 일봉 데이터 자동 업데이트 테스트")
    print("-" * 60)

    updater = DailyPriceAutoUpdater()

    print("🚀 업데이트 시작...")
    result = updater.update_all_symbols()

    if result.get("status") == "success":
        print(f"✅ 업데이트 완료!")
        print(f"  📈 총 추가: {result['total_added']}개")
        print(f"  🔄 총 수정: {result['total_updated']}개")
        print(f"  🕐 완료 시간: {result['updated_at']}")

        print("\n📋 심볼별 상세 결과:")
        for symbol, info in result["results"].items():
            if info.get("status") == "success":
                print(f"  🔹 {symbol}:")
                print(f"    - 추가: {info['added_count']}개")
                print(f"    - 수정: {info['updated_count']}개")
                print(f"    - 갭 채움: {info['gaps_filled']}개")
                print(f"    - 데이터 범위: {info.get('new_data_range', 'N/A')}")
            elif info.get("status") == "up_to_date":
                print(f"  ✅ {symbol}: 이미 최신 상태")
            elif info.get("status") == "no_new_data":
                print(f"  ℹ️ {symbol}: 새로운 데이터 없음")
            else:
                print(f"  ❌ {symbol}: {info.get('error', '알 수 없는 오류')}")
    else:
        print(f"❌ 업데이트 실패: {result.get('error')}")

    return result


def test_specific_symbol_update(symbol: str):
    """특정 심볼 업데이트 테스트"""
    print(f"\n🎯 {symbol} 개별 업데이트 테스트")
    print("-" * 60)

    updater = DailyPriceAutoUpdater()

    try:
        result = updater.update_symbol_data(symbol)

        print(f"📊 {symbol} 업데이트 결과:")
        print(f"  상태: {result['status']}")
        print(f"  마지막 날짜: {result.get('last_date', 'N/A')}")
        print(f"  새 데이터 범위: {result.get('new_data_range', 'N/A')}")
        print(f"  추가된 레코드: {result.get('added_count', 0)}개")
        print(f"  수정된 레코드: {result.get('updated_count', 0)}개")
        print(f"  채워진 갭: {result.get('gaps_filled', 0)}개")
        print(f"  총 처리 레코드: {result.get('total_records', 0)}개")

        return result

    except Exception as e:
        print(f"❌ {symbol} 업데이트 실패: {e}")
        return {"status": "error", "error": str(e)}


def test_data_quality():
    """데이터 품질 검증"""
    print("\n🔍 데이터 품질 검증")
    print("-" * 60)

    from app.common.infra.database.config.database_config import SessionLocal
    from app.technical_analysis.infra.model.entity.daily_prices import DailyPrice
    from sqlalchemy import func, and_, text

    session = SessionLocal()

    try:
        symbols = ["^IXIC", "^GSPC"]

        for symbol in symbols:
            print(f"\n📈 {symbol} 데이터 품질 검사:")

            # 1. 기본 통계
            stats = (
                session.query(
                    func.count(DailyPrice.id).label("total"),
                    func.min(DailyPrice.date).label("min_date"),
                    func.max(DailyPrice.date).label("max_date"),
                    func.avg(DailyPrice.volume).label("avg_volume"),
                )
                .filter(DailyPrice.symbol == symbol)
                .first()
            )

            print(f"  📊 총 레코드: {stats.total:,}개")
            print(f"  📅 기간: {stats.min_date} ~ {stats.max_date}")
            print(
                f"  📈 평균 거래량: {int(stats.avg_volume):,}"
                if stats.avg_volume
                else "  📈 평균 거래량: N/A"
            )

            # 2. NULL 값 검사
            null_checks = [
                ("open_price", "open_price IS NULL"),
                ("high_price", "high_price IS NULL"),
                ("low_price", "low_price IS NULL"),
                ("close_price", "close_price IS NULL"),
                ("volume", "volume IS NULL"),
            ]

            print("  🔍 NULL 값 검사:")
            for field, condition in null_checks:
                null_count = session.execute(
                    text(
                        f"SELECT COUNT(*) FROM daily_prices WHERE symbol = '{symbol}' AND {condition}"
                    )
                ).scalar()

                if null_count > 0:
                    print(f"    ⚠️ {field}: {null_count}개 NULL")
                else:
                    print(f"    ✅ {field}: 정상")

            # 3. 가격 이상치 검사
            price_checks = session.execute(
                text(
                    f"""
                SELECT 
                    COUNT(CASE WHEN high_price < low_price THEN 1 END) as high_low_error,
                    COUNT(CASE WHEN open_price < 0 OR close_price < 0 THEN 1 END) as negative_price,
                    COUNT(CASE WHEN high_price = 0 OR low_price = 0 THEN 1 END) as zero_price
                FROM daily_prices 
                WHERE symbol = '{symbol}'
                """
                )
            ).fetchone()

            print("  🔍 가격 데이터 검사:")
            if price_checks.high_low_error > 0:
                print(f"    ⚠️ 고가 < 저가: {price_checks.high_low_error}개")
            else:
                print("    ✅ 고가/저가: 정상")

            if price_checks.negative_price > 0:
                print(f"    ⚠️ 음수 가격: {price_checks.negative_price}개")
            else:
                print("    ✅ 가격 범위: 정상")

            if price_checks.zero_price > 0:
                print(f"    ⚠️ 0 가격: {price_checks.zero_price}개")
            else:
                print("    ✅ 0 가격: 없음")

            # 4. 날짜 연속성 검사 (최근 30일)
            recent_date = date.today() - timedelta(days=30)
            recent_count = (
                session.query(func.count(DailyPrice.id))
                .filter(
                    and_(DailyPrice.symbol == symbol, DailyPrice.date >= recent_date)
                )
                .scalar()
            )

            # 예상 거래일 수 (주말 제외)
            expected_days = sum(
                1 for i in range(30) if (date.today() - timedelta(days=i)).weekday() < 5
            )

            print(f"  📅 최근 30일 연속성: {recent_count}/{expected_days}일")
            if recent_count < expected_days * 0.8:  # 80% 미만이면 경고
                print("    ⚠️ 최근 데이터 누락 가능성")
            else:
                print("    ✅ 최근 데이터 양호")

    finally:
        session.close()


def main():
    """메인 실행 함수"""
    print("=" * 80)
    print("🚀 일봉 데이터 자동 업데이트 시스템 테스트")
    print("=" * 80)
    print(f"🕐 시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        # 1. 현재 데이터 현황 확인
        status = test_data_status()

        # 2. 데이터 업데이트 실행
        update_result = test_update_data()

        # 3. 업데이트 후 현황 재확인
        print("\n📊 업데이트 후 데이터 현황")
        print("-" * 60)
        final_status = test_data_status()

        # 4. 데이터 품질 검증
        test_data_quality()

        # 5. 요약
        print("\n" + "=" * 80)
        print("📋 테스트 요약")
        print("=" * 80)

        if update_result.get("status") == "success":
            print(f"✅ 업데이트 성공")
            print(f"  📈 총 추가된 레코드: {update_result['total_added']}개")
            print(f"  🔄 총 수정된 레코드: {update_result['total_updated']}개")
        else:
            print(f"❌ 업데이트 실패")

        # 심볼별 최종 상태
        if final_status.get("status") == "success":
            for symbol, info in final_status["symbols"].items():
                status_icon = "✅" if info["is_up_to_date"] else "⚠️"
                print(f"  {status_icon} {symbol}: {info['total_records']:,}개 레코드")

    except Exception as e:
        print(f"❌ 테스트 실행 중 오류: {e}")

    print(f"\n🕐 완료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)


if __name__ == "__main__":
    main()
