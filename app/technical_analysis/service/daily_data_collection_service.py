"""
일일 데이터 수집 서비스

이 서비스는 야후 파이낸스에서 최신 일봉 데이터를 수집하여
daily_prices 테이블에 저장하는 전용 서비스입니다.

주요 기능:
- 최신 일봉 데이터 수집
- 중복 데이터 자동 스킵
- 가격 변화율 자동 계산
- 에러 처리 및 로깅

아키텍처:
Controller/Scheduler → Service → Repository → Entity
"""

from typing import List, Dict, Any, Optional
from datetime import date, datetime, timedelta
import pandas as pd
from sqlalchemy.orm import Session
from app.common.infra.database.config.database_config import SessionLocal
from app.common.infra.client.yahoo_price_client import YahooPriceClient
from app.technical_analysis.infra.model.entity.daily_prices import DailyPrice
from app.technical_analysis.infra.model.repository.daily_price_repository import (
    DailyPriceRepository,
)


class DailyDataCollectionService:
    """일일 데이터 수집 서비스"""

    def __init__(self):
        self.yahoo_client = YahooPriceClient()
        self.session: Optional[Session] = None
        self.repository: Optional[DailyPriceRepository] = None

    def _get_session_and_repository(self):
        """세션과 리포지토리 초기화 (지연 초기화)"""
        if not self.session:
            self.session = SessionLocal()
            self.repository = DailyPriceRepository(self.session)
        return self.session, self.repository

    # =================================================================
    # 메인 수집 함수
    # =================================================================

    def collect_and_save_daily_data(
        self, symbols: List[str], target_date: date = None
    ) -> Dict[str, Any]:
        """
        일봉 데이터 수집 및 저장

        Args:
            symbols: 수집할 심볼 리스트 (예: ["^IXIC", "^GSPC"])
            target_date: 수집할 날짜 (기본값: 오늘)

        Returns:
            수집 결과
        """
        if target_date is None:
            target_date = datetime.now().date()

        print(f"📊 일봉 데이터 수집 시작: {target_date}")
        print(f"   - 심볼: {symbols}")

        session, repository = self._get_session_and_repository()

        results = {
            "date": target_date.isoformat(),
            "symbols": symbols,
            "results": {},
            "summary": {"collected": 0, "skipped": 0, "errors": 0},
        }

        try:
            for symbol in symbols:
                print(f"\n🔍 {symbol} 데이터 수집 중...")

                result = self._collect_symbol_data(symbol, target_date)
                results["results"][symbol] = result

                if result.get("status") == "collected":
                    results["summary"]["collected"] += 1
                    print(f"✅ {symbol} 수집 완료: ${result.get('close_price', 0):.2f}")
                elif result.get("status") == "skipped":
                    results["summary"]["skipped"] += 1
                    print(f"⏭️ {symbol} 스킵: {result.get('reason', '알 수 없음')}")
                else:
                    results["summary"]["errors"] += 1
                    print(f"❌ {symbol} 실패: {result.get('error', '알 수 없음')}")

            print(f"\n🎉 일봉 데이터 수집 완료!")
            print(f"   - 수집: {results['summary']['collected']}개")
            print(f"   - 스킵: {results['summary']['skipped']}개")
            print(f"   - 오류: {results['summary']['errors']}개")

            return results

        except Exception as e:
            print(f"❌ 일봉 데이터 수집 실패: {e}")
            return {"error": str(e)}
        finally:
            if session:
                session.close()

    def _collect_symbol_data(self, symbol: str, target_date: date) -> Dict[str, Any]:
        """
        특정 심볼의 일봉 데이터 수집

        Args:
            symbol: 심볼 (^IXIC, ^GSPC)
            target_date: 수집할 날짜

        Returns:
            수집 결과
        """
        session, repository = self._get_session_and_repository()

        try:
            # 1. 해당 날짜 데이터가 이미 있는지 확인
            existing = repository.find_by_symbol_and_date(symbol, target_date)

            if existing:
                return {
                    "symbol": symbol,
                    "date": target_date.isoformat(),
                    "status": "skipped",
                    "reason": "이미 존재하는 데이터",
                }

            # 2. 야후 파이낸스에서 최신 데이터 가져오기
            df = self.yahoo_client.get_daily_data(symbol, period="5d")  # 최근 5일

            if df is None or df.empty:
                return {
                    "symbol": symbol,
                    "date": target_date.isoformat(),
                    "status": "error",
                    "error": "야후 파이낸스에서 데이터를 가져올 수 없음",
                }

            # 3. 해당 날짜의 데이터 찾기
            target_data = None
            for date_index, row in df.iterrows():
                if date_index.date() == target_date:
                    target_data = row
                    break

            if target_data is None:
                return {
                    "symbol": symbol,
                    "date": target_date.isoformat(),
                    "status": "skipped",
                    "reason": "해당 날짜 데이터 없음 (휴장일 가능성)",
                }

            # 4. 전일 종가 조회 (가격 변화 계산용)
            prev_close = None
            latest_data = repository.find_latest_by_symbol(symbol)
            if latest_data:
                prev_close = float(latest_data.close_price)

            # 5. DailyPrice 엔티티 생성
            daily_price = DailyPrice(
                symbol=symbol,
                date=target_date,
                open_price=float(target_data["Open"]),
                high_price=float(target_data["High"]),
                low_price=float(target_data["Low"]),
                close_price=float(target_data["Close"]),
                volume=(
                    int(target_data["Volume"])
                    if pd.notna(target_data["Volume"])
                    else None
                ),
            )

            # 6. 가격 변화 계산
            if prev_close:
                daily_price.price_change = float(daily_price.close_price) - prev_close
                daily_price.price_change_percent = (
                    daily_price.price_change / prev_close
                ) * 100

            # 7. Repository를 통해 저장
            saved_data = repository.save(daily_price)

            if not saved_data:
                return {
                    "symbol": symbol,
                    "date": target_date.isoformat(),
                    "status": "error",
                    "error": "데이터베이스 저장 실패",
                }

            return {
                "symbol": symbol,
                "date": target_date.isoformat(),
                "status": "collected",
                "data": {
                    "open_price": float(daily_price.open_price),
                    "high_price": float(daily_price.high_price),
                    "low_price": float(daily_price.low_price),
                    "close_price": float(daily_price.close_price),
                    "volume": daily_price.volume,
                    "price_change": (
                        float(daily_price.price_change)
                        if daily_price.price_change
                        else None
                    ),
                    "price_change_percent": (
                        float(daily_price.price_change_percent)
                        if daily_price.price_change_percent
                        else None
                    ),
                },
            }

        except Exception as e:
            return {
                "symbol": symbol,
                "date": target_date.isoformat(),
                "status": "error",
                "error": str(e),
            }

    # =================================================================
    # 과거 데이터 수집 (보조 기능)
    # =================================================================

    def collect_recent_data(self, symbols: List[str], days: int = 5) -> Dict[str, Any]:
        """
        최근 N일 데이터 수집

        Args:
            symbols: 수집할 심볼 리스트
            days: 수집할 일수

        Returns:
            수집 결과
        """
        print(f"📊 최근 {days}일 데이터 수집 시작")

        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)

        total_results = {
            "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
            "symbols": symbols,
            "results": {},
            "summary": {"total_collected": 0, "total_skipped": 0, "total_errors": 0},
        }

        try:
            for symbol in symbols:
                print(f"\n🔍 {symbol} 최근 {days}일 데이터 수집 중...")

                symbol_results = []
                collected = 0
                skipped = 0
                errors = 0

                current_date = start_date
                while current_date <= end_date:
                    # 주말 스킵
                    if current_date.weekday() < 5:  # 평일만
                        result = self._collect_symbol_data(symbol, current_date)
                        symbol_results.append(result)

                        if result.get("status") == "collected":
                            collected += 1
                        elif result.get("status") == "skipped":
                            skipped += 1
                        else:
                            errors += 1

                    current_date += timedelta(days=1)

                total_results["results"][symbol] = {
                    "collected": collected,
                    "skipped": skipped,
                    "errors": errors,
                    "details": symbol_results,
                }

                total_results["summary"]["total_collected"] += collected
                total_results["summary"]["total_skipped"] += skipped
                total_results["summary"]["total_errors"] += errors

                print(
                    f"✅ {symbol} 완료: 수집 {collected}개, 스킵 {skipped}개, 오류 {errors}개"
                )

            return total_results

        except Exception as e:
            print(f"❌ 최근 데이터 수집 실패: {e}")
            return {"error": str(e)}

    # =================================================================
    # 유틸리티 메서드
    # =================================================================

    def check_data_freshness(self, symbols: List[str]) -> Dict[str, Any]:
        """
        데이터 신선도 확인 (최신 데이터가 언제인지)

        Args:
            symbols: 확인할 심볼 리스트

        Returns:
            신선도 정보
        """
        session, repository = self._get_session_and_repository()

        try:
            freshness = {}
            today = datetime.now().date()

            for symbol in symbols:
                latest = repository.find_latest_by_symbol(symbol)

                if latest:
                    days_old = (today - latest.date).days
                    status = (
                        "fresh"
                        if days_old <= 1
                        else "stale" if days_old <= 7 else "very_stale"
                    )

                    freshness[symbol] = {
                        "latest_date": latest.date.isoformat(),
                        "days_old": days_old,
                        "status": status,
                        "latest_price": float(latest.close_price),
                    }
                else:
                    freshness[symbol] = {
                        "latest_date": None,
                        "days_old": None,
                        "status": "no_data",
                        "latest_price": None,
                    }

            return {"check_date": today.isoformat(), "freshness": freshness}

        except Exception as e:
            return {"error": str(e)}
        finally:
            if session:
                session.close()

    def is_market_day(self, target_date: date = None) -> bool:
        """
        해당 날짜가 거래일인지 확인

        Args:
            target_date: 확인할 날짜

        Returns:
            거래일이면 True, 휴장일이면 False
        """
        if target_date is None:
            target_date = datetime.now().date()

        # 주말 체크
        if target_date.weekday() >= 5:  # 토요일(5), 일요일(6)
            return False

        # 미국 주요 휴일 체크 (간단한 버전)
        holidays = [
            date(target_date.year, 1, 1),  # 신정
            date(target_date.year, 7, 4),  # 독립기념일
            date(target_date.year, 12, 25),  # 크리스마스
        ]

        return target_date not in holidays

    def __del__(self):
        """소멸자 - 세션 정리"""
        if self.session:
            self.session.close()
