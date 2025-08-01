"""
분산 작업 큐 시스템 (내장형)

Redis나 Celery 없이 Python 내장 기능만으로 구현한 작업 큐 시스템입니다.
백그라운드 작업 처리, 우선순위 관리, 작업 상태 추적을 제공합니다.
"""

import asyncio
import time
import uuid
import json
import pickle
from typing import Dict, List, Any, Optional, Callable, Union
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor
import threading
from queue import PriorityQueue, Empty
import functools

from app.common.utils.logging_config import get_logger
from app.common.utils.memory_optimizer import memory_monitor

logger = get_logger(__name__)


class TaskStatus(Enum):
    """작업 상태"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class TaskPriority(Enum):
    """작업 우선순위"""

    LOW = 3
    NORMAL = 2
    HIGH = 1
    CRITICAL = 0


@dataclass
class TaskResult:
    """작업 결과"""

    task_id: str
    status: TaskStatus
    result: Any = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    execution_time: Optional[float] = None
    retry_count: int = 0
    worker_id: Optional[str] = None


@dataclass
class Task:
    """작업 정의"""

    task_id: str
    func_name: str
    args: tuple
    kwargs: dict
    priority: TaskPriority
    max_retries: int
    retry_delay: float
    timeout: Optional[float]
    created_at: datetime
    scheduled_at: Optional[datetime] = None

    def __lt__(self, other):
        """우선순위 비교 (PriorityQueue용)"""
        if self.priority.value != other.priority.value:
            return self.priority.value < other.priority.value
        return self.created_at < other.created_at


class TaskWorker:
    """작업 워커"""

    def __init__(self, worker_id: str, task_queue: "TaskQueue"):
        self.worker_id = worker_id
        self.task_queue = task_queue
        self.is_running = False
        self.current_task: Optional[Task] = None
        self.processed_tasks = 0
        self.failed_tasks = 0
        self.started_at = datetime.now()

    async def start(self):
        """워커 시작"""
        self.is_running = True
        logger.info("task_worker_started", worker_id=self.worker_id)

        while self.is_running:
            try:
                # 작업 가져오기 (1초 타임아웃)
                task = await self._get_next_task()

                if task:
                    await self._process_task(task)
                else:
                    # 작업이 없으면 잠시 대기
                    await asyncio.sleep(0.1)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(
                    "task_worker_error", worker_id=self.worker_id, error=str(e)
                )
                await asyncio.sleep(1)

        logger.info("task_worker_stopped", worker_id=self.worker_id)

    async def stop(self):
        """워커 중지"""
        self.is_running = False

        # 현재 실행 중인 작업이 있으면 완료까지 대기
        if self.current_task:
            logger.info(
                "waiting_for_current_task_completion",
                worker_id=self.worker_id,
                task_id=self.current_task.task_id,
            )

            # 최대 30초 대기
            for _ in range(300):
                if not self.current_task:
                    break
                await asyncio.sleep(0.1)

    async def _get_next_task(self) -> Optional[Task]:
        """다음 작업 가져오기"""
        try:
            # 논블로킹으로 작업 가져오기
            return self.task_queue._get_task_nowait()
        except Empty:
            return None

    async def _process_task(self, task: Task):
        """작업 처리"""
        self.current_task = task
        task_result = TaskResult(
            task_id=task.task_id,
            status=TaskStatus.RUNNING,
            started_at=datetime.now(),
            worker_id=self.worker_id,
        )

        # 작업 상태 업데이트
        self.task_queue._update_task_result(task_result)

        try:
            logger.info(
                "task_processing_started",
                task_id=task.task_id,
                worker_id=self.worker_id,
                func_name=task.func_name,
            )

            start_time = time.time()

            # 작업 함수 실행
            func = self.task_queue._get_registered_function(task.func_name)
            if not func:
                raise ValueError(f"등록되지 않은 함수: {task.func_name}")

            # 타임아웃 설정
            if task.timeout:
                result = await asyncio.wait_for(
                    self._execute_function(func, task.args, task.kwargs),
                    timeout=task.timeout,
                )
            else:
                result = await self._execute_function(func, task.args, task.kwargs)

            # 성공 처리
            execution_time = time.time() - start_time
            task_result.status = TaskStatus.COMPLETED
            task_result.result = result
            task_result.completed_at = datetime.now()
            task_result.execution_time = execution_time

            self.processed_tasks += 1

            logger.info(
                "task_processing_completed",
                task_id=task.task_id,
                worker_id=self.worker_id,
                execution_time=execution_time,
            )

        except asyncio.TimeoutError:
            # 타임아웃 처리
            task_result.status = TaskStatus.FAILED
            task_result.error = f"작업 타임아웃 ({task.timeout}초)"
            task_result.completed_at = datetime.now()

            self.failed_tasks += 1

            logger.error(
                "task_timeout",
                task_id=task.task_id,
                worker_id=self.worker_id,
                timeout=task.timeout,
            )

        except Exception as e:
            # 에러 처리
            task_result.status = TaskStatus.FAILED
            task_result.error = str(e)
            task_result.completed_at = datetime.now()

            self.failed_tasks += 1

            logger.error(
                "task_processing_failed",
                task_id=task.task_id,
                worker_id=self.worker_id,
                error=str(e),
            )

            # 재시도 처리
            if task_result.retry_count < task.max_retries:
                await self._schedule_retry(task, task_result)

        finally:
            # 작업 결과 업데이트
            self.task_queue._update_task_result(task_result)
            self.current_task = None

    async def _execute_function(self, func: Callable, args: tuple, kwargs: dict) -> Any:
        """함수 실행 (동기/비동기 지원)"""
        if asyncio.iscoroutinefunction(func):
            # 비동기 함수
            return await func(*args, **kwargs)
        else:
            # 동기 함수 (스레드풀에서 실행)
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                self.task_queue.thread_executor,
                functools.partial(func, *args, **kwargs),
            )

    async def _schedule_retry(self, task: Task, task_result: TaskResult):
        """재시도 스케줄링"""
        task_result.retry_count += 1
        task_result.status = TaskStatus.RETRYING

        # 재시도 지연 시간 계산 (지수 백오프)
        delay = task.retry_delay * (2 ** (task_result.retry_count - 1))
        retry_at = datetime.now() + timedelta(seconds=delay)

        # 새 작업으로 재스케줄링
        retry_task = Task(
            task_id=f"{task.task_id}_retry_{task_result.retry_count}",
            func_name=task.func_name,
            args=task.args,
            kwargs=task.kwargs,
            priority=task.priority,
            max_retries=task.max_retries,
            retry_delay=task.retry_delay,
            timeout=task.timeout,
            created_at=datetime.now(),
            scheduled_at=retry_at,
        )

        await self.task_queue.schedule_task(retry_task, delay=delay)

        logger.info(
            "task_retry_scheduled",
            original_task_id=task.task_id,
            retry_task_id=retry_task.task_id,
            retry_count=task_result.retry_count,
            delay_seconds=delay,
        )

    def get_stats(self) -> Dict[str, Any]:
        """워커 통계"""
        uptime = (datetime.now() - self.started_at).total_seconds()

        return {
            "worker_id": self.worker_id,
            "is_running": self.is_running,
            "current_task_id": self.current_task.task_id if self.current_task else None,
            "processed_tasks": self.processed_tasks,
            "failed_tasks": self.failed_tasks,
            "success_rate": (
                (self.processed_tasks / (self.processed_tasks + self.failed_tasks))
                * 100
                if (self.processed_tasks + self.failed_tasks) > 0
                else 0
            ),
            "uptime_seconds": uptime,
            "started_at": self.started_at.isoformat(),
        }


class TaskQueue:
    """작업 큐 매니저"""

    def __init__(self, max_workers: int = 4, thread_pool_size: int = 8):
        self.max_workers = max_workers
        self.thread_executor = ThreadPoolExecutor(max_workers=thread_pool_size)

        # 작업 큐 (우선순위 큐)
        self.task_queue = PriorityQueue()
        self.scheduled_tasks: Dict[str, Task] = {}

        # 작업 결과 저장소
        self.task_results: Dict[str, TaskResult] = {}

        # 등록된 함수들
        self.registered_functions: Dict[str, Callable] = {}

        # 워커들
        self.workers: Dict[str, TaskWorker] = {}
        self.worker_tasks: Dict[str, asyncio.Task] = {}

        # 스케줄러
        self.scheduler_task: Optional[asyncio.Task] = None
        self.is_running = False

        # 통계
        self.total_tasks_submitted = 0
        self.total_tasks_completed = 0
        self.total_tasks_failed = 0

        # 스레드 안전성
        self._lock = threading.Lock()

    def register_function(self, name: str, func: Callable):
        """함수 등록"""
        self.registered_functions[name] = func
        logger.info("function_registered", name=name)

    def _get_registered_function(self, name: str) -> Optional[Callable]:
        """등록된 함수 조회"""
        return self.registered_functions.get(name)

    async def start(self):
        """작업 큐 시작"""
        if self.is_running:
            logger.warning("task_queue_already_running")
            return

        self.is_running = True

        # 워커들 시작
        for i in range(self.max_workers):
            worker_id = f"worker_{i+1}"
            worker = TaskWorker(worker_id, self)
            self.workers[worker_id] = worker

            # 워커 태스크 시작
            self.worker_tasks[worker_id] = asyncio.create_task(worker.start())

        # 스케줄러 시작
        self.scheduler_task = asyncio.create_task(self._scheduler_loop())

        logger.info(
            "task_queue_started",
            max_workers=self.max_workers,
            thread_pool_size=self.thread_executor._max_workers,
        )

    async def stop(self):
        """작업 큐 중지"""
        if not self.is_running:
            return

        self.is_running = False

        # 스케줄러 중지
        if self.scheduler_task:
            self.scheduler_task.cancel()
            try:
                await self.scheduler_task
            except asyncio.CancelledError:
                pass

        # 워커들 중지
        for worker in self.workers.values():
            await worker.stop()

        # 워커 태스크들 취소
        for task in self.worker_tasks.values():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        # 스레드풀 종료
        self.thread_executor.shutdown(wait=True)

        logger.info("task_queue_stopped")

    async def submit_task(
        self,
        func_name: str,
        *args,
        priority: TaskPriority = TaskPriority.NORMAL,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        timeout: Optional[float] = None,
        **kwargs,
    ) -> str:
        """작업 제출"""
        task_id = str(uuid.uuid4())

        task = Task(
            task_id=task_id,
            func_name=func_name,
            args=args,
            kwargs=kwargs,
            priority=priority,
            max_retries=max_retries,
            retry_delay=retry_delay,
            timeout=timeout,
            created_at=datetime.now(),
        )

        # 작업 큐에 추가
        self.task_queue.put(task)

        # 초기 결과 생성
        task_result = TaskResult(task_id=task_id, status=TaskStatus.PENDING)
        self._update_task_result(task_result)

        self.total_tasks_submitted += 1

        logger.info(
            "task_submitted",
            task_id=task_id,
            func_name=func_name,
            priority=priority.name,
        )

        return task_id

    async def schedule_task(self, task: Task, delay: float):
        """작업 스케줄링 (지연 실행)"""
        scheduled_at = datetime.now() + timedelta(seconds=delay)
        task.scheduled_at = scheduled_at

        with self._lock:
            self.scheduled_tasks[task.task_id] = task

        logger.info(
            "task_scheduled",
            task_id=task.task_id,
            delay_seconds=delay,
            scheduled_at=scheduled_at.isoformat(),
        )

    def _get_task_nowait(self) -> Optional[Task]:
        """논블로킹으로 작업 가져오기"""
        try:
            return self.task_queue.get_nowait()
        except Empty:
            return None

    def _update_task_result(self, task_result: TaskResult):
        """작업 결과 업데이트"""
        with self._lock:
            self.task_results[task_result.task_id] = task_result

            # 통계 업데이트
            if task_result.status == TaskStatus.COMPLETED:
                self.total_tasks_completed += 1
            elif task_result.status == TaskStatus.FAILED:
                self.total_tasks_failed += 1

    async def _scheduler_loop(self):
        """스케줄러 루프 (예약된 작업 처리)"""
        logger.info("task_scheduler_started")

        while self.is_running:
            try:
                current_time = datetime.now()
                ready_tasks = []

                # 실행 준비된 작업들 찾기
                with self._lock:
                    for task_id, task in list(self.scheduled_tasks.items()):
                        if task.scheduled_at and task.scheduled_at <= current_time:
                            ready_tasks.append(task)
                            del self.scheduled_tasks[task_id]

                # 준비된 작업들을 큐에 추가
                for task in ready_tasks:
                    self.task_queue.put(task)
                    logger.debug("scheduled_task_queued", task_id=task.task_id)

                # 1초 대기
                await asyncio.sleep(1)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("scheduler_loop_error", error=str(e))
                await asyncio.sleep(5)

        logger.info("task_scheduler_stopped")

    def get_task_result(self, task_id: str) -> Optional[TaskResult]:
        """작업 결과 조회"""
        with self._lock:
            return self.task_results.get(task_id)

    def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """작업 상태 조회"""
        result = self.get_task_result(task_id)
        return result.status if result else None

    async def wait_for_task(
        self, task_id: str, timeout: Optional[float] = None
    ) -> TaskResult:
        """작업 완료 대기"""
        start_time = time.time()

        while True:
            result = self.get_task_result(task_id)

            if result and result.status in [
                TaskStatus.COMPLETED,
                TaskStatus.FAILED,
                TaskStatus.CANCELLED,
            ]:
                return result

            # 타임아웃 확인
            if timeout and (time.time() - start_time) > timeout:
                raise asyncio.TimeoutError(f"작업 대기 타임아웃: {task_id}")

            await asyncio.sleep(0.1)

    def cancel_task(self, task_id: str) -> bool:
        """작업 취소"""
        # 대기 중인 작업 취소
        with self._lock:
            if task_id in self.scheduled_tasks:
                del self.scheduled_tasks[task_id]

                # 취소 상태로 업데이트
                task_result = TaskResult(
                    task_id=task_id,
                    status=TaskStatus.CANCELLED,
                    completed_at=datetime.now(),
                )
                self._update_task_result(task_result)

                logger.info("scheduled_task_cancelled", task_id=task_id)
                return True

        # 실행 중인 작업은 취소할 수 없음 (현재 구현에서는)
        result = self.get_task_result(task_id)
        if result and result.status == TaskStatus.RUNNING:
            logger.warning("cannot_cancel_running_task", task_id=task_id)
            return False

        return False

    @memory_monitor(threshold_mb=200.0)
    def get_stats(self) -> Dict[str, Any]:
        """작업 큐 통계"""
        with self._lock:
            pending_tasks = self.task_queue.qsize()
            scheduled_tasks = len(self.scheduled_tasks)

            # 상태별 작업 수 계산
            status_counts = {}
            for result in self.task_results.values():
                status = result.status.value
                status_counts[status] = status_counts.get(status, 0) + 1

        # 워커 통계
        worker_stats = [worker.get_stats() for worker in self.workers.values()]

        return {
            "timestamp": datetime.now().isoformat(),
            "is_running": self.is_running,
            "queue_stats": {
                "pending_tasks": pending_tasks,
                "scheduled_tasks": scheduled_tasks,
                "total_submitted": self.total_tasks_submitted,
                "total_completed": self.total_tasks_completed,
                "total_failed": self.total_tasks_failed,
                "success_rate": (
                    (self.total_tasks_completed / self.total_tasks_submitted) * 100
                    if self.total_tasks_submitted > 0
                    else 0
                ),
            },
            "status_counts": status_counts,
            "worker_stats": worker_stats,
            "registered_functions": list(self.registered_functions.keys()),
        }

    def cleanup_old_results(self, max_age_hours: int = 24):
        """오래된 작업 결과 정리"""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)

        with self._lock:
            old_task_ids = [
                task_id
                for task_id, result in self.task_results.items()
                if (result.completed_at and result.completed_at < cutoff_time)
            ]

            for task_id in old_task_ids:
                del self.task_results[task_id]

        logger.info(
            "old_task_results_cleaned",
            cleaned_count=len(old_task_ids),
            max_age_hours=max_age_hours,
        )


# 전역 작업 큐 인스턴스
task_queue = TaskQueue(max_workers=4, thread_pool_size=8)


# 데코레이터
def task(
    priority: TaskPriority = TaskPriority.NORMAL,
    max_retries: int = 3,
    retry_delay: float = 1.0,
    timeout: Optional[float] = None,
):
    """작업 데코레이터"""

    def decorator(func: Callable):
        # 함수 등록
        func_name = f"{func.__module__}.{func.__name__}"
        task_queue.register_function(func_name, func)

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            """비동기 래퍼"""
            task_id = await task_queue.submit_task(
                func_name,
                *args,
                priority=priority,
                max_retries=max_retries,
                retry_delay=retry_delay,
                timeout=timeout,
                **kwargs,
            )
            return task_id

        def sync_wrapper(*args, **kwargs):
            """동기 래퍼"""
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(async_wrapper(*args, **kwargs))

        # 원본 함수도 보존
        async_wrapper.original_func = func
        sync_wrapper.original_func = func

        # 비동기 환경에서는 async_wrapper, 동기 환경에서는 sync_wrapper 반환
        try:
            asyncio.get_running_loop()
            return async_wrapper
        except RuntimeError:
            return sync_wrapper

    return decorator
