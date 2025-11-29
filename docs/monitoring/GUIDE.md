# Monitoring & Observability Guide

Complete guide to monitoring your Thought Processor system with Grafana, Prometheus, Loki, and Tempo.

## 📊 Overview

The monitoring stack provides comprehensive observability across all system components:

- **Prometheus**: Metrics collection and time-series storage
- **Grafana**: Visualization dashboards and alerting
- **Loki**: Log aggregation and querying
- **Tempo**: Distributed tracing
- **Exporters**: Specialized metrics for PostgreSQL, Redis, Kafka, and system resources

## 🚀 Quick Start

### Starting the Monitoring Stack

Start all services including monitoring:

```bash
docker-compose --profile monitoring up -d
```

Or start specific monitoring services:

```bash
# Start core services
docker-compose up -d db redis kafka api kafka-worker frontend

# Start monitoring stack
docker-compose --profile monitoring up -d
```

### Accessing Dashboards

Once started, access the monitoring interfaces:

| Service | URL | Default Credentials |
|---------|-----|-------------------|
| **Grafana** | http://localhost:3001 | admin / admin |
| **Prometheus** | http://localhost:9090 | N/A |
| **API Metrics** | http://localhost:8000/metrics | N/A |
| **Worker Metrics** | http://localhost:8001/metrics | N/A |

## 📈 Pre-configured Dashboards

### 1. API Metrics Dashboard

**Path**: Thought Processor → API Metrics

**Panels**:
- **Request Rate**: HTTP requests per second by endpoint
- **Error Rate**: Percentage of 5xx errors
- **Response Time**: p95 and p99 latency percentiles
- **Status Codes**: Distribution of HTTP response codes
- **Process Metrics**: Memory usage and file descriptors

**Use Cases**:
- Monitor API health and performance
- Detect traffic spikes or anomalies
- Identify slow endpoints
- Track error rates

### 2. Kafka & Batch Processing Dashboard

**Path**: Thought Processor → Kafka & Batch Processing

**Panels**:
- **Active Consumers**: Number of Kafka consumer instances
- **Consumer Lag**: Messages waiting to be processed
- **Total Partitions**: Kafka topic partition count
- **Message Rate**: Messages per second by topic/partition
- **Batch Processor Metrics**: Thoughts processed, failed, cache hits
- **Cache Hit Rate**: Percentage of cached responses
- **Processing Duration**: p95/p99 processing time

**Use Cases**:
- Monitor Kafka health and throughput
- Detect consumer lag issues
- Track processing performance
- Optimize cache efficiency

### 3. Database & Cache Dashboard

**Path**: Thought Processor → Database & Cache

**Panels**:

**PostgreSQL**:
- **Database Status**: Connection health
- **Active Connections**: Current connection count
- **Database Size**: Total storage used
- **Transaction Rate**: Commits and rollbacks per second
- **Row Operations**: Fetches, inserts, updates, deletes
- **Cache Hit Ratio**: PostgreSQL buffer cache efficiency

**Redis**:
- **Redis Status**: Connection health
- **Redis Connections**: Active client connections
- **Redis Memory**: Memory usage
- **Redis Operations**: Commands per second

**Use Cases**:
- Monitor database health
- Detect connection leaks
- Track query performance
- Optimize cache configuration

## 🎯 Key Metrics Explained

### API Metrics

| Metric | Description | Good Value | Alert On |
|--------|-------------|------------|----------|
| `http_requests_total` | Total HTTP requests | Steady growth | Sudden spikes/drops |
| `http_request_duration_seconds` | Request latency | p95 < 1s | p95 > 2s |
| `http_requests_inprogress` | Concurrent requests | < 50 | > 100 |
| Error rate | 5xx errors / total | < 1% | > 5% |

### Batch Processor Metrics

| Metric | Description | Good Value | Alert On |
|--------|-------------|------------|----------|
| `batch_processor_thoughts_processed_total` | Successfully processed | Increasing | Stalled |
| `batch_processor_thoughts_failed_total` | Failed processing | Near zero | > 5% failure rate |
| `batch_processor_cache_hits_total` | Semantic cache hits | 20-40% | < 10% |
| `batch_processor_processing_duration_seconds` | Processing time | p95 < 30s | p95 > 60s |
| `batch_processor_active_workers` | Worker count | 3 (default) | < 1 |
| `batch_processor_queue_size` | Pending thoughts | < 100 | > 1000 |

