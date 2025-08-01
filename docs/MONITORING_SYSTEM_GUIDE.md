# 모니터링 시스템 가이드

Finstage Market Data 백엔드의 모니터링 시스템 사용법과 구성 요소를 설명합니다.

## 📊 시스템 구성

### 1. Prometheus 메트릭 수집

- **포트**: 8001
- **엔드포인트**: `http://localhost:8001/metrics`
- **수집 항목**:
  - 뉴스 처리 메트릭
  - 기술적 분석 성능
  - 데이터베이스 작업 시간
  - HTTP 요청 통계
  - 시스템 리소스 사용량

### 2. 헬스체크 시스템

- **전체 헬스체크**: `GET /monitoring/health`
- **준비 상태**: `GET /monitoring/health/ready` (Kubernetes readiness probe)
- **생존 상태**: `GET /monitoring/health/live` (Kubernetes liveness probe)

### 3. 알림 시스템

- **채널**: 텔레그램, Slack, 이메일, 웹훅
- **레벨**: INFO, WARNING, ERROR, CRITICAL
- **자동 알림**: 시스템 리소스 임계값 초과 시

## 🚀 사용법

### 메트릭 수집 데코레이터 사용

```python
from app.common.monitoring.metrics import measure_news_processing, measure_analysis_time

# 뉴스 처리 시간 측정
@measure_news_processing(source="investing.com", symbol="AAPL")
def process_news_article(article):
    # 뉴스 처리 로직
    pass

# 기술적 분석 시간 측정
@measure_analysis_time(symbol="AAPL", strategy="RSI")
def calculate_rsi(data):
    # RSI 계산 로직
    pass
```

### 수동 메트릭 기록

```python
from app.common.monitoring.metrics import metrics_collector

# 신호 생성 기록
metrics_collector.record_signal_generated("AAPL", "BUY", 0.85)

# 알림 전송 기록
metrics_collector.record_notification("telegram", "success", 0.5)

# 에러 기록
metrics_collector.record_error("ConnectionError", "database")
```

### 알림 전송

```python
from app.common.monitoring.alerts import send_warning_alert, send_critical_alert

# 경고 알림
await send_warning_alert(
    title="High CPU Usage",
    message="CPU usage is at 85%",
    component="system",
    details={"cpu_percent": 85.2}
)

# 치명적 알림
await send_critical_alert(
    title="Database Connection Failed",
    message="Unable to connect to MySQL database",
    component="database",
    details={"host": "localhost", "port": 3306}
)
```

## 📈 모니터링 대시보드

### Grafana 대시보드 설정

1. **Prometheus 데이터소스 추가**

   ```
   URL: http://localhost:8001
   ```

2. **주요 메트릭 쿼리**

   **뉴스 처리 성공률**

   ```promql
   rate(finstage_news_processed_total{status="success"}[5m]) /
   rate(finstage_news_processed_total[5m]) * 100
   ```

   **평균 응답 시간**

   ```promql
   rate(finstage_http_request_duration_seconds_sum[5m]) /
   rate(finstage_http_request_duration_seconds_count[5m])
   ```

   **에러율**

   ```promql
   rate(finstage_errors_total[5m])
   ```

   **시스템 리소스**

   ```promql
   finstage_system_cpu_usage_percent
   finstage_system_memory_usage_bytes / 1024 / 1024 / 1024
   ```

### 알림 규칙 설정

**Prometheus Alert Rules (alerts.yml)**

```yaml
groups:
  - name: finstage_alerts
    rules:
      - alert: HighCPUUsage
        expr: finstage_system_cpu_usage_percent > 80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High CPU usage detected"
          description: "CPU usage is {{ $value }}%"

      - alert: CriticalCPUUsage
        expr: finstage_system_cpu_usage_percent > 95
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Critical CPU usage detected"
          description: "CPU usage is {{ $value }}%"

      - alert: HighErrorRate
        expr: rate(finstage_errors_total[5m]) > 0.1
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }} errors/second"
```

## 🔧 설정

### 환경변수

```bash
# 텔레그램 알림 설정
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Slack 웹훅 (코드에서 설정)
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK

# 메트릭 서버 포트
METRICS_PORT=8001

# 알림 설정
ALERT_RATE_LIMIT_HOURS=1
ALERT_RATE_LIMIT_COUNT=5
```

### 모니터링 임계값 조정

```python
# app/common/monitoring/alerts.py에서 수정
alert_rules = {
    "high_cpu_usage": {
        "threshold": 80,  # CPU 사용률 임계값
        "duration_minutes": 5,
        "level": AlertLevel.WARNING
    },
    "high_memory_usage": {
        "threshold": 80,  # 메모리 사용률 임계값
        "duration_minutes": 5,
        "level": AlertLevel.WARNING
    }
}
```

