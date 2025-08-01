"""
자동 알림 시스템

성능 저하 감지 시 자동 알림을 발송하고 메모리 사용량 임계값 초과 시 알림을 보내는 시스템입니다.
"""

import asyncio
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import json
import threading
import time

from app.common.monitoring.performance_metrics_collector import get_metrics_collector
from app.common.utils.logging_config import get_logger
from app.common.utils.memory_optimizer import memory_monitor
from app.common.utils.websocket_manager import WebSocketManager

logger = get_logger(__name__)


class AlertSeverity(Enum):
    """알림 심각도"""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    ERROR = "error"


class AlertChannel(Enum):
    """알림 채널"""

    EMAIL = "email"
    WEBSOCKET = "websocket"
    LOG = "log"
    WEBHOOK = "webhook"


@dataclass
class AlertRule:
    """알림 규칙"""

    id: str
    name: str
    metric_name: str
    condition: str  # ">", "<", ">=", "<=", "=="
    threshold: float
    severity: AlertSeverity
    channels: List[AlertChannel]
    cooldown_minutes: int = 5
    enabled: bool = True
    description: str = ""


@dataclass
class Alert:
    """알림 데이터"""

    id: str
    rule_id: str
    title: str
    message: str
    severity: AlertSeverity
    metric_name: str
    current_value: float
    threshold: float
    triggered_at: datetime
    resolved_at: Optional[datetime] = None
    acknowledged: bool = False


