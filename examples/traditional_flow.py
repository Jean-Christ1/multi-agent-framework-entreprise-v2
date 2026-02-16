#!/usr/bin/env python3
"""
JAF Example: Traditional Automation Flow

Demonstrates the TRADITIONAL execution mode where actors execute
deterministic logic without LLM involvement.

This is the cheapest mode ($0.00 per execution) - pure automation.

Usage:
    python examples/traditional_flow.py

Requirements:
    - No API keys needed (no LLM calls)
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from jaf.core.models import ExecutionMode
from jaf.core.actor import Actor, ActorRegistry, Tool, actor
from jaf.adapters import CrewAIAdapter
from jaf.events import get_event_bus

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# Define a deterministic actor (no LLM config)


@actor(
    name="DeterministicActor",
    description="Processes requests using hardcoded business rules",
    goal="Apply deterministic business logic without AI",
    # Note: No llm_config - this actor is purely deterministic
)
class DeterministicActor(Actor):
    """
    Deterministic Actor - No LLM Required.

    This actor demonstrates traditional automation:
    - Rules-based decision making
    - No API calls to LLMs
    - Predictable, fast execution
    - Zero cost per execution

    Similar to BPMN/Camunda workflow engines.
    """

    # Business rules (hardcoded)
    ROLE_BUDGET_MAP = {
        "intern": 500,
        "junior": 1000,
        "developer": 1500,
        "senior": 2000,
        "lead": 2500,
        "manager": 3000,
        "director": 4000,
        "vp": 5000,
    }

    DEPARTMENT_MULTIPLIERS = {
        "engineering": 1.2,
        "sales": 1.0,
        "marketing": 0.9,
        "hr": 0.8,
        "finance": 0.85,
        "operations": 0.9,
    }

    @Tool(description="Calculate equipment budget based on role and department")
    def calculate_budget(self, role: str, department: str) -> dict:
        """
        Calculate equipment budget using business rules.

        No LLM involved - pure if/else logic.
        """
        role_lower = role.lower()
        dept_lower = department.lower()

        # Get base budget from role
        base_budget = self.ROLE_BUDGET_MAP.get(role_lower, 1000)

        # Apply department multiplier
        multiplier = self.DEPARTMENT_MULTIPLIERS.get(dept_lower, 1.0)

        final_budget = int(base_budget * multiplier)

        return {
            "role": role,
            "department": department,
            "base_budget": base_budget,
            "multiplier": multiplier,
            "final_budget": final_budget,
            "currency": "USD",
            "rule_applied": f"ROLE_BUDGET[{role_lower}] * DEPT_MULT[{dept_lower}]",
        }

    @Tool(description="Determine approval requirements based on amount")
    def check_approval_required(self, amount: int, employee_type: str) -> dict:
        """
        Check if approval is needed using business rules.

        Rules:
        - Internal employees: No approval under $2000
        - External contractors: Always need approval
        - Amounts over $3000: Need director approval
        - Amounts over $5000: Need VP approval
        """
        requires_approval = False
        approval_level = None
        reason = "Within auto-approval limits"

        if employee_type.lower() == "external":
            requires_approval = True
            approval_level = "manager"
            reason = "External contractors require approval"
        elif amount > 5000:
            requires_approval = True
            approval_level = "vp"
            reason = "Amount exceeds $5000 threshold"
        elif amount > 3000:
            requires_approval = True
            approval_level = "director"
            reason = "Amount exceeds $3000 threshold"
        elif amount > 2000:
            requires_approval = True
            approval_level = "manager"
            reason = "Amount exceeds $2000 threshold"

        return {
            "amount": amount,
            "employee_type": employee_type,
            "requires_approval": requires_approval,
            "approval_level": approval_level,
            "reason": reason,
        }

    @Tool(description="Generate equipment package based on budget")
    def generate_package(self, budget: int, preferences: list = None) -> dict:
        """
        Generate equipment package within budget.

        Pure lookup logic - no AI creativity needed.
        """
        packages = {
            "basic": {
                "max_budget": 800,
                "items": ["Basic Laptop", "Basic Mouse"],
                "total": 750,
            },
            "standard": {
                "max_budget": 1500,
                "items": ["Standard Laptop", "Mouse", "Keyboard"],
                "total": 1200,
            },
            "professional": {
                "max_budget": 2500,
                "items": ["Pro Laptop", "Monitor", "Mouse", "Keyboard", "Headset"],
                "total": 2200,
            },
            "executive": {
                "max_budget": 5000,
                "items": ["Premium Laptop", "4K Monitor", "Ergonomic Setup", "Phone"],
                "total": 4500,
            },
        }

        # Find best package within budget
        selected = None
        for name, package in packages.items():
            if package["total"] <= budget:
                selected = {"name": name, **package}

        if not selected:
            selected = {"name": "custom", "items": ["TBD"], "total": budget}

        return {
            "budget": budget,
            "selected_package": selected["name"],
            "items": selected["items"],
            "estimated_cost": selected["total"],
            "remaining_budget": budget - selected["total"],
        }


async def main():
    """
    Run a traditional automation flow example.

    Scenario: Process equipment request using business rules only.

    This demonstrates:
    - Zero LLM cost
    - Fast, predictable execution
    - Rules-based decision making
    - Similar to BPMN workflows
    """
    print("\n" + "=" * 60)
    print("JAF Example: Traditional Automation Flow")
    print("=" * 60 + "\n")

    # Clear any existing actors
    ActorRegistry.clear()

    # Create the deterministic actor
    print("1. Creating DeterministicActor (no LLM)...")
    actor = DeterministicActor()
    print(f"   Actor: {actor.name}")
    print(f"   Has LLM: {actor.is_intelligent}")  # Should be False
    print(f"   Tools: {actor.tool_names}")

    # Set up event listener
    print("\n2. Setting up event listener...")
    event_bus = get_event_bus()
    events = []

    def event_handler(event):
        events.append(event)

    event_bus.subscribe(event_handler)

    # Create engine in TRADITIONAL mode
    print("\n3. Creating engine (TRADITIONAL mode)...")
    engine = CrewAIAdapter(
        mode=ExecutionMode.TRADITIONAL,
        actors=[actor],
        # Note: No model needed for traditional mode
    )
    print(f"   Mode: {engine.mode.value}")

    # Define the request
    goal = "Process equipment request for Senior Developer in Engineering"

    print("\n4. Running traditional automation...")
    print(f"   Request: {goal}")
    print("-" * 60)

    # Demonstrate direct tool execution (traditional automation style)
    print("\n   Executing tools directly (no LLM):\n")

    # Step 1: Calculate budget
    print("   STEP 1: Calculate Budget")
    budget_result = actor.calculate_budget.invoke(
        role="senior",
        department="engineering",
    )
    print(f"   → Base: ${budget_result['base_budget']}")
    print(f"   → Multiplier: {budget_result['multiplier']}")
    print(f"   → Final Budget: ${budget_result['final_budget']}")

    # Step 2: Check approval
    print("\n   STEP 2: Check Approval Requirements")
    approval_result = actor.check_approval_required.invoke(
        amount=budget_result["final_budget"],
        employee_type="internal",
    )
    print(f"   → Requires Approval: {approval_result['requires_approval']}")
    if approval_result["requires_approval"]:
        print(f"   → Approval Level: {approval_result['approval_level']}")
    print(f"   → Reason: {approval_result['reason']}")

    # Step 3: Generate package
    print("\n   STEP 3: Generate Equipment Package")
    package_result = actor.generate_package.invoke(
        budget=budget_result["final_budget"],
    )
    print(f"   → Package: {package_result['selected_package']}")
    print(f"   → Items: {', '.join(package_result['items'])}")
    print(f"   → Cost: ${package_result['estimated_cost']}")
    print(f"   → Remaining: ${package_result['remaining_budget']}")

    print("\n" + "-" * 60)

    # Summary
    print("\n5. Automation Summary:")
    print("   ✓ Employee: Senior Developer, Engineering")
    print(f"   ✓ Budget: ${budget_result['final_budget']}")
    print(
        f"   ✓ Approval: {'Required' if approval_result['requires_approval'] else 'Auto-approved'}"
    )
    print(f"   ✓ Package: {package_result['selected_package'].title()}")
    print("   ✓ LLM Calls: 0")
    print("   ✓ Cost: $0.00")

    # Compare costs
    print("\n   Cost Comparison:")
    print("   ┌─────────────────┬──────────┬──────────┐")
    print("   │ Mode            │ Cost     │ Latency  │")
    print("   ├─────────────────┼──────────┼──────────┤")
    print("   │ Traditional     │ $0.00    │ ~50ms    │ ← This demo")
    print("   │ Agentic         │ ~$0.05   │ ~2s      │")
    print("   │ Multi-Agent     │ ~$0.12   │ ~5s      │")
    print("   └─────────────────┴──────────┴──────────┘")

    # Clean up
    event_bus.unsubscribe(event_handler)
    ActorRegistry.clear()

    print("\n" + "=" * 60)
    print("Traditional Flow Example Complete")
    print("=" * 60 + "\n")

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
