"""
데이터 품질 검증 시스템

이 파일은 ML 예측 시스템에서 사용되는 데이터의 품질을 검증하는 
다양한 검증 로직을 제공합니다. 데이터 무결성, 일관성, 완성도를 
체크하여 모델 훈련과 예측의 신뢰성을 보장합니다.

주요 기능:
- 데이터 무결성 검증
- 통계적 이상치 탐지
- 시계열 데이터 연속성 확인
- 특성별 품질 점수 계산
"""

from typing import List, Dict, Any, Optional, Tuple, Union
from datetime import date, datetime, timedelta
import pandas as pd
import numpy as np
from dataclasses import dataclass
from enum import Enum
import warnings

from app.common.utils.logging_config import get_logger

logger = get_logger(__name__)


class ValidationSeverity(Enum):
    """검증 결과 심각도"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ValidationResult:
    """검증 결과"""

    check_name: str
    severity: ValidationSeverity
    passed: bool
    message: str
    details: Optional[Dict[str, Any]] = None
    affected_records: int = 0
    suggestion: Optional[str] = None


@dataclass
class QualityScore:
    """데이터 품질 점수"""

    overall_score: float  # 0.0 ~ 1.0
    completeness_score: float
    consistency_score: float
    accuracy_score: float
    timeliness_score: float
    validity_score: float


class DataQualityValidator:
    """
    데이터 품질 검증기

    다양한 검증 규칙을 적용하여 데이터 품질을 평가합니다.
    """

    def __init__(self, strict_mode: bool = False):
        """
        검증기 초기화

        Args:
            strict_mode: 엄격 모드 (더 까다로운 검증 적용)
        """
        self.strict_mode = strict_mode
        self.validation_results: List[ValidationResult] = []

    def validate_dataset(
        self,
        data: pd.DataFrame,
        symbol: str,
        expected_date_range: Optional[Tuple[date, date]] = None,
        required_columns: Optional[List[str]] = None,
    ) -> Tuple[bool, List[ValidationResult], QualityScore]:
        """
        데이터셋 전체 검증

        Args:
            data: 검증할 데이터
            symbol: 심볼
            expected_date_range: 예상 날짜 범위
            required_columns: 필수 컬럼 목록

        Returns:
            (전체 검증 통과 여부, 검증 결과 목록, 품질 점수)
        """
        self.validation_results = []

        logger.info(
            "data_quality_validation_started",
            symbol=symbol,
            records=len(data),
            columns=len(data.columns) if not data.empty else 0,
        )

        # 1. 기본 구조 검증
        self._validate_basic_structure(data, required_columns)

        # 2. 데이터 완성도 검증
        self._validate_completeness(data, expected_date_range)

        # 3. 데이터 일관성 검증
        self._validate_consistency(data)

        # 4. 가격 데이터 정확성 검증
        if self._has_price_columns(data):
            self._validate_price_accuracy(data)

        # 5. 시계열 연속성 검증
        self._validate_time_series_continuity(data)

        # 6. 통계적 이상치 검증
        self._validate_statistical_outliers(data)

        # 7. 특성별 유효성 검증
        self._validate_feature_validity(data)

        # 품질 점수 계산
        quality_score = self._calculate_quality_score(data)

        # 전체 검증 결과 판정
        overall_passed = self._determine_overall_result()

        logger.info(
            "data_quality_validation_completed",
            symbol=symbol,
            overall_passed=overall_passed,
            total_checks=len(self.validation_results),
            quality_score=quality_score.overall_score,
            errors=len(
                [
                    r
                    for r in self.validation_results
                    if r.severity == ValidationSeverity.ERROR
                ]
            ),
            warnings=len(
                [
                    r
                    for r in self.validation_results
                    if r.severity == ValidationSeverity.WARNING
                ]
            ),
        )

        return overall_passed, self.validation_results, quality_score

    def _validate_basic_structure(
        self, data: pd.DataFrame, required_columns: Optional[List[str]]
    ) -> None:
        """기본 구조 검증"""

        # 데이터 존재 여부
        if data.empty:
            self.validation_results.append(
                ValidationResult(
                    check_name="data_existence",
                    severity=ValidationSeverity.CRITICAL,
                    passed=False,
                    message="Dataset is empty",
                    suggestion="Check data source and date range",
                )
            )
            return

        # 필수 컬럼 존재 여부
        if required_columns:
            missing_columns = [
                col for col in required_columns if col not in data.columns
            ]
            if missing_columns:
                self.validation_results.append(
                    ValidationResult(
                        check_name="required_columns",
                        severity=ValidationSeverity.ERROR,
                        passed=False,
                        message=f"Missing required columns: {missing_columns}",
                        details={"missing_columns": missing_columns},
                        suggestion="Ensure all required data sources are available",
                    )
                )

        # 인덱스 타입 확인
        if not isinstance(data.index, pd.DatetimeIndex):
            # 날짜 인덱스가 아닌 경우 경고
            self.validation_results.append(
                ValidationResult(
                    check_name="date_index",
                    severity=ValidationSeverity.WARNING,
                    passed=False,
                    message="Index is not DatetimeIndex",
                    suggestion="Convert index to DatetimeIndex for time series analysis",
                )
            )

        # 기본 구조 검증 통과
        self.validation_results.append(
            ValidationResult(
                check_name="basic_structure",
                severity=ValidationSeverity.INFO,
                passed=True,
                message=f"Dataset has {len(data)} records and {len(data.columns)} columns",
            )
        )

    def _validate_completeness(
        self, data: pd.DataFrame, expected_date_range: Optional[Tuple[date, date]]
    ) -> None:
        """데이터 완성도 검증"""

        # 전체 결측치 비율
        total_cells = len(data) * len(data.columns)
        missing_cells = data.isnull().sum().sum()
        missing_ratio = missing_cells / total_cells if total_cells > 0 else 0

        missing_threshold = 0.05 if self.strict_mode else 0.1  # 5% or 10%

        if missing_ratio > missing_threshold:
            self.validation_results.append(
                ValidationResult(
                    check_name="missing_data_ratio",
                    severity=(
                        ValidationSeverity.WARNING
                        if missing_ratio < 0.2
                        else ValidationSeverity.ERROR
                    ),
                    passed=False,
                    message=f"High missing data ratio: {missing_ratio:.2%}",
                    details={
                        "missing_ratio": missing_ratio,
                        "threshold": missing_threshold,
                    },
                    affected_records=missing_cells,
                    suggestion="Check data sources for completeness",
                )
            )

        # 컬럼별 결측치 확인
        column_missing = data.isnull().sum()
        problematic_columns = column_missing[
            column_missing > len(data) * 0.3
        ]  # 30% 이상 결측

        if len(problematic_columns) > 0:
            self.validation_results.append(
                ValidationResult(
                    check_name="column_missing_data",
                    severity=ValidationSeverity.WARNING,
                    passed=False,
                    message=f"Columns with high missing data: {list(problematic_columns.index)}",
                    details={"problematic_columns": problematic_columns.to_dict()},
                    suggestion="Consider removing or imputing these columns",
                )
            )

        # 날짜 범위 완성도 (예상 범위가 주어진 경우)
        if expected_date_range and isinstance(data.index, pd.DatetimeIndex):
            expected_start, expected_end = expected_date_range
            actual_start = data.index.min().date()
            actual_end = data.index.max().date()

            if actual_start > expected_start or actual_end < expected_end:
                self.validation_results.append(
                    ValidationResult(
                        check_name="date_range_completeness",
                        severity=ValidationSeverity.WARNING,
                        passed=False,
                        message=f"Date range incomplete. Expected: {expected_start} to {expected_end}, Actual: {actual_start} to {actual_end}",
                        details={
                            "expected_start": expected_start.isoformat(),
                            "expected_end": expected_end.isoformat(),
                            "actual_start": actual_start.isoformat(),
                            "actual_end": actual_end.isoformat(),
                        },
                        suggestion="Check data source for missing date ranges",
                    )
                )

    def _validate_consistency(self, data: pd.DataFrame) -> None:
        """데이터 일관성 검증"""

        # 중복 인덱스 확인
        if data.index.duplicated().any():
            duplicate_count = data.index.duplicated().sum()
            self.validation_results.append(
                ValidationResult(
                    check_name="duplicate_indices",
                    severity=ValidationSeverity.ERROR,
                    passed=False,
                    message=f"Found {duplicate_count} duplicate indices",
                    affected_records=duplicate_count,
                    suggestion="Remove or aggregate duplicate records",
                )
            )

        # 데이터 타입 일관성
        numeric_columns = data.select_dtypes(include=[np.number]).columns
        for col in numeric_columns:
            if data[col].dtype == "object":
                self.validation_results.append(
                    ValidationResult(
                        check_name="data_type_consistency",
                        severity=ValidationSeverity.WARNING,
                        passed=False,
                        message=f"Column {col} should be numeric but has object dtype",
                        details={"column": col, "dtype": str(data[col].dtype)},
                        suggestion=f"Convert column {col} to numeric type",
                    )
                )

        # 무한값 확인
        inf_count = np.isinf(data.select_dtypes(include=[np.number])).sum().sum()
        if inf_count > 0:
            self.validation_results.append(
                ValidationResult(
                    check_name="infinite_values",
                    severity=ValidationSeverity.ERROR,
                    passed=False,
                    message=f"Found {inf_count} infinite values",
                    affected_records=inf_count,
                    suggestion="Replace infinite values with NaN or appropriate values",
                )
            )

    def _validate_price_accuracy(self, data: pd.DataFrame) -> None:
        """가격 데이터 정확성 검증"""

        price_columns = ["open", "high", "low", "close"]
        available_price_columns = [col for col in price_columns if col in data.columns]

        if len(available_price_columns) < 4:
            return  # OHLC 데이터가 완전하지 않으면 건너뛰기

        # OHLC 논리적 관계 검증
        invalid_ohlc = data[
            (data["high"] < data["low"])
            | (data["high"] < data["open"])
            | (data["high"] < data["close"])
            | (data["low"] > data["open"])
            | (data["low"] > data["close"])
        ]

        if len(invalid_ohlc) > 0:
            self.validation_results.append(
                ValidationResult(
                    check_name="ohlc_logical_consistency",
                    severity=ValidationSeverity.ERROR,
                    passed=False,
                    message=f"Found {len(invalid_ohlc)} records with invalid OHLC relationships",
                    affected_records=len(invalid_ohlc),
                    details={
                        "invalid_dates": invalid_ohlc.index.tolist()[:10]
                    },  # 처음 10개만
                    suggestion="Check data source for OHLC calculation errors",
                )
            )

        # 음수 또는 0 가격 확인
        negative_prices = data[(data[available_price_columns] <= 0).any(axis=1)]

        if len(negative_prices) > 0:
            self.validation_results.append(
                ValidationResult(
                    check_name="negative_zero_prices",
                    severity=ValidationSeverity.ERROR,
                    passed=False,
                    message=f"Found {len(negative_prices)} records with negative or zero prices",
                    affected_records=len(negative_prices),
                    suggestion="Remove or correct records with invalid prices",
                )
            )

        # 가격 변동성 검증 (일일 변동률이 50% 이상인 경우)
        if "close" in data.columns:
            daily_returns = data["close"].pct_change().abs()
            extreme_moves = daily_returns[daily_returns > 0.5]  # 50% 이상 변동

            if len(extreme_moves) > 0:
                severity = (
                    ValidationSeverity.WARNING
                    if len(extreme_moves) < 5
                    else ValidationSeverity.ERROR
                )
                self.validation_results.append(
                    ValidationResult(
                        check_name="extreme_price_movements",
                        severity=severity,
                        passed=False,
                        message=f"Found {len(extreme_moves)} days with extreme price movements (>50%)",
                        affected_records=len(extreme_moves),
                        details={"max_daily_return": daily_returns.max()},
                        suggestion="Verify extreme price movements for data quality issues",
                    )
                )

    def _validate_time_series_continuity(self, data: pd.DataFrame) -> None:
        """시계열 연속성 검증"""

        if not isinstance(data.index, pd.DatetimeIndex) or len(data) < 2:
            return

        # 날짜 간격 분석
        date_diffs = pd.Series(data.index).diff().dt.days
        date_diffs = date_diffs.dropna()

        if len(date_diffs) == 0:
            return

        # 큰 간격 (7일 이상) 확인
        large_gaps = date_diffs[date_diffs > 7]

        if len(large_gaps) > 0:
            max_gap = large_gaps.max()
            severity = (
                ValidationSeverity.WARNING
                if len(large_gaps) < 5
                else ValidationSeverity.ERROR
            )

            self.validation_results.append(
                ValidationResult(
                    check_name="time_series_gaps",
                    severity=severity,
                    passed=False,
                    message=f"Found {len(large_gaps)} large time gaps (>7 days), max gap: {max_gap} days",
                    affected_records=len(large_gaps),
                    details={
                        "max_gap_days": int(max_gap),
                        "gap_count": len(large_gaps),
                    },
                    suggestion="Check for missing data in date ranges with large gaps",
                )
            )

        # 정렬 순서 확인
        if not data.index.is_monotonic_increasing:
            self.validation_results.append(
                ValidationResult(
                    check_name="time_series_ordering",
                    severity=ValidationSeverity.WARNING,
                    passed=False,
                    message="Time series is not in chronological order",
                    suggestion="Sort data by date index",
                )
            )

    def _validate_statistical_outliers(self, data: pd.DataFrame) -> None:
        """통계적 이상치 검증"""

        numeric_columns = data.select_dtypes(include=[np.number]).columns

        for col in numeric_columns:
            if data[col].isnull().all():
                continue

            # IQR 방법으로 이상치 탐지
            Q1 = data[col].quantile(0.25)
            Q3 = data[col].quantile(0.75)
            IQR = Q3 - Q1

            if IQR == 0:  # 모든 값이 동일한 경우
                continue

            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR

            outliers = data[(data[col] < lower_bound) | (data[col] > upper_bound)]

            if len(outliers) > 0:
                outlier_ratio = len(outliers) / len(data)
                severity = (
                    ValidationSeverity.INFO
                    if outlier_ratio < 0.05
                    else ValidationSeverity.WARNING
                )

                self.validation_results.append(
                    ValidationResult(
                        check_name=f"statistical_outliers_{col}",
                        severity=severity,
                        passed=outlier_ratio < 0.1,  # 10% 이하면 통과
                        message=f"Column {col} has {len(outliers)} outliers ({outlier_ratio:.2%})",
                        affected_records=len(outliers),
                        details={
                            "column": col,
                            "outlier_ratio": outlier_ratio,
                            "bounds": {"lower": lower_bound, "upper": upper_bound},
                        },
                        suggestion="Consider outlier treatment for better model performance",
                    )
                )

    def _validate_feature_validity(self, data: pd.DataFrame) -> None:
        """특성별 유효성 검증"""

        # RSI 값 범위 확인 (0-100)
        rsi_columns = [col for col in data.columns if "rsi" in col.lower()]
        for col in rsi_columns:
            invalid_rsi = data[(data[col] < 0) | (data[col] > 100)]
            if len(invalid_rsi) > 0:
                self.validation_results.append(
                    ValidationResult(
                        check_name=f"rsi_range_{col}",
                        severity=ValidationSeverity.ERROR,
                        passed=False,
                        message=f"RSI column {col} has values outside 0-100 range",
                        affected_records=len(invalid_rsi),
                        suggestion="Check RSI calculation logic",
                    )
                )

        # 거래량 음수 확인
        volume_columns = [col for col in data.columns if "volume" in col.lower()]
        for col in volume_columns:
            negative_volume = data[data[col] < 0]
            if len(negative_volume) > 0:
                self.validation_results.append(
                    ValidationResult(
                        check_name=f"negative_volume_{col}",
                        severity=ValidationSeverity.ERROR,
                        passed=False,
                        message=f"Volume column {col} has negative values",
                        affected_records=len(negative_volume),
                        suggestion="Volume should always be non-negative",
                    )
                )

        # 백분율 특성 범위 확인
        percentage_columns = [
            col
            for col in data.columns
            if "percent" in col.lower() or "pct" in col.lower()
        ]
        for col in percentage_columns:
            extreme_percentages = data[(data[col] < -100) | (data[col] > 100)]
            if len(extreme_percentages) > 0:
                self.validation_results.append(
                    ValidationResult(
                        check_name=f"percentage_range_{col}",
                        severity=ValidationSeverity.WARNING,
                        passed=False,
                        message=f"Percentage column {col} has extreme values",
                        affected_records=len(extreme_percentages),
                        details={
                            "min_value": data[col].min(),
                            "max_value": data[col].max(),
                        },
                        suggestion="Verify percentage calculation logic",
                    )
                )

    def _has_price_columns(self, data: pd.DataFrame) -> bool:
        """가격 컬럼 존재 여부 확인"""
        price_columns = ["open", "high", "low", "close"]
        return any(col in data.columns for col in price_columns)

    def _calculate_quality_score(self, data: pd.DataFrame) -> QualityScore:
        """데이터 품질 점수 계산"""

        if data.empty:
            return QualityScore(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

        # 완성도 점수 (결측치 기반)
        total_cells = len(data) * len(data.columns)
        missing_cells = data.isnull().sum().sum()
        completeness_score = (
            1.0 - (missing_cells / total_cells) if total_cells > 0 else 0.0
        )

        # 일관성 점수 (중복, 무한값 기반)
        duplicate_ratio = (
            data.index.duplicated().sum() / len(data) if len(data) > 0 else 0.0
        )
        inf_ratio = (
            np.isinf(data.select_dtypes(include=[np.number])).sum().sum() / total_cells
            if total_cells > 0
            else 0.0
        )
        consistency_score = 1.0 - duplicate_ratio - inf_ratio

        # 정확성 점수 (가격 데이터 논리적 오류 기반)
        accuracy_score = 1.0
        if self._has_price_columns(data):
            price_columns = ["open", "high", "low", "close"]
            available_price_columns = [
                col for col in price_columns if col in data.columns
            ]

            if len(available_price_columns) >= 4:
                invalid_ohlc = data[
                    (data["high"] < data["low"])
                    | (data["high"] < data["open"])
                    | (data["high"] < data["close"])
                    | (data["low"] > data["open"])
                    | (data["low"] > data["close"])
                ]
                accuracy_score = 1.0 - (len(invalid_ohlc) / len(data))

        # 시의성 점수 (날짜 간격 기반)
        timeliness_score = 1.0
        if isinstance(data.index, pd.DatetimeIndex) and len(data) > 1:
            date_diffs = pd.Series(data.index).diff().dt.days.dropna()
            if len(date_diffs) > 0:
                large_gaps = date_diffs[date_diffs > 7]
                timeliness_score = 1.0 - (len(large_gaps) / len(date_diffs))

        # 유효성 점수 (특성별 범위 오류 기반)
        validity_score = 1.0
        error_results = [
            r for r in self.validation_results if r.severity == ValidationSeverity.ERROR
        ]
        if error_results:
            total_errors = sum(r.affected_records for r in error_results)
            validity_score = 1.0 - min(total_errors / len(data), 1.0)

        # 전체 점수 (가중 평균)
        weights = {
            "completeness": 0.25,
            "consistency": 0.20,
            "accuracy": 0.25,
            "timeliness": 0.15,
            "validity": 0.15,
        }

        overall_score = (
            completeness_score * weights["completeness"]
            + consistency_score * weights["consistency"]
            + accuracy_score * weights["accuracy"]
            + timeliness_score * weights["timeliness"]
            + validity_score * weights["validity"]
        )

        return QualityScore(
            overall_score=max(0.0, min(1.0, overall_score)),
            completeness_score=max(0.0, min(1.0, completeness_score)),
            consistency_score=max(0.0, min(1.0, consistency_score)),
            accuracy_score=max(0.0, min(1.0, accuracy_score)),
            timeliness_score=max(0.0, min(1.0, timeliness_score)),
            validity_score=max(0.0, min(1.0, validity_score)),
        )

    def _determine_overall_result(self) -> bool:
        """전체 검증 결과 판정"""

        # CRITICAL 오류가 있으면 실패
        critical_errors = [
            r
            for r in self.validation_results
            if r.severity == ValidationSeverity.CRITICAL
        ]
        if critical_errors:
            return False

        # ERROR가 너무 많으면 실패
        errors = [
            r for r in self.validation_results if r.severity == ValidationSeverity.ERROR
        ]
        if len(errors) > 5:  # 5개 이상 오류
            return False

        # 엄격 모드에서는 ERROR가 하나라도 있으면 실패
        if self.strict_mode and errors:
            return False

        return True

    def get_validation_summary(self) -> Dict[str, Any]:
        """검증 결과 요약 반환"""

        severity_counts = {}
        for severity in ValidationSeverity:
            severity_counts[severity.value] = len(
                [r for r in self.validation_results if r.severity == severity]
            )

        failed_checks = [r for r in self.validation_results if not r.passed]

        return {
            "total_checks": len(self.validation_results),
            "passed_checks": len(self.validation_results) - len(failed_checks),
            "failed_checks": len(failed_checks),
            "severity_counts": severity_counts,
            "critical_issues": [
                r.message
                for r in self.validation_results
                if r.severity == ValidationSeverity.CRITICAL
            ],
            "error_issues": [
                r.message
                for r in self.validation_results
                if r.severity == ValidationSeverity.ERROR
            ],
            "warning_issues": [
                r.message
                for r in self.validation_results
                if r.severity == ValidationSeverity.WARNING
            ],
        }
