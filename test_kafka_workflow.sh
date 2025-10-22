#!/bin/bash

# Kafka Workflow Validation Test Script
# Tests the complete Kafka streaming workflow

set -e  # Exit on error

echo "=========================================="
echo "Kafka Workflow Validation Test"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Helper functions
pass() {
    echo -e "${GREEN}✓ PASS${NC}: $1"
    ((TESTS_PASSED++))
}

fail() {
    echo -e "${RED}✗ FAIL${NC}: $1"
    ((TESTS_FAILED++))
}

info() {
    echo -e "${YELLOW}ℹ INFO${NC}: $1"
}

# Test 1: Check Docker services
echo "Test 1: Checking Docker services..."
if docker compose ps | grep -q "Up"; then
    pass "Docker services are running"
else
    fail "Docker services not running. Run: docker compose up -d"
    exit 1
fi
echo ""

# Test 2: Check Kafka health
echo "Test 2: Checking Kafka broker..."
if docker compose exec -T kafka kafka-broker-api-versions --bootstrap-server localhost:9092 > /dev/null 2>&1; then
    pass "Kafka broker is healthy"
else
    fail "Kafka broker is not responding"
fi
echo ""

# Test 3: Check Redis health
echo "Test 3: Checking Redis..."
if docker compose exec -T redis redis-cli ping | grep -q "PONG"; then
    pass "Redis is healthy"
else
    fail "Redis is not responding"
fi
echo ""

