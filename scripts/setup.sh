#!/bin/bash
# Quick setup script

set -e

echo "======================================"
echo "AI Thought Processor - Quick Setup"
echo "======================================"
echo ""

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker Desktop."
    exit 1
fi
echo "✓ Docker found"

# Check Docker Compose
if ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose not found. Please install Docker Compose."
    exit 1
fi
echo "✓ Docker Compose found"

# Create .env if not exists
if [ ! -f .env ]; then
    echo ""
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "✓ Created .env file"
    echo ""
    echo "⚠️  IMPORTANT: Edit .env and add your API keys:"
    echo "   - ANTHROPIC_API_KEY"
    echo "   - OPENAI_API_KEY"
    echo "   - SUPABASE_URL and SUPABASE_KEY (or use local PostgreSQL)"
    echo ""
    read -p "Press Enter when you've configured .env..."
else
    echo "✓ .env file exists"
fi

# Create necessary directories
mkdir -p scripts logs api/logs batch_processor/logs
echo "✓ Created directories"

# Start Docker services
echo ""
echo "Starting Docker services..."
docker compose up -d

echo ""
echo "Waiting for services to be ready..."
sleep 10

# Check services
echo ""
echo "Checking service status..."
docker compose ps

# Test API
echo ""
echo "Testing API health..."
max_attempts=30
attempt=1
while [ $attempt -le $max_attempts ]; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "✓ API is healthy"
        break
    fi
    echo "Waiting for API... (attempt $attempt/$max_attempts)"
    sleep 2
    attempt=$((attempt + 1))
done

if [ $attempt -gt $max_attempts ]; then
    echo "❌ API did not become healthy in time"
    echo "Check logs: docker compose logs api"
    exit 1
fi

echo ""
echo "======================================"
echo "Setup Complete! 🎉"
echo "======================================"
echo ""
echo "Next steps:"
echo ""
echo "1. API is running at: http://localhost:8000"
echo "   Documentation: http://localhost:8000/docs"
echo ""
echo "2. Load sample data:"
echo "   docker compose exec db psql -U thoughtprocessor -d thoughtprocessor -f /docker-entrypoint-initdb.d/seeds/001_sample_user.sql"
echo ""
echo "3. Test the API:"
echo "   ./scripts/test_api.sh"
echo ""
echo "4. Run batch processor:"
echo "   ./scripts/run_batch.sh"
echo ""
echo "5. View logs:"
echo "   docker compose logs -f"
echo ""
echo "To stop: docker compose down"
echo "To restart: docker compose restart"
echo ""
