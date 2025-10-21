# Batch Processor Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    cron \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements from root
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY batch_processor/ /app/
COPY common/ /app/common/

# Create logs directory
RUN mkdir -p /app/logs

# Copy cron job file
COPY config/batch-cron /etc/cron.d/batch-cron

# Give execution rights on the cron job
RUN chmod 0644 /etc/cron.d/batch-cron

# Apply cron job
RUN crontab /etc/cron.d/batch-cron

# Create the log file to be able to run tail
RUN touch /var/log/cron.log

# Default command: run processor once (for manual runs)
# For cron-based execution, override with: CMD ["cron", "-f"]
CMD ["python", "processor.py"]
