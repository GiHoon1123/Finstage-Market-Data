#!/usr/bin/env python3
"""
성능 모니터링 대시보드

실시간 성능 지표를 웹 인터페이스로 제공합니다.
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from deployment.post_deployment_performance_monitor import (
    PostDeploymentMonitor,
    PerformanceMetrics,
)
from deployment.performance_monitoring_config import get_config_manager
from app.common.utils.logging_config import get_logger

logger = get_logger(__name__)

# FastAPI 앱 초기화
app = FastAPI(title="성능 모니터링 대시보드", version="1.0.0")

# 전역 모니터 인스턴스
monitor: PostDeploymentMonitor = None
connected_clients: List[WebSocket] = []


class DashboardManager:
    """대시보드 관리자"""

    def __init__(self):
        self.config_manager = get_config_manager()
        self.monitoring_config = self.config_manager.get_monitoring_config()

    async def start_monitoring(self):
        """모니터링 시작"""
        global monitor

        if monitor is None:
            monitor = PostDeploymentMonitor(
                monitoring_interval=self.monitoring_config.monitoring_interval_seconds
            )

            # 설정 적용
            monitor.auto_tuning_enabled = self.monitoring_config.auto_tuning_enabled
            monitor.thresholds.memory_usage_percent = (
                self.monitoring_config.memory_usage_threshold
            )
            monitor.thresholds.cpu_usage_percent = (
                self.monitoring_config.cpu_usage_threshold
            )
            monitor.thresholds.response_time_ms = (
                self.monitoring_config.response_time_threshold_ms
            )

        # 백그라운드에서 모니터링 시작
        asyncio.create_task(self._monitoring_loop())

    async def _monitoring_loop(self):
        """모니터링 루프"""
        try:
            while True:
                if monitor and not monitor.is_monitoring:
                    # 한 번의 메트릭 수집 실행
                    await monitor._collect_and_analyze_metrics()

                    # 연결된 클라이언트들에게 실시간 데이터 전송
                    if connected_clients and monitor.performance_history:
                        latest_metrics = monitor.performance_history[-1]
                        await self._broadcast_metrics(latest_metrics)

                await asyncio.sleep(self.monitoring_config.monitoring_interval_seconds)

        except Exception as e:
            logger.error("monitoring_loop_failed", error=str(e))

    async def _broadcast_metrics(self, metrics: PerformanceMetrics):
        """연결된 클라이언트들에게 메트릭 브로드캐스트"""
        if not connected_clients:
            return

        try:
            # 메트릭을 JSON으로 변환
            metrics_data = {
                "timestamp": metrics.timestamp.isoformat(),
                "memory_usage_percent": metrics.memory_usage_percent,
                "cpu_usage_percent": metrics.cpu_usage_percent,
                "avg_response_time_ms": metrics.avg_response_time_ms,
                "p95_response_time_ms": metrics.p95_response_time_ms,
                "error_rate_percent": metrics.error_rate_percent,
                "cache_hit_rate_percent": metrics.cache_hit_rate_percent,
                "active_connections": metrics.active_connections,
                "requests_per_second": metrics.requests_per_second,
                "status": metrics.status.value,
            }

            # 연결이 끊어진 클라이언트 제거
            disconnected_clients = []

            for client in connected_clients:
                try:
                    await client.send_json(
                        {"type": "metrics_update", "data": metrics_data}
                    )
                except Exception:
                    disconnected_clients.append(client)

            # 연결이 끊어진 클라이언트 제거
            for client in disconnected_clients:
                connected_clients.remove(client)

        except Exception as e:
            logger.error("metrics_broadcast_failed", error=str(e))


# 대시보드 관리자 인스턴스
dashboard_manager = DashboardManager()


@app.on_event("startup")
async def startup_event():
    """앱 시작 시 실행"""
    await dashboard_manager.start_monitoring()


@app.get("/", response_class=HTMLResponse)
async def dashboard_home():
    """대시보드 홈페이지"""
    html_content = """
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>성능 모니터링 대시보드</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                padding: 20px;
                background-color: #f5f5f5;
            }
            .header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px;
                border-radius: 10px;
                margin-bottom: 20px;
                text-align: center;
            }
            .metrics-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 20px;
                margin-bottom: 20px;
            }
            .metric-card {
                background: white;
                border-radius: 10px;
                padding: 20px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                transition: transform 0.2s;
            }
            .metric-card:hover {
                transform: translateY(-2px);
            }
            .metric-title {
                font-size: 14px;
                color: #666;
                margin-bottom: 10px;
                text-transform: uppercase;
                letter-spacing: 1px;
            }
            .metric-value {
                font-size: 32px;
                font-weight: bold;
                margin-bottom: 5px;
            }
            .metric-unit {
                font-size: 14px;
                color: #999;
            }
            .status-indicator {
                display: inline-block;
                width: 12px;
                height: 12px;
                border-radius: 50%;
                margin-right: 8px;
            }
            .status-excellent { background-color: #4CAF50; }
            .status-good { background-color: #2196F3; }
            .status-fair { background-color: #FF9800; }
            .status-poor { background-color: #FF5722; }
            .status-critical { background-color: #F44336; }
            .chart-container {
                background: white;
                border-radius: 10px;
                padding: 20px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                margin-bottom: 20px;
            }
            .connection-status {
                position: fixed;
                top: 20px;
                right: 20px;
                padding: 10px 15px;
                border-radius: 5px;
                color: white;
                font-weight: bold;
            }
            .connected { background-color: #4CAF50; }
            .disconnected { background-color: #F44336; }
            .last-updated {
                text-align: center;
                color: #666;
                font-size: 12px;
                margin-top: 10px;
            }
        </style>
    </head>
    <body>
        <div class="connection-status" id="connectionStatus">연결 중...</div>
        
        <div class="header">
            <h1>🚀 성능 모니터링 대시보드</h1>
            <p>실시간 시스템 성능 지표</p>
        </div>
        
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-title">시스템 상태</div>
                <div class="metric-value" id="systemStatus">
                    <span class="status-indicator" id="statusIndicator"></span>
                    <span id="statusText">연결 중...</span>
                </div>
            </div>
            
            <div class="metric-card">
                <div class="metric-title">메모리 사용률</div>
                <div class="metric-value" id="memoryUsage">--</div>
                <div class="metric-unit">%</div>
            </div>
            
            <div class="metric-card">
                <div class="metric-title">CPU 사용률</div>
                <div class="metric-value" id="cpuUsage">--</div>
                <div class="metric-unit">%</div>
            </div>
            
            <div class="metric-card">
                <div class="metric-title">평균 응답 시간</div>
                <div class="metric-value" id="responseTime">--</div>
                <div class="metric-unit">ms</div>
            </div>
            
            <div class="metric-card">
                <div class="metric-title">캐시 히트율</div>
                <div class="metric-value" id="cacheHitRate">--</div>
                <div class="metric-unit">%</div>
            </div>
            
            <div class="metric-card">
                <div class="metric-title">초당 요청 수</div>
                <div class="metric-value" id="requestsPerSecond">--</div>
                <div class="metric-unit">RPS</div>
            </div>
        </div>
        
        <div class="chart-container">
            <h3>응답 시간 추이</h3>
            <canvas id="responseTimeChart" width="400" height="200"></canvas>
        </div>
        
        <div class="chart-container">
            <h3>시스템 리소스 사용률</h3>
            <canvas id="resourceChart" width="400" height="200"></canvas>
        </div>
        
        <div class="last-updated" id="lastUpdated">마지막 업데이트: --</div>
        
        <script>
            // WebSocket 연결
            const ws = new WebSocket(`ws://${window.location.host}/ws`);
            
            // 차트 초기화
            const responseTimeChart = new Chart(document.getElementById('responseTimeChart'), {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: '평균 응답 시간 (ms)',
                        data: [],
                        borderColor: 'rgb(75, 192, 192)',
                        backgroundColor: 'rgba(75, 192, 192, 0.2)',
                        tension: 0.1
                    }, {
                        label: 'P95 응답 시간 (ms)',
                        data: [],
                        borderColor: 'rgb(255, 99, 132)',
                        backgroundColor: 'rgba(255, 99, 132, 0.2)',
                        tension: 0.1
                    }]
                },
                options: {
                    responsive: true,
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    }
                }
            });
            
            const resourceChart = new Chart(document.getElementById('resourceChart'), {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: '메모리 사용률 (%)',
                        data: [],
                        borderColor: 'rgb(54, 162, 235)',
                        backgroundColor: 'rgba(54, 162, 235, 0.2)',
                        tension: 0.1
                    }, {
                        label: 'CPU 사용률 (%)',
                        data: [],
                        borderColor: 'rgb(255, 206, 86)',
                        backgroundColor: 'rgba(255, 206, 86, 0.2)',
                        tension: 0.1
                    }]
                },
                options: {
                    responsive: true,
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 100
                        }
                    }
                }
            });
            
            // WebSocket 이벤트 핸들러
            ws.onopen = function(event) {
                document.getElementById('connectionStatus').textContent = '연결됨';
                document.getElementById('connectionStatus').className = 'connection-status connected';
            };
            
            ws.onclose = function(event) {
                document.getElementById('connectionStatus').textContent = '연결 끊김';
                document.getElementById('connectionStatus').className = 'connection-status disconnected';
            };
            
            ws.onmessage = function(event) {
                const message = JSON.parse(event.data);
                
                if (message.type === 'metrics_update') {
                    updateMetrics(message.data);
                }
            };
            
            function updateMetrics(data) {
                // 메트릭 값 업데이트
                document.getElementById('memoryUsage').textContent = data.memory_usage_percent.toFixed(1);
                document.getElementById('cpuUsage').textContent = data.cpu_usage_percent.toFixed(1);
                document.getElementById('responseTime').textContent = data.avg_response_time_ms.toFixed(1);
                document.getElementById('cacheHitRate').textContent = data.cache_hit_rate_percent.toFixed(1);
                document.getElementById('requestsPerSecond').textContent = data.requests_per_second.toFixed(1);
                
                // 상태 업데이트
                const statusText = document.getElementById('statusText');
                const statusIndicator = document.getElementById('statusIndicator');
                
                statusText.textContent = data.status.toUpperCase();
                statusIndicator.className = `status-indicator status-${data.status}`;
                
                // 차트 업데이트
                const timestamp = new Date(data.timestamp).toLocaleTimeString();
                
                // 응답 시간 차트
                responseTimeChart.data.labels.push(timestamp);
                responseTimeChart.data.datasets[0].data.push(data.avg_response_time_ms);
                responseTimeChart.data.datasets[1].data.push(data.p95_response_time_ms);
                
                // 최대 20개 데이터 포인트 유지
                if (responseTimeChart.data.labels.length > 20) {
                    responseTimeChart.data.labels.shift();
                    responseTimeChart.data.datasets[0].data.shift();
                    responseTimeChart.data.datasets[1].data.shift();
                }
                
                responseTimeChart.update('none');
                
                // 리소스 차트
                resourceChart.data.labels.push(timestamp);
                resourceChart.data.datasets[0].data.push(data.memory_usage_percent);
                resourceChart.data.datasets[1].data.push(data.cpu_usage_percent);
                
                if (resourceChart.data.labels.length > 20) {
                    resourceChart.data.labels.shift();
                    resourceChart.data.datasets[0].data.shift();
                    resourceChart.data.datasets[1].data.shift();
                }
                
                resourceChart.update('none');
                
                // 마지막 업데이트 시간
                document.getElementById('lastUpdated').textContent = 
                    `마지막 업데이트: ${new Date().toLocaleString()}`;
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 엔드포인트"""
    await websocket.accept()
    connected_clients.append(websocket)

    try:
        # 초기 데이터 전송
        if monitor and monitor.performance_history:
            latest_metrics = monitor.performance_history[-1]
            await dashboard_manager._broadcast_metrics(latest_metrics)

        # 연결 유지
        while True:
            await websocket.receive_text()

    except WebSocketDisconnect:
        if websocket in connected_clients:
            connected_clients.remove(websocket)


@app.get("/api/metrics/current")
async def get_current_metrics():
    """현재 메트릭 조회"""
    if not monitor or not monitor.performance_history:
        return {"error": "No metrics available"}

    latest_metrics = monitor.performance_history[-1]

    return {
        "timestamp": latest_metrics.timestamp.isoformat(),
        "memory_usage_percent": latest_metrics.memory_usage_percent,
        "cpu_usage_percent": latest_metrics.cpu_usage_percent,
        "avg_response_time_ms": latest_metrics.avg_response_time_ms,
        "p95_response_time_ms": latest_metrics.p95_response_time_ms,
        "error_rate_percent": latest_metrics.error_rate_percent,
        "cache_hit_rate_percent": latest_metrics.cache_hit_rate_percent,
        "active_connections": latest_metrics.active_connections,
        "requests_per_second": latest_metrics.requests_per_second,
        "status": latest_metrics.status.value,
    }


@app.get("/api/metrics/history")
async def get_metrics_history(hours: int = 1):
    """메트릭 히스토리 조회"""
    if not monitor:
        return {"error": "Monitor not initialized"}

    return monitor.get_performance_summary(hours=hours)


@app.get("/api/health")
async def health_check():
    """헬스 체크"""
    return {
        "status": "healthy",
        "monitoring_active": monitor.is_monitoring if monitor else False,
        "connected_clients": len(connected_clients),
        "timestamp": datetime.now().isoformat(),
    }


def main():
    """메인 함수"""
    import argparse

    parser = argparse.ArgumentParser(description="성능 모니터링 대시보드")
    parser.add_argument("--host", default="0.0.0.0", help="호스트 주소")
    parser.add_argument("--port", type=int, default=8080, help="포트 번호")
    parser.add_argument("--reload", action="store_true", help="자동 리로드 활성화")

    args = parser.parse_args()

    print("🚀 성능 모니터링 대시보드 시작")
    print(f"📊 대시보드 URL: http://{args.host}:{args.port}")
    print("=" * 50)

    uvicorn.run(
        "deployment.performance_dashboard:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
