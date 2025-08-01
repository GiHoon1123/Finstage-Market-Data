"""
메모리 사용량 최적화 시스템

pandas DataFrame 메모리 효율화, 데이터 타입 최적화, 
가비지 컬렉션 관리 등을 제공합니다.
"""

import gc
import sys
import psutil
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Iterator, Optional, Union
from functools import wraps
import time
import threading

from app.common.utils.logging_config import get_logger

logger = get_logger(__name__)


class MemoryOptimizer:
    """메모리 최적화 유틸리티"""

    @staticmethod
    def optimize_dataframe(df: pd.DataFrame, aggressive: bool = False) -> pd.DataFrame:
        """
        DataFrame 메모리 사용량 최적화

        Args:
            df: 최적화할 DataFrame
            aggressive: 공격적 최적화 여부 (정밀도 손실 가능)

        Returns:
            최적화된 DataFrame
        """
        if df.empty:
            return df

        original_memory = df.memory_usage(deep=True).sum()
        optimized_df = df.copy()

        # 정수형 다운캐스팅
        for col in optimized_df.select_dtypes(include=["int64"]).columns:
            col_min = optimized_df[col].min()
            col_max = optimized_df[col].max()

            if col_min >= -128 and col_max <= 127:
                optimized_df[col] = optimized_df[col].astype("int8")
            elif col_min >= -32768 and col_max <= 32767:
                optimized_df[col] = optimized_df[col].astype("int16")
            elif col_min >= -2147483648 and col_max <= 2147483647:
                optimized_df[col] = optimized_df[col].astype("int32")

        # 실수형 다운캐스팅
        for col in optimized_df.select_dtypes(include=["float64"]).columns:
            if aggressive:
                # 공격적 최적화: float32로 변환 (정밀도 손실 가능)
                optimized_df[col] = pd.to_numeric(optimized_df[col], downcast="float")
            else:
                # 안전한 최적화: 값 범위 확인 후 변환
                col_min = optimized_df[col].min()
                col_max = optimized_df[col].max()

                # float32 범위 확인
                if (
                    col_min >= np.finfo(np.float32).min
                    and col_max <= np.finfo(np.float32).max
                ):
                    optimized_df[col] = optimized_df[col].astype("float32")

        # 문자열 카테고리화 (중복이 많은 경우)
        for col in optimized_df.select_dtypes(include=["object"]).columns:
            if optimized_df[col].dtype == "object":
                unique_ratio = optimized_df[col].nunique() / len(optimized_df)

                # 유니크 비율이 50% 미만이면 카테고리화
                if unique_ratio < 0.5:
                    optimized_df[col] = optimized_df[col].astype("category")

        # 불필요한 인덱스 최적화
        if not optimized_df.index.is_unique:
            optimized_df = optimized_df.reset_index(drop=True)

        optimized_memory = optimized_df.memory_usage(deep=True).sum()
        memory_saved = original_memory - optimized_memory
        reduction_percent = (memory_saved / original_memory) * 100

        logger.info(
            "dataframe_optimized",
            original_memory_mb=round(original_memory / 1024 / 1024, 2),
            optimized_memory_mb=round(optimized_memory / 1024 / 1024, 2),
            memory_saved_mb=round(memory_saved / 1024 / 1024, 2),
            reduction_percent=round(reduction_percent, 1),
            rows=len(optimized_df),
            columns=len(optimized_df.columns),
        )

        return optimized_df

    @staticmethod
    def get_memory_usage() -> Dict[str, float]:
        """현재 메모리 사용량 조회"""
        process = psutil.Process()
        memory_info = process.memory_info()

        return {
            "rss_mb": round(memory_info.rss / 1024 / 1024, 2),  # 물리 메모리
            "vms_mb": round(memory_info.vms / 1024 / 1024, 2),  # 가상 메모리
            "percent": round(process.memory_percent(), 2),  # 시스템 메모리 대비 %
            "available_mb": round(psutil.virtual_memory().available / 1024 / 1024, 2),
        }

    @staticmethod
    def force_garbage_collection() -> Dict[str, int]:
        """강제 가비지 컬렉션 실행"""
        before_memory = MemoryOptimizer.get_memory_usage()["rss_mb"]

        # 3세대 가비지 컬렉션 실행
        collected = {
            "generation_0": gc.collect(0),
            "generation_1": gc.collect(1),
            "generation_2": gc.collect(2),
        }

        after_memory = MemoryOptimizer.get_memory_usage()["rss_mb"]
        memory_freed = before_memory - after_memory

        logger.info(
            "garbage_collection_completed",
            collected_objects=sum(collected.values()),
            memory_freed_mb=round(memory_freed, 2),
            details=collected,
        )

        return collected

    @staticmethod
    def get_object_counts() -> Dict[str, int]:
        """메모리 내 객체 수 조회"""
        return {
            "total_objects": len(gc.get_objects()),
            "generation_0": len(gc.get_objects(0)),
            "generation_1": len(gc.get_objects(1)),
            "generation_2": len(gc.get_objects(2)),
            "garbage_count": len(gc.garbage),
        }


