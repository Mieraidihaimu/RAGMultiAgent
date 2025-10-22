# Kafka Streaming Validation Guide

This guide will help you validate that the Kafka streaming workflow is working correctly before adding SSE frontend integration.

---

## 🎯 What We're Testing

1. **Kafka Infrastructure** - KRaft mode, 3 partitions, health checks
2. **Producer** - API publishes events to Kafka topic
3. **Consumer** - Workers consume events and process thoughts
4. **End-to-End Flow** - API → Kafka → Worker → Database → Results
5. **Partitioning** - User thoughts go to same partition (ordered processing)
6. **Error Handling** - Retry logic and Dead Letter Queue
7. **Redis SSE** - Workers publish progress updates to Redis

---

## 📋 Pre-Validation Checklist

### 1. Environment Setup

**Create `.env` file from template:**
```bash
cd /Users/mier/Documents/Projects/TrialPrototype/RAGMultiAgent
cp .env.example .env
```

**Edit `.env` and configure:**
```bash
# Enable Kafka
KAFKA_ENABLED=true
KAFKA_MODE=true

# Set your AI provider (choose one)
AI_PROVIDER=google  # or anthropic or openai
GOOGLE_API_KEY=your-key-here  # or ANTHROPIC_API_KEY or OPENAI_API_KEY

# Database (use local for testing)
POSTGRES_PASSWORD=changeme
DATABASE_URL=postgresql://thoughtprocessor:changeme@db:5432/thoughtprocessor

# Kafka & Redis (defaults should work)
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
REDIS_URL=redis://redis:6379
```

### 2. Install Dependencies

**Update Python dependencies:**
```bash
# In your local environment or container
pip install -r requirements.txt
```

**Key new dependencies:**
- `aiokafka==0.10.0`
- `redis==5.0.1`
- `aioredis==2.0.1`
- `sse-starlette==1.8.2`
- `prometheus-client==0.19.0`

---

## 🚀 Validation Steps

### Step 1: Start Infrastructure

**Start all services:**
```bash
docker compose up -d
```

**Verify services are healthy:**
```bash
docker compose ps
```

**Expected output:**
```
NAME                          STATUS
thoughtprocessor-api          Up (healthy)
thoughtprocessor-db           Up (healthy)
thoughtprocessor-frontend     Up
thoughtprocessor-kafka        Up (healthy)
thoughtprocessor-redis        Up (healthy)
thoughtprocessor-worker       Up
```

**Check logs for startup:**
```bash
# API logs - should see "Kafka producer initialized"
docker compose logs api | grep -i kafka

# Worker logs - should see "Starting in KAFKA STREAMING mode"
docker compose logs kafka-worker | grep -i "kafka\|starting"

# Kafka logs - should see broker started
docker compose logs kafka | grep -i "started"
```

---

### Step 2: Verify Kafka Topic Creation

**Access Kafka container:**
```bash
docker compose exec kafka bash
```

**List topics (should see `thought-processing` with 3 partitions):**
```bash
kafka-topics --bootstrap-server localhost:9092 --list
```

**Describe topic:**
```bash
kafka-topics --bootstrap-server localhost:9092 --describe --topic thought-processing
```

**Expected output:**
```
Topic: thought-processing    PartitionCount: 3    ReplicationFactor: 1
    Topic: thought-processing    Partition: 0    Leader: 1
    Topic: thought-processing    Partition: 1    Leader: 1
    Topic: thought-processing    Partition: 2    Leader: 1
```

**Exit Kafka container:**
```bash
exit
```

---

### Step 3: Test Health Endpoints

**Check API health:**
```bash
curl http://localhost:8000/health | python -m json.tool
```

**Expected output:**
```json
{
    "status": "healthy",
    "timestamp": "2025-10-22T...",
    "version": "1.0.0",
    "database": "connected"
}
```

**Check if Kafka is enabled in API:**
```bash
docker compose logs api | grep "Kafka streaming"
```

**Expected:** `Kafka streaming enabled`

---

### Step 4: Create Test User

**Insert test user into database:**
```bash
docker compose exec db psql -U thoughtprocessor -d thoughtprocessor -c "
INSERT INTO users (id, email, created_at, context)
VALUES (
    'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
    'test@example.com',
    NOW(),
    '{\"name\": \"Test User\", \"goals\": [\"Learn Kafka\"]}'::jsonb
)
ON CONFLICT (id) DO NOTHING;
"
```

**Verify user created:**
```bash
curl http://localhost:8000/users/a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11 | python -m json.tool
```

---

### Step 5: Test Kafka Producer (API → Kafka)

**Submit a thought via API:**
```bash
curl -X POST http://localhost:8000/thoughts \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Should I learn Kafka streaming?",
    "user_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"
  }' | python -m json.tool
```

**Expected response:**
```json
{
    "id": "...",
    "status": "pending",
    "message": "Thought saved! Processing started...",
    "created_at": "2025-10-22T..."
}
```

**Key indicator:** Message says "Processing started..." (not "analyzed tonight")

**Verify Kafka event published:**
```bash
docker compose logs api | tail -20 | grep "Published thought"
```

