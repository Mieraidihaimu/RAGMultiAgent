#!/bin/bash
# Quick start script for monitoring stack

echo "🚀 Starting Thought Processor with Monitoring..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  Warning: .env file not found. Creating from example..."
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "✅ Created .env from .env.example"
    else
        echo "❌ Error: .env.example not found"
        exit 1
    fi
fi

# Start core services
echo ""
echo "📦 Starting core services..."
docker-compose up -d db redis kafka

# Wait for services to be healthy
echo ""
echo "⏳ Waiting for services to be healthy..."
sleep 10

# Start application services
echo ""
echo "🔧 Starting application services..."
docker-compose up -d api kafka-worker frontend

# Start monitoring stack
echo ""
echo "📊 Starting monitoring stack..."
docker-compose --profile monitoring up -d

# Wait a moment for everything to initialize
sleep 5

# Show status
echo ""
echo "✅ All services started!"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 MONITORING DASHBOARDS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  🎨 Grafana:     http://localhost:3001"
echo "     Username:    admin"
echo "     Password:    admin"
echo ""
echo "  📈 Prometheus:  http://localhost:9090"
echo ""
echo "  📝 Loki:        http://localhost:3100"
echo ""
echo "  🔍 Tempo:       http://localhost:3200"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🌐 APPLICATION SERVICES"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  🚀 API:         http://localhost:8000"
echo "  📚 API Docs:    http://localhost:8000/docs"
echo "  📊 API Metrics: http://localhost:8000/metrics"
echo ""
echo "  🎯 Frontend:    http://localhost:3000"
echo ""
echo "  🔧 Worker Metrics: http://localhost:8001/metrics"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔧 MANAGEMENT TOOLS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  🗄️  pgAdmin:    docker-compose --profile tools up -d pgadmin"
echo "                 http://localhost:5050"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📖 For more information, see MONITORING.md"
echo ""
echo "💡 Tip: First time in Grafana?"
echo "   1. Login with admin/admin"
echo "   2. Navigate to Dashboards → Thought Processor"
echo "   3. Explore the pre-configured dashboards!"
echo ""
echo "🛑 To stop all services:"
echo "   docker-compose --profile monitoring down"
echo ""
