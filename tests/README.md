# Integration Tests

Comprehensive integration test suite for validating major workflows of the RAG Multi-Agent system.

## Test Coverage

### ✅ Health Checks (`test_health.py`)
- API health endpoint verification
- API root endpoint verification
- Database connectivity through API

### ✅ Anonymous User Workflow (`test_anonymous_user.py`)
- Anonymous thought creation with session management
- Rate limiting enforcement (3 thoughts per session)
- Session information retrieval
- Thought retrieval for anonymous sessions

### ✅ Database Operations (`test_database.py`)
- Direct database connectivity
- User CRUD operations
- Thought CRUD operations  
- Anonymous session management

### ✅ Stripe Integration (`test_stripe_integration.py`)
- Stripe configuration endpoint
- Free account creation
- Duplicate email handling

## Running Tests

### Run All Tests
```bash
docker-compose --profile test run --rm integration-tests pytest -v
```

### Run Specific Test File
```bash
docker-compose --profile test run --rm integration-tests pytest test_health.py -v
```

### Run with Short Tracebacks
```bash
docker-compose --profile test run --rm integration-tests pytest -v --tb=short
```

### Run with Coverage (if pytest-cov is added)
```bash
docker-compose --profile test run --rm integration-tests pytest --cov=. -v
```

## Test Results Summary

**Last Run:** All 13 tests passing ✅

- `test_health.py`: 2/2 passed
- `test_anonymous_user.py`: 4/4 passed  
- `test_database.py`: 4/4 passed
- `test_stripe_integration.py`: 3/3 passed

## Architecture

- **Framework:** pytest with pytest-asyncio for async support
- **HTTP Client:** httpx.AsyncClient for API testing
- **Database:** asyncpg for PostgreSQL integration
- **Container:** Python 3.11-slim with isolated test environment
- **Profile:** Uses Docker Compose "test" profile

## Fixtures

### `http_client` (session scope)
Provides an async HTTP client configured to connect to the API service.

### `db_pool` (session scope)
Provides a PostgreSQL connection pool for direct database access.

### `clean_test_data` (function scope)
Cleans up test data before and after each test that uses it.

## Environment Variables

Tests use the following environment variables (configured in docker-compose.yml):

- `API_BASE_URL`: URL of the API service (default: http://api:8000)
- `DATABASE_URL`: PostgreSQL connection string

## Adding New Tests

1. Create a new test file in `tests/` directory (e.g., `test_feature.py`)
2. Import required fixtures from `conftest.py`
3. Mark async tests with `@pytest.mark.asyncio`
4. Use descriptive test names and docstrings
5. Clean up test data using the `clean_test_data` fixture
6. Rebuild the test container: `docker-compose --profile test build integration-tests`
7. Run your tests

## CI/CD Integration

To integrate with CI/CD pipelines:

```yaml
# Example GitHub Actions
- name: Run Integration Tests
  run: |
    docker-compose --profile test up -d
    docker-compose --profile test run --rm integration-tests pytest -v
    docker-compose --profile test down
```