class AlertSystem:
    """자동 알림 시스템"""

    def __init__(self):
        self.metrics_collector = get_metrics_collector()
        self.websocket_manager = WebSocketManager()

        # 알림 규칙들
        self.alert_rules: Dict[str, AlertRule] = {}

        # 활성 알림들
        self.active_alerts: Dict[str, Alert] = {}

        # 알림 히스토리
        self.alert_history: List[Alert] = []

        # 쿨다운 추적
        self.last_alert_times: Dict[str, datetime] = {}

        # 모니터링 상태
        self.is_monitoring = False
        self.monitoring_thread = None

        # 이메일 설정
        self.email_config = {
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "username": "",
            "password": "",
            "from_email": "",
        }

        # 웹훅 설정
        self.webhook_urls: List[str] = []

        # 기본 알림 규칙 설정
        self._setup_default_rules()

    def _setup_default_rules(self):
        """기본 알림 규칙 설정"""
        default_rules = [
            AlertRule(
                id="high_cpu_usage",
                name="High CPU Usage",
                metric_name="cpu_percent",
                condition=">",
                threshold=80.0,
                severity=AlertSeverity.WARNING,
                channels=[AlertChannel.WEBSOCKET, AlertChannel.LOG],
                cooldown_minutes=5,
                description="CPU 사용률이 80%를 초과했습니다",
            ),
            AlertRule(
                id="critical_cpu_usage",
                name="Critical CPU Usage",
                metric_name="cpu_percent",
                condition=">",
                threshold=90.0,
                severity=AlertSeverity.CRITICAL,
                channels=[AlertChannel.EMAIL, AlertChannel.WEBSOCKET, AlertChannel.LOG],
                cooldown_minutes=2,
                description="CPU 사용률이 90%를 초과했습니다",
            ),
            AlertRule(
                id="high_memory_usage",
                name="High Memory Usage",
                metric_name="memory_percent",
                condition=">",
                threshold=85.0,
                severity=AlertSeverity.WARNING,
                channels=[AlertChannel.WEBSOCKET, AlertChannel.LOG],
                cooldown_minutes=5,
                description="메모리 사용률이 85%를 초과했습니다",
            ),
            AlertRule(
                id="critical_memory_usage",
                name="Critical Memory Usage",
                metric_name="memory_percent",
                condition=">",
                threshold=95.0,
                severity=AlertSeverity.CRITICAL,
                channels=[AlertChannel.EMAIL, AlertChannel.WEBSOCKET, AlertChannel.LOG],
                cooldown_minutes=2,
                description="메모리 사용률이 95%를 초과했습니다",
            ),
            AlertRule(
                id="slow_api_response",
                name="Slow API Response",
                metric_name="api_response_time_ms",
                condition=">",
                threshold=1000.0,
                severity=AlertSeverity.WARNING,
                channels=[AlertChannel.WEBSOCKET, AlertChannel.LOG],
                cooldown_minutes=10,
                description="API 응답 시간이 1초를 초과했습니다",
            ),
            AlertRule(
                id="very_slow_api_response",
                name="Very Slow API Response",
                metric_name="api_response_time_ms",
                condition=">",
                threshold=2000.0,
                severity=AlertSeverity.CRITICAL,
                channels=[AlertChannel.EMAIL, AlertChannel.WEBSOCKET, AlertChannel.LOG],
                cooldown_minutes=5,
                description="API 응답 시간이 2초를 초과했습니다",
            ),
            AlertRule(
                id="low_cache_hit_rate",
                name="Low Cache Hit Rate",
                metric_name="cache_hit_rate",
                condition="<",
                threshold=70.0,
                severity=AlertSeverity.WARNING,
                channels=[AlertChannel.WEBSOCKET, AlertChannel.LOG],
                cooldown_minutes=15,
                description="캐시 히트율이 70% 미만입니다",
            ),
            AlertRule(
                id="high_error_rate",
                name="High Error Rate",
                metric_name="error_rate_percent",
                condition=">",
                threshold=5.0,
                severity=AlertSeverity.WARNING,
                channels=[AlertChannel.WEBSOCKET, AlertChannel.LOG],
                cooldown_minutes=10,
                description="에러율이 5%를 초과했습니다",
            ),
        ]

        for rule in default_rules:
            self.alert_rules[rule.id] = rule

    @memory_monitor
    def start_monitoring(self, check_interval: int = 30):
        """알림 모니터링 시작"""
        if self.is_monitoring:
            logger.warning("alert_monitoring_already_running")
            return

        self.is_monitoring = True
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop, args=(check_interval,), daemon=True
        )
        self.monitoring_thread.start()

        logger.info("alert_monitoring_started", interval=check_interval)

    def stop_monitoring(self):
        """알림 모니터링 중지"""
        self.is_monitoring = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)

        logger.info("alert_monitoring_stopped")

    def _monitoring_loop(self, check_interval: int):
        """알림 모니터링 루프"""
        while self.is_monitoring:
            try:
                self._check_alert_conditions()
                time.sleep(check_interval)
            except Exception as e:
                logger.error("alert_monitoring_error", error=str(e))
                time.sleep(check_interval)

    @memory_monitor
    def _check_alert_conditions(self):
        """알림 조건 확인"""
        try:
            # 현재 메트릭 조회
            current_metrics = self._get_current_metrics()

            for rule_id, rule in self.alert_rules.items():
                if not rule.enabled:
                    continue

                # 쿨다운 확인
                if self._is_in_cooldown(rule_id, rule.cooldown_minutes):
                    continue

                # 메트릭 값 조회
                metric_value = current_metrics.get(rule.metric_name)
                if metric_value is None:
                    continue

                # 조건 확인
                if self._evaluate_condition(
                    metric_value, rule.condition, rule.threshold
                ):
                    # 알림 발생
                    alert = self._create_alert(rule, metric_value)
                    self._trigger_alert(alert)
                    self.last_alert_times[rule_id] = datetime.now()
                else:
                    # 알림 해제 확인
                    self._check_alert_resolution(rule_id, metric_value)

        except Exception as e:
            logger.error("alert_condition_check_failed", error=str(e))

    def _get_current_metrics(self) -> Dict[str, float]:
        """현재 메트릭 조회"""
        try:
            # 시스템 메트릭
            if self.metrics_collector.system_metrics_storage:
                latest_system = self.metrics_collector.system_metrics_storage[-1]
                system_metrics = {
                    "cpu_percent": latest_system.cpu_percent,
                    "memory_percent": latest_system.memory_percent,
                    "memory_used_mb": latest_system.memory_used_mb,
                    "disk_usage_percent": latest_system.disk_usage_percent,
                }
            else:
                system_metrics = {}

            # 애플리케이션 메트릭
            if self.metrics_collector.app_metrics_storage:
                latest_app = self.metrics_collector.app_metrics_storage[-1]
                app_metrics = {
                    "api_response_time_ms": latest_app.api_response_time_ms,
                    "cache_hit_rate": latest_app.cache_hit_rate,
                    "active_connections": float(latest_app.active_connections),
                    "processed_requests": float(latest_app.processed_requests),
                    "failed_requests": float(latest_app.failed_requests),
                }

                # 에러율 계산
                if latest_app.processed_requests > 0:
                    error_rate = (
                        latest_app.failed_requests / latest_app.processed_requests
                    ) * 100
                    app_metrics["error_rate_percent"] = error_rate
                else:
                    app_metrics["error_rate_percent"] = 0.0
            else:
                app_metrics = {}

            # 메트릭 합치기
            current_metrics = {**system_metrics, **app_metrics}
            return current_metrics

        except Exception as e:
            logger.error("current_metrics_retrieval_failed", error=str(e))
            return {}

    def _is_in_cooldown(self, rule_id: str, cooldown_minutes: int) -> bool:
        """쿨다운 상태 확인"""
        if rule_id not in self.last_alert_times:
            return False

        last_alert_time = self.last_alert_times[rule_id]
        cooldown_period = timedelta(minutes=cooldown_minutes)

        return datetime.now() - last_alert_time < cooldown_period

    def _evaluate_condition(
        self, value: float, condition: str, threshold: float
    ) -> bool:
        """조건 평가"""
        if condition == ">":
            return value > threshold
        elif condition == ">=":
            return value >= threshold
        elif condition == "<":
            return value < threshold
        elif condition == "<=":
            return value <= threshold
        elif condition == "==":
            return abs(value - threshold) < 0.001  # 부동소수점 비교
        else:
            return False

    def _create_alert(self, rule: AlertRule, current_value: float) -> Alert:
        """알림 생성"""
        alert_id = f"{rule.id}_{int(datetime.now().timestamp())}"

        alert = Alert(
            id=alert_id,
            rule_id=rule.id,
            title=rule.name,
            message=f"{rule.description}. 현재 값: {current_value:.2f}, 임계값: {rule.threshold:.2f}",
            severity=rule.severity,
            metric_name=rule.metric_name,
            current_value=current_value,
            threshold=rule.threshold,
            triggered_at=datetime.now(),
        )

        return alert

    @memory_monitor
    def _trigger_alert(self, alert: Alert):
        """알림 발생"""
        try:
            # 활성 알림에 추가
            self.active_alerts[alert.id] = alert

            # 히스토리에 추가
            self.alert_history.append(alert)

            # 히스토리 크기 제한 (최근 1000개만 유지)
            if len(self.alert_history) > 1000:
                self.alert_history = self.alert_history[-1000:]

            # 알림 규칙에 따라 알림 발송
            rule = self.alert_rules.get(alert.rule_id)
            if rule:
                for channel in rule.channels:
                    self._send_alert(alert, channel)

            logger.info(
                "alert_triggered",
                alert_id=alert.id,
                rule_id=alert.rule_id,
                severity=alert.severity.value,
                metric=alert.metric_name,
                value=alert.current_value,
            )

        except Exception as e:
            logger.error("alert_trigger_failed", alert_id=alert.id, error=str(e))

    def _send_alert(self, alert: Alert, channel: AlertChannel):
        """채널별 알림 발송"""
        try:
            if channel == AlertChannel.LOG:
                self._send_log_alert(alert)
            elif channel == AlertChannel.WEBSOCKET:
                asyncio.create_task(self._send_websocket_alert(alert))
            elif channel == AlertChannel.EMAIL:
                self._send_email_alert(alert)
            elif channel == AlertChannel.WEBHOOK:
                self._send_webhook_alert(alert)

        except Exception as e:
            logger.error(
                "alert_send_failed",
                alert_id=alert.id,
                channel=channel.value,
                error=str(e),
            )

    def _send_log_alert(self, alert: Alert):
        """로그 알림 발송"""
        log_level = "warning" if alert.severity == AlertSeverity.WARNING else "error"

        if log_level == "warning":
            logger.warning(
                "performance_alert",
                alert_id=alert.id,
                title=alert.title,
                message=alert.message,
                metric=alert.metric_name,
                value=alert.current_value,
                threshold=alert.threshold,
            )
        else:
            logger.error(
                "performance_alert",
                alert_id=alert.id,
                title=alert.title,
                message=alert.message,
                metric=alert.metric_name,
                value=alert.current_value,
                threshold=alert.threshold,
            )

    async def _send_websocket_alert(self, alert: Alert):
        """WebSocket 알림 발송"""
        try:
            alert_data = {
                "type": "performance_alert",
                "alert": {
                    "id": alert.id,
                    "title": alert.title,
                    "message": alert.message,
                    "severity": alert.severity.value,
                    "metric_name": alert.metric_name,
                    "current_value": alert.current_value,
                    "threshold": alert.threshold,
                    "triggered_at": alert.triggered_at.isoformat(),
                },
            }

            await self.websocket_manager.broadcast_message(json.dumps(alert_data))

        except Exception as e:
            logger.error("websocket_alert_failed", alert_id=alert.id, error=str(e))

    def _send_email_alert(self, alert: Alert):
        """이메일 알림 발송"""
        try:
            if not self.email_config.get("username") or not self.email_config.get(
                "password"
            ):
                logger.warning("email_config_not_set", alert_id=alert.id)
                return

            # 이메일 내용 구성
            subject = f"[{alert.severity.value.upper()}] {alert.title}"

            body = f"""
성능 알림이 발생했습니다.

알림 ID: {alert.id}
제목: {alert.title}
심각도: {alert.severity.value.upper()}
메트릭: {alert.metric_name}
현재 값: {alert.current_value:.2f}
임계값: {alert.threshold:.2f}
발생 시간: {alert.triggered_at.strftime('%Y-%m-%d %H:%M:%S')}

메시지: {alert.message}

시스템을 확인해 주세요.
            """

            # 이메일 발송
            msg = MIMEMultipart()
            msg["From"] = self.email_config["from_email"]
            msg["To"] = self.email_config["username"]  # 자기 자신에게 발송
            msg["Subject"] = subject

            msg.attach(MIMEText(body, "plain", "utf-8"))

            server = smtplib.SMTP(
                self.email_config["smtp_server"], self.email_config["smtp_port"]
            )
            server.starttls()
            server.login(self.email_config["username"], self.email_config["password"])

            text = msg.as_string()
            server.sendmail(
                self.email_config["from_email"], self.email_config["username"], text
            )
            server.quit()

            logger.info("email_alert_sent", alert_id=alert.id)

        except Exception as e:
            logger.error("email_alert_failed", alert_id=alert.id, error=str(e))

    def _send_webhook_alert(self, alert: Alert):
        """웹훅 알림 발송"""
        try:
            import requests

            alert_data = {
                "alert_id": alert.id,
                "rule_id": alert.rule_id,
                "title": alert.title,
                "message": alert.message,
                "severity": alert.severity.value,
                "metric_name": alert.metric_name,
                "current_value": alert.current_value,
                "threshold": alert.threshold,
                "triggered_at": alert.triggered_at.isoformat(),
            }

            for webhook_url in self.webhook_urls:
                try:
                    response = requests.post(
                        webhook_url,
                        json=alert_data,
                        timeout=10,
                        headers={"Content-Type": "application/json"},
                    )

                    if response.status_code == 200:
                        logger.info(
                            "webhook_alert_sent", alert_id=alert.id, url=webhook_url
                        )
                    else:
                        logger.warning(
                            "webhook_alert_failed",
                            alert_id=alert.id,
                            url=webhook_url,
                            status_code=response.status_code,
                        )

                except requests.RequestException as e:
                    logger.error(
                        "webhook_request_failed",
                        alert_id=alert.id,
                        url=webhook_url,
                        error=str(e),
                    )

        except Exception as e:
            logger.error("webhook_alert_system_failed", alert_id=alert.id, error=str(e))

    def _check_alert_resolution(self, rule_id: str, current_value: float):
        """알림 해제 확인"""
        try:
            # 해당 규칙의 활성 알림 찾기
            active_alerts_for_rule = [
                alert
                for alert in self.active_alerts.values()
                if alert.rule_id == rule_id and alert.resolved_at is None
            ]

            if not active_alerts_for_rule:
                return

            rule = self.alert_rules.get(rule_id)
            if not rule:
                return

            # 조건이 해제되었는지 확인
            condition_resolved = not self._evaluate_condition(
                current_value, rule.condition, rule.threshold
            )

            if condition_resolved:
                for alert in active_alerts_for_rule:
                    alert.resolved_at = datetime.now()

                    # 해제 알림 발송
                    self._send_resolution_notification(alert, current_value)

                    logger.info(
                        "alert_resolved",
                        alert_id=alert.id,
                        rule_id=rule_id,
                        current_value=current_value,
                    )

        except Exception as e:
            logger.error("alert_resolution_check_failed", rule_id=rule_id, error=str(e))

    def _send_resolution_notification(self, alert: Alert, current_value: float):
        """알림 해제 통지"""
        try:
            resolution_data = {
                "type": "alert_resolved",
                "alert": {
                    "id": alert.id,
                    "title": f"[RESOLVED] {alert.title}",
                    "message": f"알림이 해제되었습니다. 현재 값: {current_value:.2f}",
                    "severity": "info",
                    "resolved_at": (
                        alert.resolved_at.isoformat() if alert.resolved_at else None
                    ),
                },
            }

            # WebSocket으로 해제 통지
            asyncio.create_task(
                self.websocket_manager.broadcast_message(json.dumps(resolution_data))
            )

        except Exception as e:
            logger.error(
                "resolution_notification_failed", alert_id=alert.id, error=str(e)
            )

    @memory_monitor
    def add_alert_rule(self, rule: AlertRule):
        """알림 규칙 추가"""
        self.alert_rules[rule.id] = rule
        logger.info("alert_rule_added", rule_id=rule.id, rule_name=rule.name)

    def remove_alert_rule(self, rule_id: str):
        """알림 규칙 제거"""
        if rule_id in self.alert_rules:
            del self.alert_rules[rule_id]
            logger.info("alert_rule_removed", rule_id=rule_id)

    def enable_alert_rule(self, rule_id: str):
        """알림 규칙 활성화"""
        if rule_id in self.alert_rules:
            self.alert_rules[rule_id].enabled = True
            logger.info("alert_rule_enabled", rule_id=rule_id)

    def disable_alert_rule(self, rule_id: str):
        """알림 규칙 비활성화"""
        if rule_id in self.alert_rules:
            self.alert_rules[rule_id].enabled = False
            logger.info("alert_rule_disabled", rule_id=rule_id)

    @memory_monitor
    def acknowledge_alert(self, alert_id: str):
        """알림 확인"""
        if alert_id in self.active_alerts:
            self.active_alerts[alert_id].acknowledged = True
            logger.info("alert_acknowledged", alert_id=alert_id)

    def get_active_alerts(self) -> List[Alert]:
        """활성 알림 조회"""
        return [
            alert for alert in self.active_alerts.values() if alert.resolved_at is None
        ]

    def get_alert_history(self, hours: int = 24) -> List[Alert]:
        """알림 히스토리 조회"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [
            alert for alert in self.alert_history if alert.triggered_at >= cutoff_time
        ]

    def get_alert_statistics(self, hours: int = 24) -> Dict[str, Any]:
        """알림 통계 조회"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            recent_alerts = [
                alert
                for alert in self.alert_history
                if alert.triggered_at >= cutoff_time
            ]

            # 심각도별 통계
            severity_stats = {}
            for severity in AlertSeverity:
                severity_stats[severity.value] = len(
                    [alert for alert in recent_alerts if alert.severity == severity]
                )

            # 규칙별 통계
            rule_stats = {}
            for alert in recent_alerts:
                rule_id = alert.rule_id
                if rule_id not in rule_stats:
                    rule_stats[rule_id] = 0
                rule_stats[rule_id] += 1

            # 시간대별 통계 (시간별)
            hourly_stats = {}
            for alert in recent_alerts:
                hour = alert.triggered_at.strftime("%Y-%m-%d %H:00")
                if hour not in hourly_stats:
                    hourly_stats[hour] = 0
                hourly_stats[hour] += 1

            return {
                "time_range_hours": hours,
                "total_alerts": len(recent_alerts),
                "active_alerts": len(self.get_active_alerts()),
                "severity_breakdown": severity_stats,
                "rule_breakdown": rule_stats,
                "hourly_breakdown": hourly_stats,
                "generated_at": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error("alert_statistics_failed", error=str(e))
            return {"error": str(e)}

    def configure_email(
        self,
        smtp_server: str,
        smtp_port: int,
        username: str,
        password: str,
        from_email: str,
    ):
        """이메일 설정"""
        self.email_config = {
            "smtp_server": smtp_server,
            "smtp_port": smtp_port,
            "username": username,
            "password": password,
            "from_email": from_email,
        }
        logger.info("email_config_updated")

    def add_webhook_url(self, webhook_url: str):
        """웹훅 URL 추가"""
        if webhook_url not in self.webhook_urls:
            self.webhook_urls.append(webhook_url)
            logger.info("webhook_url_added", url=webhook_url)

    def remove_webhook_url(self, webhook_url: str):
        """웹훅 URL 제거"""
        if webhook_url in self.webhook_urls:
            self.webhook_urls.remove(webhook_url)
            logger.info("webhook_url_removed", url=webhook_url)


# 글로벌 알림 시스템 인스턴스
_alert_system = None


def get_alert_system() -> AlertSystem:
    """글로벌 알림 시스템 인스턴스 조회"""
    global _alert_system
    if _alert_system is None:
        _alert_system = AlertSystem()
    return _alert_system


def start_alert_monitoring(check_interval: int = 30):
    """알림 모니터링 시작 (편의 함수)"""
    alert_system = get_alert_system()
    alert_system.start_monitoring(check_interval)


def stop_alert_monitoring():
    """알림 모니터링 중지 (편의 함수)"""
    alert_system = get_alert_system()
    alert_system.stop_monitoring()