## 📋 헬스체크 응답 예시

### 전체 헬스체크 (`/monitoring/health`)

```json
{
  "status": "healthy",
  "timestamp": "2025-01-31T10:30:00Z",
  "uptime_seconds": 3600,
  "version": "1.0.0",
  "environment": "production",
  "checks": {
    "database": {
      "status": "healthy",
      "message": "Database connection successful",
      "duration_ms": 15.2,
      "timestamp": "2025-01-31T10:30:00Z",
      "details": {
        "host": "localhost",
        "port": 3306,
        "database": "finstage_db"
      }
    },
    "telegram": {
      "status": "healthy",
      "message": "Telegram bot connection successful",
      "duration_ms": 120.5,
      "timestamp": "2025-01-31T10:30:00Z"
    },
    "system_resources": {
      "status": "healthy",
      "message": "Normal resource usage: CPU 45.2%, Memory 62.1%",
      "duration_ms": 100.1,
      "timestamp": "2025-01-31T10:30:00Z",
      "details": {
        "cpu_percent": 45.2,
        "memory_percent": 62.1,
        "memory_available_gb": 3.2,
        "cpu_count": 4
      }
    }
  }
}
```

### 상태별 HTTP 응답 코드

- **200**: 모든 컴포넌트 정상
- **503**: 일부 또는 전체 컴포넌트 비정상
- **500**: 헬스체크 자체 실패

## 🚨 알림 예시

### 텔레그램 알림 형태

```
🚨 **Critical CPU Usage**

**레벨:** CRITICAL
**컴포넌트:** system
**시간:** 2025-01-31 10:30:00

**메시지:**
CPU usage is at 96.5%

**상세 정보:**
• cpu_percent: 96.5
• memory_percent: 78.2
• available_memory_gb: 1.8

**태그:** system, performance, critical
```

### Slack 알림 형태

Slack에서는 색상이 있는 attachment 형태로 전송되며, 알림 레벨에 따라 다른 색상을 사용합니다:

- **INFO**: 녹색 (#36a64f)
- **WARNING**: 주황색 (#ff9500)
- **ERROR**: 빨간색 (#ff0000)
- **CRITICAL**: 진한 빨간색 (#8b0000)

## 📊 주요 메트릭 설명

### 애플리케이션 메트릭

1. **finstage_news_processed_total**

   - 처리된 뉴스 기사 총 개수
   - 라벨: source, symbol, status

2. **finstage_analysis_duration_seconds**

   - 기술적 분석 소요 시간
   - 라벨: symbol, strategy

3. **finstage_signals_generated_total**

   - 생성된 거래 신호 총 개수
   - 라벨: symbol, signal_type, confidence_level

4. **finstage_notifications_sent_total**
   - 전송된 알림 총 개수
   - 라벨: channel, status

### 시스템 메트릭

1. **finstage_system_cpu_usage_percent**

   - CPU 사용률 (%)

2. **finstage_system_memory_usage_bytes**

   - 메모리 사용량 (bytes)

3. **finstage_system_disk_usage_percent**

   - 디스크 사용률 (%)

4. **finstage_http_requests_total**
   - HTTP 요청 총 개수
   - 라벨: method, endpoint, status_code

## 🔍 트러블슈팅

### 메트릭 서버가 시작되지 않는 경우

1. **포트 충돌 확인**

   ```bash
   lsof -i :8001
   ```

2. **권한 문제 확인**
   ```bash
   # 다른 포트로 시작
   METRICS_PORT=8002 python app/main.py
   ```

### 알림이 전송되지 않는 경우

1. **텔레그램 봇 토큰 확인**

   ```bash
   curl "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getMe"
   ```

2. **네트워크 연결 확인**

   ```bash
   curl -I https://api.telegram.org
   ```

3. **로그 확인**
   ```bash
   grep "alert" logs/app.log
   ```

### 헬스체크 실패 시

1. **개별 컴포넌트 상태 확인**

   ```bash
   curl http://localhost:8081/monitoring/health | jq '.checks'
   ```

2. **데이터베이스 연결 테스트**
   ```bash
   mysql -h localhost -u username -p database_name -e "SELECT 1"
   ```

## 📚 추가 리소스

- [Prometheus 공식 문서](https://prometheus.io/docs/)
- [Grafana 대시보드 가이드](https://grafana.com/docs/)
- [FastAPI 모니터링 가이드](https://fastapi.tiangolo.com/advanced/monitoring/)

---

이 모니터링 시스템을 통해 애플리케이션의 상태를 실시간으로 파악하고, 문제 발생 시 즉시 대응할 수 있습니다.
