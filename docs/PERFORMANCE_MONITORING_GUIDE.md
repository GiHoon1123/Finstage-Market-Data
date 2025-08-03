# PERFORMANCE MONITORING GUIDE

## OVERVIEW

This guide provides comprehensive instructions for using the post-deployment performance monitoring system that collects performance metrics in production environments and performs automatic tuning.

## KEY FEATURES

### 1. Real-time Performance Monitoring

- Memory usage, CPU usage monitoring
- API response time and throughput measurement
- Cache performance and hit rate tracking
- Error rate and system status monitoring

### 2. Automatic Performance Tuning

- Automatic optimization application when performance degradation is detected
- Cache size adjustment when memory usage is high
- Async processing activation when response time increases
- TTL adjustment and warmup when cache hit rate decreases

### 3. Alert System

- Automatic alerts when performance thresholds are exceeded
- Detection and warning of consecutive performance degradation
- Notifications of automatic tuning execution results

### 4. Performance Analysis and Recommendations

- Performance trend analysis
- Automatic generation of tuning recommendations
- Performance history storage and analysis

## INSTALLATION AND SETUP

### Required Package Installation

```bash
pip install psutil fastapi uvicorn websockets
```

### Environment Variable Configuration

```bash
# Monitoring interval (seconds)
export MONITORING_INTERVAL=60

# Enable automatic tuning
export AUTO_TUNING_ENABLED=true

# Performance threshold settings
export MEMORY_THRESHOLD=80.0
export CPU_THRESHOLD=70.0
export RESPONSE_TIME_THRESHOLD=1000.0

# Cache size settings
export CACHE_SIZE_TECHNICAL_ANALYSIS=1000
export CACHE_SIZE_PRICE_DATA=2000
export CACHE_SIZE_NEWS_DATA=500
```

## USAGE

### 1. Basic Monitoring Execution

```bash
# Start monitoring with default settings
python deployment/run_performance_monitoring.py

# Run with custom settings
python deployment/run_performance_monitoring.py \
    --interval 30 \
    --memory-threshold 75 \
    --cpu-threshold 65 \
    --response-threshold 800
```

### 2. Using Configuration Files

```bash
# Create configuration file
python deployment/run_performance_monitoring.py \
    --save-config config/monitoring_config.json

# Run with configuration file
python deployment/run_performance_monitoring.py \
    --config config/monitoring_config.json
```

### 3. Web Dashboard Execution

```bash
# Start dashboard server
python deployment/performance_dashboard.py --port 8080

# Access via browser
# http://localhost:8080
```

### 4. Disable Automatic Tuning

```bash
python deployment/run_performance_monitoring.py --no-auto-tuning
```

## MONITORING METRICS

### System Metrics

- **Memory Usage Percentage**: System-wide memory usage ratio
- **CPU Usage Percentage**: Processor usage ratio
- **Active Connections**: Number of currently active network connections

### Application Metrics

- **Average Response Time**: Average processing time for API requests
- **P95 Response Time**: 95th percentile response time
- **Requests Per Second**: Number of requests processed (RPS)
- **Error Rate**: Error occurrence ratio relative to total requests

### Cache Metrics

- **Cache Hit Rate**: Percentage of data found in cache
- **Cache Size**: Number of items currently stored in cache

## AUTOMATIC TUNING FEATURES

### Memory Optimization

- **Trigger**: Memory usage > 85%
- **Actions**:
  - Enable memory optimization decorators
  - Reduce cache size by 30%
  - Force garbage collection execution

### Response Time Optimization

- **Trigger**: Average response time > 1500ms
- **Actions**:
  - Enable async processing optimization
  - Adjust task queue priorities
  - Move heavy tasks to background

### Cache Performance Optimization

- **Trigger**: Cache hit rate < 60%
- **Actions**:
  - Increase cache TTL by 50%
  - Execute cache warmup
  - Pre-load frequently used data

### Emergency Response

