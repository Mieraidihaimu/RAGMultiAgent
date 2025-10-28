#!/bin/bash
# ==============================================================================
# Deployment Script for EC2
# ==============================================================================
# This script automates the deployment process on an EC2 instance
#
# Usage:
#   chmod +x deploy.sh
#   ./deploy.sh
# ==============================================================================

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

# Configuration
APP_DIR="/opt/ragmultiagent"
BACKUP_DIR="/backups"
LOG_FILE="/var/log/ragmultiagent-deploy.log"

# Check if running as root or with sudo
if [ "$EUID" -ne 0 ]; then 
    error "Please run with sudo"
fi

# Create backup directory
mkdir -p $BACKUP_DIR

log "Starting deployment..." | tee -a $LOG_FILE

# Step 1: Backup current state
if [ -d "$APP_DIR" ]; then
    log "Creating backup..."
    BACKUP_NAME="backup_$(date +%Y%m%d_%H%M%S)"
    
    # Backup database
    docker-compose exec -T db pg_dump -U thoughtprocessor thoughtprocessor | \
        gzip > "$BACKUP_DIR/${BACKUP_NAME}_db.sql.gz" || \
        warn "Database backup failed"
    
    # Backup .env
    cp $APP_DIR/.env "$BACKUP_DIR/${BACKUP_NAME}_env" || warn "Env backup failed"
    
    log "Backup created: $BACKUP_NAME"
fi

# Step 2: Pull latest code
log "Pulling latest code..."
cd $APP_DIR || error "Application directory not found"

# Stash local changes
git stash || true

# Pull latest
git pull origin main || error "Git pull failed"

# Step 3: Update dependencies
log "Updating dependencies..."

# Rebuild Docker images
docker-compose build --no-cache || error "Docker build failed"

# Step 4: Database migrations (if any)
log "Running database migrations..."
# Add migration commands here if you have them

# Step 5: Stop old containers
log "Stopping old containers..."
docker-compose down || warn "Some containers failed to stop"

# Step 6: Start new containers
log "Starting new containers..."
docker-compose up -d || error "Failed to start containers"

# Step 7: Wait for services to be healthy
log "Waiting for services to be ready..."
sleep 10

# Check API health
MAX_RETRIES=30
RETRY_COUNT=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        log "API is healthy!"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
        error "API failed to start"
    fi
    sleep 2
done

# Step 8: Clean up
log "Cleaning up old Docker resources..."
docker system prune -f || warn "Cleanup had issues"

# Step 9: Verification
log "Verifying deployment..."
docker-compose ps

# Check all services
SERVICES=("api" "db" "kafka" "redis" "frontend")
for service in "${SERVICES[@]}"; do
    if docker-compose ps $service | grep -q "Up"; then
        log "✓ $service is running"
    else
        warn "✗ $service is NOT running"
    fi
done

log "Deployment completed successfully!" | tee -a $LOG_FILE
log ""
log "Access your application at:"
log "  - API: http://$(curl -s ifconfig.me):8000"
log "  - Frontend: http://$(curl -s ifconfig.me):3000"
log "  - Docs: http://$(curl -s ifconfig.me):8000/docs"
log ""
log "View logs with: docker-compose logs -f"
