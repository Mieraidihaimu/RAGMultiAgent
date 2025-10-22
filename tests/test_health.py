"""
Basic health check tests
"""
import pytest
import httpx


@pytest.mark.asyncio
async def test_api_health(http_client: httpx.AsyncClient):
    """Test API health endpoint"""
    response = await http_client.get("/health")
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] in ["healthy", "unhealthy"]
    assert "database" in data
    assert data["database"] == "connected"
    assert "version" in data


@pytest.mark.asyncio
async def test_api_root(http_client: httpx.AsyncClient):
    """Test API root endpoint"""
    response = await http_client.get("/")
    assert response.status_code == 200
    
    data = response.json()
    assert "message" in data
    assert "version" in data
    assert data["version"] == "1.0.0"