### Kafka Metrics

| Metric | Description | Good Value | Alert On |
|--------|-------------|------------|----------|
| `kafka_consumergroup_members` | Active consumers | 3 (default) | < 1 |
| `kafka_consumergroup_lag` | Unprocessed messages | < 100 | > 1000 |
| `kafka_topic_partition_current_offset` | Total messages | Increasing | Stalled |

### Database Metrics

| Metric | Description | Good Value | Alert On |
|--------|-------------|------------|----------|
| `pg_up` | Database status | 1 | 0 |
| `pg_stat_activity_count` | Active connections | < 50 | > 80 |
| `pg_database_size_bytes` | Database size | < 5GB (free tier) | > 4GB |
| `pg_stat_database_xact_commit` | Commits/sec | Steady | Sudden drops |
| Cache hit ratio | Buffer cache hits | > 95% | < 90% |

### Redis Metrics

| Metric | Description | Good Value | Alert On |
|--------|-------------|------------|----------|
| `redis_up` | Redis status | 1 | 0 |
| `redis_connected_clients` | Active clients | < 20 | > 50 |
| `redis_memory_used_bytes` | Memory usage | < 100MB | > 500MB |
| `redis_commands_processed_total` | Commands/sec | Steady | Sudden spikes |

## 🔍 Log Aggregation with Loki

### Viewing Logs in Grafana

1. Open Grafana: http://localhost:3001
2. Navigate to **Explore**
3. Select **Loki** data source
4. Use LogQL to query logs

### Common Log Queries

**All API logs**:
```logql
{service="thoughtprocessor-api"}
```

**Error logs only**:
```logql
{service="thoughtprocessor-api"} |= "ERROR"
```

**Batch processor logs**:
```logql
{service="kafka-worker"}
```

**Logs for specific user**:
```logql
{service="thoughtprocessor-api"} |= "user_id=123abc"
```

**Rate of errors**:
```logql
sum(rate({service="thoughtprocessor-api"} |= "ERROR" [5m]))
```

### Log Retention

- **Duration**: 7 days (configurable in `config/loki-config.yml`)
- **Storage**: Local filesystem (`loki_data` volume)

## 🔗 Distributed Tracing with Tempo

Tempo is configured but requires application instrumentation for full tracing.

### Future Enhancements

To enable distributed tracing:

1. Install OpenTelemetry instrumentation:
```bash
pip install opentelemetry-api opentelemetry-sdk opentelemetry-instrumentation-fastapi
```

2. Configure in FastAPI app
3. Traces will automatically appear in Tempo
4. View in Grafana: Explore → Tempo

## ⚙️ Configuration

### Prometheus Configuration

Edit `config/prometheus.yml` to:
- Adjust scrape intervals
- Add new scrape targets
- Configure alerting rules

```yaml
scrape_configs:
  - job_name: 'my-service'
    static_configs:
      - targets: ['my-service:9090']
```

### Grafana Configuration

**Datasources**: `config/grafana/provisioning/datasources/datasources.yml`
**Dashboards**: `config/grafana/provisioning/dashboards/dashboards.yml`
**Dashboard JSONs**: `config/grafana/dashboards/`

### Loki Configuration

Edit `config/loki-config.yml` to:
- Change retention period
- Adjust ingestion limits
- Configure storage backend

### Adding Custom Metrics

**In FastAPI (api/main.py)**:
```python
from prometheus_client import Counter

my_counter = Counter('my_metric_total', 'Description')
my_counter.inc()
```

**In Batch Processor (batch_processor/processor.py)**:
```python
from prometheus_client import Histogram

my_histogram = Histogram('my_duration_seconds', 'Description')

with my_histogram.time():
    # Your code here
    pass
```

## 🚨 Alerting (Future)

### Setting Up Alerts

1. Create alert rules in `config/prometheus/rules/`
2. Configure Alertmanager in `docker-compose.yml`
3. Set up notification channels (email, Slack, PagerDuty)

