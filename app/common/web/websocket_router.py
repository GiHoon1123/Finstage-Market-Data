"""
WebSocket API 라우터

실시간 데이터 스트리밍을 위한 WebSocket 엔드포인트들을 제공합니다.
가격 스트리밍, 기술적 분석 결과, 알림 등을 실시간으로 전송합니다.
"""

import asyncio
import json
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException
from fastapi.responses import HTMLResponse

from app.common.utils.websocket_manager import (
    websocket_manager,
    MessageType,
    SubscriptionType,
)
from app.market_price.service.realtime_price_streamer import realtime_price_streamer
from app.common.utils.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/ws", tags=["WebSocket"])


@router.websocket("/realtime")
async def websocket_realtime_endpoint(websocket: WebSocket):
    """
    실시간 데이터 스트리밍 WebSocket 엔드포인트

    클라이언트는 다음과 같은 메시지를 보낼 수 있습니다:
    - {"action": "subscribe", "type": "prices", "symbols": ["AAPL", "GOOGL"]}
    - {"action": "subscribe", "type": "alerts"}
    - {"action": "unsubscribe", "type": "prices", "symbols": ["AAPL"]}
    - {"action": "heartbeat"}
    """
    await websocket.accept()

    # 클라이언트 연결 등록
    client_id = await websocket_manager.connect(websocket)

    try:
        # 환영 메시지 전송
        welcome_message = {
            "type": MessageType.SYSTEM_STATUS.value,
            "message": "WebSocket 연결이 성공했습니다",
            "client_id": client_id,
            "available_actions": [
                "subscribe",
                "unsubscribe",
                "heartbeat",
                "get_status",
            ],
            "subscription_types": ["prices", "technical_analysis", "alerts", "all"],
        }
        await websocket.send_text(json.dumps(welcome_message))

        # 메시지 처리 루프
        while True:
            try:
                # 클라이언트로부터 메시지 수신
                data = await websocket.receive_text()
                message = json.loads(data)

                # 메시지 처리
                response = await _handle_websocket_message(client_id, message)

                if response:
                    await websocket.send_text(json.dumps(response))

            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                error_response = {
                    "type": MessageType.ERROR.value,
                    "message": "잘못된 JSON 형식입니다",
                    "timestamp": asyncio.get_event_loop().time(),
                }
                await websocket.send_text(json.dumps(error_response))
            except Exception as e:
                logger.error(
                    "websocket_message_handling_error",
                    client_id=client_id,
                    error=str(e),
                )
                error_response = {
                    "type": MessageType.ERROR.value,
                    "message": f"메시지 처리 중 오류 발생: {str(e)}",
                    "timestamp": asyncio.get_event_loop().time(),
                }
                await websocket.send_text(json.dumps(error_response))

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error("websocket_connection_error", client_id=client_id, error=str(e))
    finally:
        # 연결 해제
        await websocket_manager.disconnect(client_id)


