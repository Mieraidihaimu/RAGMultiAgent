"""
Integration tests for Stripe payment workflow
"""
import pytest
import httpx


@pytest.mark.asyncio
async def test_stripe_config_endpoint(http_client: httpx.AsyncClient):
    """Test Stripe configuration endpoint returns publishable key"""
    response = await http_client.get("/api/stripe-config")
    
    # Should return 200 if configured, 503 if not
    if response.status_code == 200:
        data = response.json()
        assert "publishable_key" in data
        assert data["publishable_key"].startswith("pk_")
    elif response.status_code == 503:
        # Stripe not configured - acceptable in test environment
        assert "not configured" in response.json()["detail"].lower()
    else:
        pytest.fail(f"Unexpected status code: {response.status_code}")


@pytest.mark.asyncio
async def test_create_free_account(http_client: httpx.AsyncClient, clean_test_data):
    """Test creating a free account"""
    response = await http_client.post(
        "/api/create-free-account",
        json={
            "email": "test@integration.free.com",
            "name": "Test Free User"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["success"] is True
    assert "user_id" in data
    assert data["error"] is None


@pytest.mark.asyncio  
async def test_create_free_account_duplicate_email(http_client: httpx.AsyncClient, clean_test_data):
    """Test creating free account with duplicate email updates plan"""
    email = "test@integration.duplicate.com"
    
    # Create first account
    response1 = await http_client.post(
        "/api/create-free-account",
        json={"email": email, "name": "Test User 1"}
    )
    assert response1.status_code == 200
    
    # Create second account with same email
    response2 = await http_client.post(
        "/api/create-free-account",
        json={"email": email, "name": "Test User 2"}
    )
    assert response2.status_code == 200
    assert response2.json()["success"] is True
