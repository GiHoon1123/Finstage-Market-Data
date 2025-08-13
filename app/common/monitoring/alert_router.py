"""
알림 시스템 API 라우터

알림 규칙 관리, 알림 조회, 통계 등을 위한 REST API 엔드포인트를 제공합니다.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel

from app.common.monitoring.alert_system import (
    get_alert_system,
    AlertRule,
    AlertSeverity,
    AlertChannel,
    start_alert_monitoring,
    stop_alert_monitoring,
)
from app.common.utils.logging_config import get_logger
from app.common.utils.memory_optimizer import memory_monitor
from app.common.dto.api_response import ApiResponse
from app.common.utils.response_helper import (
    success_response,
    handle_service_error,
)

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v2/alerts", tags=["Alert System"])


class AlertRuleRequest(BaseModel):
    """알림 규칙 요청 모델"""

    id: str
    name: str
    metric_name: str
    condition: str
    threshold: float
    severity: str
    channels: List[str]
    cooldown_minutes: int = 5
    enabled: bool = True
    description: str = ""


class EmailConfigRequest(BaseModel):
    """이메일 설정 요청 모델"""

    smtp_server: str
    smtp_port: int
    username: str
    password: str
    from_email: str


class WebhookRequest(BaseModel):
    """웹훅 요청 모델"""

    webhook_url: str


@router.get(
    "/", 
    summary="활성 알림 조회",
    responses={
        200: {
            "description": "활성 알림 조회 성공",
            "content": {
                "application/json": {
                    "example": {
                        "status": 200,
                        "message": "활성 알림 조회 완료 (3개 알림)",
                        "data": {
                            "active_alerts": [
                                {
                                    "id": "alert_001",
                                    "rule_id": "rule_001",
                                    "title": "높은 CPU 사용률",
                                    "message": "CPU 사용률이 90%를 초과했습니다",
                                    "severity": "high",
                                    "triggered_at": "2025-08-13T13:25:00Z"
                                }
                            ],
                            "total_count": 3,
                            "retrieved_at": "2025-08-13T13:30:00Z"
                        }
                    }
                }
            },
        }
    },
)
@memory_monitor
async def get_active_alerts() -> ApiResponse:
    """
    현재 활성 상태인 알림들을 조회합니다.

    Returns:
        활성 알림 목록
    """
    try:
        alert_system = get_alert_system()
        active_alerts = alert_system.get_active_alerts()

        alerts_data = []
        for alert in active_alerts:
            alerts_data.append(
                {
                    "id": alert.id,
                    "rule_id": alert.rule_id,
                    "title": alert.title,
                    "message": alert.message,
                    "severity": alert.severity.value,
                    "metric_name": alert.metric_name,
                    "current_value": alert.current_value,
                    "threshold": alert.threshold,
                    "triggered_at": alert.triggered_at.isoformat(),
                    "acknowledged": alert.acknowledged,
                }
            )

        response_data = {
            "active_alerts": alerts_data,
            "total_count": len(alerts_data),
            "retrieved_at": datetime.now().isoformat(),
        }

        return success_response(
            data=response_data,
            message=f"활성 알림 조회 완료 ({len(alerts_data)}개 알림)"
        )

    except Exception as e:
        logger.error("active_alerts_retrieval_failed", error=str(e))
        handle_service_error(e, "활성 알림 조회 실패")


@router.get(
    "/history", 
    summary="알림 히스토리 조회",
    responses={
        200: {
            "description": "알림 히스토리 조회 성공",
            "content": {
                "application/json": {
                    "example": {
                        "status": 200,
                        "message": "알림 히스토리 조회 완료 (15개 알림, 24시간 범위)",
                        "data": {
                            "alert_history": [
                                {
                                    "id": "alert_001",
                                    "rule_id": "rule_001",
                                    "title": "높은 CPU 사용률",
                                    "message": "CPU 사용률이 90%를 초과했습니다",
                                    "severity": "high",
                                    "triggered_at": "2025-08-13T13:25:00Z",
                                    "resolved_at": "2025-08-13T13:28:00Z"
                                }
                            ],
                            "time_range_hours": 24,
                            "total_count": 15,
                            "retrieved_at": "2025-08-13T13:30:00Z"
                        }
                    }
                }
            },
        }
    },
)
@memory_monitor
async def get_alert_history(
    hours: int = Query(24, description="조회할 시간 범위 (시간)")
) -> ApiResponse:
    """
    지정된 시간 범위 내의 알림 히스토리를 조회합니다.

    Args:
        hours: 조회할 시간 범위

    Returns:
        알림 히스토리
    """
    try:
        alert_system = get_alert_system()
        alert_history = alert_system.get_alert_history(hours)

        history_data = []
        for alert in alert_history:
            history_data.append(
                {
                    "id": alert.id,
                    "rule_id": alert.rule_id,
                    "title": alert.title,
                    "message": alert.message,
                    "severity": alert.severity.value,
                    "metric_name": alert.metric_name,
                    "current_value": alert.current_value,
                    "threshold": alert.threshold,
                    "triggered_at": alert.triggered_at.isoformat(),
                    "resolved_at": (
                        alert.resolved_at.isoformat() if alert.resolved_at else None
                    ),
                    "acknowledged": alert.acknowledged,
                }
            )

        response_data = {
            "alert_history": history_data,
            "time_range_hours": hours,
            "total_count": len(history_data),
            "retrieved_at": datetime.now().isoformat(),
        }

        return success_response(
            data=response_data,
            message=f"알림 히스토리 조회 완료 ({len(history_data)}개 알림, {hours}시간 범위)"
        )

    except Exception as e:
        logger.error("alert_history_retrieval_failed", error=str(e))
        handle_service_error(e, "알림 히스토리 조회 실패")


@router.get("/statistics", summary="알림 통계 조회")
@memory_monitor
async def get_alert_statistics(
    hours: int = Query(24, description="통계 기간 (시간)")
) -> Dict[str, Any]:
    """
    알림 통계를 조회합니다.

    Args:
        hours: 통계 기간

    Returns:
        알림 통계
    """
    try:
        alert_system = get_alert_system()
        statistics = alert_system.get_alert_statistics(hours)

        if "error" in statistics:
            raise HTTPException(status_code=500, detail=statistics["error"])

        return statistics

    except Exception as e:
        logger.error("alert_statistics_retrieval_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rules", summary="알림 규칙 조회")
@memory_monitor
async def get_alert_rules() -> Dict[str, Any]:
    """
    현재 설정된 알림 규칙들을 조회합니다.

    Returns:
        알림 규칙 목록
    """
    try:
        alert_system = get_alert_system()
        rules_data = []

        for rule_id, rule in alert_system.alert_rules.items():
            rules_data.append(
                {
                    "id": rule.id,
                    "name": rule.name,
                    "metric_name": rule.metric_name,
                    "condition": rule.condition,
                    "threshold": rule.threshold,
                    "severity": rule.severity.value,
                    "channels": [channel.value for channel in rule.channels],
                    "cooldown_minutes": rule.cooldown_minutes,
                    "enabled": rule.enabled,
                    "description": rule.description,
                }
            )

        return {
            "alert_rules": rules_data,
            "total_count": len(rules_data),
            "retrieved_at": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error("alert_rules_retrieval_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rules", summary="알림 규칙 추가")
@memory_monitor
async def add_alert_rule(rule_request: AlertRuleRequest) -> Dict[str, Any]:
    """
    새로운 알림 규칙을 추가합니다.

    Args:
        rule_request: 알림 규칙 정보

    Returns:
        추가 결과
    """
    try:
        # 심각도 변환
        try:
            severity = AlertSeverity(rule_request.severity)
        except ValueError:
            raise HTTPException(
                status_code=400, detail=f"Invalid severity: {rule_request.severity}"
            )

        # 채널 변환
        channels = []
        for channel_str in rule_request.channels:
            try:
                channels.append(AlertChannel(channel_str))
            except ValueError:
                raise HTTPException(
                    status_code=400, detail=f"Invalid channel: {channel_str}"
                )

        # 알림 규칙 생성
        alert_rule = AlertRule(
            id=rule_request.id,
            name=rule_request.name,
            metric_name=rule_request.metric_name,
            condition=rule_request.condition,
            threshold=rule_request.threshold,
            severity=severity,
            channels=channels,
            cooldown_minutes=rule_request.cooldown_minutes,
            enabled=rule_request.enabled,
            description=rule_request.description,
        )

        # 알림 시스템에 추가
        alert_system = get_alert_system()
        alert_system.add_alert_rule(alert_rule)

        return {
            "status": "success",
            "message": "Alert rule added successfully",
            "rule_id": rule_request.id,
            "added_at": datetime.now().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "alert_rule_addition_failed", rule_id=rule_request.id, error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/rules/{rule_id}", summary="알림 규칙 삭제")
@memory_monitor
async def remove_alert_rule(rule_id: str) -> Dict[str, Any]:
    """
    알림 규칙을 삭제합니다.

    Args:
        rule_id: 삭제할 규칙 ID

    Returns:
        삭제 결과
    """
    try:
        alert_system = get_alert_system()

        if rule_id not in alert_system.alert_rules:
            raise HTTPException(
                status_code=404, detail=f"Alert rule not found: {rule_id}"
            )

        alert_system.remove_alert_rule(rule_id)

        return {
            "status": "success",
            "message": "Alert rule removed successfully",
            "rule_id": rule_id,
            "removed_at": datetime.now().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("alert_rule_removal_failed", rule_id=rule_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/rules/{rule_id}/enable", summary="알림 규칙 활성화")
@memory_monitor
async def enable_alert_rule(rule_id: str) -> Dict[str, Any]:
    """
    알림 규칙을 활성화합니다.

    Args:
        rule_id: 활성화할 규칙 ID

    Returns:
        활성화 결과
    """
    try:
        alert_system = get_alert_system()

        if rule_id not in alert_system.alert_rules:
            raise HTTPException(
                status_code=404, detail=f"Alert rule not found: {rule_id}"
            )

        alert_system.enable_alert_rule(rule_id)

        return {
            "status": "success",
            "message": "Alert rule enabled successfully",
            "rule_id": rule_id,
            "enabled_at": datetime.now().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("alert_rule_enable_failed", rule_id=rule_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/rules/{rule_id}/disable", summary="알림 규칙 비활성화")
@memory_monitor
async def disable_alert_rule(rule_id: str) -> Dict[str, Any]:
    """
    알림 규칙을 비활성화합니다.

    Args:
        rule_id: 비활성화할 규칙 ID

    Returns:
        비활성화 결과
    """
    try:
        alert_system = get_alert_system()

        if rule_id not in alert_system.alert_rules:
            raise HTTPException(
                status_code=404, detail=f"Alert rule not found: {rule_id}"
            )

        alert_system.disable_alert_rule(rule_id)

        return {
            "status": "success",
            "message": "Alert rule disabled successfully",
            "rule_id": rule_id,
            "disabled_at": datetime.now().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("alert_rule_disable_failed", rule_id=rule_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/alerts/{alert_id}/acknowledge", summary="알림 확인")
@memory_monitor
async def acknowledge_alert(alert_id: str) -> Dict[str, Any]:
    """
    알림을 확인 처리합니다.

    Args:
        alert_id: 확인할 알림 ID

    Returns:
        확인 결과
    """
    try:
        alert_system = get_alert_system()

        if alert_id not in alert_system.active_alerts:
            raise HTTPException(status_code=404, detail=f"Alert not found: {alert_id}")

        alert_system.acknowledge_alert(alert_id)

        return {
            "status": "success",
            "message": "Alert acknowledged successfully",
            "alert_id": alert_id,
            "acknowledged_at": datetime.now().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("alert_acknowledge_failed", alert_id=alert_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/monitoring/start", summary="알림 모니터링 시작")
@memory_monitor
async def start_monitoring(
    check_interval: int = Query(30, description="체크 간격 (초)")
) -> Dict[str, Any]:
    """
    알림 모니터링을 시작합니다.

    Args:
        check_interval: 체크 간격

    Returns:
        시작 결과
    """
    try:
        start_alert_monitoring(check_interval)

        return {
            "status": "success",
            "message": "Alert monitoring started successfully",
            "check_interval": check_interval,
            "started_at": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error("alert_monitoring_start_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/monitoring/stop", summary="알림 모니터링 중지")
@memory_monitor
async def stop_monitoring() -> Dict[str, Any]:
    """
    알림 모니터링을 중지합니다.

    Returns:
        중지 결과
    """
    try:
        stop_alert_monitoring()

        return {
            "status": "success",
            "message": "Alert monitoring stopped successfully",
            "stopped_at": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error("alert_monitoring_stop_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/config/email", summary="이메일 설정")
@memory_monitor
async def configure_email(config: EmailConfigRequest) -> Dict[str, Any]:
    """
    이메일 알림 설정을 구성합니다.

    Args:
        config: 이메일 설정 정보

    Returns:
        설정 결과
    """
    try:
        alert_system = get_alert_system()
        alert_system.configure_email(
            smtp_server=config.smtp_server,
            smtp_port=config.smtp_port,
            username=config.username,
            password=config.password,
            from_email=config.from_email,
        )

        return {
            "status": "success",
            "message": "Email configuration updated successfully",
            "configured_at": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error("email_config_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/config/webhook", summary="웹훅 URL 추가")
@memory_monitor
async def add_webhook_url(webhook: WebhookRequest) -> Dict[str, Any]:
    """
    웹훅 URL을 추가합니다.

    Args:
        webhook: 웹훅 정보

    Returns:
        추가 결과
    """
    try:
        alert_system = get_alert_system()
        alert_system.add_webhook_url(webhook.webhook_url)

        return {
            "status": "success",
            "message": "Webhook URL added successfully",
            "webhook_url": webhook.webhook_url,
            "added_at": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error("webhook_add_failed", url=webhook.webhook_url, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/config/webhook", summary="웹훅 URL 제거")
@memory_monitor
async def remove_webhook_url(webhook: WebhookRequest) -> Dict[str, Any]:
    """
    웹훅 URL을 제거합니다.

    Args:
        webhook: 웹훅 정보

    Returns:
        제거 결과
    """
    try:
        alert_system = get_alert_system()
        alert_system.remove_webhook_url(webhook.webhook_url)

        return {
            "status": "success",
            "message": "Webhook URL removed successfully",
            "webhook_url": webhook.webhook_url,
            "removed_at": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error("webhook_remove_failed", url=webhook.webhook_url, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config", summary="알림 시스템 설정 조회")
@memory_monitor
async def get_alert_config() -> Dict[str, Any]:
    """
    현재 알림 시스템 설정을 조회합니다.

    Returns:
        설정 정보
    """
    try:
        alert_system = get_alert_system()

        # 이메일 설정 (비밀번호 제외)
        email_config = alert_system.email_config.copy()
        if email_config.get("password"):
            email_config["password"] = "***"

        return {
            "monitoring_status": alert_system.is_monitoring,
            "total_rules": len(alert_system.alert_rules),
            "enabled_rules": len(
                [r for r in alert_system.alert_rules.values() if r.enabled]
            ),
            "active_alerts": len(alert_system.get_active_alerts()),
            "email_config": email_config,
            "webhook_urls": alert_system.webhook_urls,
            "retrieved_at": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error("alert_config_retrieval_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
