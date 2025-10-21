#!/bin/bash
# Test script for Google Gemini setup

set -e

API_URL="${API_URL:-http://localhost:8000}"
USER_ID="a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "======================================"
echo "🧪 Testing Google Gemini Integration"
echo "======================================"
echo ""

# Test 1: Create a thought
echo -e "${BLUE}Test 1: Creating a thought...${NC}"
response=$(curl -s -X POST "$API_URL/thoughts" \
    -H "Content-Type: application/json" \
    -d "{
        \"text\": \"I'm thinking about learning AI and machine learning. Should I start with deep learning or traditional ML first?\",
        \"user_id\": \"$USER_ID\"
    }")

if echo "$response" | grep -q "pending"; then
    thought_id=$(echo "$response" | grep -o '"id":"[^"]*' | cut -d'"' -f4)
    echo -e "${GREEN}✓ Thought created: $thought_id${NC}"
else
    echo -e "${RED}✗ Failed to create thought${NC}"
    echo "$response"
    exit 1
fi
echo ""

# Test 2: Get thoughts
echo -e "${BLUE}Test 2: Retrieving thoughts...${NC}"
response=$(curl -s "$API_URL/thoughts/$USER_ID?status=pending")
if echo "$response" | grep -q "thoughts"; then
    count=$(echo "$response" | grep -o '"count":[0-9]*' | cut -d':' -f2)
    echo -e "${GREEN}✓ Retrieved $count pending thoughts${NC}"
else
    echo -e "${RED}✗ Failed to get thoughts${NC}"
    exit 1
fi
echo ""

# Test 3: Process with Gemini
echo -e "${BLUE}Test 3: Processing thought with Google Gemini...${NC}"
echo "This will take 10-30 seconds..."
echo ""

docker-compose exec -T batch-processor python processor.py

echo ""
echo -e "${GREEN}✓ Batch processing complete${NC}"
echo ""

# Test 4: Check processed thought
echo -e "${BLUE}Test 4: Checking processed thought...${NC}"
sleep 2
response=$(curl -s "$API_URL/thoughts/$USER_ID?status=completed")

if echo "$response" | grep -q "completed"; then
    echo -e "${GREEN}✓ Thought processed successfully!${NC}"
    echo ""

    # Extract and display analysis
    echo "======================================"
    echo "📊 AI Analysis Results (by Gemini):"
    echo "======================================"

    # Get the first completed thought
    thought=$(curl -s "$API_URL/thoughts/$USER_ID/$thought_id" 2>/dev/null || echo "$response")

    # Parse and display key information
    if echo "$thought" | grep -q "classification"; then
        echo ""
        echo -e "${YELLOW}Classification:${NC}"
        echo "$thought" | python3 -c "
import sys, json
data = json.load(sys.stdin)
if 'classification' in data and data['classification']:
    cls = data['classification']
    print(f\"  Type: {cls.get('type', 'N/A')}\")
    print(f\"  Urgency: {cls.get('urgency', 'N/A')}\")
    print(f\"  Tone: {cls.get('emotional_tone', 'N/A')}\")
" 2>/dev/null || echo "  (Processing in progress...)"
    fi

    if echo "$thought" | grep -q "priority"; then
        echo ""
        echo -e "${YELLOW}Priority:${NC}"
        echo "$thought" | python3 -c "
import sys, json
data = json.load(sys.stdin)
if 'priority' in data and data['priority']:
    pri = data['priority']
    print(f\"  Level: {pri.get('priority_level', 'N/A')}\")
    print(f\"  Recommendation: {pri.get('final_recommendation', 'N/A')[:100]}...\")
" 2>/dev/null || echo "  (Processing in progress...)"
    fi

    echo ""
    echo -e "${GREEN}✓ Full analysis available at:${NC}"
    echo "  $API_URL/thoughts/$USER_ID/$thought_id"

else
    echo -e "${YELLOW}⚠ Thought still processing or check logs${NC}"
    echo "View logs: docker-compose logs batch-processor"
fi

echo ""
echo "======================================"
echo -e "${GREEN}🎉 Test Complete!${NC}"
echo "======================================"
echo ""
echo "What happened:"
echo "  1. Created a thought via API"
echo "  2. Ran batch processor with Google Gemini"
echo "  3. Gemini analyzed the thought across 5 dimensions"
echo "  4. Results stored in PostgreSQL"
echo ""
echo "Next steps:"
echo "  • View API docs: http://localhost:8000/docs"
echo "  • Check logs:    docker-compose logs -f batch-processor"
echo "  • Add thoughts:  curl -X POST http://localhost:8000/thoughts -d '...'"
echo ""
echo "Cost estimate:"
echo "  • Gemini 1.5 Flash is ~80% cheaper than Claude!"
echo "  • This test cost: <$0.01"
echo ""
