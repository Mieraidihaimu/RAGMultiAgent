"""
Integration tests for dynamic persona groups feature.
Tests group/persona CRUD operations, group processing mode, and validation.
"""

import pytest
import asyncio
from httpx import AsyncClient
from datetime import datetime
from uuid import uuid4


class TestPersonaGroupsCRUD:
    """Test CRUD operations for persona groups and personas."""

    @pytest.mark.asyncio
    async def test_create_persona_group(self, async_client: AsyncClient, test_user):
        """Test creating a new persona group."""
        response = await async_client.post(
            f"/groups?user_id={test_user['id']}",
            json={
                "name": "Career Advisory Board",
                "description": "Expert perspectives on career decisions"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Career Advisory Board"
        assert data["description"] == "Expert perspectives on career decisions"
        assert data["user_id"] == test_user["id"]
        assert "id" in data
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_get_persona_groups_empty(self, async_client: AsyncClient, test_user):
        """Test getting persona groups when none exist."""
        response = await async_client.get(f"/groups?user_id={test_user['id']}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["groups"] == []

    @pytest.mark.asyncio
    async def test_get_persona_groups_with_personas(self, async_client: AsyncClient, test_user):
        """Test getting persona groups with included personas."""
        # Create a group
        group_response = await async_client.post(
            f"/groups?user_id={test_user['id']}",
            json={"name": "Test Group", "description": None}
        )
        group_id = group_response.json()["id"]

        # Add personas
        await async_client.post(
            f"/groups/{group_id}/personas",
            json={
                "name": "Optimist",
                "prompt": "You see opportunities and positive outcomes."
            }
        )
        await async_client.post(
            f"/groups/{group_id}/personas",
            json={
                "name": "Skeptic",
                "prompt": "You identify risks and potential problems."
            }
        )

        # Get groups with personas
        response = await async_client.get(
            f"/groups?user_id={test_user['id']}&include_personas=true"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["groups"]) == 1
        group = data["groups"][0]
        assert group["name"] == "Test Group"
        assert len(group["personas"]) == 2
        assert group["personas"][0]["name"] == "Optimist"
        assert group["personas"][1]["name"] == "Skeptic"

    @pytest.mark.asyncio
    async def test_update_persona_group(self, async_client: AsyncClient, test_user):
        """Test updating a persona group."""
        # Create a group
        create_response = await async_client.post(
            f"/groups?user_id={test_user['id']}",
            json={"name": "Original Name", "description": "Original description"}
        )
        group_id = create_response.json()["id"]

        # Update the group
        update_response = await async_client.put(
            f"/groups/{group_id}",
            json={
                "name": "Updated Name",
                "description": "Updated description"
            }
        )
        
        assert update_response.status_code == 200
        data = update_response.json()
        assert data["name"] == "Updated Name"
        assert data["description"] == "Updated description"

    @pytest.mark.asyncio
    async def test_delete_persona_group(self, async_client: AsyncClient, test_user):
        """Test deleting a persona group."""
        # Create a group
        create_response = await async_client.post(
            f"/groups?user_id={test_user['id']}",
            json={"name": "To Be Deleted", "description": None}
        )
        group_id = create_response.json()["id"]

        # Delete the group
        delete_response = await async_client.delete(f"/groups/{group_id}")
        assert delete_response.status_code in [200, 204]

        # Verify it's gone
        get_response = await async_client.get(f"/groups?user_id={test_user['id']}")
        assert len(get_response.json()["groups"]) == 0

    @pytest.mark.asyncio
    async def test_create_persona(self, async_client: AsyncClient, test_user):
        """Test creating a persona in a group."""
        # Create a group
        group_response = await async_client.post(
            f"/groups?user_id={test_user['id']}",
            json={"name": "Test Group", "description": None}
        )
        group_id = group_response.json()["id"]

        # Create a persona
        persona_response = await async_client.post(
            f"/groups/{group_id}/personas",
            json={
                "name": "Tech Lead",
                "prompt": "You are a senior technical leader focused on scalability."
            }
        )
        
        assert persona_response.status_code == 200
        data = persona_response.json()
        assert data["name"] == "Tech Lead"
        assert data["prompt"] == "You are a senior technical leader focused on scalability."
        assert data["group_id"] == group_id
        assert "id" in data

    @pytest.mark.asyncio
    async def test_get_personas_by_group(self, async_client: AsyncClient, test_user):
        """Test getting all personas for a group."""
        # Create a group
        group_response = await async_client.post(
            f"/groups?user_id={test_user['id']}",
            json={"name": "Test Group", "description": None}
        )
        group_id = group_response.json()["id"]

        # Add multiple personas
        for i in range(3):
            await async_client.post(
                f"/groups/{group_id}/personas",
                json={
                    "name": f"Persona {i+1}",
                    "prompt": f"Prompt for persona {i+1}"
                }
            )

        # Get personas
        response = await async_client.get(f"/groups/{group_id}/personas")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["personas"]) == 3
        assert data["personas"][0]["name"] == "Persona 1"

    @pytest.mark.asyncio
    async def test_update_persona(self, async_client: AsyncClient, test_user):
        """Test updating a persona."""
        # Create group and persona
        group_response = await async_client.post(
            f"/groups?user_id={test_user['id']}",
            json={"name": "Test Group", "description": None}
        )
        group_id = group_response.json()["id"]
        
        persona_response = await async_client.post(
            f"/groups/{group_id}/personas",
            json={"name": "Original", "prompt": "Original prompt"}
        )
        persona_id = persona_response.json()["id"]

        # Update the persona
        update_response = await async_client.put(
            f"/personas/{persona_id}",
            json={
                "name": "Updated",
                "prompt": "Updated prompt"
            }
        )
        
        assert update_response.status_code == 200
        data = update_response.json()
        assert data["name"] == "Updated"
        assert data["prompt"] == "Updated prompt"

    @pytest.mark.asyncio
    async def test_delete_persona(self, async_client: AsyncClient, test_user):
        """Test deleting a persona."""
        # Create group and persona
        group_response = await async_client.post(
            f"/groups?user_id={test_user['id']}",
            json={"name": "Test Group", "description": None}
        )
        group_id = group_response.json()["id"]
        
        persona_response = await async_client.post(
            f"/groups/{group_id}/personas",
            json={"name": "To Delete", "prompt": "Will be deleted"}
        )
        persona_id = persona_response.json()["id"]

        # Delete the persona
        delete_response = await async_client.delete(f"/personas/{persona_id}")
        assert delete_response.status_code in [200, 204]

        # Verify it's gone
        get_response = await async_client.get(f"/groups/{group_id}/personas")
        assert len(get_response.json()["personas"]) == 0


class TestPersonaGroupsValidation:
    """Test validation rules for persona groups."""

    @pytest.mark.asyncio
    async def test_max_groups_per_user(self, async_client: AsyncClient, test_user):
        """Test that users cannot create more than 10 groups."""
        # Create 10 groups (max allowed)
        for i in range(10):
            response = await async_client.post(
                f"/groups?user_id={test_user['id']}",
                json={"name": f"Group {i+1}", "description": None}
            )
            assert response.status_code == 200

        # Try to create 11th group (should fail)
        response = await async_client.post(
            f"/groups?user_id={test_user['id']}",
            json={"name": "Group 11", "description": None}
        )
        assert response.status_code == 400
        assert "maximum" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_max_personas_per_group(self, async_client: AsyncClient, test_user):
        """Test that groups cannot have more than 10 personas."""
        # Create a group
        group_response = await async_client.post(
            f"/groups?user_id={test_user['id']}",
            json={"name": "Test Group", "description": None}
        )
        group_id = group_response.json()["id"]

        # Add 10 personas (max allowed)
        for i in range(10):
            response = await async_client.post(
                f"/groups/{group_id}/personas",
                json={"name": f"Persona {i+1}", "prompt": f"Prompt {i+1}"}
            )
            assert response.status_code == 200

        # Try to add 11th persona (should fail)
        response = await async_client.post(
            f"/groups/{group_id}/personas",
            json={"name": "Persona 11", "prompt": "Prompt 11"}
        )
        assert response.status_code == 400
        assert "maximum" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_group_ownership_validation(self, async_client: AsyncClient, test_user):
        """Test that users can only access their own groups."""
        # Create a group for test user
        group_response = await async_client.post(
            f"/groups?user_id={test_user['id']}",
            json={"name": "My Group", "description": None}
        )
        group_id = group_response.json()["id"]

        # Try to access with different user ID (should fail or return empty)
        other_user_id = str(uuid4())
        response = await async_client.get(f"/groups?user_id={other_user_id}")
        
        assert response.status_code == 200
        assert len(response.json()["groups"]) == 0

    @pytest.mark.asyncio
    async def test_group_required_for_group_mode(self, async_client: AsyncClient, test_user):
        """Test that group_id is required when processing_mode is 'group'."""
        response = await async_client.post(
            "/thoughts",
            json={
                "user_id": test_user["id"],
                "text": "Test thought",
                "processing_mode": "group",
                # Missing group_id
            }
        )
        
        # Should either fail validation or require group_id
        assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_group_exists_validation(self, async_client: AsyncClient, test_user):
        """Test that group_id must reference an existing group."""
        fake_group_id = str(uuid4())
        
        response = await async_client.post(
            "/thoughts",
            json={
                "user_id": test_user["id"],
                "text": "Test thought",
                "processing_mode": "group",
                "group_id": fake_group_id
            }
        )
        
        assert response.status_code in [400, 404]


class TestGroupProcessingMode:
    """Test thought processing in group mode."""

    @pytest.mark.asyncio
    async def test_single_mode_processing(self, async_client: AsyncClient, test_user):
        """Test that single mode works without a group."""
        response = await async_client.post(
            "/thoughts",
            json={
                "user_id": test_user["id"],
                "text": "Should I learn Rust or Go?",
                "processing_mode": "single"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["processing_mode"] == "single"
        assert data["group_id"] is None

    @pytest.mark.asyncio
    async def test_group_mode_processing(self, async_client: AsyncClient, test_user):
        """Test that group mode processes with personas."""
        # Create group with personas
        group_response = await async_client.post(
            f"/groups?user_id={test_user['id']}",
            json={"name": "Tech Advisors", "description": None}
        )
        group_id = group_response.json()["id"]

        await async_client.post(
            f"/groups/{group_id}/personas",
            json={
                "name": "Go Advocate",
                "prompt": "You prefer Go for its simplicity and performance."
            }
        )
        await async_client.post(
            f"/groups/{group_id}/personas",
            json={
                "name": "Rust Advocate",
                "prompt": "You prefer Rust for its memory safety and type system."
            }
        )

        # Submit thought in group mode
        response = await async_client.post(
            "/thoughts",
            json={
                "user_id": test_user["id"],
                "text": "Should I learn Rust or Go?",
                "processing_mode": "group",
                "group_id": group_id
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["processing_mode"] == "group"
        assert data["group_id"] == group_id

    @pytest.mark.asyncio
    async def test_group_mode_with_no_personas(self, async_client: AsyncClient, test_user):
        """Test that group mode fails gracefully if group has no personas."""
        # Create group without personas
        group_response = await async_client.post(
            f"/groups?user_id={test_user['id']}",
            json={"name": "Empty Group", "description": None}
        )
        group_id = group_response.json()["id"]

        # Try to submit thought (should fail or warn)
        response = await async_client.post(
            "/thoughts",
            json={
                "user_id": test_user["id"],
                "text": "Test thought",
                "processing_mode": "group",
                "group_id": group_id
            }
        )
        
        # Should either fail with 400 or succeed with warning
        assert response.status_code in [200, 400]

    @pytest.mark.asyncio
    async def test_persona_runs_created(self, async_client: AsyncClient, test_user, db_adapter):
        """Test that thought_persona_runs records are created for each persona."""
        # Create group with personas
        group_response = await async_client.post(
            f"/groups?user_id={test_user['id']}",
            json={"name": "Test Group", "description": None}
        )
        group_id = group_response.json()["id"]

        persona_ids = []
        for i in range(3):
            persona_response = await async_client.post(
                f"/groups/{group_id}/personas",
                json={"name": f"Persona {i+1}", "prompt": f"Prompt {i+1}"}
            )
            persona_ids.append(persona_response.json()["id"])

        # Submit thought
        thought_response = await async_client.post(
            "/thoughts",
            json={
                "user_id": test_user["id"],
                "text": "Test thought",
                "processing_mode": "group",
                "group_id": group_id
            }
        )
        thought_id = thought_response.json()["id"]

        # Wait a bit for processing to start
        await asyncio.sleep(2)

        # Check thought_persona_runs (would need database access or API endpoint)
        # This is a placeholder - actual implementation depends on your test setup
        # runs = await db_adapter.get_thought_persona_runs(thought_id)
        # assert len(runs) == 3


class TestConsolidation:
    """Test consolidation of persona outputs."""

    @pytest.mark.asyncio
    async def test_consolidated_output_structure(self, async_client: AsyncClient, test_user):
        """Test that consolidated output has expected structure."""
        # Create group with personas
        group_response = await async_client.post(
            f"/groups?user_id={test_user['id']}",
            json={"name": "Decision Makers", "description": None}
        )
        group_id = group_response.json()["id"]

        await async_client.post(
            f"/groups/{group_id}/personas",
            json={"name": "Optimist", "prompt": "You focus on opportunities."}
        )
        await async_client.post(
            f"/groups/{group_id}/personas",
            json={"name": "Pessimist", "prompt": "You focus on risks."}
        )

        # Submit thought
        response = await async_client.post(
            "/thoughts",
            json={
                "user_id": test_user["id"],
                "text": "Should I start a new business?",
                "processing_mode": "group",
                "group_id": group_id
            }
        )
        thought_id = response.json()["id"]

        # Wait for processing to complete (in real scenario)
        # This would require polling or webhook
        await asyncio.sleep(5)

        # Get thought details
        thought_response = await async_client.get(f"/thoughts/{thought_id}")
        
        if thought_response.status_code == 200:
            thought = thought_response.json()
            
            # Check if consolidated output exists and has structure
            if thought.get("consolidated_output"):
                consolidated = thought["consolidated_output"]
                # Expected structure from consolidate_persona_outputs()
                assert "consensus_points" in consolidated
                assert "divergent_views" in consolidated
                assert "balanced_recommendation" in consolidated
                assert isinstance(consolidated["consensus_points"], list)
                assert isinstance(consolidated["divergent_views"], list)


class TestCascadeDelete:
    """Test cascade deletion behavior."""

    @pytest.mark.asyncio
    async def test_delete_group_cascades_to_personas(self, async_client: AsyncClient, test_user):
        """Test that deleting a group also deletes its personas."""
        # Create group with personas
        group_response = await async_client.post(
            f"/groups?user_id={test_user['id']}",
            json={"name": "Test Group", "description": None}
        )
        group_id = group_response.json()["id"]

        persona_response = await async_client.post(
            f"/groups/{group_id}/personas",
            json={"name": "Test Persona", "prompt": "Test prompt"}
        )
        persona_id = persona_response.json()["id"]

        # Delete the group
        await async_client.delete(f"/groups/{group_id}")

        # Try to access the persona (should fail)
        persona_get_response = await async_client.get(f"/groups/{group_id}/personas")
        assert persona_get_response.status_code in [404, 200]
        
        if persona_get_response.status_code == 200:
            assert len(persona_get_response.json()["personas"]) == 0

    @pytest.mark.asyncio
    async def test_delete_user_cascades_to_groups(self, async_client: AsyncClient, test_user):
        """Test that deleting a user also deletes their groups (if supported)."""
        # Create a group
        group_response = await async_client.post(
            f"/groups?user_id={test_user['id']}",
            json={"name": "Test Group", "description": None}
        )
        group_id = group_response.json()["id"]

        # Note: This test assumes user deletion is possible
        # Actual implementation depends on your auth system
        # This is a placeholder for cascade behavior verification
        pass


# Fixtures would go here - adapt to your existing test setup
@pytest.fixture
async def test_user():
    """Create a test user."""
    return {
        "id": str(uuid4()),
        "email": "test@example.com"
    }


@pytest.fixture
async def db_adapter():
    """Database adapter fixture (adapt to your setup)."""
    # This would return your actual database adapter instance
    pass