**Expected:** `Published thought <UUID> to Kafka`

---

### Step 6: Test Kafka Consumer (Kafka → Worker)

**Monitor worker logs in real-time:**
```bash
docker compose logs -f kafka-worker
```

**You should see:**
1. `Starting in KAFKA STREAMING mode`
2. `Kafka consumer started: kafka:9092`
3. `Received event: thought_created | thought_id=...`
4. `Processing thought <UUID> with AI pipeline`
5. `Agent 1/5`, `Agent 2/5`, ... `Agent 5/5` (progress updates)
6. `Published SSE update: thought_completed`
7. `Successfully processed: <UUID>`

**Stop following logs:** Press `Ctrl+C`

---

### Step 7: Verify Database Results

**Check thought status:**
```bash
curl "http://localhost:8000/thoughts/a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11?status=completed" | python -m json.tool
```

**Expected:** Status should be `"completed"` with full analysis (classification, analysis, value_impact, action_plan, priority)

**Or check database directly:**
```bash
docker compose exec db psql -U thoughtprocessor -d thoughtprocessor -c "
SELECT id, status, created_at, processed_at
FROM thoughts
WHERE user_id = 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11'
ORDER BY created_at DESC
LIMIT 1;
"
```

---

### Step 8: Test Partitioning (Multiple Users)

**Create 3 thoughts from different users:**
```bash
# User 1
curl -X POST http://localhost:8000/thoughts \
  -H "Content-Type: application/json" \
  -d '{"text": "Test from user 1", "user_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"}'

# User 2 (create this user first or use existing)
curl -X POST http://localhost:8000/thoughts \
  -H "Content-Type: application/json" \
  -d '{"text": "Test from user 2", "user_id": "b1ffbc99-9c0b-4ef8-bb6d-6bb9bd380a22"}'

# User 3
curl -X POST http://localhost:8000/thoughts \
  -H "Content-Type: application/json" \
  -d '{"text": "Test from user 3", "user_id": "c2ffbc99-9c0b-4ef8-bb6d-6bb9bd380a33"}'
```

**Check which partition each went to:**
```bash
docker compose exec kafka bash
kafka-console-consumer --bootstrap-server localhost:9092 \
  --topic thought-processing \
  --from-beginning \
  --property print.key=true \
  --property print.partition=true \
  --timeout-ms 5000
```

**Expected:** Same user_id always goes to same partition (ordered processing guaranteed)

---

### Step 9: Test Redis SSE Broadcasting

**Monitor Redis pub/sub activity:**
```bash
docker compose exec redis redis-cli MONITOR
```

**Submit a thought (in another terminal):**
```bash
curl -X POST http://localhost:8000/thoughts \
  -H "Content-Type: application/json" \
  -d '{"text": "Testing Redis SSE", "user_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"}'
```

**In Redis MONITOR, you should see:**
```
"PUBLISH" "thought_updates:a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11" "{...}"
```

**Stop monitoring:** Press `Ctrl+C`

---

### Step 10: Test Error Handling & DLQ

**Submit invalid thought (triggers error):**
```bash
# Submitting to non-existent user
curl -X POST http://localhost:8000/thoughts \
  -H "Content-Type: application/json" \
  -d '{"text": "This should fail", "user_id": "00000000-0000-0000-0000-000000000000"}'
```

**Check worker logs for retry attempts:**
```bash
docker compose logs kafka-worker | grep -i "retry\|failed\|dlq"
```

**Expected:** After 3 retries, thought should be sent to DLQ topic

**Verify DLQ topic exists:**
```bash
docker compose exec kafka kafka-topics --bootstrap-server localhost:9092 --list | grep dlq
```

**Check DLQ messages:**
```bash
docker compose exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic thought-processing-dlq \
  --from-beginning \
  --timeout-ms 5000
```

---

## ✅ Success Criteria

Your Kafka workflow is healthy if:

1. ✅ **Infrastructure:** All services (kafka, redis, api, worker) are UP and healthy
2. ✅ **Topic:** `thought-processing` topic exists with 3 partitions
3. ✅ **Producer:** API publishes events to Kafka (logs show "Published thought")
4. ✅ **Consumer:** Worker consumes events (logs show "Received event: thought_created")
5. ✅ **Processing:** Thoughts go from `pending` → `processing` → `completed` in ~18-25 seconds
6. ✅ **Partitioning:** Same user_id always goes to same partition
7. ✅ **Redis:** Worker publishes progress updates to Redis channels
8. ✅ **Error Handling:** Failed thoughts retry 3 times then go to DLQ
9. ✅ **Performance:** Multiple thoughts can be processed in parallel (3 workers)

---

## 🐛 Troubleshooting

### Issue: Kafka won't start

**Symptoms:** `thoughtprocessor-kafka` status is "unhealthy" or restarting

**Solutions:**
1. Check if port 9092 is already in use: `lsof -i :9092`
2. Clear Kafka data: `docker compose down -v` then `docker compose up -d`
3. Check logs: `docker compose logs kafka`
4. Ensure sufficient memory (Kafka needs ~1GB)

