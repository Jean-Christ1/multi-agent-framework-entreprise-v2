import pytest
from unittest.mock import MagicMock
from framework.actor.base_actor import Actor
from framework.actor.registry import ActorRegistry
from framework.types import PlanStep, AgentAction
from framework.engine.crewai_adapter import CrewAIAdapter
from framework.event_bus import get_event_bus


# 1. Define the Test Actor
class ProvisioningActor(Actor):
    def configure(self) -> None:
        self.name = "ProvisioningActor"
        self.description = "Expert in cloud infrastructure provisioning."
        self.goal = "Deploy resources efficiently."
        self.tools = [self.provision_vm]
        self.llm_config = None

    def provision_vm(self, vm_name: str, cpu: int):
        """Provisions a virtual machine."""
        return f"Successfully created VM {vm_name} with {cpu} CPUs."


@pytest.mark.asyncio
async def test_provisioning_step_integration(monkeypatch):
    # Setup
    ActorRegistry.clear()
    ActorRegistry.register("ProvisioningActor", ProvisioningActor)

    # Prevent environment errors (Quota/Key errors)
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key")

    adapter = CrewAIAdapter()

    # 2. Mocking Crew.kickoff()
    # Instead of letting CrewAI call OpenAI, we simulate the final result directly.
    # This verifies that your Adapter correctly interacts with the Registry,
    # creates the Agent, and maps the result.

    mock_result = "Successfully created VM test-server with 2 CPUs."

    # Create mock crewai module
    mock_crew_instance = MagicMock()
    mock_crew_instance.kickoff.return_value = mock_result
    mock_crew_class = MagicMock(return_value=mock_crew_instance)
    mock_agent = MagicMock()
    mock_task = MagicMock()
    mock_process = MagicMock()

    # Patch sys.modules to mock crewai before import
    import sys

    original_modules = sys.modules.copy()

    try:
        # Create mock crewai module
        mock_crewai = MagicMock()
        mock_crewai.Crew = mock_crew_class
        mock_crewai.Agent = mock_agent
        mock_crewai.Task = mock_task
        mock_crewai.Process = mock_process
        mock_crewai.tools = MagicMock()
        mock_crewai.tools.tool = MagicMock()

        sys.modules["crewai"] = mock_crewai
        sys.modules["crewai.tools"] = mock_crewai.tools

        step = PlanStep(
            actor_name="ProvisioningActor",
            tool_name="provision_vm",
            parameters={"vm_name": "test-server", "cpu": 2},
        )

        # Execute
        result = await adapter.execute_step(step, context={})

        # Assert
        assert result.status == "success", f"Adapter returned an error: {result.error}"
        assert "test-server" in result.output["result"]
        assert (
            mock_crew_class.called
        ), "The CrewAI Crew class should have been instantiated"
        assert (
            mock_crew_instance.kickoff.called
        ), "The CrewAI kickoff method should have been called."
    finally:
        # Restore original modules
        sys.modules.clear()
        sys.modules.update(original_modules)

    print(f"\n✅ Test passed successfully! Output: {result.output['result']}")