def memory_efficient_batch_processor(
    data: List[Any], batch_size: int = 100, cleanup_interval: int = 10
) -> Iterator[Any]:
    """
    메모리 효율적인 배치 처리기

    Args:
        data: 처리할 데이터 리스트
        batch_size: 배치 크기
        cleanup_interval: 가비지 컬렉션 실행 간격 (배치 수)

    Yields:
        처리된 배치 결과
    """
    batch_count = 0

    for i in range(0, len(data), batch_size):
        batch = data[i : i + batch_size]

        try:
            # 배치 처리
            yield batch

            batch_count += 1

            # 주기적 메모리 정리
            if batch_count % cleanup_interval == 0:
                MemoryOptimizer.force_garbage_collection()

                memory_usage = MemoryOptimizer.get_memory_usage()
                logger.debug(
                    "batch_processing_memory_check",
                    batch_number=batch_count,
                    memory_usage_mb=memory_usage["rss_mb"],
                    memory_percent=memory_usage["percent"],
                )

        except Exception as e:
            logger.error(
                "batch_processing_error",
                batch_number=batch_count,
                batch_size=len(batch),
                error=str(e),
            )
            raise


def memory_monitor(threshold_mb: float = 500.0):
    """
    메모리 사용량 모니터링 데코레이터

    Args:
        threshold_mb: 경고 임계값 (MB)
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 실행 전 메모리 상태
            before_memory = MemoryOptimizer.get_memory_usage()
            start_time = time.time()

            try:
                result = func(*args, **kwargs)

                # 실행 후 메모리 상태
                after_memory = MemoryOptimizer.get_memory_usage()
                execution_time = time.time() - start_time

                memory_diff = after_memory["rss_mb"] - before_memory["rss_mb"]

                # 메모리 사용량 로깅
                logger.info(
                    "function_memory_usage",
                    function=func.__name__,
                    execution_time=round(execution_time, 3),
                    memory_before_mb=before_memory["rss_mb"],
                    memory_after_mb=after_memory["rss_mb"],
                    memory_diff_mb=round(memory_diff, 2),
                    memory_percent=after_memory["percent"],
                )

                # 임계값 초과 경고
                if after_memory["rss_mb"] > threshold_mb:
                    logger.warning(
                        "high_memory_usage_detected",
                        function=func.__name__,
                        memory_usage_mb=after_memory["rss_mb"],
                        threshold_mb=threshold_mb,
                    )

                return result

            except Exception as e:
                after_memory = MemoryOptimizer.get_memory_usage()
                execution_time = time.time() - start_time

                logger.error(
                    "function_memory_error",
                    function=func.__name__,
                    execution_time=round(execution_time, 3),
                    memory_mb=after_memory["rss_mb"],
                    error=str(e),
                )
                raise

        return wrapper

    return decorator


def optimize_dataframe_memory(aggressive: bool = False):
    """DataFrame 메모리 최적화 데코레이터"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)

            # 결과가 DataFrame인 경우 최적화
            if isinstance(result, pd.DataFrame):
                return MemoryOptimizer.optimize_dataframe(result, aggressive=aggressive)

            # 결과가 DataFrame을 포함한 딕셔너리인 경우
            elif isinstance(result, dict):
                optimized_result = {}
                for key, value in result.items():
                    if isinstance(value, pd.DataFrame):
                        optimized_result[key] = MemoryOptimizer.optimize_dataframe(
                            value, aggressive=aggressive
                        )
                    else:
                        optimized_result[key] = value
                return optimized_result

            # 결과가 DataFrame 리스트인 경우
            elif (
                isinstance(result, list)
                and result
                and isinstance(result[0], pd.DataFrame)
            ):
                return [
                    MemoryOptimizer.optimize_dataframe(df, aggressive=aggressive)
                    for df in result
                ]

            return result

        return wrapper

    return decorator