### Example Alert Rule

```yaml
groups:
  - name: thoughtprocessor
    interval: 30s
    rules:
      - alert: HighErrorRate
        expr: |
          sum(rate(http_requests_total{status=~"5.."}[5m])) 
          / sum(rate(http_requests_total[5m])) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value | humanizePercentage }}"
```

## 📊 Custom Dashboards

### Creating New Dashboards

1. Open Grafana UI
2. Click **+** → **Dashboard**
3. Add panels with queries
4. Save dashboard
5. Export as JSON
6. Save to `config/grafana/dashboards/`

### Dashboard Best Practices

- Use consistent time ranges
- Group related metrics in rows
- Add descriptions to panels
- Use thresholds for visual alerts
- Include links between related dashboards

## 🐛 Troubleshooting

### Prometheus Not Scraping

**Check targets**: http://localhost:9090/targets

**Common issues**:
- Service not exposing metrics endpoint
- Network connectivity issues
- Incorrect port in `prometheus.yml`

**Solution**:
```bash
# Check if metrics endpoint responds
curl http://localhost:8000/metrics
curl http://localhost:8001/metrics
```

### Grafana Not Showing Data

**Check datasource**:
1. Grafana → Configuration → Data Sources
2. Click **Test** on Prometheus datasource

**Common issues**:
- Prometheus URL incorrect
- No data in selected time range
- Query syntax errors

**Solution**:
```bash
# Check Prometheus has data
curl http://localhost:9090/api/v1/query?query=up
```

### High Memory Usage

**Monitor resource usage**:
```bash
docker stats
```

**Reduce retention**:
- Prometheus: `--storage.tsdb.retention.time=7d`
- Loki: `retention_period: 168h`

### Loki Not Receiving Logs

**Check Promtail**:
```bash
docker logs thoughtprocessor-promtail
```

**Verify log files exist**:
```bash
docker exec thoughtprocessor-api ls -la /app/logs/
```

## 📱 Mobile/Production Considerations

### For Production Deployment

1. **Secure Grafana**:
   - Change default password
   - Enable HTTPS
   - Configure authentication (OAuth, LDAP)

2. **Data Retention**:
   - Adjust based on storage capacity
   - Archive old metrics if needed

3. **Resource Limits**:
   - Set memory/CPU limits in docker-compose
   - Monitor disk usage

4. **Backup**:
   - Backup Grafana dashboards regularly
   - Export dashboard JSONs to git

5. **External Access**:
   - Use reverse proxy (nginx, Traefik)
   - Enable authentication
   - Use HTTPS/TLS

### Example Production Config

```yaml
# docker-compose.yml
services:
  grafana:
    environment:
      - GF_SERVER_ROOT_URL=https://metrics.yourdomain.com
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
      - GF_AUTH_ANONYMOUS_ENABLED=false
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.5'
```

## 🔄 Updating Monitoring Stack

### Updating Docker Images

```bash
docker-compose --profile monitoring pull
docker-compose --profile monitoring up -d
```

### Updating Dashboards

1. Edit JSON files in `config/grafana/dashboards/`
2. Restart Grafana:
```bash
docker-compose restart grafana
```

Or use Grafana UI and export updated dashboards.

## 📚 Additional Resources

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [Loki Documentation](https://grafana.com/docs/loki/)
- [Tempo Documentation](https://grafana.com/docs/tempo/)
- [PromQL Basics](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [LogQL Basics](https://grafana.com/docs/loki/latest/logql/)

## 🎓 Learning Path

1. **Week 1**: Learn Prometheus basics and PromQL
2. **Week 2**: Create custom dashboards in Grafana
3. **Week 3**: Master Loki log queries
4. **Week 4**: Set up alerting and notifications
5. **Week 5**: Implement distributed tracing with Tempo

## 📞 Support

For issues or questions:
1. Check logs: `docker-compose logs <service-name>`
2. Review this documentation
3. Check Grafana/Prometheus documentation
4. Open an issue in the repository

---

**Version**: 1.0.0  
**Last Updated**: 2025-10-23  
**Maintained by**: Thought Processor Team
