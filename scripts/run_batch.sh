#!/bin/bash
# Helper script to run batch processor

set -e

echo "======================================"
echo "Running Batch Processor"
echo "======================================"
echo ""
echo "Time: $(date)"
echo ""

# Check if running in Docker or locally
if [ -f "/.dockerenv" ]; then
    echo "Running in Docker container..."
    cd /app
    python processor.py
else
    echo "Running locally..."

    # Check if we should use Docker
    if docker-compose ps | grep -q "thoughtprocessor-batch"; then
        echo "Using Docker container..."
        docker-compose exec batch-processor python processor.py
    else
        # Run locally
        if [ ! -d "venv" ]; then
            echo "Error: Virtual environment not found"
            echo "Please run: python -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
            exit 1
        fi

        source venv/bin/activate
        cd batch_processor
        python processor.py
    fi
fi

echo ""
echo "======================================"
echo "Batch processing completed"
echo "======================================"
