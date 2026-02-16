#!/usr/bin/env python3
"""
JAF Example: Agentic Flow (Demo Outcome #1)

Demonstrates the AGENTIC execution mode where a SINGLE orchestrator actor
uses MULTIPLE tools to accomplish a goal - without delegating to other agents.

Scenario: Onboarding a new developer with equipment provisioning.

Usage:
    python examples/agentic_flow.py

No external dependencies required - uses mock responses for demo.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any
from unittest.mock import patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from framework.event_bus import get_event_bus
from framework.types import AgentAction
from agents.provisionning_agent import ProvisionningAgent

# =============================================================================
# MOCK RESPONSES - Simulate real API responses for demo
# =============================================================================

MOCK_RESPONSES = {
    # Eligibility check - employee is eligible
    "eligibility": {
        "eligible": True,
        "statut": "Full-time",
        "contrat": "Active",
        "metier": "Full Stack Developer",
        "entite": "IT Department - Software Engineering",
        "raisons": [],
    },
    # Equipment status - no existing equipment
    "equipment_status": {"materiel_existant": False, "materiel_actuel": []},
    # Model selection
    "model_selection": {
        "modele_recommande": 'MacBook Pro 14" M3 Pro',
        "generation": "2024",
        "justification": "Developer profile - high performance configuration required",
    },
    # Available models
    "available_models": {
        "alternatives": [
            'MacBook Pro 14" M3',
            "Dell XPS 15",
            "ThinkPad X1 Carbon Gen 11",
        ],
        "stock": 15,
    },
    # Order confirmation
    "order": {
        "numero_commande": "ORD-2024-78542",
        "statut": "processing",
        "date_livraison_prevue": (datetime.now() + timedelta(days=5)).strftime(
            "%Y-%m-%d"
        ),
        "transporteur": "DHL Express",
        "numero_suivi": "DHL-US-4859632147",
    },
    # Manager notification
    "notification": {"notification_id": "NOTIF-2024-12458", "envoyee": True},
    # Order status
    "order_status": {
        "statut": "preparation",
        "statut_detaille": "Order is being prepared",
        "date_maj": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "suivi": {
            "etapes": [
                {
                    "etape": "Order received",
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "complete": True,
                },
                {
                    "etape": "Preparation",
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "complete": True,
                },
                {"etape": "Shipping", "date": "", "complete": False},
                {"etape": "Delivery", "date": "", "complete": False},
            ]
        },
    },
}


def create_mock_response(json_data: Dict, status_code: int = 200):
    """Create a mock response object."""
    mock = MagicMock()
    mock.status_code = status_code
    mock.ok = status_code < 400
    mock.json.return_value = json_data
    return mock


def mock_requests_get(url: str, *args, **kwargs):
    """Mock GET requests based on URL patterns."""
    if "/eligibilite/" in url:
        return create_mock_response(MOCK_RESPONSES["eligibility"])
    elif "/materiel/status/" in url:
        return create_mock_response(MOCK_RESPONSES["equipment_status"])
    elif "/modeles/attribution/" in url:
        return create_mock_response(MOCK_RESPONSES["model_selection"])
    elif "/modeles/disponibles" in url:
        return create_mock_response(MOCK_RESPONSES["available_models"])
    elif "/commandes/" in url and "/statut" in url:
        return create_mock_response(MOCK_RESPONSES["order_status"])
    elif "/commandes/" in url:
        return create_mock_response(MOCK_RESPONSES["order"])
    else:
        return create_mock_response({"error": "Not found"}, 404)


def mock_requests_post(url: str, *args, **kwargs):
    """Mock POST requests based on URL patterns."""
    if "/commandes" in url:
        return create_mock_response(MOCK_RESPONSES["order"])
    elif "/notifications" in url:
        return create_mock_response(MOCK_RESPONSES["notification"])
    else:
        return create_mock_response({"error": "Not found"}, 404)


# =============================================================================
# DEMO EXECUTION
# =============================================================================


def print_header(title: str):
    """Print a formatted header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_step(step_num: int, title: str):
    """Print a step header."""
    print(f"\n{'─' * 70}")
    print(f"  STEP {step_num}: {title}")
    print(f"{'─' * 70}")


def print_result(result: Dict[str, Any], indent: int = 4):
    """Pretty print a result dictionary."""
    prefix = " " * indent
    for key, value in result.items():
        if isinstance(value, dict):
            print(f"{prefix}📦 {key}:")
            print_result(value, indent + 4)
        elif isinstance(value, list):
            print(f"{prefix}📋 {key}:")
            for item in value:
                if isinstance(item, dict):
                    print_result(item, indent + 4)
                else:
                    print(f"{prefix}    • {item}")
        else:
            emoji = "✅" if value is True else "❌" if value is False else "📝"
            print(f"{prefix}{emoji} {key}: {value}")


def event_subscriber(action: AgentAction):
    """Event subscriber that prints events in real-time."""
    status_icon = "✓" if action.status == "complete" else "✗"
    print(f"    [{status_icon}] EVENT: {action.actionType:<20} | {action.message}")


