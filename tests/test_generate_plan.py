"""
Unit tests for CrewAI Adapter generate_plan method
Ticket: JAF-7

Tests cover all acceptance criteria:
1. Method accepts goal string and available actors
2. Uses LLM to create plan
3. Returns Plan object with steps
4. Handles errors gracefully
"""

import pytest
import json
from unittest.mock import AsyncMock, Mock
from datetime import datetime

# Import the implementation
import sys

sys.path.insert(0, "/home/claude")
from framework.engine.crewai_adapter import CrewAIAdapter

# Import framework types
from framework.types import Plan, PlanStep
from framework.actor.base_actor import Actor


# Mock Actor implementations for testing
class MockProvisioningActor(Actor):
    """Mock provisioning actor for testing."""

    def configure(self):
        self.name = "ProvisioningActor"
        self.description = "Provisions cloud infrastructure"
        self.goal = "Provision and configure cloud resources"
        self.tools = [self.create_ec2_instance, self.configure_security_group]
        self.utilities = []
        self.llm_config = None

    def create_ec2_instance(self, instance_type: str, ami_id: str, region: str) -> str:
        """Create an EC2 instance with specified configuration."""
        return f"Created {instance_type} instance in {region}"

    def configure_security_group(self, group_name: str, rules: list) -> str:
        """Configure security group with ingress/egress rules."""
        return f"Configured security group {group_name}"


class MockDatabaseActor(Actor):
    """Mock database actor for testing."""

    def configure(self):
        self.name = "DatabaseActor"
        self.description = "Manages database operations"
        self.goal = "Setup and configure databases"
        self.tools = [self.create_database, self.run_migration]
        self.utilities = []
        self.llm_config = None

    def create_database(self, db_name: str, db_type: str) -> str:
        """Create a new database instance."""
        return f"Created {db_type} database {db_name}"

    def run_migration(self, migration_script: str) -> str:
        """Run database migration script."""
        return f"Ran migration: {migration_script}"


