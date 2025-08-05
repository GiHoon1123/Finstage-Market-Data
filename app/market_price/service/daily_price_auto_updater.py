"""
일봉 데이터 자동 업데이트 서비스

주요 기능:
1. 나스닥(^IXIC)과 S&P500(^GSPC) 일봉 데이터 자동 업데이트
2. 누락된 날짜 구간 자동 감지 및 채우기
3. 중복 데이터 방지
4. 주말/공휴일 자동 스킵
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, date, timedelta
import yfinance as yf
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from app.common.infra.database.config.database_config import SessionLocal
from app.technical_analysis.infra.model.entity.daily_prices import DailyPrice
from app.technical_analysis.infra.model.repository.daily_price_repository import (
    DailyPriceRepository,
)
from app.common.utils.logging_config import get_logger

logger = get_logger(__name__)


class DailyPriceAutoUpdater:
    """일봉 데이터 자동 업데이트 서비스"""

    def __init__(self):
        self.target_symbols = ["^IXIC", "^GSPC"]
        self.symbol_names = {"^IXIC": "나스닥 종합지수", "^GSPC": "S&P 500"}

    def update_all_symbols(self) -> Dict[str, Any]:
        """모든 대상 심볼의 일봉 데이터 업데이트"""
        logger.info("daily_price_auto_update_started")

        results = {}
        total_added = 0
        total_updated = 0

        for symbol in self.target_symbols:
            try:
                result = self.update_symbol_data(symbol)
                results[symbol] = result
                total_added += result.get("added_count", 0)
                total_updated += result.get("updated_count", 0)

                logger.info(
                    "symbol_update_completed",
                    symbol=symbol,
                    added=result.get("added_count", 0),
                    updated=result.get("updated_count", 0),
                )

            except Exception as e:
                logger.error("symbol_update_failed", symbol=symbol, error=str(e))
                results[symbol] = {"status": "error", "error": str(e)}

        logger.info(
            "daily_price_auto_update_completed",
            total_added=total_added,
            total_updated=total_updated,
        )

        return {
            "status": "success",
            "total_added": total_added,
            "total_updated": total_updated,
            "results": results,
            "updated_at": datetime.now().isoformat(),
        }

    def update_symbol_data(self, symbol: str) -> Dict[str, Any]:
        """특정 심볼의 일봉 데이터 업데이트"""
        session = SessionLocal()
        daily_price_repo = DailyPriceRepository(session)

        try:
            # 1. 현재 DB의 최신 날짜 확인
            last_date = self._get_last_date(session, symbol)
            today = date.today()

            logger.info(
                "checking_data_gap",
                symbol=symbol,
                last_date=last_date.isoformat() if last_date else "None",
                today=today.isoformat(),
            )

            # 2. 업데이트할 날짜 범위 계산
            if last_date is None:
                # 데이터가 없으면 10년치 가져오기
                start_date = today - timedelta(days=3650)  # 약 10년
                logger.info(
                    "no_existing_data",
                    symbol=symbol,
                    fetching_from=start_date.isoformat(),
                )
            else:
                # 마지막 날짜 다음날부터 오늘까지
                start_date = last_date + timedelta(days=1)

                if start_date > today:
                    logger.info("data_already_up_to_date", symbol=symbol)
                    return {
                        "status": "up_to_date",
                        "last_date": last_date.isoformat(),
                        "added_count": 0,
                        "updated_count": 0,
                    }

            # 3. Yahoo Finance에서 데이터 가져오기
            new_data = self._fetch_yahoo_data(symbol, start_date, today)

            if new_data.empty:
                logger.info("no_new_data_available", symbol=symbol)
                return {
                    "status": "no_new_data",
                    "last_date": last_date.isoformat() if last_date else None,
                    "added_count": 0,
                    "updated_count": 0,
                }

            # 4. 데이터베이스에 저장
            added_count, updated_count = self._save_daily_prices(
                session, symbol, new_data
            )

            # 5. 누락된 구간 확인 및 채우기
            gap_filled = self._fill_data_gaps(session, symbol)

            session.commit()

            return {
                "status": "success",
                "last_date": last_date.isoformat() if last_date else None,
                "new_data_range": f"{start_date.isoformat()} ~ {today.isoformat()}",
                "added_count": added_count,
                "updated_count": updated_count,
                "gaps_filled": gap_filled,
                "total_records": len(new_data),
            }

        except Exception as e:
            session.rollback()
            logger.error("update_symbol_data_failed", symbol=symbol, error=str(e))
            raise
        finally:
            session.close()

    def _get_last_date(self, session: Session, symbol: str) -> Optional[date]:
        """심볼의 최신 날짜 조회"""
        result = (
            session.query(func.max(DailyPrice.date))
            .filter(DailyPrice.symbol == symbol)
            .scalar()
        )
        return result

    def _fetch_yahoo_data(
        self, symbol: str, start_date: date, end_date: date
    ) -> pd.DataFrame:
        """Yahoo Finance에서 일봉 데이터 가져오기"""
        try:
            logger.info(
                "fetching_yahoo_data",
                symbol=symbol,
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
            )

            ticker = yf.Ticker(symbol)
            data = ticker.history(
                start=start_date,
                end=end_date + timedelta(days=1),  # end는 exclusive이므로 +1
                interval="1d",
                auto_adjust=True,
                prepost=False,
            )

            if data.empty:
                logger.warning("no_data_from_yahoo", symbol=symbol)
                return pd.DataFrame()

            # 인덱스를 날짜 컬럼으로 변환
            data.reset_index(inplace=True)
            data["Date"] = data["Date"].dt.date

            # 컬럼명 정리
            data = data.rename(
                columns={
                    "Date": "date",
                    "Open": "open_price",
                    "High": "high_price",
                    "Low": "low_price",
                    "Close": "close_price",
                    "Volume": "volume",
                }
            )

            # 필요한 컬럼만 선택
            data = data[
                [
                    "date",
                    "open_price",
                    "high_price",
                    "low_price",
                    "close_price",
                    "volume",
                ]
            ]

            # NaN 값 제거
            data = data.dropna()

            logger.info(
                "yahoo_data_fetched",
                symbol=symbol,
                records=len(data),
                date_range=f"{data['date'].min()} ~ {data['date'].max()}",
            )

            return data

        except Exception as e:
            logger.error("fetch_yahoo_data_failed", symbol=symbol, error=str(e))
            return pd.DataFrame()

    def _save_daily_prices(
        self, session: Session, symbol: str, data: pd.DataFrame
    ) -> Tuple[int, int]:
        """일봉 데이터를 데이터베이스에 저장"""
        added_count = 0
        updated_count = 0

        for _, row in data.iterrows():
            try:
                # 기존 데이터 확인
                existing = (
                    session.query(DailyPrice)
                    .filter(
                        and_(
                            DailyPrice.symbol == symbol, DailyPrice.date == row["date"]
                        )
                    )
                    .first()
                )

                # 가격 변화 계산
                price_change = None
                price_change_percent = None

                if existing:
                    # 기존 데이터 업데이트
                    existing.open_price = float(row["open_price"])
                    existing.high_price = float(row["high_price"])
                    existing.low_price = float(row["low_price"])
                    existing.close_price = float(row["close_price"])
                    existing.volume = (
                        int(row["volume"]) if pd.notna(row["volume"]) else None
                    )
                    existing.updated_at = datetime.now()

                    # 전일 대비 변화 계산
                    prev_close = self._get_previous_close(session, symbol, row["date"])
                    if prev_close:
                        price_change = float(row["close_price"]) - prev_close
                        price_change_percent = (price_change / prev_close) * 100
                        existing.price_change = price_change
                        existing.price_change_percent = price_change_percent

                    updated_count += 1

                else:
                    # 새 데이터 추가
                    # 전일 대비 변화 계산
                    prev_close = self._get_previous_close(session, symbol, row["date"])
                    if prev_close:
                        price_change = float(row["close_price"]) - prev_close
                        price_change_percent = (price_change / prev_close) * 100

                    daily_price = DailyPrice(
                        symbol=symbol,
                        date=row["date"],
                        open_price=float(row["open_price"]),
                        high_price=float(row["high_price"]),
                        low_price=float(row["low_price"]),
                        close_price=float(row["close_price"]),
                        volume=int(row["volume"]) if pd.notna(row["volume"]) else None,
                        price_change=price_change,
                        price_change_percent=price_change_percent,
                        created_at=datetime.now(),
                        updated_at=datetime.now(),
                    )

                    session.add(daily_price)
                    added_count += 1

            except Exception as e:
                logger.error(
                    "save_daily_price_failed",
                    symbol=symbol,
                    date=str(row["date"]),
                    error=str(e),
                )
                continue

        return added_count, updated_count

    def _get_previous_close(
        self, session: Session, symbol: str, current_date: date
    ) -> Optional[float]:
        """전일 종가 조회"""
        prev_price = (
            session.query(DailyPrice.close_price)
            .filter(and_(DailyPrice.symbol == symbol, DailyPrice.date < current_date))
            .order_by(DailyPrice.date.desc())
            .first()
        )

        return float(prev_price[0]) if prev_price else None

    def _fill_data_gaps(self, session: Session, symbol: str) -> int:
        """누락된 날짜 구간 감지 및 채우기"""
        try:
            # 전체 날짜 범위 조회
            date_range = (
                session.query(
                    func.min(DailyPrice.date).label("min_date"),
                    func.max(DailyPrice.date).label("max_date"),
                )
                .filter(DailyPrice.symbol == symbol)
                .first()
            )

            if not date_range or not date_range.min_date:
                return 0

            # 기존 날짜들 조회
            existing_dates = set(
                row[0]
                for row in session.query(DailyPrice.date)
                .filter(DailyPrice.symbol == symbol)
                .all()
            )

            # 누락된 날짜 찾기 (주말 제외)
            missing_dates = []
            current_date = date_range.min_date

            while current_date <= date_range.max_date:
                # 주말이 아니고 기존 데이터에 없는 날짜
                if current_date.weekday() < 5 and current_date not in existing_dates:
                    missing_dates.append(current_date)
                current_date += timedelta(days=1)

            if not missing_dates:
                logger.info("no_data_gaps_found", symbol=symbol)
                return 0

            logger.info(
                "data_gaps_found",
                symbol=symbol,
                gap_count=len(missing_dates),
                first_gap=missing_dates[0].isoformat(),
                last_gap=missing_dates[-1].isoformat(),
            )

            # 누락된 구간별로 데이터 가져오기
            filled_count = 0
            gap_start = missing_dates[0]
            gap_end = missing_dates[0]

            for i, missing_date in enumerate(missing_dates):
                # 연속된 구간인지 확인
                if i > 0 and missing_date - missing_dates[i - 1] > timedelta(days=1):
                    # 이전 구간 처리
                    gap_data = self._fetch_yahoo_data(symbol, gap_start, gap_end)
                    if not gap_data.empty:
                        added, _ = self._save_daily_prices(session, symbol, gap_data)
                        filled_count += added

                    # 새 구간 시작
                    gap_start = missing_date

                gap_end = missing_date

            # 마지막 구간 처리
            if gap_start <= gap_end:
                gap_data = self._fetch_yahoo_data(symbol, gap_start, gap_end)
                if not gap_data.empty:
                    added, _ = self._save_daily_prices(session, symbol, gap_data)
                    filled_count += added

            logger.info("data_gaps_filled", symbol=symbol, filled_count=filled_count)
            return filled_count

        except Exception as e:
            logger.error("fill_data_gaps_failed", symbol=symbol, error=str(e))
            return 0

    def get_data_status(self) -> Dict[str, Any]:
        """각 심볼의 데이터 현황 조회"""
        session = SessionLocal()

        try:
            status = {}

            for symbol in self.target_symbols:
                # 기본 통계
                stats = (
                    session.query(
                        func.count(DailyPrice.id).label("total_count"),
                        func.min(DailyPrice.date).label("first_date"),
                        func.max(DailyPrice.date).label("last_date"),
                    )
                    .filter(DailyPrice.symbol == symbol)
                    .first()
                )

                # 최근 7일 데이터 확인
                recent_count = (
                    session.query(func.count(DailyPrice.id))
                    .filter(
                        and_(
                            DailyPrice.symbol == symbol,
                            DailyPrice.date >= date.today() - timedelta(days=7),
                        )
                    )
                    .scalar()
                )

                # 오늘까지의 예상 거래일 수 (주말 제외)
                if stats.first_date:
                    total_days = (date.today() - stats.first_date).days + 1
                    expected_trading_days = sum(
                        1
                        for i in range(total_days)
                        if (stats.first_date + timedelta(days=i)).weekday() < 5
                    )

                    gap_count = expected_trading_days - stats.total_count
                else:
                    expected_trading_days = 0
                    gap_count = 0

                status[symbol] = {
                    "symbol_name": self.symbol_names.get(symbol, symbol),
                    "total_records": stats.total_count or 0,
                    "first_date": (
                        stats.first_date.isoformat() if stats.first_date else None
                    ),
                    "last_date": (
                        stats.last_date.isoformat() if stats.last_date else None
                    ),
                    "recent_7days_count": recent_count,
                    "expected_trading_days": expected_trading_days,
                    "estimated_gaps": max(0, gap_count),
                    "days_behind": (
                        (date.today() - stats.last_date).days
                        if stats.last_date
                        else None
                    ),
                    "is_up_to_date": (
                        stats.last_date == date.today() if stats.last_date else False
                    ),
                }

            return {
                "status": "success",
                "symbols": status,
                "checked_at": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error("get_data_status_failed", error=str(e))
            return {"status": "error", "error": str(e)}
        finally:
            session.close()


# 스케줄러에서 사용할 함수
def run_daily_price_update():
    """일일 가격 데이터 업데이트 실행"""
    updater = DailyPriceAutoUpdater()
    return updater.update_all_symbols()


def check_data_status():
    """데이터 현황 확인"""
    updater = DailyPriceAutoUpdater()
    return updater.get_data_status()
