"""
고도화된 알림 시스템

시스템 상태, 에러, 성능 이슈 등을 다양한 채널로 알림을 전송합니다.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union
from enum import Enum
from dataclasses import dataclass, asdict
import aiohttp

from app.common.utils.logging_config import get_logger
from app.common.config.settings import get_settings
from app.common.monitoring.metrics import metrics_collector

logger = get_logger(__name__)
settings = get_settings()


class AlertLevel(Enum):
    """알림 레벨"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertChannel(Enum):
    """알림 채널"""

    TELEGRAM = "telegram"
    SLACK = "slack"
    EMAIL = "email"
    WEBHOOK = "webhook"


@dataclass
class Alert:
    """알림 데이터 구조"""

    title: str
    message: str
    level: AlertLevel
    component: str
    timestamp: datetime
    details: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        data["level"] = self.level.value
        return data


class AlertManager:
    """알림 관리자"""

    def __init__(self):
        self.alert_history = []
        self.rate_limits = {}  # 알림 속도 제한
        self.alert_rules = self._setup_alert_rules()

    def _setup_alert_rules(self) -> Dict[str, Dict]:
        """알림 규칙 설정"""
        return {
            "high_cpu_usage": {
                "threshold": 80,
                "duration_minutes": 5,
                "level": AlertLevel.WARNING,
                "channels": [AlertChannel.TELEGRAM],
            },
            "critical_cpu_usage": {
                "threshold": 95,
                "duration_minutes": 1,
                "level": AlertLevel.CRITICAL,
                "channels": [AlertChannel.TELEGRAM, AlertChannel.SLACK],
            },
            "high_memory_usage": {
                "threshold": 80,
                "duration_minutes": 5,
                "level": AlertLevel.WARNING,
                "channels": [AlertChannel.TELEGRAM],
            },
            "critical_memory_usage": {
                "threshold": 95,
                "duration_minutes": 1,
                "level": AlertLevel.CRITICAL,
                "channels": [AlertChannel.TELEGRAM, AlertChannel.SLACK],
            },
            "disk_space_low": {
                "threshold": 85,
                "duration_minutes": 10,
                "level": AlertLevel.WARNING,
                "channels": [AlertChannel.TELEGRAM],
            },
            "disk_space_critical": {
                "threshold": 95,
                "duration_minutes": 1,
                "level": AlertLevel.CRITICAL,
                "channels": [AlertChannel.TELEGRAM, AlertChannel.SLACK],
            },
            "database_connection_failed": {
                "level": AlertLevel.CRITICAL,
                "channels": [AlertChannel.TELEGRAM, AlertChannel.SLACK],
            },
            "external_api_failed": {
                "level": AlertLevel.ERROR,
                "channels": [AlertChannel.TELEGRAM],
            },
            "scheduler_stopped": {
                "level": AlertLevel.CRITICAL,
                "channels": [AlertChannel.TELEGRAM, AlertChannel.SLACK],
            },
            "high_error_rate": {
                "threshold": 10,  # 10% 에러율
                "duration_minutes": 5,
                "level": AlertLevel.ERROR,
                "channels": [AlertChannel.TELEGRAM],
            },
        }

    async def send_alert(
        self, alert: Alert, channels: Optional[List[AlertChannel]] = None
    ):
        """알림 전송"""
        try:
            # 속도 제한 확인
            if self._is_rate_limited(alert):
                logger.debug(
                    "alert_rate_limited", title=alert.title, component=alert.component
                )
                return

            # 전송할 채널 결정
            target_channels = channels or [AlertChannel.TELEGRAM]

            # 각 채널로 알림 전송
            tasks = []
            for channel in target_channels:
                if channel == AlertChannel.TELEGRAM:
                    tasks.append(self._send_telegram_alert(alert))
                elif channel == AlertChannel.SLACK:
                    tasks.append(self._send_slack_alert(alert))
                elif channel == AlertChannel.EMAIL:
                    tasks.append(self._send_email_alert(alert))
                elif channel == AlertChannel.WEBHOOK:
                    tasks.append(self._send_webhook_alert(alert))

            # 병렬 전송
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 결과 처리
            success_count = 0
            for i, result in enumerate(results):
                channel = target_channels[i]
                if isinstance(result, Exception):
                    logger.error(
                        "alert_send_failed", channel=channel.value, error=str(result)
                    )
                    metrics_collector.record_notification(channel.value, "error", 0)
                else:
                    success_count += 1
                    metrics_collector.record_notification(
                        channel.value, "success", result
                    )

            # 알림 히스토리에 추가
            self.alert_history.append(alert)
            self._update_rate_limit(alert)

            logger.info(
                "alert_sent",
                title=alert.title,
                level=alert.level.value,
                channels=len(target_channels),
                success_count=success_count,
            )

        except Exception as e:
            logger.error("alert_send_error", error=str(e))
            metrics_collector.record_error(type(e).__name__, "alert_manager")

    async def _send_telegram_alert(self, alert: Alert) -> float:
        """텔레그램 알림 전송"""
        start_time = asyncio.get_event_loop().time()

        try:
            # 알림 레벨에 따른 이모지
            level_emojis = {
                AlertLevel.INFO: "ℹ️",
                AlertLevel.WARNING: "⚠️",
                AlertLevel.ERROR: "❌",
                AlertLevel.CRITICAL: "🚨",
            }

            emoji = level_emojis.get(alert.level, "📢")

            # 메시지 구성
            message = f"{emoji} **{alert.title}**\n\n"
            message += f"**레벨:** {alert.level.value.upper()}\n"
            message += f"**컴포넌트:** {alert.component}\n"
            message += f"**시간:** {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            message += f"**메시지:**\n{alert.message}\n"

            if alert.details:
                message += f"\n**상세 정보:**\n"
                for key, value in alert.details.items():
                    message += f"• {key}: {value}\n"

            if alert.tags:
                message += f"\n**태그:** {', '.join(alert.tags)}"

            # 텔레그램 API 호출
            url = (
                f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
            )

            payload = {
                "chat_id": settings.telegram_chat_id,
                "text": message,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True,
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        duration = asyncio.get_event_loop().time() - start_time
                        logger.debug(
                            "telegram_alert_sent", title=alert.title, duration=duration
                        )
                        return duration
                    else:
                        error_text = await response.text()
                        raise Exception(
                            f"Telegram API error: {response.status} - {error_text}"
                        )

        except Exception as e:
            logger.error("telegram_alert_failed", title=alert.title, error=str(e))
            raise

    async def _send_slack_alert(self, alert: Alert) -> float:
        """Slack 알림 전송 (웹훅 사용)"""
        start_time = asyncio.get_event_loop().time()

        try:
            # Slack 웹훅 URL (환경변수에서 가져와야 함)
            webhook_url = (
                "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"  # 실제 URL로 교체
            )

            # 알림 레벨에 따른 색상
            level_colors = {
                AlertLevel.INFO: "#36a64f",  # 녹색
                AlertLevel.WARNING: "#ff9500",  # 주황색
                AlertLevel.ERROR: "#ff0000",  # 빨간색
                AlertLevel.CRITICAL: "#8b0000",  # 진한 빨간색
            }

            color = level_colors.get(alert.level, "#36a64f")

            # Slack 메시지 구성
            payload = {
                "username": "Finstage Monitor",
                "icon_emoji": ":warning:",
                "attachments": [
                    {
                        "color": color,
                        "title": alert.title,
                        "text": alert.message,
                        "fields": [
                            {
                                "title": "Level",
                                "value": alert.level.value.upper(),
                                "short": True,
                            },
                            {
                                "title": "Component",
                                "value": alert.component,
                                "short": True,
                            },
                            {
                                "title": "Timestamp",
                                "value": alert.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                                "short": True,
                            },
                        ],
                        "footer": "Finstage Market Data",
                        "ts": int(alert.timestamp.timestamp()),
                    }
                ],
            }

            # 상세 정보 추가
            if alert.details:
                detail_text = "\n".join(
                    [f"• {k}: {v}" for k, v in alert.details.items()]
                )
                payload["attachments"][0]["fields"].append(
                    {"title": "Details", "value": detail_text, "short": False}
                )

            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload) as response:
                    if response.status == 200:
                        duration = asyncio.get_event_loop().time() - start_time
                        logger.debug(
                            "slack_alert_sent", title=alert.title, duration=duration
                        )
                        return duration
                    else:
                        error_text = await response.text()
                        raise Exception(
                            f"Slack webhook error: {response.status} - {error_text}"
                        )

        except Exception as e:
            logger.error("slack_alert_failed", title=alert.title, error=str(e))
            raise

    async def _send_email_alert(self, alert: Alert) -> float:
        """이메일 알림 전송"""
        start_time = asyncio.get_event_loop().time()

        try:
            # 이메일 전송 로직 (SMTP 또는 이메일 서비스 API 사용)
            # 여기서는 시뮬레이션
            await asyncio.sleep(0.1)

            duration = asyncio.get_event_loop().time() - start_time
            logger.debug("email_alert_sent", title=alert.title, duration=duration)
            return duration

        except Exception as e:
            logger.error("email_alert_failed", title=alert.title, error=str(e))
            raise

    async def _send_webhook_alert(self, alert: Alert) -> float:
        """웹훅 알림 전송"""
        start_time = asyncio.get_event_loop().time()

        try:
            # 웹훅 URL (환경변수에서 가져와야 함)
            webhook_url = "https://your-webhook-endpoint.com/alerts"  # 실제 URL로 교체

            payload = alert.to_dict()

            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload) as response:
                    if response.status == 200:
                        duration = asyncio.get_event_loop().time() - start_time
                        logger.debug(
                            "webhook_alert_sent", title=alert.title, duration=duration
                        )
                        return duration
                    else:
                        error_text = await response.text()
                        raise Exception(
                            f"Webhook error: {response.status} - {error_text}"
                        )

        except Exception as e:
            logger.error("webhook_alert_failed", title=alert.title, error=str(e))
            raise

    def _is_rate_limited(self, alert: Alert) -> bool:
        """속도 제한 확인"""
        key = f"{alert.component}:{alert.title}"
        now = datetime.now()

        if key in self.rate_limits:
            last_sent, count = self.rate_limits[key]

            # 1시간 내에 같은 알림이 5번 이상 전송되었으면 제한
            if now - last_sent < timedelta(hours=1) and count >= 5:
                return True

        return False

    def _update_rate_limit(self, alert: Alert):
        """속도 제한 정보 업데이트"""
        key = f"{alert.component}:{alert.title}"
        now = datetime.now()

        if key in self.rate_limits:
            last_sent, count = self.rate_limits[key]

            # 1시간이 지났으면 카운트 리셋
            if now - last_sent >= timedelta(hours=1):
                self.rate_limits[key] = (now, 1)
            else:
                self.rate_limits[key] = (now, count + 1)
        else:
            self.rate_limits[key] = (now, 1)

    def get_alert_history(self, hours: int = 24) -> List[Alert]:
        """알림 히스토리 조회"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [alert for alert in self.alert_history if alert.timestamp >= cutoff_time]

    def get_alert_stats(self, hours: int = 24) -> Dict[str, Any]:
        """알림 통계 조회"""
        recent_alerts = self.get_alert_history(hours)

        stats = {
            "total_alerts": len(recent_alerts),
            "by_level": {},
            "by_component": {},
            "by_hour": {},
        }

        # 레벨별 통계
        for level in AlertLevel:
            stats["by_level"][level.value] = len(
                [a for a in recent_alerts if a.level == level]
            )

        # 컴포넌트별 통계
        components = set(alert.component for alert in recent_alerts)
        for component in components:
            stats["by_component"][component] = len(
                [a for a in recent_alerts if a.component == component]
            )

        # 시간별 통계 (간단화)
        stats["by_hour"] = len(recent_alerts)  # 실제로는 시간대별로 분류

        return stats


# 전역 알림 매니저 인스턴스
alert_manager = AlertManager()


# 편의 함수들
async def send_info_alert(title: str, message: str, component: str, **kwargs):
    """정보 알림 전송"""
    alert = Alert(
        title=title,
        message=message,
        level=AlertLevel.INFO,
        component=component,
        timestamp=datetime.now(),
        **kwargs,
    )
    await alert_manager.send_alert(alert)


async def send_warning_alert(title: str, message: str, component: str, **kwargs):
    """경고 알림 전송"""
    alert = Alert(
        title=title,
        message=message,
        level=AlertLevel.WARNING,
        component=component,
        timestamp=datetime.now(),
        **kwargs,
    )
    await alert_manager.send_alert(alert)


async def send_error_alert(title: str, message: str, component: str, **kwargs):
    """에러 알림 전송"""
    alert = Alert(
        title=title,
        message=message,
        level=AlertLevel.ERROR,
        component=component,
        timestamp=datetime.now(),
        **kwargs,
    )
    await alert_manager.send_alert(alert)


async def send_critical_alert(title: str, message: str, component: str, **kwargs):
    """치명적 알림 전송"""
    alert = Alert(
        title=title,
        message=message,
        level=AlertLevel.CRITICAL,
        component=component,
        timestamp=datetime.now(),
        **kwargs,
    )
    await alert_manager.send_alert(
        alert, channels=[AlertChannel.TELEGRAM, AlertChannel.SLACK]
    )


# 시스템 메트릭 기반 자동 알림
class AutoAlertMonitor:
    """자동 알림 모니터"""

    def __init__(self):
        self.monitoring = False
        self.check_interval = 60  # 1분마다 체크

    async def start_monitoring(self):
        """자동 모니터링 시작"""
        self.monitoring = True

        while self.monitoring:
            try:
                await self._check_system_metrics()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error("auto_alert_monitor_error", error=str(e))
                await asyncio.sleep(self.check_interval)

    def stop_monitoring(self):
        """자동 모니터링 중지"""
        self.monitoring = False

    async def _check_system_metrics(self):
        """시스템 메트릭 확인 및 알림"""
        import psutil

        # CPU 사용률 확인
        cpu_percent = psutil.cpu_percent(interval=1)
        if cpu_percent > 95:
            await send_critical_alert(
                "Critical CPU Usage",
                f"CPU usage is at {cpu_percent:.1f}%",
                "system",
                details={"cpu_percent": cpu_percent},
            )
        elif cpu_percent > 80:
            await send_warning_alert(
                "High CPU Usage",
                f"CPU usage is at {cpu_percent:.1f}%",
                "system",
                details={"cpu_percent": cpu_percent},
            )

        # 메모리 사용률 확인
        memory = psutil.virtual_memory()
        if memory.percent > 95:
            await send_critical_alert(
                "Critical Memory Usage",
                f"Memory usage is at {memory.percent:.1f}%",
                "system",
                details={
                    "memory_percent": memory.percent,
                    "available_gb": memory.available / (1024**3),
                },
            )
        elif memory.percent > 80:
            await send_warning_alert(
                "High Memory Usage",
                f"Memory usage is at {memory.percent:.1f}%",
                "system",
                details={
                    "memory_percent": memory.percent,
                    "available_gb": memory.available / (1024**3),
                },
            )

        # 디스크 사용률 확인
        disk = psutil.disk_usage("/")
        disk_percent = (disk.used / disk.total) * 100
        if disk_percent > 95:
            await send_critical_alert(
                "Critical Disk Usage",
                f"Disk usage is at {disk_percent:.1f}%",
                "system",
                details={
                    "disk_percent": disk_percent,
                    "free_gb": disk.free / (1024**3),
                },
            )
        elif disk_percent > 85:
            await send_warning_alert(
                "High Disk Usage",
                f"Disk usage is at {disk_percent:.1f}%",
                "system",
                details={
                    "disk_percent": disk_percent,
                    "free_gb": disk.free / (1024**3),
                },
            )


# 전역 자동 알림 모니터
auto_alert_monitor = AutoAlertMonitor()
