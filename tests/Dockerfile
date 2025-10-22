FROM python:3.11-slim

WORKDIR /tests

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy test files
COPY . .

# Default command runs all tests
CMD ["pytest", "-v", "--color=yes", "--tb=short"]