- **Trigger**: 5 consecutive performance degradations detected
- **Actions**:
  - Force enable all optimizations
  - Execute emergency cache cleanup
  - Force memory cleanup

## PERFORMANCE STATUS CLASSIFICATION

### 🟢 Excellent

- Memory < 40%, CPU < 30%
- Response time < 200ms
- Cache hit rate > 90%

### 🔵 Good

- Normal operational state
- No special action required

### 🟡 Fair

- Memory > 60% or CPU > 50%
- Response time > 500ms
- Cache hit rate < 70%

### 🟠 Poor

- Threshold exceeded state
- Subject to automatic tuning

### 🔴 Critical

- Memory > 95% or CPU > 90%
- Response time > 5000ms
- Error rate > 20%
- Immediate action required

## ALERT CONFIGURATION

### Alert Channels

- **Console**: Real-time output to terminal
- **Log File**: Structured log storage
- **Webhook**: External system integration (implementation required)

### Alert Conditions

- Performance threshold exceeded
- Consecutive performance degradation detected
- Automatic tuning execution
- System error occurrence

## FILE STRUCTURE

```
deployment/
├── post_deployment_performance_monitor.py  # Main monitoring system
├── performance_monitoring_config.py        # Configuration management
├── run_performance_monitoring.py           # Execution script
├── performance_dashboard.py                # Web dashboard
└── README_performance_monitoring.md        # Usage guide

logs/
├── performance_monitoring.log              # Monitoring logs
└── performance_history_YYYYMMDD_HHMMSS.json # Performance history

config/
└── monitoring_config.json                  # Configuration file (optional)
```

## API ENDPOINTS

### Dashboard API

- `GET /`: Web dashboard homepage
- `GET /api/metrics/current`: Current performance metrics
- `GET /api/metrics/history?hours=24`: Performance history
- `GET /api/health`: System status check
- `WebSocket /ws`: Real-time metrics stream

### Usage Examples

```bash
# Query current metrics
curl http://localhost:8080/api/metrics/current

# Query last 6 hours history
curl http://localhost:8080/api/metrics/history?hours=6

# Check system status
curl http://localhost:8080/api/health
```

## TROUBLESHOOTING

### Monitoring Won't Start

1. Check required package installation
2. Check permission issues (system metrics access)
3. Check port conflicts

### Performance Data Not Collected

1. Check application metrics collector status
2. Check cache system connection status
3. Check log files for error messages

### Automatic Tuning Not Working

1. Check automatic tuning enabled status
2. Check optimization manager status
3. Check cooldown time

### Dashboard Access Issues

1. Check port number
2. Check firewall settings
3. Check WebSocket connection status

## LOG ANALYSIS

### Log Levels

- **INFO**: General monitoring information
- **WARNING**: Performance degradation detected
- **ERROR**: System errors
- **CRITICAL**: Situations requiring immediate action

### Key Log Messages

```
post_deployment_monitoring_started: Monitoring started
performance_degradation_detected: Performance degradation detected
auto_tuning_started: Automatic tuning started
threshold_violation: Threshold violation
consecutive_poor_performance: Consecutive performance degradation
```

## ADVANCED USAGE

### Adding Custom Metrics

```python
# Implement custom metrics collector
class CustomMetricsCollector:
    def collect_custom_metrics(self):
        # Custom metrics collection logic
        pass
```

### Adding Custom Tuning Rules

```python
# Implement custom tuning rules
async def custom_tuning_rule(metrics):
    if metrics.custom_metric > threshold:
        # Custom tuning logic
        pass
```

### External Monitoring System Integration

```python
# Integration with Prometheus, Grafana, etc.
class PrometheusExporter:
    def export_metrics(self, metrics):
        # Export to Prometheus metrics format
        pass
```

## SUPPORT

For issues or feature improvement requests:

1. Check log files
2. Review configuration files
3. Check system resource status
4. Contact development team

---

**Important Notes**:

- Test thoroughly before using in production environment
- Enable automatic tuning features carefully
- Regularly backup performance history