@pytest.mark.asyncio
async def test_execute_step_emits_events_on_success(monkeypatch):
    """
    Integration test to verify that execute_step() emits correct events.

    Verifies:
    - step_started event with actionType="started"
    - step_completed event with actionType=tool_name
    - Events have correct structure (agentId, actionType, message, status)
    """
    # Setup
    ActorRegistry.clear()
    ActorRegistry.register("ProvisioningActor", ProvisioningActor)
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key")

    # Setup event bus subscriber to capture events
    events_received = []

    def event_subscriber(event):
        events_received.append(event)

    event_bus = get_event_bus()
    event_bus.clear()  # Clear any existing subscribers
    event_bus.subscribe(event_subscriber)

    adapter = CrewAIAdapter()

    mock_result = "Successfully created VM test-server with 2 CPUs."

    # Create mock crewai module
    mock_crew_instance = MagicMock()
    mock_crew_instance.kickoff.return_value = mock_result
    mock_crew_class = MagicMock(return_value=mock_crew_instance)
    mock_agent = MagicMock()
    mock_task = MagicMock()
    mock_process = MagicMock()

    # Patch sys.modules to mock crewai before import
    import sys

    original_modules = sys.modules.copy()

    try:
        # Create mock crewai module
        mock_crewai = MagicMock()
        mock_crewai.Crew = mock_crew_class
        mock_crewai.Agent = mock_agent
        mock_crewai.Task = mock_task
        mock_crewai.Process = mock_process
        mock_crewai.tools = MagicMock()
        mock_crewai.tools.tool = MagicMock()

        sys.modules["crewai"] = mock_crewai
        sys.modules["crewai.tools"] = mock_crewai.tools

        step = PlanStep(
            actor_name="ProvisioningActor",
            tool_name="provision_vm",
            parameters={"vm_name": "test-server", "cpu": 2},
        )

        # Execute
        result = await adapter.execute_step(step, context={})

        # Verify execution succeeded
        assert result.status == "success"

        # Verify Crew was called
        assert mock_crew_class.called, "Crew should have been instantiated"
        assert mock_crew_instance.kickoff.called, "Crew.kickoff should have been called"

        # Verify events were emitted
        assert (
            len(events_received) >= 2
        ), f"Expected at least 2 events, got {len(events_received)}"

        # Verify step_started event
        started_event = events_received[0]
        assert isinstance(started_event, AgentAction), "Event should be AgentAction"
        assert started_event.agentId == "ProvisioningActor"
        assert (
            started_event.actionType == "started"
        ), f"Expected 'started', got '{started_event.actionType}'"
        assert started_event.status == "complete"
        assert "Starting execution of provision_vm" in started_event.message

        # Verify step_completed event
        completed_event = events_received[1]
        assert isinstance(completed_event, AgentAction), "Event should be AgentAction"
        assert completed_event.agentId == "ProvisioningActor"
        assert (
            completed_event.actionType == "provision_vm"
        ), f"Expected 'provision_vm', got '{completed_event.actionType}'"
        assert completed_event.status == "complete"
        assert "Completed provision_vm" in completed_event.message
        assert "ms" in completed_event.message  # Should include execution time

        # Verify event structure (all required fields)
        for event in events_received:
            assert hasattr(event, "agentId")
            assert hasattr(event, "actionType")
            assert hasattr(event, "message")
            assert hasattr(event, "status")
            assert hasattr(event, "timestamp")
            assert event.status in ["complete", "error"]
    finally:
        # Restore original modules
        sys.modules.clear()
        sys.modules.update(original_modules)


@pytest.mark.asyncio
async def test_execute_step_emits_events_on_error(monkeypatch):
    """
    Integration test to verify that execute_step() emits error events correctly.

    Verifies:
    - step_started event with actionType="started"
    - step_error event with actionType=tool_name and status="error"
    """
    # Setup
    ActorRegistry.clear()
    ActorRegistry.register("ProvisioningActor", ProvisioningActor)
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key")

    # Setup event bus subscriber
    events_received = []

    def event_subscriber(event):
        events_received.append(event)

    event_bus = get_event_bus()
    event_bus.clear()
    event_bus.subscribe(event_subscriber)

    adapter = CrewAIAdapter()

    # Create mock crewai module with error
    mock_crew_instance = MagicMock()
    mock_crew_instance.kickoff.side_effect = ValueError(
        "Simulated error during execution"
    )
    mock_crew_class = MagicMock(return_value=mock_crew_instance)
    mock_agent = MagicMock()
    mock_task = MagicMock()
    mock_process = MagicMock()

    # Patch sys.modules to mock crewai before import
    import sys

    original_modules = sys.modules.copy()

    try:
        # Create mock crewai module
        mock_crewai = MagicMock()
        mock_crewai.Crew = mock_crew_class
        mock_crewai.Agent = mock_agent
        mock_crewai.Task = mock_task
        mock_crewai.Process = mock_process
        mock_crewai.tools = MagicMock()
        mock_crewai.tools.tool = MagicMock()

        sys.modules["crewai"] = mock_crewai
        sys.modules["crewai.tools"] = mock_crewai.tools

        step = PlanStep(
            actor_name="ProvisioningActor",
            tool_name="provision_vm",
            parameters={"vm_name": "test-server", "cpu": 2},
        )

        # Execute (should raise or return error)
        result = await adapter.execute_step(step, context={})

        # Verify execution failed
        assert result.status == "error"

        # Verify events were emitted
        assert (
            len(events_received) >= 2
        ), f"Expected at least 2 events, got {len(events_received)}"

        # Verify step_started event
        started_event = events_received[0]
        assert started_event.actionType == "started"
        assert started_event.status == "complete"

        # Verify step_error event
        error_event = events_received[1]
        assert error_event.agentId == "ProvisioningActor"
        assert (
            error_event.actionType == "provision_vm"
        ), f"Expected 'provision_vm', got '{error_event.actionType}'"
        assert error_event.status == "error"
        assert (
            "failed" in error_event.message.lower()
            or "error" in error_event.message.lower()
        )
    finally:
        # Restore original modules
        sys.modules.clear()
        sys.modules.update(original_modules)


