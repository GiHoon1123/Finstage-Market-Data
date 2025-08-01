"""
과거 데이터 수집 서비스

이 서비스는 야후 파이낸스에서 10년치 과거 일봉 데이터를 수집하여
daily_prices 테이블에 저장하는 역할을 담당합니다.

주요 기능:
- 10년치 과거 데이터 일괄 수집
- 중복 데이터 자동 스킵
- 누락된 데이터 보완
- 수집 진행상황 모니터링
- 데이터 품질 검증
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
from app.common.utils.logging_config import get_logger

logger = get_logger(__name__)


class HistoricalDataService:
    """과거 데이터 수집 서비스"""

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
    # 10년치 과거 데이터 수집
    # =================================================================

    def collect_10_years_data(
        self, symbols: List[str] = None, start_year: int = 2015, end_date: date = None
    ) -> Dict[str, Any]:
        """
        10년치 과거 데이터 수집

        Args:
            symbols: 수집할 심볼 리스트 (기본값: ["^IXIC", "^GSPC"])
            start_year: 시작 연도 (기본값: 2015)
            end_date: 종료 날짜 (기본값: 오늘)

        Returns:
            수집 결과 통계
        """
        if symbols is None:
            symbols = ["^IXIC", "^GSPC"]  # 나스닥, S&P 500

        if end_date is None:
            end_date = datetime.now().date()

        start_date = date(start_year, 1, 1)

        print(f"📊 10년치 과거 데이터 수집 시작")
        print(f"   - 심볼: {symbols}")
        print(f"   - 기간: {start_date} ~ {end_date}")

        session, repository = self._get_session_and_repository()

        total_results = {
            "symbols": symbols,
            "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
            "results": {},
            "summary": {"total_saved": 0, "total_duplicates": 0, "total_errors": 0},
        }

        try:
            for symbol in symbols:
                print(f"\n🔍 {symbol} 데이터 수집 중...")

                result = self.collect_symbol_data(
                    symbol=symbol, start_date=start_date, end_date=end_date
                )

                total_results["results"][symbol] = result
                total_results["summary"]["total_saved"] += result.get("saved", 0)
                total_results["summary"]["total_duplicates"] += result.get(
                    "duplicates", 0
                )
                total_results["summary"]["total_errors"] += result.get("errors", 0)

                print(
                    f"✅ {symbol} 완료: 저장 {result.get('saved', 0)}개, 중복 {result.get('duplicates', 0)}개"
                )

            print(f"\n🎉 전체 수집 완료!")
            print(f"   - 총 저장: {total_results['summary']['total_saved']}개")
            print(f"   - 총 중복: {total_results['summary']['total_duplicates']}개")
            print(f"   - 총 오류: {total_results['summary']['total_errors']}개")

            return total_results

        except Exception as e:
            print(f"❌ 데이터 수집 실패: {e}")
            return {"error": str(e)}
        finally:
            if session:
                session.close()

    def collect_symbol_data(
        self, symbol: str, start_date: date, end_date: date
    ) -> Dict[str, Any]:
        """
        특정 심볼의 기간별 데이터 수집

        Args:
            symbol: 심볼 (^IXIC, ^GSPC)
            start_date: 시작 날짜
            end_date: 종료 날짜

        Returns:
            수집 결과
        """
        session, repository = self._get_session_and_repository()

        try:
            # 1. 야후 파이낸스에서 데이터 가져오기
            print(f"   📡 {symbol} 야후 파이낸스 데이터 요청...")
            df = self.yahoo_client.get_daily_data(
                symbol=symbol, period="max"  # 최대한 많은 데이터
            )

            if df is None or df.empty:
                return {"error": f"{symbol} 데이터를 가져올 수 없습니다"}

            # 2. 날짜 범위 필터링
            df = df[(df.index.date >= start_date) & (df.index.date <= end_date)]

            if df.empty:
                return {"error": f"{symbol} 해당 기간에 데이터가 없습니다"}

            print(f"   📊 {symbol} 수집된 데이터: {len(df)}개")

            # 3. DailyPrice 엔티티로 변환
            daily_prices = []
            for date_index, row in df.iterrows():
                # 전일 종가 계산 (가격 변화 계산용)
                prev_close = None
                if len(daily_prices) > 0:
                    prev_close = float(daily_prices[-1].close_price)

                daily_price = DailyPrice(
                    symbol=symbol,
                    date=date_index.date(),
                    open_price=float(row["Open"]),
                    high_price=float(row["High"]),
                    low_price=float(row["Low"]),
                    close_price=float(row["Close"]),
                    volume=int(row["Volume"]) if pd.notna(row["Volume"]) else None,
                )

                # 가격 변화 계산
                if prev_close:
                    daily_price.price_change = (
                        float(daily_price.close_price) - prev_close
                    )
                    daily_price.price_change_percent = (
                        daily_price.price_change / prev_close
                    ) * 100

                daily_prices.append(daily_price)

            # 4. 데이터베이스에 저장 (중복 자동 처리)
            print(f"   💾 {symbol} 데이터베이스 저장 중...")
            save_result = repository.save_bulk(daily_prices)

            return save_result

        except Exception as e:
            print(f"❌ {symbol} 데이터 수집 실패: {e}")
            return {"error": str(e)}

    # =================================================================
    # 누락 데이터 보완
    # =================================================================

    def fill_missing_data(
        self, symbol: str, start_date: date = None, end_date: date = None
    ) -> Dict[str, Any]:
        """
        누락된 데이터 보완

        Args:
            symbol: 심볼
            start_date: 시작 날짜 (기본값: 1년 전)
            end_date: 종료 날짜 (기본값: 오늘)

        Returns:
            보완 결과
        """
        if start_date is None:
            start_date = datetime.now().date() - timedelta(days=365)
        if end_date is None:
            end_date = datetime.now().date()

        session, repository = self._get_session_and_repository()

        try:
            print(f"🔍 {symbol} 누락 데이터 확인 중...")

            # 1. 누락된 날짜 찾기
            missing_dates = repository.get_missing_dates(symbol, start_date, end_date)

            if not missing_dates:
                print(f"✅ {symbol} 누락된 데이터 없음")
                return {"symbol": symbol, "missing_count": 0, "filled_count": 0}

            print(f"⚠️ {symbol} 누락된 날짜: {len(missing_dates)}개")

            # 2. 누락된 기간의 데이터 다시 수집
            fill_result = self.collect_symbol_data(symbol, start_date, end_date)

            return {
                "symbol": symbol,
                "missing_count": len(missing_dates),
                "fill_result": fill_result,
            }

        except Exception as e:
            print(f"❌ {symbol} 누락 데이터 보완 실패: {e}")
            return {"error": str(e)}
        finally:
            if session:
                session.close()

    # =================================================================
    # 데이터 상태 확인
    # =================================================================

    def get_data_status(self, symbols: List[str] = None) -> Dict[str, Any]:
        """
        저장된 데이터 상태 확인

        Args:
            symbols: 확인할 심볼 리스트

        Returns:
            데이터 상태 정보
        """
        if symbols is None:
            symbols = ["^IXIC", "^GSPC"]

        session, repository = self._get_session_and_repository()

        try:
            status = {
                "symbols": {},
                "total_records": 0,
                "checked_at": datetime.now().isoformat(),
            }

            for symbol in symbols:
                # 데이터 개수
                count = repository.get_data_count_by_symbol(symbol)

                # 날짜 범위
                date_range = repository.get_date_range_by_symbol(symbol)

                # 최신 데이터
                latest = repository.find_latest_by_symbol(symbol)

                status["symbols"][symbol] = {
                    "count": count,
                    "date_range": {
                        "start": (
                            date_range["start_date"].isoformat()
                            if date_range["start_date"]
                            else None
                        ),
                        "end": (
                            date_range["end_date"].isoformat()
                            if date_range["end_date"]
                            else None
                        ),
                    },
                    "latest_data": {
                        "date": latest.date.isoformat() if latest else None,
                        "close_price": float(latest.close_price) if latest else None,
                    },
                }

                status["total_records"] += count

            return status

        except Exception as e:
            print(f"❌ 데이터 상태 확인 실패: {e}")
            return {"error": str(e)}
        finally:
            if session:
                session.close()

    # =================================================================
    # 데이터 품질 검증
    # =================================================================

    def validate_data_quality(self, symbol: str, days: int = 30) -> Dict[str, Any]:
        """
        데이터 품질 검증

        Args:
            symbol: 심볼
            days: 검증할 최근 일수

        Returns:
            품질 검증 결과
        """
        session, repository = self._get_session_and_repository()

        try:
            # 최근 N일 데이터 조회
            recent_data = repository.find_latest_n_days(symbol, days)

            if not recent_data:
                return {"error": f"{symbol} 데이터가 없습니다"}

            issues = []
            valid_count = 0

            for data in recent_data:
                # 1. 가격 데이터 유효성 검사
                if (
                    data.open_price <= 0
                    or data.high_price <= 0
                    or data.low_price <= 0
                    or data.close_price <= 0
                ):
                    issues.append(f"{data.date}: 음수 또는 0인 가격 데이터")
                    continue

                # 2. OHLC 논리적 관계 검사
                if (
                    data.high_price < data.low_price
                    or data.high_price < data.open_price
                    or data.high_price < data.close_price
                    or data.low_price > data.open_price
                    or data.low_price > data.close_price
                ):
                    issues.append(f"{data.date}: OHLC 관계 오류")
                    continue

                # 3. 극단적 가격 변동 검사 (전일 대비 50% 이상 변동)
                if len(recent_data) > 1:
                    prev_data = None
                    for i, d in enumerate(recent_data):
                        if d.date == data.date and i > 0:
                            prev_data = recent_data[i - 1]
                            break

                    if prev_data:
                        change_pct = abs(
                            (float(data.close_price) - float(prev_data.close_price))
                            / float(prev_data.close_price)
                        )
                        if change_pct > 0.5:  # 50% 이상 변동
                            issues.append(
                                f"{data.date}: 극단적 가격 변동 ({change_pct:.1%})"
                            )
                            continue

                valid_count += 1

            quality_score = (valid_count / len(recent_data)) * 100 if recent_data else 0

            return {
                "symbol": symbol,
                "period": f"최근 {days}일",
                "total_records": len(recent_data),
                "valid_records": valid_count,
                "quality_score": quality_score,
                "issues": issues,
                "status": (
                    "양호"
                    if quality_score >= 95
                    else "주의" if quality_score >= 80 else "불량"
                ),
            }

        except Exception as e:
            print(f"❌ {symbol} 데이터 품질 검증 실패: {e}")
            return {"error": str(e)}
        finally:
            if session:
                session.close()

    # =================================================================
    # 유틸리티 메서드
    # =================================================================

    def get_trading_days_count(self, start_date: date, end_date: date) -> int:
        """
        기간 내 예상 거래일 수 계산 (주말 제외)

        Args:
            start_date: 시작 날짜
            end_date: 종료 날짜

        Returns:
            예상 거래일 수
        """
        trading_days = 0
        current_date = start_date

        while current_date <= end_date:
            # 주말 제외 (월요일=0, 일요일=6)
            if current_date.weekday() < 5:  # 0-4는 평일
                trading_days += 1
            current_date += timedelta(days=1)

        return trading_days

    def __del__(self):
        """소멸자 - 세션 정리"""
        if self.session:
            self.session.close()
