"""
데이터 소스 인터페이스 및 구현체

이 파일은 ML 예측 시스템에서 사용할 다양한 데이터 소스들의 인터페이스와
기본 구현체들을 정의합니다. 플러그인 방식으로 새로운 데이터 소스를
쉽게 추가할 수 있도록 설계되었습니다.

주요 기능:
- 추상 데이터 소스 인터페이스 정의
- 기존 데이터베이스 소스 구현
- 데이터 품질 검증 및 변환
- 확장 가능한 플러그인 구조
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from datetime import date, datetime
import pandas as pd
import numpy as np
from sqlalchemy.orm import Session

from app.common.infra.database.config.database_config import SessionLocal
from app.technical_analysis.infra.model.entity.daily_prices import DailyPrice
from app.technical_analysis.infra.model.entity.technical_signals import TechnicalSignal
from app.technical_analysis.infra.model.repository.daily_price_repository import (
    DailyPriceRepository,
)
from app.technical_analysis.infra.model.repository.technical_signal_repository import (
    TechnicalSignalRepository,
)
from app.common.utils.logging_config import get_logger

logger = get_logger(__name__)


class DataSource(ABC):
    """
    데이터 소스 추상 인터페이스

    모든 데이터 소스는 이 인터페이스를 구현해야 합니다.
    플러그인 방식으로 새로운 데이터 소스를 추가할 수 있습니다.
    """

    def __init__(self, name: str, priority: int = 1):
        """
        데이터 소스 초기화

        Args:
            name: 데이터 소스 이름
            priority: 우선순위 (낮을수록 높은 우선순위)
        """
        self.name = name
        self.priority = priority
        self._is_available = True
        self._last_error = None

    @abstractmethod
    def fetch_data(self, symbol: str, start_date: date, end_date: date) -> pd.DataFrame:
        """
        데이터 수집

        Args:
            symbol: 심볼
            start_date: 시작 날짜
            end_date: 종료 날짜

        Returns:
            수집된 데이터 DataFrame
        """
        pass

    @abstractmethod
    def get_feature_columns(self) -> List[str]:
        """
        제공하는 특성 컬럼 목록 반환

        Returns:
            특성 컬럼 이름 목록
        """
        pass

    @abstractmethod
    def validate_data(self, data: pd.DataFrame) -> Tuple[bool, List[str]]:
        """
        데이터 품질 검증

        Args:
            data: 검증할 데이터

        Returns:
            (검증 성공 여부, 오류 메시지 목록)
        """
        pass

    def is_available(self) -> bool:
        """
        데이터 소스 사용 가능 여부

        Returns:
            사용 가능 여부
        """
        return self._is_available

    def get_last_error(self) -> Optional[str]:
        """
        마지막 오류 메시지 반환

        Returns:
            오류 메시지 (없으면 None)
        """
        return self._last_error

    def set_error(self, error_message: str) -> None:
        """
        오류 상태 설정

        Args:
            error_message: 오류 메시지
        """
        self._is_available = False
        self._last_error = error_message

        logger.error("data_source_error", source_name=self.name, error=error_message)

    def reset_error(self) -> None:
        """오류 상태 초기화"""
        self._is_available = True
        self._last_error = None

    def get_info(self) -> Dict[str, Any]:
        """
        데이터 소스 정보 반환

        Returns:
            데이터 소스 정보 딕셔너리
        """
        return {
            "name": self.name,
            "priority": self.priority,
            "is_available": self.is_available(),
            "last_error": self.get_last_error(),
            "feature_columns": self.get_feature_columns(),
        }


class DatabasePriceDataSource(DataSource):
    """
    데이터베이스 일봉 데이터 소스

    기존 daily_prices 테이블에서 OHLCV 데이터를 가져옵니다.
    """

    def __init__(self):
        super().__init__("database_price_data", priority=1)
        self.session = None

    def _get_session(self) -> Session:
        """데이터베이스 세션 생성"""
        if not self.session:
            self.session = SessionLocal()
        return self.session

    def fetch_data(self, symbol: str, start_date: date, end_date: date) -> pd.DataFrame:
        """
        일봉 데이터 수집

        Args:
            symbol: 심볼
            start_date: 시작 날짜
            end_date: 종료 날짜

        Returns:
            일봉 데이터 DataFrame
        """
        try:
            session = self._get_session()
            repository = DailyPriceRepository(session)

            # 데이터 조회
            daily_prices = repository.find_by_symbol_and_date_range(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                order_desc=False,
            )

            if not daily_prices:
                self.set_error(
                    f"No price data found for {symbol} between {start_date} and {end_date}"
                )
                return pd.DataFrame()

            # DataFrame 변환
            data_list = []
            for price in daily_prices:
                data_list.append(
                    {
                        "date": price.date,
                        "open": float(price.open_price),
                        "high": float(price.high_price),
                        "low": float(price.low_price),
                        "close": float(price.close_price),
                        "volume": price.volume or 0,
                        "price_change": (
                            float(price.price_change) if price.price_change else 0.0
                        ),
                        "price_change_percent": (
                            float(price.price_change_percent)
                            if price.price_change_percent
                            else 0.0
                        ),
                    }
                )

            df = pd.DataFrame(data_list)
            df.set_index("date", inplace=True)
            df.sort_index(inplace=True)

            # 데이터 검증
            is_valid, errors = self.validate_data(df)
            if not is_valid:
                self.set_error(f"Data validation failed: {', '.join(errors)}")
                return pd.DataFrame()

            self.reset_error()

            logger.info(
                "database_price_data_fetched",
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                records=len(df),
            )

            return df

        except Exception as e:
            self.set_error(f"Failed to fetch price data: {str(e)}")
            return pd.DataFrame()

    def get_feature_columns(self) -> List[str]:
        """제공하는 특성 컬럼 목록"""
        return [
            "open",
            "high",
            "low",
            "close",
            "volume",
            "price_change",
            "price_change_percent",
        ]

    def validate_data(self, data: pd.DataFrame) -> Tuple[bool, List[str]]:
        """
        일봉 데이터 품질 검증

        Args:
            data: 검증할 데이터

        Returns:
            (검증 성공 여부, 오류 메시지 목록)
        """
        errors = []

        # 필수 컬럼 확인
        required_columns = ["open", "high", "low", "close"]
        missing_columns = [col for col in required_columns if col not in data.columns]
        if missing_columns:
            errors.append(f"Missing required columns: {missing_columns}")

        if not errors:
            # 가격 데이터 논리적 검증
            invalid_ohlc = data[
                (data["high"] < data["low"])
                | (data["high"] < data["open"])
                | (data["high"] < data["close"])
                | (data["low"] > data["open"])
                | (data["low"] > data["close"])
            ]

            if len(invalid_ohlc) > 0:
                errors.append(f"Invalid OHLC data found in {len(invalid_ohlc)} records")

            # 음수 가격 확인
            negative_prices = data[
                (data["open"] <= 0)
                | (data["high"] <= 0)
                | (data["low"] <= 0)
                | (data["close"] <= 0)
            ]

            if len(negative_prices) > 0:
                errors.append(
                    f"Negative or zero prices found in {len(negative_prices)} records"
                )

            # 결측치 확인
            missing_ratio = data[required_columns].isnull().sum().sum() / (
                len(data) * len(required_columns)
            )
            if missing_ratio > 0.05:  # 5% 이상 결측치
                errors.append(f"Too many missing values: {missing_ratio:.2%}")

        return len(errors) == 0, errors


class DatabaseTechnicalDataSource(DataSource):
    """
    데이터베이스 기술적 지표 데이터 소스

    기존 technical_signals 테이블에서 기술적 분석 지표를 가져옵니다.
    """

    def __init__(self):
        super().__init__("database_technical_data", priority=2)
        self.session = None

    def _get_session(self) -> Session:
        """데이터베이스 세션 생성"""
        if not self.session:
            self.session = SessionLocal()
        return self.session

    def fetch_data(self, symbol: str, start_date: date, end_date: date) -> pd.DataFrame:
        """
        기술적 지표 데이터 수집

        Args:
            symbol: 심볼
            start_date: 시작 날짜
            end_date: 종료 날짜

        Returns:
            기술적 지표 DataFrame
        """
        try:
            session = self._get_session()
            repository = TechnicalSignalRepository(session)

            # 날짜 범위를 datetime으로 변환
            start_datetime = datetime.combine(start_date, datetime.min.time())
            end_datetime = datetime.combine(end_date, datetime.max.time())

            # 기술적 신호 조회
            signals = repository.find_by_date_range(
                start_date=start_datetime, end_date=end_datetime, symbol=symbol
            )

            if not signals:
                self.set_error(
                    f"No technical signals found for {symbol} between {start_date} and {end_date}"
                )
                return pd.DataFrame()

            # 신호 타입별로 그룹화하여 DataFrame 생성
            signal_data = {}

            for signal in signals:
                signal_date = signal.triggered_at.date()
                signal_type = signal.signal_type

                if signal_date not in signal_data:
                    signal_data[signal_date] = {}

                # 신호 강도를 특성으로 사용
                signal_data[signal_date][f"{signal_type}_strength"] = (
                    float(signal.signal_strength) if signal.signal_strength else 0.0
                )
                signal_data[signal_date][f"{signal_type}_value"] = (
                    float(signal.indicator_value) if signal.indicator_value else 0.0
                )

                # 신호 발생 여부를 바이너리 특성으로 추가
                signal_data[signal_date][f"{signal_type}_triggered"] = 1.0

            # DataFrame 생성
            if not signal_data:
                return pd.DataFrame()

            df = pd.DataFrame.from_dict(signal_data, orient="index")
            df.index.name = "date"
            df.fillna(0.0, inplace=True)  # 신호가 없는 날은 0으로 채움
            df.sort_index(inplace=True)

            # 데이터 검증
            is_valid, errors = self.validate_data(df)
            if not is_valid:
                self.set_error(f"Data validation failed: {', '.join(errors)}")
                return pd.DataFrame()

            self.reset_error()

            logger.info(
                "database_technical_data_fetched",
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                records=len(df),
                features=len(df.columns),
            )

            return df

        except Exception as e:
            self.set_error(f"Failed to fetch technical data: {str(e)}")
            return pd.DataFrame()

    def get_feature_columns(self) -> List[str]:
        """제공하는 특성 컬럼 목록 (동적으로 생성됨)"""
        # 일반적인 기술적 지표 컬럼들
        base_signals = [
            "MA20_breakout_up",
            "MA50_breakout_up",
            "MA200_breakout_up",
            "RSI_overbought",
            "RSI_oversold",
            "BB_touch_upper",
            "BB_touch_lower",
        ]

        columns = []
        for signal in base_signals:
            columns.extend(
                [f"{signal}_strength", f"{signal}_value", f"{signal}_triggered"]
            )

        return columns

    def validate_data(self, data: pd.DataFrame) -> Tuple[bool, List[str]]:
        """
        기술적 지표 데이터 품질 검증

        Args:
            data: 검증할 데이터

        Returns:
            (검증 성공 여부, 오류 메시지 목록)
        """
        errors = []

        # 데이터가 비어있는지 확인
        if data.empty:
            errors.append("No technical indicator data available")
            return False, errors

        # 무한값이나 NaN 확인
        if data.isnull().sum().sum() > 0:
            errors.append("NaN values found in technical data")

        if np.isinf(data.select_dtypes(include=[np.number])).sum().sum() > 0:
            errors.append("Infinite values found in technical data")

        # 데이터 타입 확인
        non_numeric_cols = data.select_dtypes(exclude=[np.number]).columns.tolist()
        if non_numeric_cols:
            errors.append(f"Non-numeric columns found: {non_numeric_cols}")

        return len(errors) == 0, errors


class TimeBasedFeatureSource(DataSource):
    """
    시간 기반 특성 데이터 소스

    날짜 정보를 기반으로 요일, 월, 분기 등의 시간적 특성을 생성합니다.
    """

    def __init__(self):
        super().__init__("time_based_features", priority=3)

    def fetch_data(self, symbol: str, start_date: date, end_date: date) -> pd.DataFrame:
        """
        시간 기반 특성 생성

        Args:
            symbol: 심볼 (사용하지 않음)
            start_date: 시작 날짜
            end_date: 종료 날짜

        Returns:
            시간 기반 특성 DataFrame
        """
        try:
            # 날짜 범위 생성
            date_range = pd.date_range(start=start_date, end=end_date, freq="D")

            # 시간 기반 특성 생성
            time_features = []
            for dt in date_range:
                features = {
                    "date": dt.date(),
                    "day_of_week": dt.weekday(),  # 0=월요일, 6=일요일
                    "day_of_month": dt.day,
                    "month": dt.month,
                    "quarter": dt.quarter,
                    "is_month_start": dt.is_month_start,
                    "is_month_end": dt.is_month_end,
                    "is_quarter_start": dt.is_quarter_start,
                    "is_quarter_end": dt.is_quarter_end,
                    "week_of_year": dt.isocalendar()[1],
                }

                # 요일별 원-핫 인코딩
                for i in range(7):
                    features[f"is_weekday_{i}"] = 1.0 if dt.weekday() == i else 0.0

                # 월별 원-핫 인코딩
                for i in range(1, 13):
                    features[f"is_month_{i}"] = 1.0 if dt.month == i else 0.0

                # 분기별 원-핫 인코딩
                for i in range(1, 5):
                    features[f"is_quarter_{i}"] = 1.0 if dt.quarter == i else 0.0

                time_features.append(features)

            df = pd.DataFrame(time_features)
            df.set_index("date", inplace=True)
            df.sort_index(inplace=True)

            # 데이터 검증
            is_valid, errors = self.validate_data(df)
            if not is_valid:
                self.set_error(f"Data validation failed: {', '.join(errors)}")
                return pd.DataFrame()

            self.reset_error()

            logger.info(
                "time_based_features_generated",
                start_date=start_date,
                end_date=end_date,
                records=len(df),
                features=len(df.columns),
            )

            return df

        except Exception as e:
            self.set_error(f"Failed to generate time features: {str(e)}")
            return pd.DataFrame()

    def get_feature_columns(self) -> List[str]:
        """제공하는 특성 컬럼 목록"""
        base_columns = [
            "day_of_week",
            "day_of_month",
            "month",
            "quarter",
            "is_month_start",
            "is_month_end",
            "is_quarter_start",
            "is_quarter_end",
            "week_of_year",
        ]

        # 원-핫 인코딩 컬럼들 추가
        weekday_columns = [f"is_weekday_{i}" for i in range(7)]
        month_columns = [f"is_month_{i}" for i in range(1, 13)]
        quarter_columns = [f"is_quarter_{i}" for i in range(1, 5)]

        return base_columns + weekday_columns + month_columns + quarter_columns

    def validate_data(self, data: pd.DataFrame) -> Tuple[bool, List[str]]:
        """
        시간 기반 특성 데이터 검증

        Args:
            data: 검증할 데이터

        Returns:
            (검증 성공 여부, 오류 메시지 목록)
        """
        errors = []

        # 데이터가 비어있는지 확인
        if data.empty:
            errors.append("No time-based features generated")
            return False, errors

        # 필수 컬럼 확인
        required_columns = ["day_of_week", "month", "quarter"]
        missing_columns = [col for col in required_columns if col not in data.columns]
        if missing_columns:
            errors.append(f"Missing required time columns: {missing_columns}")

        # 값 범위 확인
        if not errors:
            if (data["day_of_week"] < 0).any() or (data["day_of_week"] > 6).any():
                errors.append("Invalid day_of_week values (should be 0-6)")

            if (data["month"] < 1).any() or (data["month"] > 12).any():
                errors.append("Invalid month values (should be 1-12)")

            if (data["quarter"] < 1).any() or (data["quarter"] > 4).any():
                errors.append("Invalid quarter values (should be 1-4)")

        return len(errors) == 0, errors
