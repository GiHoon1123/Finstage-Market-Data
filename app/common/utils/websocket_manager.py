"""
WebSocket 연결 관리 시스템

실시간 데이터 스트리밍을 위한 WebSocket 연결을 효율적으로 관리합니다.
클라이언트별 구독 관리, 브로드캐스팅, 연결 상태 모니터링을 제공합니다.
"""

import asyncio
import json
import time
from typing import Dict, Set, List, Any, Optional, Callable
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
from enum import Enum
import uuid

from app.common.utils.logging_config import get_logger
from app.common.utils.memory_optimizer import memory_monitor

logger = get_logger(__name__)


class MessageType(Enum):
    """WebSocket 메시지 타입"""

    PRICE_UPDATE = "price_update"
    TECHNICAL_ANALYSIS = "technical_analysis"
    ALERT = "alert"
    SYSTEM_STATUS = "system_status"
    SUBSCRIPTION = "subscription"
    HEARTBEAT = "heartbeat"
    ERROR = "error"


class SubscriptionType(Enum):
    """구독 타입"""

    PRICES = "prices"
    TECHNICAL_ANALYSIS = "technical_analysis"
    ALERTS = "alerts"
    ALL = "all"


class WebSocketConnection:
    """개별 WebSocket 연결 정보"""

    def __init__(self, websocket: WebSocket, client_id: str = None):
        self.websocket = websocket
        self.client_id = client_id or str(uuid.uuid4())
        self.connected_at = datetime.now()
        self.last_heartbeat = time.time()
        self.subscriptions: Set[str] = set()
        self.subscription_types: Set[SubscriptionType] = set()
        self.is_active = True
        self.message_count = 0
        self.error_count = 0

    async def send_message(self, message: Dict[str, Any]) -> bool:
        """메시지 전송"""
        try:
            if not self.is_active:
                return False

            await self.websocket.send_text(json.dumps(message))
            self.message_count += 1
            return True

        except Exception as e:
            logger.error(
                "websocket_send_failed", client_id=self.client_id, error=str(e)
            )
            self.error_count += 1
            self.is_active = False
            return False

    def update_heartbeat(self):
        """하트비트 업데이트"""
        self.last_heartbeat = time.time()

    def is_subscribed_to(
        self, symbol: str = None, message_type: MessageType = None
    ) -> bool:
        """구독 여부 확인"""
        # 전체 구독인 경우
        if SubscriptionType.ALL in self.subscription_types:
            return True

        # 메시지 타입별 구독 확인
        if message_type == MessageType.PRICE_UPDATE:
            if SubscriptionType.PRICES in self.subscription_types:
                return symbol is None or symbol in self.subscriptions
        elif message_type == MessageType.TECHNICAL_ANALYSIS:
            if SubscriptionType.TECHNICAL_ANALYSIS in self.subscription_types:
                return symbol is None or symbol in self.subscriptions
        elif message_type == MessageType.ALERT:
            if SubscriptionType.ALERTS in self.subscription_types:
                return True

        return False

    def get_stats(self) -> Dict[str, Any]:
        """연결 통계 조회"""
        return {
            "client_id": self.client_id,
            "connected_at": self.connected_at.isoformat(),
            "connection_duration_seconds": (
                datetime.now() - self.connected_at
            ).total_seconds(),
            "last_heartbeat": self.last_heartbeat,
            "subscriptions": list(self.subscriptions),
            "subscription_types": [st.value for st in self.subscription_types],
            "message_count": self.message_count,
            "error_count": self.error_count,
            "is_active": self.is_active,
        }