### Issue: Worker not consuming messages

**Symptoms:** Thoughts stay in `pending` status, worker logs show no activity

**Solutions:**
1. Verify `KAFKA_MODE=true` in `.env`
2. Check worker logs: `docker compose logs kafka-worker`
3. Verify Kafka is reachable from worker: `docker compose exec kafka-worker ping kafka`
4. Restart worker: `docker compose restart kafka-worker`

### Issue: "Kafka streaming disabled" in API logs

**Symptoms:** API doesn't publish to Kafka, falls back to batch mode

**Solutions:**
1. Set `KAFKA_ENABLED=true` in `.env`
2. Verify dependencies installed: `pip list | grep aiokafka`
3. Restart API: `docker compose restart api`
4. Check API logs: `docker compose logs api | grep -i kafka`

### Issue: Redis connection failed

**Symptoms:** Worker logs show "Failed to connect to Redis"

**Solutions:**
1. Verify Redis is running: `docker compose ps redis`
2. Test connection: `docker compose exec redis redis-cli ping`
3. Check REDIS_URL in `.env`: should be `redis://redis:6379`
4. Restart Redis: `docker compose restart redis`

### Issue: Thoughts processed but no progress updates

**Symptoms:** Processing completes, but no SSE events in Redis

**Solutions:**
1. This is expected behavior for now (SSE frontend not yet implemented)
2. Verify Redis pub/sub activity: `docker compose exec redis redis-cli MONITOR`
3. Events are being published, just no frontend to consume them yet

---

## 📊 Performance Benchmarks

**Expected performance (with 3 workers, Google Gemini):**

| Metric | Target | How to Measure |
|--------|--------|----------------|
| **Throughput** | 180 thoughts/min | Submit 10 thoughts, measure total time |
| **Latency (P50)** | < 20 seconds | Single thought, pending → completed |
| **Latency (P95)** | < 40 seconds | 10 thoughts, check slowest |
| **Partition Balance** | 33% each | Submit 30 thoughts from 30 users, check partition distribution |
| **Cache Hit Rate** | 0-30% (first run) | Check worker logs: "Cache hit rate: X%" |
| **Worker Utilization** | 60-80% | Monitor during 10 concurrent thoughts |

**Test throughput:**
```bash
# Submit 10 thoughts rapidly
for i in {1..10}; do
  curl -X POST http://localhost:8000/thoughts \
    -H "Content-Type: application/json" \
    -d "{\"text\": \"Throughput test $i\", \"user_id\": \"a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11\"}" &
done

# Wait for all to complete
wait

# Check how long it took in worker logs
docker compose logs kafka-worker | grep "processed"
```

---

## 🎯 Next Steps After Validation

Once all tests pass:

1. ✅ **Kafka workflow validated** - Ready for SSE frontend
2. **Add SSE endpoint** to `api/main.py` - `GET /thoughts/stream/{user_id}`
3. **Create frontend SSE client** - `frontend/sse-client.js`
4. **Update frontend HTML** - Live progress UI (Agent 1/5, 2/5, etc.)
5. **End-to-end demo** - Submit thought → Watch live progress → See results

---

## 📝 Validation Checklist

Use this checklist to track your validation progress:

- [ ] Step 1: All services started and healthy
- [ ] Step 2: Kafka topic created with 3 partitions
- [ ] Step 3: Health endpoints responding
- [ ] Step 4: Test user created
- [ ] Step 5: Kafka producer publishes events
- [ ] Step 6: Kafka consumer processes events
- [ ] Step 7: Database shows completed thoughts with analysis
- [ ] Step 8: Partitioning works (same user → same partition)
- [ ] Step 9: Redis SSE broadcasting works
- [ ] Step 10: Error handling and DLQ tested
- [ ] Performance benchmarks acceptable

**Once all checkboxes are ticked, Kafka workflow is validated! 🎉**

---

## 💾 Save Validation Results

Create a validation report:
```bash
cat > KAFKA_VALIDATION_RESULTS.md << 'EOF'
# Kafka Validation Results

**Date:** $(date)
**Tester:** [Your Name]
**Environment:** Local Docker

## Test Results

### Infrastructure
- [ ] PASS / [ ] FAIL - All services healthy
- Notes:

### Producer
- [ ] PASS / [ ] FAIL - Events published to Kafka
- Notes:

### Consumer
- [ ] PASS / [ ] FAIL - Events consumed and processed
- Notes:

### End-to-End
- [ ] PASS / [ ] FAIL - Thoughts complete successfully
- Notes:

### Performance
- Throughput: ___ thoughts/min
- Latency (avg): ___ seconds
- Cache hit rate: ___%

### Issues Found
1.
2.

### Conclusion
[ ] ✅ Ready for SSE frontend integration
[ ] ❌ Needs fixes before proceeding

EOF
```

---

**Good luck with validation! 🚀**

If you encounter any issues not covered here, check:
- Docker logs: `docker compose logs <service>`
- Kafka logs: `docker compose logs kafka`
- Worker logs: `docker compose logs kafka-worker -f`
- API logs: `docker compose logs api -f`