class MemoryProfiler:
    """메모리 프로파일링 도구"""

    def __init__(self):
        self.snapshots = []

    def take_snapshot(self, label: str = None) -> Dict[str, Any]:
        """메모리 스냅샷 생성"""
        snapshot = {
            "timestamp": time.time(),
            "label": label or f"snapshot_{len(self.snapshots)}",
            "memory_usage": MemoryOptimizer.get_memory_usage(),
            "object_counts": MemoryOptimizer.get_object_counts(),
            "gc_stats": gc.get_stats(),
        }

        self.snapshots.append(snapshot)

        logger.debug(
            "memory_snapshot_taken",
            label=snapshot["label"],
            memory_mb=snapshot["memory_usage"]["rss_mb"],
            total_objects=snapshot["object_counts"]["total_objects"],
        )

        return snapshot

    def compare_snapshots(self, start_label: str, end_label: str) -> Dict[str, Any]:
        """두 스냅샷 간 메모리 사용량 비교"""
        start_snapshot = next(
            (s for s in self.snapshots if s["label"] == start_label), None
        )
        end_snapshot = next(
            (s for s in self.snapshots if s["label"] == end_label), None
        )

        if not start_snapshot or not end_snapshot:
            raise ValueError("Snapshot not found")

        memory_diff = (
            end_snapshot["memory_usage"]["rss_mb"]
            - start_snapshot["memory_usage"]["rss_mb"]
        )

        object_diff = (
            end_snapshot["object_counts"]["total_objects"]
            - start_snapshot["object_counts"]["total_objects"]
        )

        time_diff = end_snapshot["timestamp"] - start_snapshot["timestamp"]

        comparison = {
            "start_label": start_label,
            "end_label": end_label,
            "time_diff_seconds": round(time_diff, 2),
            "memory_diff_mb": round(memory_diff, 2),
            "object_diff": object_diff,
            "start_memory_mb": start_snapshot["memory_usage"]["rss_mb"],
            "end_memory_mb": end_snapshot["memory_usage"]["rss_mb"],
        }

        logger.info("memory_snapshot_comparison", **comparison)

        return comparison

    def get_memory_trend(self) -> List[Dict[str, Any]]:
        """메모리 사용량 트렌드 조회"""
        if len(self.snapshots) < 2:
            return []

        trend = []
        for i in range(1, len(self.snapshots)):
            prev = self.snapshots[i - 1]
            curr = self.snapshots[i]

            trend.append(
                {
                    "from_label": prev["label"],
                    "to_label": curr["label"],
                    "time_diff": curr["timestamp"] - prev["timestamp"],
                    "memory_diff_mb": curr["memory_usage"]["rss_mb"]
                    - prev["memory_usage"]["rss_mb"],
                    "object_diff": (
                        curr["object_counts"]["total_objects"]
                        - prev["object_counts"]["total_objects"]
                    ),
                }
            )

        return trend


# 전역 메모리 프로파일러
memory_profiler = MemoryProfiler()


