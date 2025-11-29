# 📊 Monitoring Quick Reference

## 🚀 Start Monitoring

```bash
# Quick start (recommended)
./start_monitoring.sh

# Or manually
docker-compose --profile monitoring up -d

# Stop monitoring
docker-compose --profile monitoring down
```

## 🌐 Access URLs

| Service | URL | Default Login |
|---------|-----|---------------|
| **Grafana** | http://localhost:3001 | admin / admin |
| **Prometheus** | http://localhost:9090 | - |
| **Loki** | http://localhost:3100 | - |
| **Tempo** | http://localhost:3200 | - |
| **API Metrics** | http://localhost:8000/metrics | - |
| **Worker Metrics** | http://localhost:8001/metrics | - |

## 📈 Grafana Dashboards

Navigate to: **Dashboards** → **Thought Processor**

1. **API Metrics** - Request rates, latency, errors
2. **Kafka & Batch Processing** - Consumer lag, throughput, cache hits
3. **Database & Cache** - PostgreSQL and Redis health

## 🔍 Common Log Queries (Loki)

Access: **Explore** → Select **Loki**

```logql
# All API logs
{service="thoughtprocessor-api"}

# API errors only
{service="thoughtprocessor-api"} |= "ERROR"

# Batch processor logs
{service="kafka-worker"}

# Logs for specific user
{service="thoughtprocessor-api"} |= "user_id=YOUR_USER_ID"

# Error rate (last 5min)
sum(rate({service="thoughtprocessor-api"} |= "ERROR" [5m]))
```

## 📊 Key Metrics

### API Health
```promql
# Request rate
rate(http_requests_total[5m])

# Error rate
sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))

# Response time (p95)
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
```

### Batch Processing
```promql
# Thoughts processed
batch_processor_thoughts_processed_total

# Cache hit rate
batch_processor_cache_hits_total / (batch_processor_cache_hits_total + batch_processor_cache_misses_total)

# Processing duration (p95)
histogram_quantile(0.95, rate(batch_processor_processing_duration_seconds_bucket[5m]))
```

### Kafka
```promql
# Consumer lag
kafka_consumergroup_lag

# Active consumers
kafka_consumergroup_members

# Message rate
rate(kafka_topic_partition_current_offset[5m])
```

### Database
```promql
# Active connections
pg_stat_activity_count

# Transaction rate
rate(pg_stat_database_xact_commit[5m])

# Cache hit ratio
rate(pg_stat_database_blks_hit[5m]) / (rate(pg_stat_database_blks_hit[5m]) + rate(pg_stat_database_blks_read[5m]))
```

## 🚨 Alert Thresholds

| Metric | Warning | Critical |
|--------|---------|----------|
| API Error Rate | > 1% | > 5% |
| Consumer Lag | > 100 | > 1000 |
| Response Time p95 | > 1s | > 2s |
| Cache Hit Rate | < 20% | < 10% |
| DB Connections | > 50 | > 80 |
| Processing Duration p95 | > 30s | > 60s |

## 🔧 Troubleshooting

### No Data in Grafana?
1. Check datasource: **Configuration** → **Data Sources** → **Test**
2. Check Prometheus targets: http://localhost:9090/targets
3. Check time range (last 1 hour recommended)

### Prometheus Not Scraping?
```bash
# Check if metrics endpoint works
curl http://localhost:8000/metrics
curl http://localhost:8001/metrics

# Check Prometheus logs
docker logs thoughtprocessor-prometheus
```

### Loki No Logs?
```bash
# Check Promtail logs
docker logs thoughtprocessor-promtail

# Check log files exist
docker exec thoughtprocessor-api ls -la /app/logs/
```

### High Memory Usage?
```bash
# Check container stats
docker stats

# Reduce retention if needed
# Edit config/prometheus.yml or config/loki-config.yml
```

## 📚 Documentation

- **Full Guide**: [MONITORING.md](MONITORING.md)
- **Implementation Summary**: [MONITORING_SUMMARY.md](MONITORING_SUMMARY.md)
- **Main README**: [README.md](README.md)

## 💡 Pro Tips

1. **First Login**: Change Grafana password immediately
2. **Explore Mode**: Great for ad-hoc queries
3. **Time Range**: Use "Last 1 hour" for recent activity
4. **Refresh**: Set to 10s for live monitoring
5. **Save**: Export dashboards after customization
6. **Alerts**: Set up Alertmanager for notifications

## 🎯 Next Steps

1. ✅ Start monitoring stack
2. ✅ Login to Grafana
3. ✅ Explore pre-built dashboards
4. ⏳ Customize for your needs
5. ⏳ Set up alerting
6. ⏳ Enable distributed tracing

---

**Quick Help**: For detailed information, see [MONITORING.md](MONITORING.md)