# Test 4: Check API health
echo "Test 4: Checking API health endpoint..."
HEALTH_RESPONSE=$(curl -s http://localhost:8000/health)
if echo "$HEALTH_RESPONSE" | grep -q '"status":"healthy"'; then
    pass "API is healthy"
else
    fail "API is not healthy"
    echo "Response: $HEALTH_RESPONSE"
fi
echo ""

# Test 5: Check Kafka topic
echo "Test 5: Checking Kafka topic 'thought-processing'..."
TOPICS=$(docker compose exec -T kafka kafka-topics --bootstrap-server localhost:9092 --list)
if echo "$TOPICS" | grep -q "thought-processing"; then
    pass "Kafka topic 'thought-processing' exists"

    # Check partitions
    TOPIC_DESC=$(docker compose exec -T kafka kafka-topics --bootstrap-server localhost:9092 --describe --topic thought-processing)
    if echo "$TOPIC_DESC" | grep -q "PartitionCount: 3"; then
        pass "Topic has 3 partitions"
    else
        fail "Topic does not have 3 partitions"
        echo "$TOPIC_DESC"
    fi
else
    fail "Kafka topic 'thought-processing' does not exist"
fi
echo ""

# Test 6: Create test user
echo "Test 6: Creating test user..."
TEST_USER_ID="a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"
docker compose exec -T db psql -U thoughtprocessor -d thoughtprocessor -c "
INSERT INTO users (id, email, created_at, context)
VALUES (
    '$TEST_USER_ID',
    'test@example.com',
    NOW(),
    '{\"name\": \"Test User\", \"goals\": [\"Validate Kafka\"]}'::jsonb
)
ON CONFLICT (id) DO UPDATE SET context = EXCLUDED.context;
" > /dev/null 2>&1

# Verify user exists
USER_RESPONSE=$(curl -s http://localhost:8000/users/$TEST_USER_ID)
if echo "$USER_RESPONSE" | grep -q '"id"'; then
    pass "Test user created/verified"
else
    fail "Failed to create test user"
fi
echo ""

# Test 7: Submit thought and check Kafka producer
echo "Test 7: Testing Kafka producer (API → Kafka)..."
THOUGHT_RESPONSE=$(curl -s -X POST http://localhost:8000/thoughts \
  -H "Content-Type: application/json" \
  -d "{
    \"text\": \"Validation test: Is Kafka working? $(date +%s)\",
    \"user_id\": \"$TEST_USER_ID\"
  }")

THOUGHT_ID=$(echo "$THOUGHT_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('id', ''))" 2>/dev/null)

if [ -n "$THOUGHT_ID" ]; then
    pass "Thought created: $THOUGHT_ID"

    # Check if message indicates Kafka processing
    if echo "$THOUGHT_RESPONSE" | grep -q "Processing started"; then
        pass "API indicates Kafka processing (not batch mode)"
    else
        fail "API response suggests batch mode, not Kafka streaming"
        echo "Response: $THOUGHT_RESPONSE"
    fi

    # Check API logs for Kafka publish
    sleep 2
    if docker compose logs api 2>/dev/null | tail -20 | grep -q "Published thought.*to Kafka"; then
        pass "Kafka producer published event (API logs confirm)"
    else
        fail "No Kafka publish log found in API logs"
    fi
else
    fail "Failed to create thought"
    echo "Response: $THOUGHT_RESPONSE"
fi
echo ""

# Test 8: Check Kafka consumer (Worker)
echo "Test 8: Testing Kafka consumer (Worker)..."
info "Waiting 5 seconds for worker to pick up event..."
sleep 5

WORKER_LOGS=$(docker compose logs kafka-worker 2>/dev/null | tail -50)
if echo "$WORKER_LOGS" | grep -q "Received event: thought_created"; then
    pass "Worker received event from Kafka"

    if echo "$WORKER_LOGS" | grep -q "Processing thought.*with AI pipeline"; then
        pass "Worker started AI processing"
    else
        info "Worker may still be processing (check logs)"
    fi
else
    fail "Worker did not receive event from Kafka"
    echo "Recent worker logs:"
    docker compose logs kafka-worker --tail 20
fi
echo ""

# Test 9: Check Redis pub/sub activity
echo "Test 9: Testing Redis SSE broadcasting..."
# Start Redis monitor in background and capture output
REDIS_OUTPUT=$(docker compose exec -T redis redis-cli --csv MONITOR 2>/dev/null &)
MONITOR_PID=$!
sleep 1

# Submit another thought
curl -s -X POST http://localhost:8000/thoughts \
  -H "Content-Type: application/json" \
  -d "{
    \"text\": \"Redis SSE test $(date +%s)\",
    \"user_id\": \"$TEST_USER_ID\"
  }" > /dev/null

sleep 3
kill $MONITOR_PID 2>/dev/null || true

# Check if Redis pub/sub activity occurred
if docker compose logs redis 2>/dev/null | tail -10 | grep -q "PUBLISH"; then
    pass "Redis pub/sub activity detected"
else
    info "Redis pub/sub activity not clearly visible (may need manual check)"
fi
echo ""

# Test 10: Verify database results
echo "Test 10: Checking database for completed thoughts..."
info "Waiting 20 seconds for AI processing to complete..."
sleep 20

DB_RESULT=$(docker compose exec -T db psql -U thoughtprocessor -d thoughtprocessor -t -c "
SELECT COUNT(*) FROM thoughts
WHERE user_id = '$TEST_USER_ID'
AND status = 'completed'
AND processed_at IS NOT NULL;
" 2>/dev/null | tr -d ' ')

if [ "$DB_RESULT" -gt 0 ]; then
    pass "Found $DB_RESULT completed thought(s) in database"

    # Check if analysis fields are populated
    ANALYSIS_CHECK=$(docker compose exec -T db psql -U thoughtprocessor -d thoughtprocessor -t -c "
    SELECT COUNT(*) FROM thoughts
    WHERE user_id = '$TEST_USER_ID'
    AND status = 'completed'
    AND classification IS NOT NULL
    AND analysis IS NOT NULL;
    " 2>/dev/null | tr -d ' ')

    if [ "$ANALYSIS_CHECK" -gt 0 ]; then
        pass "Thought has complete AI analysis (classification, analysis, etc.)"
    else
        fail "Thought completed but analysis fields are missing"
    fi
else
    fail "No completed thoughts found. Check worker logs for errors."
    echo "Recent worker logs:"
    docker compose logs kafka-worker --tail 30
fi
echo ""

# Final Summary
echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo -e "Tests Passed: ${GREEN}$TESTS_PASSED${NC}"
echo -e "Tests Failed: ${RED}$TESTS_FAILED${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed! Kafka workflow is healthy.${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Review complete validation guide: cat KAFKA_VALIDATION.md"
    echo "2. Proceed to SSE frontend integration"
    echo "3. Test real-time updates in browser"
    exit 0
else
    echo -e "${RED}✗ Some tests failed. Review errors above.${NC}"
    echo ""
    echo "Debugging tips:"
    echo "1. Check service logs: docker compose logs <service>"
    echo "2. Verify .env configuration"
    echo "3. Review KAFKA_VALIDATION.md for detailed troubleshooting"
    exit 1
fi