async def _handle_websocket_message(
    client_id: str, message: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """WebSocket 메시지 처리"""
    action = message.get("action")

    if not action:
        return {"type": MessageType.ERROR.value, "message": "action 필드가 필요합니다"}

    try:
        if action == "subscribe":
            return await _handle_subscribe(client_id, message)

        elif action == "unsubscribe":
            return await _handle_unsubscribe(client_id, message)

        elif action == "heartbeat":
            return await _handle_heartbeat(client_id)

        elif action == "get_status":
            return await _handle_get_status(client_id)

        elif action == "get_current_prices":
            return await _handle_get_current_prices(message)

        elif action == "get_price_history":
            return await _handle_get_price_history(message)

        else:
            return {
                "type": MessageType.ERROR.value,
                "message": f"알 수 없는 액션: {action}",
            }

    except Exception as e:
        logger.error(
            "websocket_action_handling_error",
            client_id=client_id,
            action=action,
            error=str(e),
        )
        return {
            "type": MessageType.ERROR.value,
            "message": f"액션 처리 중 오류: {str(e)}",
        }


async def _handle_subscribe(client_id: str, message: Dict[str, Any]) -> Dict[str, Any]:
    """구독 처리"""
    subscription_type_str = message.get("type")
    symbols = message.get("symbols", [])

    if not subscription_type_str:
        return {
            "type": MessageType.ERROR.value,
            "message": "구독 타입이 필요합니다 (prices, technical_analysis, alerts, all)",
        }

    try:
        subscription_type = SubscriptionType(subscription_type_str)
    except ValueError:
        return {
            "type": MessageType.ERROR.value,
            "message": f"잘못된 구독 타입: {subscription_type_str}",
        }

    # 구독 등록
    success = await websocket_manager.subscribe(client_id, subscription_type, symbols)

    if success:
        # 실시간 스트리밍이 시작되지 않았다면 시작
        if not realtime_price_streamer.is_streaming and subscription_type in [
            SubscriptionType.PRICES,
            SubscriptionType.ALL,
        ]:
            try:
                await realtime_price_streamer.start_streaming()
            except Exception as e:
                logger.error("failed_to_start_streaming_on_subscription", error=str(e))

        return {
            "type": MessageType.SUBSCRIPTION.value,
            "action": "subscribed",
            "subscription_type": subscription_type_str,
            "symbols": symbols,
            "message": f"{subscription_type_str} 구독이 완료되었습니다",
        }
    else:
        return {"type": MessageType.ERROR.value, "message": "구독 등록에 실패했습니다"}


async def _handle_unsubscribe(
    client_id: str, message: Dict[str, Any]
) -> Dict[str, Any]:
    """구독 해제 처리"""
    subscription_type_str = message.get("type")
    symbols = message.get("symbols", [])

    subscription_type = None
    if subscription_type_str:
        try:
            subscription_type = SubscriptionType(subscription_type_str)
        except ValueError:
            return {
                "type": MessageType.ERROR.value,
                "message": f"잘못된 구독 타입: {subscription_type_str}",
            }

    # 구독 해제
    success = await websocket_manager.unsubscribe(client_id, subscription_type, symbols)

    if success:
        return {
            "type": MessageType.SUBSCRIPTION.value,
            "action": "unsubscribed",
            "subscription_type": subscription_type_str,
            "symbols": symbols,
            "message": "구독 해제가 완료되었습니다",
        }
    else:
        return {"type": MessageType.ERROR.value, "message": "구독 해제에 실패했습니다"}


async def _handle_heartbeat(client_id: str) -> Dict[str, Any]:
    """하트비트 처리"""
    # 하트비트 시간 업데이트
    if client_id in websocket_manager.connections:
        websocket_manager.connections[client_id].update_heartbeat()

    return {
        "type": MessageType.HEARTBEAT.value,
        "message": "pong",
        "server_time": asyncio.get_event_loop().time(),
    }


async def _handle_get_status(client_id: str) -> Dict[str, Any]:
    """상태 조회 처리"""
    client_stats = websocket_manager.get_client_stats(client_id)
    manager_stats = websocket_manager.get_stats()
    streamer_stats = realtime_price_streamer.get_stats()

    return {
        "type": MessageType.SYSTEM_STATUS.value,
        "client_stats": client_stats,
        "websocket_manager_stats": manager_stats,
        "price_streamer_stats": streamer_stats,
    }


async def _handle_get_current_prices(message: Dict[str, Any]) -> Dict[str, Any]:
    """현재 가격 조회 처리"""
    symbols = message.get("symbols", [])

    if symbols:
        # 특정 심볼들의 가격만 조회
        all_prices = realtime_price_streamer.get_current_prices()
        prices = {symbol: all_prices.get(symbol) for symbol in symbols}
    else:
        # 모든 가격 조회
        prices = realtime_price_streamer.get_current_prices()

    return {
        "type": MessageType.PRICE_UPDATE.value,
        "action": "current_prices",
        "prices": prices,
        "timestamp": asyncio.get_event_loop().time(),
    }


async def _handle_get_price_history(message: Dict[str, Any]) -> Dict[str, Any]:
    """가격 히스토리 조회 처리"""
    symbol = message.get("symbol")
    limit = message.get("limit", 50)

    if not symbol:
        return {"type": MessageType.ERROR.value, "message": "symbol 필드가 필요합니다"}

    history = realtime_price_streamer.get_price_history(symbol, limit)

    return {
        "type": MessageType.PRICE_UPDATE.value,
        "action": "price_history",
        "symbol": symbol,
        "history": history,
        "count": len(history),
    }


# REST API 엔드포인트들
@router.get("/status", summary="WebSocket 시스템 상태")
async def get_websocket_status():
    """WebSocket 시스템의 전체 상태를 조회합니다."""
    try:
        manager_stats = websocket_manager.get_stats()
        streamer_stats = realtime_price_streamer.get_stats()

        return {
            "timestamp": asyncio.get_event_loop().time(),
            "websocket_manager": manager_stats,
            "price_streamer": streamer_stats,
            "system_health": (
                "healthy" if manager_stats["active_connections"] >= 0 else "unhealthy"
            ),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"상태 조회 실패: {str(e)}")


@router.get("/clients", summary="연결된 클라이언트 목록")
async def get_connected_clients():
    """현재 연결된 모든 클라이언트의 정보를 조회합니다."""
    try:
        return websocket_manager.get_client_stats()
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"클라이언트 정보 조회 실패: {str(e)}"
        )