def main():
    """
    Run the Agentic Flow Demo.

    This demonstrates a SINGLE actor (ProvisionningAgent) using MULTIPLE tools
    to accomplish the goal of onboarding a new employee with equipment.

    The flow:
    1. Check employee eligibility for equipment
    2. Select the appropriate equipment model
    3. Place the order
    4. Notify the manager

    All steps are performed by ONE actor with its tools - no delegation to other agents.
    """

    print_header("JAF AGENTIC FLOW DEMO")
    print(
        """
    🎯 SCENARIO: Onboarding a new developer with equipment provisioning

    👤 Employee Details:
       • ID: EMP001
       • Name: John Smith
       • Role: Full Stack Developer
       • Department: Engineering
       • Manager: MGR001

    📍 Delivery Address:
       • 123 Tech Park Drive, San Francisco, CA 94102

    🤖 Actor: ProvisionningAgent (single actor, multiple tools)
    """
    )

    # Set up event bus for real-time feedback
    bus = get_event_bus()
    bus.clear()
    bus.subscribe(event_subscriber)

    # Demo input data
    employee = {
        "cuid": "EMP001",
        "name": "John Smith",
        "role": "Full Stack Developer",
        "department": "Engineering",
    }
    manager_cuid = "MGR001"
    delivery_address = "123 Tech Park Drive, San Francisco, CA 94102"

    # Create the actor
    print("\n🔧 Initializing ProvisionningAgent...")
    agent = ProvisionningAgent()
    agent.configure()

    print(f"   Actor: {agent.name}")
    print(f"   Description: {agent.description}")
    print(f"   Tools available: {len(agent.tools)}")
    for tool in agent.tools[:5]:  # Show first 5 tools
        print(f"      • {tool.__name__}")
    print(f"      ... and {len(agent.tools) - 5} more")

    # Emit start event
    bus.emit(
        AgentAction(
            agentId=agent.name,
            actionType="workflow_started",
            message=f"Starting onboarding workflow for {employee['name']}",
            status="complete",
        )
    )

    # Execute workflow with mocked API calls
    with (
        patch("requests.get", side_effect=mock_requests_get),
        patch("requests.post", side_effect=mock_requests_post),
        patch(
            "requests.put",
            side_effect=lambda *a, **k: create_mock_response({"statut_change": True}),
        ),
    ):
        # STEP 1: Check eligibility
        print_step(1, "Check Employee Eligibility")
        bus.emit(
            AgentAction(
                agentId=agent.name,
                actionType="tool_call",
                message="Calling verifier_eligibilite_collaborateur_offre_A",
                status="complete",
            )
        )

        eligibility = agent.verifier_eligibilite_collaborateur_offre_A(employee["cuid"])
        print_result(eligibility)

        if not eligibility.get("eligible"):
            print("\n❌ Employee not eligible. Workflow stopped.")
            return 1

        bus.emit(
            AgentAction(
                agentId=agent.name,
                actionType="eligibility_verified",
                message=f"Employee {employee['cuid']} is eligible for equipment",
                status="complete",
            )
        )

        # STEP 2: Select equipment model
        print_step(2, "Select Equipment Model")
        bus.emit(
            AgentAction(
                agentId=agent.name,
                actionType="tool_call",
                message="Calling selectionner_modele_attribue",
                status="complete",
            )
        )

        model = agent.selectionner_modele_attribue(employee["cuid"])
        print_result(model)

        if model.get("error"):
            print("\n❌ Model selection failed. Workflow stopped.")
            return 1

        bus.emit(
            AgentAction(
                agentId=agent.name,
                actionType="model_selected",
                message=f"Selected model: {model.get('modele_attribue')}",
                status="complete",
            )
        )

        # STEP 3: Place order
        print_step(3, "Place Order")
        bus.emit(
            AgentAction(
                agentId=agent.name,
                actionType="tool_call",
                message="Calling commander_produit",
                status="complete",
            )
        )

        order = agent.commander_produit(
            cuid=employee["cuid"],
            modele=model.get("modele_attribue", ""),
            adresse_livraison=delivery_address,
        )
        print_result(order)

        if order.get("error"):
            print("\n❌ Order placement failed. Workflow stopped.")
            return 1

        bus.emit(
            AgentAction(
                agentId=agent.name,
                actionType="order_placed",
                message=f"Order {order.get('numero_commande')} placed successfully",
                status="complete",
            )
        )

        # STEP 4: Notify manager
        print_step(4, "Notify Manager")
        bus.emit(
            AgentAction(
                agentId=agent.name,
                actionType="tool_call",
                message="Calling notifier_manager_statut_livraison",
                status="complete",
            )
        )

        notification = agent.notifier_manager_statut_livraison(
            cuid=employee["cuid"],
            numero_commande=order.get("numero_commande", ""),
            manager_cuid=manager_cuid,
        )
        print_result(notification)

        bus.emit(
            AgentAction(
                agentId=agent.name,
                actionType="manager_notified",
                message=f"Manager {manager_cuid} notified of delivery status",
                status="complete",
            )
        )

    print_header("WORKFLOW COMPLETED SUCCESSFULLY ✅")
    print(
        f"""
    📊 SUMMARY:

    👤 Employee: {employee["name"]} ({employee["cuid"]})
    ✅ Eligibility: Verified
    💻 Equipment: {model.get("modele_attribue")}
    📦 Order: {order.get("numero_commande")}
    🚚 Tracking: {order.get("numero_suivi")}
    📅 Expected Delivery: {order.get("date_livraison_prevue")}
    📧 Manager Notified: {manager_cuid}

    🤖 This workflow was executed by a SINGLE actor (ProvisionningAgent)
       using MULTIPLE tools - demonstrating the AGENTIC flow pattern.
    """
    )

    # Emit completion event
    bus.emit(
        AgentAction(
            agentId=agent.name,
            actionType="workflow_completed",
            message="Onboarding workflow completed successfully",
            status="complete",
        )
    )

    # Clean up
    bus.unsubscribe(event_subscriber)
    bus.clear()

    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
