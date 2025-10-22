"""
Integration tests for anonymous user workflow
"""
import pytest
import httpx


@pytest.mark.asyncio
async def test_anonymous_thought_creation(http_client: httpx.AsyncClient, clean_test_data):
    """Test creating a thought as anonymous user"""
    # Create first thought (should create session)
    response = await http_client.post(
        "/anonymous/thoughts",
        json={"text": "TEST_ANON: My first anonymous thought"}
    )
    
    assert response.status_code == 201
    data = response.json()
    
    # Verify response structure
    assert "id" in data
    assert data["status"] == "pending"
    assert "session_info" in data
    
    # Verify session info
    session_info = data["session_info"]
    assert "session_token" in session_info
    assert session_info["thoughts_remaining"] == 2
    assert session_info["thoughts_used"] == 1
    assert session_info["limit_reached"] is False
    
    session_token = session_info["session_token"]
    
    # Create second thought with session token
    response2 = await http_client.post(
        "/anonymous/thoughts",
        json={
            "text": "TEST_ANON: My second anonymous thought",
            "session_token": session_token
        }
    )
    
    assert response2.status_code == 201
    data2 = response2.json()
    assert data2["session_info"]["thoughts_remaining"] == 1
    assert data2["session_info"]["thoughts_used"] == 2


@pytest.mark.asyncio
async def test_anonymous_rate_limit(http_client: httpx.AsyncClient, clean_test_data):
    """Test anonymous user rate limiting (3 thoughts max)"""
    session_token = None
    
    # Create 3 thoughts
    for i in range(3):
        response = await http_client.post(
            "/anonymous/thoughts",
            json={
                "text": f"TEST_ANON: Thought number {i+1}",
                "session_token": session_token
            }
        )
        assert response.status_code == 201
        data = response.json()
        session_token = data["session_info"]["session_token"]
        
        if i < 2:
            assert data["session_info"]["limit_reached"] is False
        else:
            assert data["session_info"]["limit_reached"] is True
    
    # Try to create 4th thought - should be rejected
    response = await http_client.post(
        "/anonymous/thoughts",
        json={
            "text": "TEST_ANON: Fourth thought should fail",
            "session_token": session_token
        }
    )
    
    assert response.status_code == 429
    assert "limit" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_anonymous_session_info(http_client: httpx.AsyncClient, clean_test_data):
    """Test retrieving anonymous session information"""
    # Create a thought to get session
    response = await http_client.post(
        "/anonymous/thoughts",
        json={"text": "TEST_ANON: Session info test"}
    )
    
    assert response.status_code == 201
    session_token = response.json()["session_info"]["session_token"]
    
    # Get session info
    response = await http_client.get(f"/anonymous/session/{session_token}")
    assert response.status_code == 200
    
    data = response.json()
    assert data["session_token"] == session_token
    assert data["thoughts_remaining"] == 2
    assert data["thoughts_used"] == 1


@pytest.mark.asyncio
async def test_anonymous_get_thoughts(http_client: httpx.AsyncClient, clean_test_data):
    """Test retrieving thoughts for anonymous session"""
    # Create thoughts
    response = await http_client.post(
        "/anonymous/thoughts",
        json={"text": "TEST_ANON: First thought for retrieval"}
    )
    
    session_token = response.json()["session_info"]["session_token"]
    
    await http_client.post(
        "/anonymous/thoughts",
        json={
            "text": "TEST_ANON: Second thought for retrieval",
            "session_token": session_token
        }
    )
    
    # Get all thoughts
    response = await http_client.get(f"/anonymous/thoughts/{session_token}")
    assert response.status_code == 200
    
    data = response.json()
    assert data["count"] == 2
    assert len(data["thoughts"]) == 2
    
    # Verify thoughts contain expected data
    for thought in data["thoughts"]:
        assert "id" in thought
        assert "text" in thought
        assert "status" in thought
        assert "TEST_ANON" in thought["text"]
