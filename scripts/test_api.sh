#!/bin/bash
# API Testing Script

set -e

API_URL="${API_URL:-http://localhost:8000}"
USER_ID="a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"

echo "======================================"
echo "AI Thought Processor - API Test Suite"
echo "======================================"
echo ""
echo "API URL: $API_URL"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test 1: Health Check
echo -e "${YELLOW}Test 1: Health Check${NC}"
response=$(curl -s "$API_URL/health")
if echo "$response" | grep -q "healthy"; then
    echo -e "${GREEN}✓ Health check passed${NC}"
else
    echo -e "${RED}✗ Health check failed${NC}"
    echo "$response"
fi
echo ""

# Test 2: Create Thought
echo -e "${YELLOW}Test 2: Create Thought${NC}"
response=$(curl -s -X POST "$API_URL/thoughts" \
    -H "Content-Type: application/json" \
    -d "{
        \"text\": \"Test thought: Should I invest more time in learning AI?\",
        \"user_id\": \"$USER_ID\"
    }")

if echo "$response" | grep -q "pending"; then
    thought_id=$(echo "$response" | grep -o '"id":"[^"]*' | cut -d'"' -f4)
    echo -e "${GREEN}✓ Thought created: $thought_id${NC}"
else
    echo -e "${RED}✗ Failed to create thought${NC}"
    echo "$response"
fi
echo ""

# Test 3: Get Thoughts
echo -e "${YELLOW}Test 3: Get User Thoughts${NC}"
response=$(curl -s "$API_URL/thoughts/$USER_ID")
if echo "$response" | grep -q "thoughts"; then
    count=$(echo "$response" | grep -o '"count":[0-9]*' | cut -d':' -f2)
    echo -e "${GREEN}✓ Retrieved $count thoughts${NC}"
else
    echo -e "${RED}✗ Failed to get thoughts${NC}"
    echo "$response"
fi
echo ""

# Test 4: Get Specific Thought
if [ ! -z "$thought_id" ]; then
    echo -e "${YELLOW}Test 4: Get Specific Thought${NC}"
    response=$(curl -s "$API_URL/thoughts/$USER_ID/$thought_id")
    if echo "$response" | grep -q "status"; then
        echo -e "${GREEN}✓ Retrieved thought details${NC}"
    else
        echo -e "${RED}✗ Failed to get thought details${NC}"
        echo "$response"
    fi
    echo ""
fi

# Test 5: Get User Info
echo -e "${YELLOW}Test 5: Get User Info${NC}"
response=$(curl -s "$API_URL/users/$USER_ID")
if echo "$response" | grep -q "context"; then
    echo -e "${GREEN}✓ Retrieved user info${NC}"
else
    echo -e "${RED}✗ Failed to get user info${NC}"
    echo "$response"
fi
echo ""

# Test 6: Filter by Status
echo -e "${YELLOW}Test 6: Filter by Status (pending)${NC}"
response=$(curl -s "$API_URL/thoughts/$USER_ID?status=pending")
if echo "$response" | grep -q "thoughts"; then
    count=$(echo "$response" | grep -o '"count":[0-9]*' | cut -d':' -f2)
    echo -e "${GREEN}✓ Retrieved $count pending thoughts${NC}"
else
    echo -e "${RED}✗ Failed to filter thoughts${NC}"
    echo "$response"
fi
echo ""

# Test 7: API Documentation
echo -e "${YELLOW}Test 7: API Documentation${NC}"
status_code=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/docs")
if [ "$status_code" = "200" ]; then
    echo -e "${GREEN}✓ API docs accessible at $API_URL/docs${NC}"
else
    echo -e "${RED}✗ API docs not accessible${NC}"
fi
echo ""

echo "======================================"
echo "Test suite completed!"
echo "======================================"
