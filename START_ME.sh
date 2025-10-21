#!/bin/bash
# Simple startup script for Google Gemini (no OpenAI needed!)

echo "======================================"
echo "🚀 Starting AI Thought Processor"
echo "   AI: Google Gemini (all-in-one!)"
echo "   DB: PostgreSQL (Docker)"
echo "======================================"
echo ""

# Stop any running containers
docker-compose down 2>/dev/null

# Start fresh
echo "Starting services..."
docker-compose up -d --build

echo ""
echo "Waiting for services to start..."
sleep 15

# Load sample data
echo "Loading sample data..."
docker-compose exec -T db psql -U thoughtprocessor -d thoughtprocessor \
  -f /docker-entrypoint-initdb.d/seeds/001_sample_user.sql 2>/dev/null || true

echo ""
echo "======================================"
echo "✅ System Ready!"
echo "======================================"
echo ""
echo "📊 Services:"
echo "  • API:      http://localhost:8000"
echo "  • Docs:     http://localhost:8000/docs"
echo "  • Database: PostgreSQL (Docker)"
echo ""
echo "🧪 Quick Test:"
echo "  curl http://localhost:8000/health"
echo ""
echo "🎯 Process Thoughts:"
echo "  docker-compose exec batch-processor python processor.py"
echo ""
echo "📝 View Logs:"
echo "  docker-compose logs -f"
echo ""
echo "======================================"
echo "🎉 Using Google Gemini for EVERYTHING!"
echo "   • AI Generation: Gemini 1.5 Flash"
echo "   • Embeddings: Google (FREE!)"
echo "   • No OpenAI needed!"
echo "======================================"
