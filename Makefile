# Makefile for AI Thought Processor

.PHONY: help setup up down restart logs test-api run-batch clean

# Default target
help:
	@echo "AI Thought Processor - Available Commands"
	@echo ""
	@echo "Setup & Control:"
	@echo "  make setup        - Initial setup (create .env, start services)"
	@echo "  make up           - Start all services"
	@echo "  make down         - Stop all services"
	@echo "  make restart      - Restart all services"
	@echo ""
	@echo "Operations:"
	@echo "  make logs         - View logs (all services)"
	@echo "  make logs-api     - View API logs"
	@echo "  make logs-batch   - View batch processor logs"
	@echo "  make logs-db      - View database logs"
	@echo ""
	@echo "Testing & Running:"
	@echo "  make test-api     - Test API endpoints"
	@echo "  make run-batch    - Run batch processor manually"
	@echo "  make load-sample  - Load sample data"
	@echo ""
	@echo "Database:"
	@echo "  make db-shell     - Open PostgreSQL shell"
	@echo "  make db-migrate   - Run database migrations"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean        - Remove containers and volumes"
	@echo "  make rebuild      - Rebuild and restart all services"
	@echo ""

# Setup
setup:
	@./scripts/setup.sh

# Start services
up:
	@echo "Starting services..."
	@docker compose up -d
	@echo "Services started!"
	@echo "API: http://localhost:8000"
	@echo "Docs: http://localhost:8000/docs"

# Stop services
down:
	@echo "Stopping services..."
	@docker compose down

# Restart services
restart:
	@echo "Restarting services..."
	@docker compose restart
	@echo "Services restarted!"

# View logs
logs:
	@docker compose logs -f

logs-api:
	@docker compose logs -f api

logs-batch:
	@docker compose logs -f batch-processor

logs-db:
	@docker compose logs -f db

# Test API
test-api:
	@./scripts/test_api.sh

# Run batch processor
run-batch:
	@./scripts/run_batch.sh

# Load sample data
load-sample:
	@echo "Loading sample data..."
	@docker compose exec db psql -U thoughtprocessor -d thoughtprocessor -f /docker-entrypoint-initdb.d/seeds/001_sample_user.sql
	@echo "Sample data loaded!"

# Database shell
db-shell:
	@docker compose exec db psql -U thoughtprocessor -d thoughtprocessor

# Run migrations
db-migrate:
	@echo "Running migrations..."
	@docker compose exec db psql -U thoughtprocessor -d thoughtprocessor -f /docker-entrypoint-initdb.d/migrations/001_initial_schema.sql
	@echo "Migrations complete!"

# Clean up
clean:
	@echo "WARNING: This will remove all containers and volumes!"
	@read -p "Are you sure? (y/N) " -n 1 -r; \
	echo ""; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker compose down -v; \
		echo "Cleanup complete!"; \
	else \
		echo "Cancelled."; \
	fi

# Rebuild
rebuild:
	@echo "Rebuilding services..."
	@docker compose down
	@docker compose build --no-cache
	@docker compose up -d
	@echo "Rebuild complete!"

# Check status
status:
	@docker compose ps

# Health check
health:
	@echo "Checking service health..."
	@curl -s http://localhost:8000/health | python -m json.tool || echo "API not responding"