class WebSocketManager:
    """WebSocket 연결 관리자"""

    def __init__(self):
        self.connections: Dict[str, WebSocketConnection] = {}
        self.symbol_subscribers: Dict[str, Set[str]] = {}  # symbol -> client_ids
        self.type_subscribers: Dict[SubscriptionType, Set[str]] = {
            sub_type: set() for sub_type in SubscriptionType
        }
        self._lock = asyncio.Lock()
        self.heartbeat_interval = 30  # 30초
        self.heartbeat_task: Optional[asyncio.Task] = None
        self.cleanup_task: Optional[asyncio.Task] = None

        # 통계
        self.total_connections = 0
        self.total_messages_sent = 0
        self.total_errors = 0

    async def connect(self, websocket: WebSocket, client_id: str = None) -> str:
        """새 WebSocket 연결 등록"""
        connection = WebSocketConnection(websocket, client_id)

        async with self._lock:
            self.connections[connection.client_id] = connection
            self.total_connections += 1

        logger.info(
            "websocket_connected",
            client_id=connection.client_id,
            total_connections=len(self.connections),
        )

        # 하트비트 태스크 시작 (첫 연결시)
        if len(self.connections) == 1:
            await self._start_background_tasks()

        return connection.client_id

    async def disconnect(self, client_id: str):
        """WebSocket 연결 해제"""
        async with self._lock:
            if client_id in self.connections:
                connection = self.connections[client_id]
                connection.is_active = False

                # 구독 정리
                await self._cleanup_subscriptions(client_id)

                # 연결 제거
                del self.connections[client_id]

                logger.info(
                    "websocket_disconnected",
                    client_id=client_id,
                    total_connections=len(self.connections),
                    connection_stats=connection.get_stats(),
                )

        # 모든 연결이 끊어지면 백그라운드 태스크 정리
        if len(self.connections) == 0:
            await self._stop_background_tasks()

    async def subscribe(
        self,
        client_id: str,
        subscription_type: SubscriptionType,
        symbols: List[str] = None,
    ) -> bool:
        """구독 등록"""
        async with self._lock:
            if client_id not in self.connections:
                return False

            connection = self.connections[client_id]
            connection.subscription_types.add(subscription_type)

            # 심볼별 구독 등록
            if symbols:
                for symbol in symbols:
                    connection.subscriptions.add(symbol)

                    if symbol not in self.symbol_subscribers:
                        self.symbol_subscribers[symbol] = set()
                    self.symbol_subscribers[symbol].add(client_id)

            # 타입별 구독자 등록
            self.type_subscribers[subscription_type].add(client_id)

            logger.info(
                "websocket_subscribed",
                client_id=client_id,
                subscription_type=subscription_type.value,
                symbols=symbols or [],
            )

            return True

    async def unsubscribe(
        self,
        client_id: str,
        subscription_type: SubscriptionType = None,
        symbols: List[str] = None,
    ) -> bool:
        """구독 해제"""
        async with self._lock:
            if client_id not in self.connections:
                return False

            connection = self.connections[client_id]

            if subscription_type:
                connection.subscription_types.discard(subscription_type)
                self.type_subscribers[subscription_type].discard(client_id)

            if symbols:
                for symbol in symbols:
                    connection.subscriptions.discard(symbol)
                    if symbol in self.symbol_subscribers:
                        self.symbol_subscribers[symbol].discard(client_id)

                        # 구독자가 없으면 심볼 제거
                        if not self.symbol_subscribers[symbol]:
                            del self.symbol_subscribers[symbol]

            logger.info(
                "websocket_unsubscribed",
                client_id=client_id,
                subscription_type=(
                    subscription_type.value if subscription_type else None
                ),
                symbols=symbols or [],
            )

            return True

    async def broadcast_to_symbol_subscribers(
        self, symbol: str, message: Dict[str, Any], message_type: MessageType
    ):
        """특정 심볼 구독자들에게 브로드캐스트"""
        try:
            if symbol not in self.symbol_subscribers:
                return

            subscriber_ids = self.symbol_subscribers[symbol].copy()
            await self._send_to_clients(subscriber_ids, message, message_type, symbol)
        except Exception as e:
            logger.error("symbol_broadcast_failed", symbol=symbol, error=str(e))

    async def broadcast_to_type_subscribers(
        self,
        subscription_type: SubscriptionType,
        message: Dict[str, Any],
        message_type: MessageType,
    ):
        """특정 타입 구독자들에게 브로드캐스트"""
        try:
            if subscription_type not in self.type_subscribers:
                return

            subscriber_ids = self.type_subscribers[subscription_type].copy()
            await self._send_to_clients(subscriber_ids, message, message_type)
        except Exception as e:
            logger.error(
                "type_broadcast_failed",
                subscription_type=subscription_type.value,
                error=str(e),
            )

    async def broadcast_to_all(
        self, message: Dict[str, Any], message_type: MessageType
    ):
        """모든 연결된 클라이언트에게 브로드캐스트"""
        client_ids = list(self.connections.keys())
        await self._send_to_clients(client_ids, message, message_type)

    async def send_to_client(self, client_id: str, message: Dict[str, Any]) -> bool:
        """특정 클라이언트에게 메시지 전송"""
        if client_id not in self.connections:
            return False

        connection = self.connections[client_id]
        success = await connection.send_message(message)

        if success:
            self.total_messages_sent += 1
        else:
            self.total_errors += 1
            # 연결이 끊어진 경우 정리
            await self.disconnect(client_id)

        return success

    async def _send_to_clients(
        self,
        client_ids: List[str],
        message: Dict[str, Any],
        message_type: MessageType,
        symbol: str = None,
    ):
        """여러 클라이언트에게 메시지 전송"""
        if not client_ids:
            return

        # 메시지에 타입과 타임스탬프 추가
        enhanced_message = {
            **message,
            "type": message_type.value,
            "timestamp": datetime.now().isoformat(),
            "symbol": symbol,
        }

        # 병렬로 메시지 전송
        tasks = []
        for client_id in client_ids:
            if client_id in self.connections:
                connection = self.connections[client_id]

                # 구독 확인
                if connection.is_subscribed_to(symbol, message_type):
                    tasks.append(connection.send_message(enhanced_message))

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)

            success_count = sum(1 for r in results if r is True)
            error_count = len(results) - success_count

            self.total_messages_sent += success_count
            self.total_errors += error_count

            logger.debug(
                "broadcast_completed",
                message_type=message_type.value,
                symbol=symbol,
                target_clients=len(client_ids),
                success_count=success_count,
                error_count=error_count,
            )

    async def _cleanup_subscriptions(self, client_id: str):
        """클라이언트의 모든 구독 정리"""
        if client_id not in self.connections:
            return

        connection = self.connections[client_id]

        # 심볼별 구독 정리
        for symbol in connection.subscriptions:
            if symbol in self.symbol_subscribers:
                self.symbol_subscribers[symbol].discard(client_id)
                if not self.symbol_subscribers[symbol]:
                    del self.symbol_subscribers[symbol]

        # 타입별 구독 정리
        for sub_type in connection.subscription_types:
            self.type_subscribers[sub_type].discard(client_id)

    async def _start_background_tasks(self):
        """백그라운드 태스크 시작"""
        if not self.heartbeat_task:
            self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())

        if not self.cleanup_task:
            self.cleanup_task = asyncio.create_task(self._cleanup_loop())

        logger.info("websocket_background_tasks_started")

    async def _stop_background_tasks(self):
        """백그라운드 태스크 정리"""
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass
            self.heartbeat_task = None

        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
            self.cleanup_task = None

        logger.info("websocket_background_tasks_stopped")

    async def _heartbeat_loop(self):
        """하트비트 루프"""
        while True:
            try:
                await asyncio.sleep(self.heartbeat_interval)

                heartbeat_message = {
                    "type": MessageType.HEARTBEAT.value,
                    "timestamp": datetime.now().isoformat(),
                    "server_time": time.time(),
                }

                await self.broadcast_to_all(heartbeat_message, MessageType.HEARTBEAT)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("heartbeat_loop_error", error=str(e))
                await asyncio.sleep(5)

    async def _cleanup_loop(self):
        """연결 정리 루프"""
        while True:
            try:
                await asyncio.sleep(60)  # 1분마다 실행

                current_time = time.time()
                disconnected_clients = []

                async with self._lock:
                    for client_id, connection in self.connections.items():
                        # 하트비트 타임아웃 확인 (2분)
                        if current_time - connection.last_heartbeat > 120:
                            disconnected_clients.append(client_id)
                            logger.warning(
                                "websocket_heartbeat_timeout", client_id=client_id
                            )

                # 타임아웃된 연결들 정리
                for client_id in disconnected_clients:
                    await self.disconnect(client_id)

                if disconnected_clients:
                    logger.info(
                        "websocket_cleanup_completed",
                        cleaned_connections=len(disconnected_clients),
                    )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("cleanup_loop_error", error=str(e))
                await asyncio.sleep(30)

    @memory_monitor(threshold_mb=100.0)
    def get_stats(self) -> Dict[str, Any]:
        """WebSocket 관리자 통계"""
        return {
            "timestamp": datetime.now().isoformat(),
            "active_connections": len(self.connections),
            "total_connections": self.total_connections,
            "total_messages_sent": self.total_messages_sent,
            "total_errors": self.total_errors,
            "subscribed_symbols": len(self.symbol_subscribers),
            "subscription_stats": {
                sub_type.value: len(subscribers)
                for sub_type, subscribers in self.type_subscribers.items()
            },
            "background_tasks_active": {
                "heartbeat": self.heartbeat_task is not None
                and not self.heartbeat_task.done(),
                "cleanup": self.cleanup_task is not None
                and not self.cleanup_task.done(),
            },
        }

    def get_client_stats(self, client_id: str = None) -> Dict[str, Any]:
        """클라이언트별 통계"""
        if client_id:
            if client_id in self.connections:
                return self.connections[client_id].get_stats()
            return {"error": "Client not found"}

        return {
            "clients": [
                connection.get_stats() for connection in self.connections.values()
            ]
        }


# 전역 WebSocket 매니저
websocket_manager = WebSocketManager()