@router.post("/broadcast", summary="브로드캐스트 메시지 전송")
async def broadcast_message(
    message: str,
    message_type: str = Query("system_status", description="메시지 타입"),
    target_type: str = Query("all", description="대상 타입 (all, prices, alerts)"),
):
    """모든 연결된 클라이언트에게 메시지를 브로드캐스트합니다."""
    try:
        # 메시지 타입 검증
        try:
            msg_type = MessageType(message_type)
        except ValueError:
            raise HTTPException(
                status_code=400, detail=f"잘못된 메시지 타입: {message_type}"
            )

        broadcast_message_data = {
            "message": message,
            "source": "admin",
            "broadcast_type": target_type,
        }

        if target_type == "all":
            await websocket_manager.broadcast_to_all(broadcast_message_data, msg_type)
        else:
            try:
                sub_type = SubscriptionType(target_type)
                await websocket_manager.broadcast_to_type_subscribers(
                    sub_type, broadcast_message_data, msg_type
                )
            except ValueError:
                raise HTTPException(
                    status_code=400, detail=f"잘못된 대상 타입: {target_type}"
                )

        return {
            "success": True,
            "message": "브로드캐스트 완료",
            "target_type": target_type,
            "active_connections": len(websocket_manager.connections),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"브로드캐스트 실패: {str(e)}")


@router.post("/streaming/start", summary="실시간 스트리밍 시작")
async def start_price_streaming(
    symbols: Optional[List[str]] = Query(None, description="모니터링할 심볼들")
):
    """실시간 가격 스트리밍을 시작합니다."""
    try:
        if realtime_price_streamer.is_streaming:
            return {
                "success": False,
                "message": "스트리밍이 이미 활성화되어 있습니다",
                "stats": realtime_price_streamer.get_stats(),
            }

        await realtime_price_streamer.start_streaming(symbols)

        return {
            "success": True,
            "message": "실시간 스트리밍이 시작되었습니다",
            "monitored_symbols": len(realtime_price_streamer.monitored_symbols),
            "stats": realtime_price_streamer.get_stats(),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"스트리밍 시작 실패: {str(e)}")


@router.post("/streaming/stop", summary="실시간 스트리밍 중지")
async def stop_price_streaming():
    """실시간 가격 스트리밍을 중지합니다."""
    try:
        if not realtime_price_streamer.is_streaming:
            return {"success": False, "message": "스트리밍이 활성화되어 있지 않습니다"}

        await realtime_price_streamer.stop_streaming()

        return {"success": True, "message": "실시간 스트리밍이 중지되었습니다"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"스트리밍 중지 실패: {str(e)}")


