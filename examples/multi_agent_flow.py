#!/usr/bin/env python3
"""
JAF Example: Multi-Agent Flow

Demonstrates the MULTI_AGENT execution mode where an orchestrator
delegates tasks to multiple specialized actors.

This mode is suitable for complex workflows (~$0.12 per execution).

Usage:
    python examples/multi_agent_flow.py

Requirements:
    - OPENAI_API_KEY environment variable set
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from jaf.core.models import ExecutionMode, ProcessState, LLMConfig
from jaf.core.actor import Actor, ActorRegistry, Tool, actor
from jaf.adapters import CrewAIAdapter
from jaf.actors import ProvisioningActor
from jaf.events import get_event_bus

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# Define additional actors for the multi-agent scenario


@actor(
    name="IdentityActor",
    description="Manages employee identity and access",
    goal="Verify and classify employee identity for access provisioning",
    llm_config=LLMConfig(model="gpt-4o-mini", temperature=0),
)
class IdentityActor(Actor):
    """Identity management actor."""

    @Tool(description="Classify employee identity type")
    def classify_identity(self, employee_id: str, department: str) -> dict:
        """Classify employee identity."""
        # Simulated identity classification
        internal_departments = ["Engineering", "Product", "Design", "HR"]
        is_internal = department in internal_departments

        return {
            "employee_id": employee_id,
            "department": department,
            "identity_type": "Internal" if is_internal else "External",
            "access_level": "Full" if is_internal else "Limited",
            "requires_approval": not is_internal,
        }

    @Tool(description="Get employee entity from HRIS")
    def get_entity(self, employee_id: str) -> dict:
        """Get employee entity details."""
        # Simulated HRIS lookup
        return {
            "employee_id": employee_id,
            "name": "Alice Johnson",
            "email": "alice.johnson@company.com",
            "manager": "Bob Smith",
            "start_date": "2024-01-15",
            "location": "Paris Office",
        }


@actor(
    name="EmailActor",
    description="Manages email and communication accounts",
    goal="Create and configure email accounts for employees",
    llm_config=LLMConfig(model="gpt-4o-mini", temperature=0),
)
class EmailActor(Actor):
    """Email management actor."""

    @Tool(description="Create a new email account")
    def create_email(self, employee_id: str, name: str, department: str) -> dict:
        """Create email account."""
        # Generate email address
        first_name = name.split()[0].lower()
        last_name = name.split()[-1].lower()
        email = f"{first_name}.{last_name}@company.com"

        return {
            "employee_id": employee_id,
            "email": email,
            "mailbox_size": "50GB",
            "distribution_lists": [f"{department.lower()}-all@company.com"],
            "created": True,
        }

    @Tool(description="Configure email forwarding and aliases")
    def configure_email(self, email: str, aliases: list = None) -> dict:
        """Configure email settings."""
        return {
            "email": email,
            "aliases": aliases or [],
            "forwarding": None,
            "out_of_office": False,
            "configured": True,
        }


async def main():
    """
    Run a multi-agent flow example.

    Scenario: Full employee onboarding with multiple actors.

    The orchestrator will coordinate:
    1. IdentityActor: Verify and classify employee
    2. ProvisioningActor: Order equipment
    3. EmailActor: Create email account

    Each actor specializes in its domain.
    """
    print("\n" + "=" * 60)
    print("JAF Example: Multi-Agent Flow")
    print("=" * 60 + "\n")

    # Clear any existing actors
    ActorRegistry.clear()

    # Create the actors
    print("1. Creating specialized actors...")

    identity_actor = IdentityActor()
    print(f"   - {identity_actor.name}: {identity_actor.tool_names}")

    provisioning_actor = ProvisioningActor()
    print(f"   - {provisioning_actor.name}: {provisioning_actor.tool_names}")

    email_actor = EmailActor()
    print(f"   - {email_actor.name}: {email_actor.tool_names}")

    # List all registered actors
    print(f"\n   Total actors registered: {ActorRegistry.count()}")

    # Set up event listener
    print("\n2. Setting up event listener...")
    event_bus = get_event_bus()
    events = []

    def event_handler(event):
        events.append(event)
        if event.actor:
            logger.info(
                f"[{event.actor}] {event.event_type.value}: {event.action or 'N/A'}"
            )

    event_bus.subscribe(event_handler)

    # Create the engine in MULTI_AGENT mode
    print("\n3. Creating engine (MULTI_AGENT mode)...")
    engine = CrewAIAdapter(
        mode=ExecutionMode.MULTI_AGENT,
        actors=[identity_actor, provisioning_actor, email_actor],
        model="gpt-4o",  # Use smarter model for orchestration
        verbose=False,
    )
    print(f"   Mode: {engine.mode.value}")
    print(f"   Actors: {[a.name for a in engine.actors]}")

    # Define the complex goal
    goal = """
    Complete full onboarding for a new employee:

    Employee Details:
    - ID: E99999
    - Name: Alice Johnson
    - Department: Engineering
    - Role: Senior Developer
    - Type: Internal

    Required Steps:
    1. Verify and classify employee identity
    2. Provision appropriate equipment (laptop, phone)
    3. Create email account with department distribution list

    Return a summary of all completed actions.
    """

    print("\n4. Running multi-agent process...")
    print("   Goal: Complete employee onboarding")
    print("-" * 60)

    try:
        process = await engine.run(
            goal=goal,
            context={
                "employee_id": "E99999",
                "name": "Alice Johnson",
                "department": "Engineering",
                "role": "Senior Developer",
                "employee_type": "internal",
            },
        )

        print("-" * 60)
        print("\n5. Process completed!")
        print(f"   State: {process.state.value}")
        print(f"   Duration: {process.duration_ms}ms")
        print(f"   Steps executed: {len(process.results)}")

        if process.state == ProcessState.COMPLETED:
            print("\n   STEP RESULTS:")
            for i, result in enumerate(process.results, 1):
                step = process.plan.steps[i - 1] if process.plan else None
                actor_name = step.actor if step else "Unknown"
                status = "✓" if result.is_success else "✗"
                print(f"\n   {status} Step {i} ({actor_name}):")
                print(f"      Status: {result.status.value}")
                print(f"      Duration: {result.duration_ms}ms")
        else:
            print(f"\n   ERROR: {process.error}")

        print(f"\n   Total events: {len(events)}")

        # Show actor participation
        actor_events = {}
        for e in events:
            if e.actor:
                actor_events[e.actor] = actor_events.get(e.actor, 0) + 1

        if actor_events:
            print("\n   Actor Participation:")
            for actor_name, count in actor_events.items():
                print(f"      {actor_name}: {count} events")

    except Exception as e:
        logger.exception(f"Process failed: {e}")
        return 1

    finally:
        event_bus.unsubscribe(event_handler)
        ActorRegistry.clear()

    print("\n" + "=" * 60)
    print("Multi-Agent Flow Example Complete")
    print("=" * 60 + "\n")

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