@pytest.mark.asyncio
async def test_execute_step_emits_events_structure(monkeypatch):
    """
    Integration test to verify event structure matches specification.

    Verifies that all events have the required fields according to JAF-30:
    - agentId: Actor name
    - actionType: "started" for step start, tool_name for completion/error
    - message: Human-readable description
    - status: "complete" or "error"
    - timestamp: ISO format string
    """
    # Setup
    ActorRegistry.clear()
    ActorRegistry.register("ProvisioningActor", ProvisioningActor)
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key")

    # Setup event bus subscriber
    events_received = []

    def event_subscriber(event):
        events_received.append(event)

    event_bus = get_event_bus()
    event_bus.clear()
    event_bus.subscribe(event_subscriber)

    adapter = CrewAIAdapter()

    mock_result = "Successfully created VM test-server with 2 CPUs."

    # Create mock crewai module
    mock_crew_instance = MagicMock()
    mock_crew_instance.kickoff.return_value = mock_result
    mock_crew_class = MagicMock(return_value=mock_crew_instance)
    mock_agent = MagicMock()
    mock_task = MagicMock()
    mock_process = MagicMock()

    # Patch sys.modules to mock crewai before import
    import sys

    original_modules = sys.modules.copy()

    try:
        # Create mock crewai module
        mock_crewai = MagicMock()
        mock_crewai.Crew = mock_crew_class
        mock_crewai.Agent = mock_agent
        mock_crewai.Task = mock_task
        mock_crewai.Process = mock_process
        mock_crewai.tools = MagicMock()
        mock_crewai.tools.tool = MagicMock()

        sys.modules["crewai"] = mock_crewai
        sys.modules["crewai.tools"] = mock_crewai.tools

        step = PlanStep(
            actor_name="ProvisioningActor",
            tool_name="provision_vm",
            parameters={"vm_name": "test-server", "cpu": 2},
        )

        # Execute
        await adapter.execute_step(step, context={})

        # Verify all events have correct structure
        assert len(events_received) >= 2

        for event in events_received:
            # Verify it's an AgentAction instance
            assert isinstance(
                event, AgentAction
            ), f"Event should be AgentAction, got {type(event)}"

            # Verify required fields exist
            assert hasattr(event, "agentId"), "Event missing agentId"
            assert hasattr(event, "actionType"), "Event missing actionType"
            assert hasattr(event, "message"), "Event missing message"
            assert hasattr(event, "status"), "Event missing status"
            assert hasattr(event, "timestamp"), "Event missing timestamp"

            # Verify field types and values
            assert isinstance(event.agentId, str), "agentId should be string"
            assert isinstance(event.actionType, str), "actionType should be string"
            assert isinstance(event.message, str), "message should be string"
            assert event.status in [
                "complete",
                "error",
            ], f"status should be 'complete' or 'error', got '{event.status}'"
            assert isinstance(event.timestamp, str), "timestamp should be string"

            assert event.timestamp.endswith(
                "Z"
            ), f"timestamp should end with 'Z', got '{event.timestamp}'"

            # Verify agentId matches step
            assert (
                event.agentId == "ProvisioningActor"
            ), f"agentId should be 'ProvisioningActor', got '{event.agentId}'"
    finally:
        # Restore original modules
        sys.modules.clear()
        sys.modules.update(original_modules)
