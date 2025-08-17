"""
일봉 가격 데이터 리포지토리

이 파일은 daily_prices 테이블에 대한 데이터베이스 접근을 담당합니다.

주요 기능:
- 일봉 데이터 저장 (중복 체크 포함)
- 심볼별, 날짜별 데이터 조회
- 기간별 데이터 조회 (백테스팅용)
- 최신 데이터 조회
- 데이터 존재 여부 확인
"""

from typing import List, Optional, Dict, Any
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, asc, func
from sqlalchemy.exc import IntegrityError
from app.technical_analysis.infra.model.entity.daily_prices import DailyPrice


class DailyPriceRepository:
    """일봉 가격 데이터 리포지토리"""

    def __init__(self, session: Session):
        self.session = session

    # =================================================================
    # 기본 CRUD 작업
    # =================================================================

    def save(self, daily_price: DailyPrice) -> Optional[DailyPrice]:
        """
        일봉 데이터 저장

        Args:
            daily_price: 저장할 일봉 데이터

        Returns:
            저장된 엔티티 또는 None (중복인 경우)
        """
        try:
            self.session.add(daily_price)
            self.session.commit()
            return daily_price
        except IntegrityError:
            # 중복 데이터인 경우 (symbol + date 유니크 제약 위반)
            self.session.rollback()
            print(f"⚠️ 중복 데이터: {daily_price.symbol} {daily_price.date}")
            return None
        except Exception as e:
            self.session.rollback()
            print(f"❌ 데이터 저장 실패: {e}")
            return None

    def save_bulk(self, daily_prices: List[DailyPrice]) -> Dict[str, int]:
        """
        일봉 데이터 대량 저장

        Args:
            daily_prices: 저장할 일봉 데이터 리스트

        Returns:
            저장 결과 통계
        """
        saved_count = 0
        duplicate_count = 0
        error_count = 0

        for daily_price in daily_prices:
            result = self.save(daily_price)
            if result:
                saved_count += 1
            elif self.exists_by_symbol_and_date(daily_price.symbol, daily_price.date):
                duplicate_count += 1
            else:
                error_count += 1

        return {
            "saved": saved_count,
            "duplicates": duplicate_count,
            "errors": error_count,
            "total": len(daily_prices),
        }

    def find_by_id(self, id: int) -> Optional[DailyPrice]:
        """ID로 일봉 데이터 조회"""
        return self.session.query(DailyPrice).filter(DailyPrice.id == id).first()

    def find_all(self, limit: int = 1000) -> List[DailyPrice]:
        """모든 일봉 데이터 조회 (최신순)"""
        return (
            self.session.query(DailyPrice)
            .order_by(desc(DailyPrice.date))
            .limit(limit)
            .all()
        )

    # =================================================================
    # 심볼별 조회
    # =================================================================

    def find_by_symbol(
        self, symbol: str, limit: int = 1000, order_desc: bool = True
    ) -> List[DailyPrice]:
        """
        심볼별 일봉 데이터 조회

        Args:
            symbol: 심볼 (^IXIC, ^GSPC)
            limit: 조회 개수 제한
            order_desc: True면 최신순, False면 과거순

        Returns:
            일봉 데이터 리스트
        """
        query = self.session.query(DailyPrice).filter(DailyPrice.symbol == symbol)

        if order_desc:
            query = query.order_by(desc(DailyPrice.date))
        else:
            query = query.order_by(asc(DailyPrice.date))

        return query.limit(limit).all()

    def find_by_symbol_and_date(
        self, symbol: str, target_date: date
    ) -> Optional[DailyPrice]:
        """
        심볼과 날짜로 특정 일봉 데이터 조회

        Args:
            symbol: 심볼
            target_date: 조회할 날짜

        Returns:
            일봉 데이터 또는 None
        """
        return (
            self.session.query(DailyPrice)
            .filter(and_(DailyPrice.symbol == symbol, DailyPrice.date == target_date))
            .first()
        )

    def find_by_symbol_and_date_range(
        self, symbol: str, start_date: date, end_date: date, order_desc: bool = False
    ) -> List[DailyPrice]:
        """
        심볼과 날짜 범위로 일봉 데이터 조회

        Args:
            symbol: 심볼
            start_date: 시작 날짜
            end_date: 종료 날짜
            order_desc: True면 최신순, False면 과거순

        Returns:
            해당 기간의 일봉 데이터 리스트
        """
        query = self.session.query(DailyPrice).filter(
            and_(
                DailyPrice.symbol == symbol,
                DailyPrice.date >= start_date,
                DailyPrice.date <= end_date,
            )
        )

        if order_desc:
            query = query.order_by(desc(DailyPrice.date))
        else:
            query = query.order_by(asc(DailyPrice.date))

        return query.all()

    # =================================================================
    # 최신 데이터 조회
    # =================================================================

    def find_latest_by_symbol(self, symbol: str) -> Optional[DailyPrice]:
        """
        심볼의 가장 최신 일봉 데이터 조회

        Args:
            symbol: 심볼

        Returns:
            최신 일봉 데이터 또는 None
        """
        return (
            self.session.query(DailyPrice)
            .filter(DailyPrice.symbol == symbol)
            .order_by(desc(DailyPrice.date))
            .first()
        )

    def find_latest_n_days(self, symbol: str, n: int) -> List[DailyPrice]:
        """
        심볼의 최근 N일 데이터 조회

        Args:
            symbol: 심볼
            n: 조회할 일수

        Returns:
            최근 N일 일봉 데이터 (과거순 정렬)
        """
        return (
            self.session.query(DailyPrice)
            .filter(DailyPrice.symbol == symbol)
            .order_by(desc(DailyPrice.date))
            .limit(n)
            .all()[::-1]  # 과거순으로 뒤집기
        )

    # =================================================================
    # 데이터 존재 여부 확인
    # =================================================================

    def exists_by_symbol_and_date(self, symbol: str, target_date: date) -> bool:
        """
        특정 심볼과 날짜의 데이터 존재 여부 확인

        Args:
            symbol: 심볼
            target_date: 확인할 날짜

        Returns:
            존재하면 True, 없으면 False
        """
        count = (
            self.session.query(DailyPrice)
            .filter(and_(DailyPrice.symbol == symbol, DailyPrice.date == target_date))
            .count()
        )
        return count > 0

    def get_missing_dates(
        self, symbol: str, start_date: date, end_date: date
    ) -> List[date]:
        """
        특정 기간에서 누락된 날짜들 조회

        Args:
            symbol: 심볼
            start_date: 시작 날짜
            end_date: 종료 날짜

        Returns:
            누락된 날짜 리스트
        """
        # 해당 기간의 모든 데이터 조회
        existing_data = self.find_by_symbol_and_date_range(symbol, start_date, end_date)
        existing_dates = {data.date for data in existing_data}

        # 기대되는 모든 날짜 생성 (주말 제외)
        expected_dates = []
        current_date = start_date
        while current_date <= end_date:
            # 주말 제외 (월요일=0, 일요일=6)
            if current_date.weekday() < 5:  # 0-4는 평일
                expected_dates.append(current_date)
            current_date += timedelta(days=1)

        # 누락된 날짜 찾기
        missing_dates = [d for d in expected_dates if d not in existing_dates]
        return missing_dates

    # =================================================================
    # 통계 및 분석
    # =================================================================

    def get_data_count_by_symbol(self, symbol: str) -> int:
        """심볼별 데이터 개수 조회"""
        return (
            self.session.query(DailyPrice).filter(DailyPrice.symbol == symbol).count()
        )

    def get_date_range_by_symbol(self, symbol: str) -> Dict[str, Optional[date]]:
        """
        심볼별 데이터 날짜 범위 조회

        Returns:
            {'start_date': 가장 오래된 날짜, 'end_date': 가장 최신 날짜}
        """
        result = (
            self.session.query(
                func.min(DailyPrice.date).label("start_date"),
                func.max(DailyPrice.date).label("end_date"),
            )
            .filter(DailyPrice.symbol == symbol)
            .first()
        )

        return {
            "start_date": result.start_date if result else None,
            "end_date": result.end_date if result else None,
        }

    def get_all_symbols(self) -> List[str]:
        """저장된 모든 심볼 조회"""
        result = self.session.query(DailyPrice.symbol).distinct().all()
        return [row.symbol for row in result]

    # =================================================================
    # 데이터 정리
    # =================================================================

    def delete_by_symbol_and_date(self, symbol: str, target_date: date) -> bool:
        """
        특정 심볼과 날짜의 데이터 삭제

        Args:
            symbol: 심볼
            target_date: 삭제할 날짜

        Returns:
            삭제 성공 여부
        """
        try:
            deleted_count = (
                self.session.query(DailyPrice)
                .filter(
                    and_(DailyPrice.symbol == symbol, DailyPrice.date == target_date)
                )
                .delete()
            )
            self.session.commit()
            return deleted_count > 0
        except Exception as e:
            self.session.rollback()
            print(f"❌ 데이터 삭제 실패: {e}")
            return False

    def save_daily_price(
        self,
        symbol: str,
        date: datetime,
        open_price: float,
        high_price: float,
        low_price: float,
        close_price: float,
        volume: float
    ) -> Optional[DailyPrice]:
        """
        일봉 데이터 저장 (편의 메서드)

        Args:
            symbol: 심볼
            date: 날짜
            open_price: 시가
            high_price: 고가
            low_price: 저가
            close_price: 종가
            volume: 거래량

        Returns:
            저장된 엔티티 또는 None
        """
        try:
            # 날짜를 date 객체로 변환
            if isinstance(date, datetime):
                date = date.date()
            
            # DailyPrice 엔티티 생성
            daily_price = DailyPrice(
                symbol=symbol,
                date=date,
                open_price=open_price,
                high_price=high_price,
                low_price=low_price,
                close_price=close_price,
                volume=volume
            )
            
            # 저장
            return self.save(daily_price)
            
        except Exception as e:
            print(f"❌ {symbol} 일봉 데이터 저장 실패: {e}")
            return None

    def delete_old_data(self, symbol: str, keep_days: int = 365) -> int:
        """
        오래된 데이터 삭제 (용량 관리용)

        Args:
            symbol: 심볼
            keep_days: 보관할 일수

        Returns:
            삭제된 레코드 수
        """
        cutoff_date = datetime.now().date() - timedelta(days=keep_days)

        try:
            deleted_count = (
                self.session.query(DailyPrice)
                .filter(
                    and_(DailyPrice.symbol == symbol, DailyPrice.date < cutoff_date)
                )
                .delete()
            )
            self.session.commit()
            return deleted_count
        except Exception as e:
            self.session.rollback()
            print(f"❌ 오래된 데이터 삭제 실패: {e}")
            return 0
