FROM python:3.11-slim

WORKDIR /tests

# Install dependencies
COPY tests/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy Kafka module from parent directory (needed for direct Kafka tests)
COPY kafka /app/kafka
COPY common /app/common

# Copy test files
COPY tests/ .

# Default command runs all tests
CMD ["pytest", "-v", "--color=yes", "--tb=short"]
