#!/bin/bash
# Quick start script for local Docker + PostgreSQL + Google Gemini

set -e

echo "======================================"
echo "🚀 Starting AI Thought Processor"
echo "   Database: PostgreSQL (Docker)"
echo "   AI: Google Gemini"
echo "======================================"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  .env file not found!${NC}"
    echo ""
    echo "Creating .env from template..."

    # Check if user has already configured .env
    if [ -f .env.local.example ]; then
        cp .env.local.example .env
        echo -e "${GREEN}✓ Created .env from .env.local.example${NC}"
    else
        cp .env.example .env
        echo -e "${GREEN}✓ Created .env from .env.example${NC}"
    fi

    echo ""
    echo -e "${YELLOW}⚠️  IMPORTANT: Edit .env and add your API keys!${NC}"
    echo ""
    echo "Required keys:"
    echo "  1. GOOGLE_API_KEY=your-google-api-key"
    echo "  2. OPENAI_API_KEY=your-openai-key (for embeddings)"
    echo ""
    read -p "Press Enter after you've edited .env with your keys..."
fi

# Verify API keys are set
source .env

if [ -z "$GOOGLE_API_KEY" ] || [ "$GOOGLE_API_KEY" = "YOUR_GOOGLE_API_KEY_HERE" ]; then
    echo -e "${RED}❌ GOOGLE_API_KEY not set in .env${NC}"
    echo "Please edit .env and add your Google API key"
    exit 1
fi

if [ -z "$OPENAI_API_KEY" ] || [ "$OPENAI_API_KEY" = "YOUR_OPENAI_KEY_HERE" ]; then
    echo -e "${RED}❌ OPENAI_API_KEY not set in .env${NC}"
    echo "Please edit .env and add your OpenAI API key (needed for embeddings)"
    exit 1
fi

# Check if SUPABASE_URL is empty (to use local PostgreSQL)
if [ ! -z "$SUPABASE_URL" ]; then
    echo -e "${YELLOW}⚠️  SUPABASE_URL is set in .env${NC}"
    echo "To use local PostgreSQL, comment out or remove SUPABASE_URL"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo -e "${GREEN}✓ API keys configured${NC}"
echo ""

# Stop any running containers
echo "Stopping any running containers..."
docker-compose down 2>/dev/null || true
echo ""

# Build and start services
echo "Building and starting services..."
echo ""
docker-compose up -d --build

echo ""
echo "Waiting for services to start..."
sleep 10

# Check service status
echo ""
echo "======================================"
echo "Service Status:"
echo "======================================"
docker-compose ps

# Wait for database to be ready
echo ""
echo "Waiting for PostgreSQL to be ready..."
max_attempts=30
attempt=1
while [ $attempt -le $max_attempts ]; do
    if docker-compose exec -T db pg_isready -U thoughtprocessor > /dev/null 2>&1; then
        echo -e "${GREEN}✓ PostgreSQL is ready!${NC}"
        break
    fi
    echo "  Attempt $attempt/$max_attempts..."
    sleep 2
    attempt=$((attempt + 1))
done

if [ $attempt -gt $max_attempts ]; then
    echo -e "${RED}❌ PostgreSQL failed to start${NC}"
    docker-compose logs db
    exit 1
fi

# Load sample data
echo ""
echo "Loading sample data..."
docker-compose exec -T db psql -U thoughtprocessor -d thoughtprocessor -f /docker-entrypoint-initdb.d/seeds/001_sample_user.sql > /dev/null 2>&1 || true

# Test API
echo ""
echo "Testing API..."
sleep 3
max_attempts=30
attempt=1
while [ $attempt -le $max_attempts ]; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ API is healthy!${NC}"
        break
    fi
    echo "  Attempt $attempt/$max_attempts..."
    sleep 2
    attempt=$((attempt + 1))
done

if [ $attempt -gt $max_attempts ]; then
    echo -e "${RED}❌ API failed to start${NC}"
    docker-compose logs api
    exit 1
fi

echo ""
echo "======================================"
echo -e "${GREEN}🎉 System is ready!${NC}"
echo "======================================"
echo ""
echo "📊 Services:"
echo "  • API:        http://localhost:8000"
echo "  • API Docs:   http://localhost:8000/docs"
echo "  • PostgreSQL: localhost:5432"
echo ""
echo "🔑 Demo User:"
echo "  • ID:    a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"
echo "  • Email: demo@example.com"
echo ""
echo "🧪 Quick Tests:"
echo "  • Health:  curl http://localhost:8000/health"
echo "  • Test:    ./scripts/test_api.sh"
echo "  • Process: docker-compose exec batch-processor python processor.py"
echo ""
echo "📝 View Logs:"
echo "  • All:     docker-compose logs -f"
echo "  • API:     docker-compose logs -f api"
echo "  • Batch:   docker-compose logs -f batch-processor"
echo "  • DB:      docker-compose logs -f db"
echo ""
echo "🛑 Stop:"
echo "  • docker-compose down"
echo ""
echo "======================================"
echo -e "${GREEN}Happy thought processing! 🧠✨${NC}"
echo "======================================"