# Test fixtures
@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client."""
    client = AsyncMock()

    # Mock OpenAI-style response
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = json.dumps(
        [
            {
                "actor_name": "ProvisioningActor",
                "tool_name": "create_ec2_instance",
                "parameters": {
                    "instance_type": "t2.micro",
                    "ami_id": "ami-12345",
                    "region": "us-east-1",
                },
                "description": "Create EC2 instance",
            },
            {
                "actor_name": "ProvisioningActor",
                "tool_name": "configure_security_group",
                "parameters": {
                    "group_name": "web-sg",
                    "rules": ["allow 443", "allow 80"],
                },
                "description": "Configure security group",
            },
        ]
    )

    client.chat.completions.create = AsyncMock(return_value=mock_response)
    return client


@pytest.fixture
def available_actors():
    """Create list of available actors for testing."""
    provisioning = MockProvisioningActor()
    provisioning.configure()

    database = MockDatabaseActor()
    database.configure()

    return [provisioning, database]


@pytest.fixture
def adapter(mock_llm_client):
    """Create CrewAI adapter with mock LLM client."""
    return CrewAIAdapter(llm_client=mock_llm_client)


# Test cases
@pytest.mark.asyncio
async def test_generate_plan_accepts_goal_and_actors(adapter, available_actors):
    """
    Method accepts goal string and available actors
    """
    goal = "Provision a web server with database"

    # Should not raise an exception
    plan = await adapter.generate_plan(goal, available_actors)

    assert plan is not None
    assert isinstance(plan, Plan)


@pytest.mark.asyncio
async def test_generate_plan_uses_llm(adapter, available_actors, mock_llm_client):
    """
    Uses LLM to create plan
    """
    goal = "Deploy application infrastructure"

    await adapter.generate_plan(goal, available_actors)

    # Verify LLM was called
    mock_llm_client.chat.completions.create.assert_called_once()

    # Verify prompt contains goal and capabilities
    call_args = mock_llm_client.chat.completions.create.call_args
    messages = call_args.kwargs["messages"]
    prompt_content = messages[0]["content"]

    assert goal in prompt_content
    assert "ProvisioningActor" in prompt_content
    assert "DatabaseActor" in prompt_content


@pytest.mark.asyncio
async def test_generate_plan_returns_valid_plan(adapter, available_actors):
    """
    Returns Plan object with steps
    """
    goal = "Setup production environment"

    plan = await adapter.generate_plan(goal, available_actors)

    # Verify Plan structure
    assert isinstance(plan, Plan)
    assert hasattr(plan, "steps")
    assert hasattr(plan, "status")
    assert hasattr(plan, "created_at")

    # Verify Plan has steps
    assert len(plan.steps) > 0
    assert all(isinstance(step, PlanStep) for step in plan.steps)

    # Verify Plan status
    assert plan.status == "PLANNING"


@pytest.mark.asyncio
async def test_generate_plan_creates_valid_plan_steps(adapter, available_actors):
    """
    Extended: Verify PlanStep structure
    """
    goal = "Deploy web application"

    plan = await adapter.generate_plan(goal, available_actors)

    for step in plan.steps:
        # Verify PlanStep has required fields
        assert hasattr(step, "id")
        assert hasattr(step, "actor_name")
        assert hasattr(step, "tool_name")
        assert hasattr(step, "parameters")
        assert hasattr(step, "status")

        # Verify field types and values
        assert isinstance(step.id, str)
        assert isinstance(step.actor_name, str)
        assert isinstance(step.tool_name, str)
        assert isinstance(step.parameters, dict)
        assert step.status == "pending"

        # Verify actor and tool exist
        assert step.actor_name in ["ProvisioningActor", "DatabaseActor"]


@pytest.mark.asyncio
async def test_generate_plan_handles_empty_goal_error(adapter, available_actors):
    """
    Handles errors gracefully - empty goal
    """
    with pytest.raises(ValueError, match="Goal cannot be empty"):
        await adapter.generate_plan("", available_actors)

    with pytest.raises(ValueError, match="Goal cannot be empty"):
        await adapter.generate_plan("   ", available_actors)


@pytest.mark.asyncio
async def test_generate_plan_handles_no_actors_error(adapter):
    """
    Handles errors gracefully - no actors
    """
    goal = "Do something"

    with pytest.raises(ValueError, match="No actors available"):
        await adapter.generate_plan(goal, [])


@pytest.mark.asyncio
async def test_generate_plan_handles_markdown_json_response(available_actors):
    """
    Test parsing JSON wrapped in markdown code blocks
    """
    # Create adapter with LLM returning markdown-wrapped JSON
    markdown_client = AsyncMock()
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[
        0
    ].message.content = """```json
[
    {
        "actor_name": "ProvisioningActor",
        "tool_name": "create_ec2_instance",
        "parameters": {"instance_type": "t2.micro", "ami_id": "ami-123", "region": "us-east-1"},
        "description": "Create instance"
    }
]
```"""
    markdown_client.chat.completions.create = AsyncMock(return_value=mock_response)

    adapter = CrewAIAdapter(llm_client=markdown_client)
    goal = "Deploy infrastructure"

    plan = await adapter.generate_plan(goal, available_actors)

    assert len(plan.steps) == 1
    assert plan.steps[0].actor_name == "ProvisioningActor"


@pytest.mark.asyncio
async def test_generate_plan_validates_parameters(adapter, available_actors):
    """
    Verify that plan steps have properly structured parameters
    """
    goal = "Setup complete infrastructure"

    plan = await adapter.generate_plan(goal, available_actors)

    for step in plan.steps:
        assert isinstance(step.parameters, dict)
        # Parameters should match the tool signature
        if step.tool_name == "create_ec2_instance":
            assert "instance_type" in step.parameters
            assert "ami_id" in step.parameters
            assert "region" in step.parameters


@pytest.mark.asyncio
async def test_generate_plan_builds_capabilities_correctly(adapter, available_actors):
    """
    Test the _build_actor_capabilities helper method
    """
    capabilities = adapter._build_actor_capabilities(available_actors)

    # Should contain both actors
    assert "ProvisioningActor" in capabilities
    assert "DatabaseActor" in capabilities

    # Should contain tool names
    assert "create_ec2_instance" in capabilities
    assert "configure_security_group" in capabilities
    assert "create_database" in capabilities
    assert "run_migration" in capabilities

    # Should contain descriptions
    assert "Provisions cloud infrastructure" in capabilities
    assert "Manages database operations" in capabilities


@pytest.mark.asyncio
async def test_generate_plan_creates_unique_step_ids(adapter, available_actors):
    """
    Verify that each PlanStep gets a unique ID
    """
    goal = "Deploy infrastructure"

    plan = await adapter.generate_plan(goal, available_actors)

    step_ids = [step.id for step in plan.steps]
    assert len(step_ids) == len(set(step_ids))


@pytest.mark.asyncio
async def test_generate_plan_sets_correct_initial_status(adapter, available_actors):
    """
    Verify Plan and PlanSteps have correct initial status
    """
    goal = "Deploy infrastructure"

    plan = await adapter.generate_plan(goal, available_actors)

    # Plan should be in PLANNING status
    assert plan.status == "PLANNING"

    # All steps should be pending
    assert all(step.status == "pending" for step in plan.steps)


@pytest.mark.asyncio
async def test_generate_plan_includes_timestamp(adapter, available_actors):
    """
    Verify Plan includes creation timestamp
    """
    goal = "Deploy infrastructure"

    before = datetime.utcnow()
    plan = await adapter.generate_plan(goal, available_actors)
    after = datetime.utcnow()

    assert plan.created_at is not None
    assert before <= plan.created_at <= after


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