class MemoryManager:
    """통합 메모리 관리 시스템"""

    def __init__(self):
        self.optimization_history = []
        self.memory_alerts = []
        self._lock = threading.Lock()

    def optimize_system_memory(self, aggressive: bool = False) -> Dict[str, Any]:
        """시스템 전체 메모리 최적화"""
        start_time = time.time()
        before_memory = MemoryOptimizer.get_memory_usage()

        optimization_results = {
            "timestamp": start_time,
            "before_memory_mb": before_memory["rss_mb"],
            "optimizations_performed": [],
            "memory_freed_mb": 0,
            "success": True,
        }

        try:
            # 1. 가비지 컬렉션 실행
            gc_result = MemoryOptimizer.force_garbage_collection()
            optimization_results["optimizations_performed"].append(
                {
                    "type": "garbage_collection",
                    "objects_collected": sum(gc_result.values()),
                    "details": gc_result,
                }
            )

            # 2. 캐시 정리 (만료된 항목)
            try:
                from app.common.utils.memory_cache import cache_manager

                expired_items = cache_manager.cleanup_all_expired()
                total_expired = sum(expired_items.values())

                optimization_results["optimizations_performed"].append(
                    {
                        "type": "cache_cleanup",
                        "expired_items": total_expired,
                        "details": expired_items,
                    }
                )
            except ImportError:
                pass

            # 3. 공격적 최적화 (필요시)
            if aggressive:
                # 추가 메모리 정리 작업
                import sys

                # 모듈 캐시 정리
                modules_before = len(sys.modules)

                # 사용하지 않는 모듈 정리 (주의: 필요한 모듈까지 제거될 수 있음)
                unused_modules = []
                for module_name, module in list(sys.modules.items()):
                    if hasattr(module, "__file__") and module.__file__:
                        # 특정 조건에 맞는 모듈만 제거
                        if any(
                            pattern in module_name
                            for pattern in ["test_", "_test", "debug"]
                        ):
                            unused_modules.append(module_name)

                for module_name in unused_modules:
                    if module_name in sys.modules:
                        del sys.modules[module_name]

                optimization_results["optimizations_performed"].append(
                    {
                        "type": "module_cleanup",
                        "modules_removed": len(unused_modules),
                        "modules_before": modules_before,
                        "modules_after": len(sys.modules),
                    }
                )

            # 최종 메모리 상태 확인
            after_memory = MemoryOptimizer.get_memory_usage()
            memory_freed = before_memory["rss_mb"] - after_memory["rss_mb"]

            optimization_results.update(
                {
                    "after_memory_mb": after_memory["rss_mb"],
                    "memory_freed_mb": round(memory_freed, 2),
                    "optimization_time_seconds": round(time.time() - start_time, 2),
                    "memory_reduction_percent": (
                        round((memory_freed / before_memory["rss_mb"]) * 100, 2)
                        if before_memory["rss_mb"] > 0
                        else 0
                    ),
                }
            )

            # 최적화 기록 저장
            with self._lock:
                self.optimization_history.append(optimization_results)
                # 최근 100개 기록만 유지
                if len(self.optimization_history) > 100:
                    self.optimization_history = self.optimization_history[-100:]

            logger.info(
                "system_memory_optimization_completed",
                **{
                    k: v
                    for k, v in optimization_results.items()
                    if k not in ["optimizations_performed"]
                },
            )

            return optimization_results

        except Exception as e:
            optimization_results.update(
                {
                    "success": False,
                    "error": str(e),
                    "optimization_time_seconds": round(time.time() - start_time, 2),
                }
            )

            logger.error("system_memory_optimization_failed", error=str(e))
            return optimization_results

    def check_memory_health(self) -> Dict[str, Any]:
        """메모리 건강 상태 확인"""
        memory_usage = MemoryOptimizer.get_memory_usage()
        object_counts = MemoryOptimizer.get_object_counts()

        # 건강 상태 판정
        health_status = "healthy"
        alerts = []

        # 메모리 사용률 확인
        if memory_usage["percent"] > 90:
            health_status = "critical"
            alerts.append("메모리 사용률이 90%를 초과했습니다")
        elif memory_usage["percent"] > 75:
            health_status = "warning"
            alerts.append("메모리 사용률이 75%를 초과했습니다")

        # 가용 메모리 확인
        if memory_usage["available_mb"] < 500:
            health_status = "critical"
            alerts.append("가용 메모리가 500MB 미만입니다")
        elif memory_usage["available_mb"] < 1000:
            if health_status == "healthy":
                health_status = "warning"
            alerts.append("가용 메모리가 1GB 미만입니다")

        # 객체 수 확인
        if object_counts["total_objects"] > 100000:
            if health_status == "healthy":
                health_status = "warning"
            alerts.append("메모리 내 객체 수가 100,000개를 초과했습니다")

        # 가비지 컬렉션 확인
        if object_counts["garbage_count"] > 1000:
            if health_status == "healthy":
                health_status = "warning"
            alerts.append("가비지 컬렉션 대상 객체가 1,000개를 초과했습니다")

        health_report = {
            "timestamp": time.time(),
            "health_status": health_status,
            "alerts": alerts,
            "memory_usage": memory_usage,
            "object_counts": object_counts,
            "recommendations": self._get_optimization_recommendations(
                memory_usage, object_counts
            ),
        }

        # 알림 저장
        if alerts:
            with self._lock:
                self.memory_alerts.extend(
                    [
                        {
                            "timestamp": time.time(),
                            "level": health_status,
                            "message": alert,
                        }
                        for alert in alerts
                    ]
                )

                # 최근 50개 알림만 유지
                if len(self.memory_alerts) > 50:
                    self.memory_alerts = self.memory_alerts[-50:]

        return health_report

    def _get_optimization_recommendations(
        self, memory_usage: Dict, object_counts: Dict
    ) -> List[str]:
        """최적화 권장사항 생성"""
        recommendations = []

        if memory_usage["percent"] > 80:
            recommendations.append(
                "메모리 사용률이 높습니다. 시스템 메모리 최적화를 실행하세요."
            )

        if object_counts["garbage_count"] > 500:
            recommendations.append(
                "가비지 컬렉션을 실행하여 불필요한 객체를 정리하세요."
            )

        if memory_usage["available_mb"] < 1000:
            recommendations.append(
                "가용 메모리가 부족합니다. 불필요한 프로세스를 종료하거나 메모리를 추가하세요."
            )

        if object_counts["total_objects"] > 50000:
            recommendations.append(
                "메모리 내 객체 수가 많습니다. 캐시 정리나 데이터 구조 최적화를 고려하세요."
            )

        return recommendations

    def get_optimization_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """최적화 기록 조회"""
        with self._lock:
            return (
                self.optimization_history[-limit:] if self.optimization_history else []
            )

    def get_memory_alerts(self, limit: int = 20) -> List[Dict[str, Any]]:
        """메모리 알림 조회"""
        with self._lock:
            return self.memory_alerts[-limit:] if self.memory_alerts else []