@router.get("/demo", response_class=HTMLResponse, summary="WebSocket 데모 페이지")
async def websocket_demo():
    """WebSocket 연결을 테스트할 수 있는 간단한 HTML 페이지를 제공합니다."""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>WebSocket 실시간 데이터 데모</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .container { max-width: 1200px; margin: 0 auto; }
            .section { margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }
            .messages { height: 300px; overflow-y: scroll; background: #f5f5f5; padding: 10px; }
            .message { margin: 5px 0; padding: 5px; background: white; border-radius: 3px; }
            .controls { margin: 10px 0; }
            button { margin: 5px; padding: 8px 15px; }
            input, select { margin: 5px; padding: 5px; }
            .status { padding: 10px; margin: 10px 0; border-radius: 5px; }
            .connected { background: #d4edda; color: #155724; }
            .disconnected { background: #f8d7da; color: #721c24; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 WebSocket 실시간 데이터 스트리밍 데모</h1>
            
            <div class="section">
                <h3>연결 상태</h3>
                <div id="status" class="status disconnected">연결되지 않음</div>
                <button onclick="connect()">연결</button>
                <button onclick="disconnect()">연결 해제</button>
            </div>
            
            <div class="section">
                <h3>구독 관리</h3>
                <select id="subscriptionType">
                    <option value="prices">가격 데이터</option>
                    <option value="alerts">알림</option>
                    <option value="all">전체</option>
                </select>
                <input type="text" id="symbols" placeholder="심볼들 (쉼표로 구분, 예: AAPL,GOOGL)" />
                <button onclick="subscribe()">구독</button>
                <button onclick="unsubscribe()">구독 해제</button>
            </div>
            
            <div class="section">
                <h3>기능 테스트</h3>
                <button onclick="sendHeartbeat()">하트비트</button>
                <button onclick="getStatus()">상태 조회</button>
                <button onclick="getCurrentPrices()">현재 가격</button>
                <input type="text" id="historySymbol" placeholder="히스토리 조회할 심볼" />
                <button onclick="getPriceHistory()">가격 히스토리</button>
            </div>
            
            <div class="section">
                <h3>실시간 메시지</h3>
                <button onclick="clearMessages()">메시지 지우기</button>
                <div id="messages" class="messages"></div>
            </div>
        </div>

        <script>
            let ws = null;
            
            function connect() {
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                const wsUrl = `${protocol}//${window.location.host}/ws/realtime`;
                
                ws = new WebSocket(wsUrl);
                
                ws.onopen = function(event) {
                    updateStatus('연결됨', true);
                    addMessage('시스템', '웹소켓 연결 성공');
                };
                
                ws.onmessage = function(event) {
                    const data = JSON.parse(event.data);
                    addMessage(data.type || '메시지', JSON.stringify(data, null, 2));
                };
                
                ws.onclose = function(event) {
                    updateStatus('연결 해제됨', false);
                    addMessage('시스템', '웹소켓 연결 종료');
                };
                
                ws.onerror = function(error) {
                    updateStatus('연결 오류', false);
                    addMessage('오류', '웹소켓 연결 오류: ' + error);
                };
            }
            
            function disconnect() {
                if (ws) {
                    ws.close();
                }
            }
            
            function subscribe() {
                if (!ws) return;
                
                const type = document.getElementById('subscriptionType').value;
                const symbolsInput = document.getElementById('symbols').value;
                const symbols = symbolsInput ? symbolsInput.split(',').map(s => s.trim()) : [];
                
                const message = {
                    action: 'subscribe',
                    type: type,
                    symbols: symbols
                };
                
                ws.send(JSON.stringify(message));
            }
            
            function unsubscribe() {
                if (!ws) return;
                
                const type = document.getElementById('subscriptionType').value;
                const symbolsInput = document.getElementById('symbols').value;
                const symbols = symbolsInput ? symbolsInput.split(',').map(s => s.trim()) : [];
                
                const message = {
                    action: 'unsubscribe',
                    type: type,
                    symbols: symbols
                };
                
                ws.send(JSON.stringify(message));
            }
            
            function sendHeartbeat() {
                if (!ws) return;
                ws.send(JSON.stringify({action: 'heartbeat'}));
            }
            
            function getStatus() {
                if (!ws) return;
                ws.send(JSON.stringify({action: 'get_status'}));
            }
            
            function getCurrentPrices() {
                if (!ws) return;
                const symbolsInput = document.getElementById('symbols').value;
                const symbols = symbolsInput ? symbolsInput.split(',').map(s => s.trim()) : [];
                
                ws.send(JSON.stringify({
                    action: 'get_current_prices',
                    symbols: symbols
                }));
            }
            
            function getPriceHistory() {
                if (!ws) return;
                const symbol = document.getElementById('historySymbol').value;
                if (!symbol) return;
                
                ws.send(JSON.stringify({
                    action: 'get_price_history',
                    symbol: symbol,
                    limit: 20
                }));
            }
            
            function updateStatus(message, connected) {
                const statusEl = document.getElementById('status');
                statusEl.textContent = message;
                statusEl.className = 'status ' + (connected ? 'connected' : 'disconnected');
            }
            
            function addMessage(type, content) {
                const messagesEl = document.getElementById('messages');
                const messageEl = document.createElement('div');
                messageEl.className = 'message';
                messageEl.innerHTML = `<strong>[${new Date().toLocaleTimeString()}] ${type}:</strong><br><pre>${content}</pre>`;
                messagesEl.appendChild(messageEl);
                messagesEl.scrollTop = messagesEl.scrollHeight;
            }
            
            function clearMessages() {
                document.getElementById('messages').innerHTML = '';
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)