# 전역 메모리 매니저
memory_manager = MemoryManager()


def auto_memory_optimization(threshold_percent: float = 85.0):
    """자동 메모리 최적화 데코레이터"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 함수 실행 전 메모리 확인
            before_memory = MemoryOptimizer.get_memory_usage()

            result = func(*args, **kwargs)

            # 함수 실행 후 메모리 확인
            after_memory = MemoryOptimizer.get_memory_usage()

            # 임계값 초과 시 자동 최적화
            if after_memory["percent"] > threshold_percent:
                logger.warning(
                    "auto_optimization_triggered",
                    function=func.__name__,
                    memory_percent=after_memory["percent"],
                    threshold=threshold_percent,
                )

                optimization_result = memory_manager.optimize_system_memory()

                logger.info(
                    "auto_optimization_completed",
                    function=func.__name__,
                    memory_freed_mb=optimization_result["memory_freed_mb"],
                )

            return result

        return wrapper

    return decorator


def profile_memory(label: str = None):
    """메모리 프로파일링 데코레이터"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_label = f"{func.__name__}_start" if not label else f"{label}_start"
            end_label = f"{func.__name__}_end" if not label else f"{label}_end"

            # 시작 스냅샷
            memory_profiler.take_snapshot(start_label)

            try:
                result = func(*args, **kwargs)

                # 종료 스냅샷
                memory_profiler.take_snapshot(end_label)

                # 비교 결과 로깅
                comparison = memory_profiler.compare_snapshots(start_label, end_label)

                return result

            except Exception as e:
                # 에러 시에도 스냅샷 생성
                memory_profiler.take_snapshot(f"{end_label}_error")
                raise

        return wrapper

    return decorator
