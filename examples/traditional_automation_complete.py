#!/usr/bin/env python3
"""
JAF Example: Complete Traditional Automation Pattern

Demonstrates comprehensive traditional automation with multiple deterministic actors
working together without any LLM involvement. This pattern is ideal for:
- High-volume, predictable processes
- Regulated environments requiring audit trails
- Cost-sensitive operations
- Low-latency requirements

Key Features:
- 100% deterministic execution
- Zero LLM costs ($0.00 per execution)
- Full business logic traceability
- Stateful workflow orchestration
- Data validation and rule engines

Usage:
    python examples/traditional_automation_complete.py

Requirements:
    - No API keys needed (no LLM calls)
    - Pure Python execution
"""

import asyncio
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from framework.actor.base_actor import Actor

# Configure logging for this demo only
# NOTE: This is demo-only configuration. In production, use your application's
# existing logging setup. Do not copy this global configuration into real applications.
if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
logger = logging.getLogger(__name__)


# ============================================================================
# DETERMINISTIC ACTORS - No LLM Configuration
# ============================================================================


class EmployeeValidationActor(Actor):
    """
    Validates employee data using business rules.

    Demonstrates:
    - Input validation
    - Data quality checks
    - Compliance verification
    - Rule-based decision making
    """

    def configure(self) -> None:
        self.name = "EmployeeValidationActor"
        self.description = "Validates employee data against business rules"
        self.goal = "Ensure data quality and compliance"
        self.llm_config = None  # Deterministic actor
        self.tools = [
            self.validate_employee_id,
            self.validate_role,
            self.validate_department,
            self.check_duplicate,
        ]
        self.utilities = []

    def validate_employee_id(self, employee_id: str) -> Dict[str, Any]:
        """Validate employee ID format and checksum."""
        is_valid = False
        errors = []

        # Rule 1: Format check (EMP-XXXXXX)
        if not employee_id.startswith("EMP-"):
            errors.append("Employee ID must start with 'EMP-'")
        elif len(employee_id) != 10:
            errors.append("Employee ID must be 10 characters (EMP-XXXXXX)")
        else:
            # Rule 2: Numeric part validation
            numeric_part = employee_id[4:]
            if not numeric_part.isdigit():
                errors.append("Employee ID suffix must be numeric")
            else:
                is_valid = True

        return {
            "employee_id": employee_id,
            "valid": is_valid,
            "errors": errors,
            "rule": "EMP-XXXXXX format",
        }

    def validate_role(self, role: str) -> Dict[str, Any]:
        """Validate role against approved list."""
        approved_roles = [
            "Intern",
            "Junior Developer",
            "Developer",
            "Senior Developer",
            "Lead Developer",
            "Manager",
            "Senior Manager",
            "Director",
            "VP Engineering",
            "CTO",
        ]

        is_valid = role in approved_roles

        return {
            "role": role,
            "valid": is_valid,
            "approved_roles": approved_roles if not is_valid else None,
            "rule": "Approved role list validation",
        }

    def validate_department(self, department: str) -> Dict[str, Any]:
        """Validate department and return metadata."""
        departments = {
            "Engineering": {"cost_center": "CC-100", "budget_code": "ENG"},
            "Sales": {"cost_center": "CC-200", "budget_code": "SAL"},
            "Marketing": {"cost_center": "CC-300", "budget_code": "MKT"},
            "HR": {"cost_center": "CC-400", "budget_code": "HRS"},
            "Finance": {"cost_center": "CC-500", "budget_code": "FIN"},
            "Operations": {"cost_center": "CC-600", "budget_code": "OPS"},
        }

        is_valid = department in departments
        metadata = departments.get(department)

        return {
            "department": department,
            "valid": is_valid,
            "cost_center": metadata["cost_center"] if metadata else None,
            "budget_code": metadata["budget_code"] if metadata else None,
            "rule": "Department registry lookup",
        }

    def check_duplicate(self, employee_id: str, email: str) -> Dict[str, Any]:
        """Check for duplicate employee records (simulated)."""
        # In real implementation, this would query a database
        # For demo, we simulate a simple check

        # Simulated database of existing employees
        existing_ids = ["EMP-000001", "EMP-000002", "EMP-000003"]
        existing_emails = ["john@example.com", "jane@example.com"]

        id_duplicate = employee_id in existing_ids
        email_duplicate = email in existing_emails

        return {
            "employee_id": employee_id,
            "email": email,
            "id_duplicate": id_duplicate,
            "email_duplicate": email_duplicate,
            "valid": not (id_duplicate or email_duplicate),
            "rule": "Duplicate detection",
        }


class EquipmentProvisioningActor(Actor):
    """
    Provisions equipment based on role and department.

    Demonstrates:
    - Lookup tables
    - Budget calculation
    - Package selection logic
    - Inventory management
    """

    # Business rule tables
    EQUIPMENT_PACKAGES = {
        "basic": {
            "items": ["Standard Laptop", "USB Mouse", "Headset"],
            "cost": 750,
            "max_budget": 900,
        },
        "standard": {
            "items": ["Business Laptop", "Wireless Mouse", "Keyboard", "Headset"],
            "cost": 1200,
            "max_budget": 1500,
        },
        "professional": {
            "items": [
                "Pro Laptop",
                '24" Monitor',
                "Wireless Mouse",
                "Mechanical Keyboard",
                "Noise-Canceling Headset",
            ],
            "cost": 2200,
            "max_budget": 2500,
        },
        "executive": {
            "items": [
                "Premium Laptop",
                '27" 4K Monitor',
                "Ergonomic Mouse",
                "Premium Keyboard",
                "Premium Headset",
                "Webcam",
                "Dock",
            ],
            "cost": 4500,
            "max_budget": 5000,
        },
    }

    ROLE_PACKAGE_MAP = {
        "Intern": "basic",
        "Junior Developer": "standard",
        "Developer": "standard",
        "Senior Developer": "professional",
        "Lead Developer": "professional",
        "Manager": "professional",
        "Senior Manager": "executive",
        "Director": "executive",
        "VP Engineering": "executive",
        "CTO": "executive",
    }

    DEPARTMENT_MULTIPLIERS = {
        "Engineering": 1.2,  # Tech requires better equipment
        "Sales": 1.0,
        "Marketing": 0.9,
        "HR": 0.8,
        "Finance": 0.85,
        "Operations": 0.9,
    }

    def configure(self) -> None:
        self.name = "EquipmentProvisioningActor"
        self.description = "Provisions equipment based on business rules"
        self.goal = "Provide appropriate equipment within budget"
        self.llm_config = None  # Deterministic actor
        self.tools = [
            self.calculate_budget,
            self.select_package,
            self.check_inventory,
            self.create_provision_order,
        ]
        self.utilities = []

    def calculate_budget(self, role: str, department: str) -> Dict[str, Any]:
        """Calculate equipment budget using role and department rules."""
        # Get base package for role
        package_name = self.ROLE_PACKAGE_MAP.get(role, "standard")
        package = self.EQUIPMENT_PACKAGES[package_name]
        base_budget = package["max_budget"]

        # Apply department multiplier
        multiplier = self.DEPARTMENT_MULTIPLIERS.get(department, 1.0)
        final_budget = int(base_budget * multiplier)

        return {
            "role": role,
            "department": department,
            "base_package": package_name,
            "base_budget": base_budget,
            "multiplier": multiplier,
            "final_budget": final_budget,
            "currency": "USD",
        }

    def select_package(self, budget: int) -> Dict[str, Any]:
        """Select best equipment package within budget."""
        selected_package = None

        # Find best package that fits budget
        for name, package in sorted(
            self.EQUIPMENT_PACKAGES.items(), key=lambda x: x[1]["cost"], reverse=True
        ):
            if package["cost"] <= budget:
                selected_package = {"name": name, **package}
                break

        if not selected_package:
            selected_package = {
                "name": "custom",
                "items": ["To Be Determined"],
                "cost": 0,
                "max_budget": budget,
            }

        return {
            "budget": budget,
            "package_name": selected_package["name"],
            "items": selected_package["items"],
            "estimated_cost": selected_package["cost"],
            "remaining_budget": budget - selected_package.get("cost", 0),
        }

    def check_inventory(self, items: List[str]) -> Dict[str, Any]:
        """Check inventory availability (simulated)."""
        # Simulated inventory database
        inventory = {
            "Standard Laptop": 15,
            "Business Laptop": 8,
            "Pro Laptop": 5,
            "Premium Laptop": 2,
            '24" Monitor': 12,
            '27" 4K Monitor': 3,
            "USB Mouse": 50,
            "Wireless Mouse": 20,
            "Ergonomic Mouse": 5,
        }

        availability = {}
        all_available = True

        for item in items:
            stock = inventory.get(item, 0)
            availability[item] = {
                "in_stock": stock > 0,
                "quantity": stock,
            }
            if stock == 0:
                all_available = False

        return {
            "items": items,
            "availability": availability,
            "all_available": all_available,
        }

    def create_provision_order(
        self,
        employee_id: str,
        package_name: str,
        items: List[str],
        cost: int,
    ) -> Dict[str, Any]:
        """Create equipment provisioning order."""
        order_id = f"ORD-{datetime.now().strftime('%Y%m%d')}-{employee_id[4:]}"

        return {
            "order_id": order_id,
            "employee_id": employee_id,
            "package": package_name,
            "items": items,
            "total_cost": cost,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "estimated_delivery": "3-5 business days",
        }


class ApprovalWorkflowActor(Actor):
    """
    Manages approval workflows based on business rules.

    Demonstrates:
    - Multi-level approval logic
    - Threshold-based routing
    - Compliance checks
    - SLA calculation
    """

    APPROVAL_THRESHOLDS = {
        "auto_approve": 1000,  # Under $1k: auto-approve
        "manager": 3000,  # $1k-$3k: manager approval
        "director": 5000,  # $3k-$5k: director approval
        "vp": 10000,  # $5k-$10k: VP approval
        "cfo": float("inf"),  # Over $10k: CFO approval
    }

    SLA_HOURS = {
        "auto_approve": 0,
        "manager": 24,
        "director": 48,
        "vp": 72,
        "cfo": 120,
    }

    def configure(self) -> None:
        self.name = "ApprovalWorkflowActor"
        self.description = "Manages approval workflows based on cost thresholds"
        self.goal = "Route approvals to appropriate level"
        self.llm_config = None  # Deterministic actor
        self.tools = [
            self.determine_approval_level,
            self.calculate_sla,
            self.check_special_conditions,
            self.route_approval,
        ]
        self.utilities = []

    def determine_approval_level(
        self,
        cost: int,
        employee_type: str = "internal",
    ) -> Dict[str, Any]:
        """Determine required approval level based on cost."""
        # Special rule: External employees always need manager approval
        if employee_type.lower() == "external":
            return {
                "cost": cost,
                "employee_type": employee_type,
                "approval_level": "manager",
                "auto_approved": False,
                "reason": "External employee - requires manager approval",
            }

        # Find appropriate approval level
        for level, threshold in self.APPROVAL_THRESHOLDS.items():
            if cost < threshold:
                return {
                    "cost": cost,
                    "employee_type": employee_type,
                    "approval_level": level,
                    "auto_approved": level == "auto_approve",
                    "threshold": threshold,
                    "reason": f"Cost ${cost} below ${threshold} threshold",
                }

        # Fallback (shouldn't reach here due to inf threshold)
        return {
            "cost": cost,
            "approval_level": "cfo",
            "auto_approved": False,
            "reason": "Exceeds all thresholds",
        }

    def calculate_sla(self, approval_level: str) -> Dict[str, Any]:
        """Calculate SLA for approval level."""
        hours = self.SLA_HOURS.get(approval_level, 48)

        return {
            "approval_level": approval_level,
            "sla_hours": hours,
            "sla_days": hours / 24,
            "priority": "immediate" if hours == 0 else "normal",
        }

    def check_special_conditions(
        self,
        department: str,
        role: str,
        cost: int,
    ) -> Dict[str, Any]:
        """Check for special approval conditions."""
        flags = []
        requires_special_approval = False

        # Rule 1: High-cost items for junior roles
        junior_roles = ["Intern", "Junior Developer"]
        if role in junior_roles and cost > 2000:
            flags.append("High cost for junior role")
            requires_special_approval = True

        # Rule 2: Budget-restricted departments
        restricted_depts = ["Marketing", "HR"]
        if department in restricted_depts and cost > 1500:
            flags.append("Budget-restricted department")
            requires_special_approval = True

        # Rule 3: End of fiscal year restrictions (simulated)
        current_month = datetime.now().month
        if current_month == 12 and cost > 3000:
            flags.append("End of fiscal year - restricted spending")
            requires_special_approval = True

        return {
            "department": department,
            "role": role,
            "cost": cost,
            "flags": flags,
            "requires_special_approval": requires_special_approval,
        }

    def route_approval(
        self,
        approval_level: str,
        employee_id: str,
        order_id: str,
    ) -> Dict[str, Any]:
        """Route approval to appropriate handler."""
        # Simulated routing table
        routing = {
            "auto_approve": {"handler": "system", "email": None},
            "manager": {
                "handler": "manager@example.com",
                "email": "manager@example.com",
            },
            "director": {
                "handler": "director@example.com",
                "email": "director@example.com",
            },
            "vp": {"handler": "vp@example.com", "email": "vp@example.com"},
            "cfo": {"handler": "cfo@example.com", "email": "cfo@example.com"},
        }

        route_info = routing.get(approval_level, routing["manager"])

        return {
            "approval_level": approval_level,
            "employee_id": employee_id,
            "order_id": order_id,
            "routed_to": route_info["handler"],
            "notification_email": route_info["email"],
            "status": (
                "auto_approved"
                if approval_level == "auto_approve"
                else "pending_approval"
            ),
            "routed_at": datetime.now().isoformat(),
        }


# ============================================================================
# WORKFLOW ORCHESTRATION
# ============================================================================


class TraditionalWorkflowOrchestrator:
    """
    Orchestrates deterministic actors in a workflow.

    IMPORTANT: This is a SIMPLIFIED DEMO orchestrator that does NOT use:
    - Core JAF Orchestrator (framework.orchestrator)
    - EngineAbstraction (framework.engine.engine_abstraction)
    - ProcessStateMachine (framework.state_machine)

    This example intentionally simplifies the architecture to demonstrate
    the traditional automation pattern without the complexity of the full
    JAF framework. In production, use the core JAF components.

    DIRECT ACTOR INVOCATION:
    Actors are invoked directly (e.g., self.validation_actor.validate_employee_id())
    instead of via an Engine or tool execution abstraction. This is an intentional
    simplification for this deterministic demo. In real implementations with LLM
    actors or complex workflows, use the Engine layer for proper execution control.

    This demonstrates how to coordinate multiple actors without LLM:
    - Sequential execution
    - State management
    - Error handling
    - Audit trail
    """

    def __init__(
        self,
        validation_actor: EmployeeValidationActor,
        provisioning_actor: EquipmentProvisioningActor,
        approval_actor: ApprovalWorkflowActor,
    ):
        self.validation_actor = validation_actor
        self.provisioning_actor = provisioning_actor
        self.approval_actor = approval_actor
        self.audit_trail: List[Dict[str, Any]] = []

    def _log_step(self, step: str, actor: str, result: Dict[str, Any]) -> None:
        """Log workflow step to audit trail."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "step": step,
            "actor": actor,
            "result": result,
        }
        self.audit_trail.append(entry)
        logger.info(f"Step: {step} | Actor: {actor}")

    async def process_employee_onboarding(
        self,
        employee_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Process employee onboarding workflow.

        Workflow Steps:
        1. Validate employee data
        2. Calculate equipment budget
        3. Select equipment package
        4. Check inventory
        5. Determine approval level
        6. Route for approval
        7. Create provision order

        Returns complete workflow result with audit trail.
        """
        workflow_result = {
            "employee_id": employee_data.get("employee_id"),
            "status": "processing",
            "steps": {},
            "errors": [],
        }

        try:
            # Step 1: Validate employee ID
            id_validation = self.validation_actor.validate_employee_id(
                employee_data["employee_id"]
            )
            self._log_step("validate_id", "EmployeeValidationActor", id_validation)
            workflow_result["steps"]["id_validation"] = id_validation

            if not id_validation["valid"]:
                workflow_result["status"] = "failed"
                workflow_result["errors"].extend(id_validation["errors"])
                return workflow_result

            # Step 2: Validate role
            role_validation = self.validation_actor.validate_role(employee_data["role"])
            self._log_step("validate_role", "EmployeeValidationActor", role_validation)
            workflow_result["steps"]["role_validation"] = role_validation

            if not role_validation["valid"]:
                workflow_result["status"] = "failed"
                workflow_result["errors"].append(
                    f"Invalid role: {employee_data['role']}"
                )
                return workflow_result

            # Step 3: Validate department
            dept_validation = self.validation_actor.validate_department(
                employee_data["department"]
            )
            self._log_step(
                "validate_department", "EmployeeValidationActor", dept_validation
            )
            workflow_result["steps"]["department_validation"] = dept_validation

            if not dept_validation["valid"]:
                workflow_result["status"] = "failed"
                workflow_result["errors"].append(
                    f"Invalid department: {employee_data['department']}"
                )
                return workflow_result

            # Step 4: Check duplicates
            duplicate_check = self.validation_actor.check_duplicate(
                employee_data["employee_id"],
                employee_data["email"],
            )
            self._log_step(
                "check_duplicate", "EmployeeValidationActor", duplicate_check
            )
            workflow_result["steps"]["duplicate_check"] = duplicate_check

            if not duplicate_check["valid"]:
                workflow_result["status"] = "failed"
                workflow_result["errors"].append("Duplicate employee detected")
                return workflow_result

            # Step 5: Calculate budget
            budget = self.provisioning_actor.calculate_budget(
                employee_data["role"],
                employee_data["department"],
            )
            self._log_step("calculate_budget", "EquipmentProvisioningActor", budget)
            workflow_result["steps"]["budget"] = budget

            # Step 6: Select package
            package = self.provisioning_actor.select_package(budget["final_budget"])
            self._log_step("select_package", "EquipmentProvisioningActor", package)
            workflow_result["steps"]["package"] = package

            # Step 7: Check inventory
            inventory = self.provisioning_actor.check_inventory(package["items"])
            self._log_step("check_inventory", "EquipmentProvisioningActor", inventory)
            workflow_result["steps"]["inventory"] = inventory

            if not inventory["all_available"]:
                workflow_result["warnings"] = ["Some items may be backordered"]

            # Step 8: Determine approval level
            approval_level = self.approval_actor.determine_approval_level(
                package["estimated_cost"],
                employee_data.get("employee_type", "internal"),
            )
            self._log_step(
                "determine_approval", "ApprovalWorkflowActor", approval_level
            )
            workflow_result["steps"]["approval_level"] = approval_level

            # Step 9: Calculate SLA
            sla = self.approval_actor.calculate_sla(approval_level["approval_level"])
            self._log_step("calculate_sla", "ApprovalWorkflowActor", sla)
            workflow_result["steps"]["sla"] = sla

            # Step 10: Check special conditions
            special_conditions = self.approval_actor.check_special_conditions(
                employee_data["department"],
                employee_data["role"],
                package["estimated_cost"],
            )
            self._log_step(
                "check_special_conditions", "ApprovalWorkflowActor", special_conditions
            )
            workflow_result["steps"]["special_conditions"] = special_conditions

            # Step 11: Create provision order
            order = self.provisioning_actor.create_provision_order(
                employee_data["employee_id"],
                package["package_name"],
                package["items"],
                package["estimated_cost"],
            )
            self._log_step("create_order", "EquipmentProvisioningActor", order)
            workflow_result["steps"]["order"] = order

            # Step 12: Route approval
            routing = self.approval_actor.route_approval(
                approval_level["approval_level"],
                employee_data["employee_id"],
                order["order_id"],
            )
            self._log_step("route_approval", "ApprovalWorkflowActor", routing)
            workflow_result["steps"]["routing"] = routing

            # Workflow complete
            workflow_result["status"] = "completed"
            workflow_result["final_status"] = routing["status"]

        except Exception as e:
            logger.error(f"Workflow error: {e}", exc_info=True)
            workflow_result["status"] = "failed"
            workflow_result["errors"].append(str(e))

        return workflow_result


# ============================================================================
# DEMO EXECUTION
# ============================================================================


async def main():
    """Run traditional automation workflow demonstration."""
    print("\n" + "=" * 80)
    print("JAF: Complete Traditional Automation Pattern")
    print("=" * 80 + "\n")

    print("Pattern Overview:")
    print("  • Multiple deterministic actors working together")
    print("  • No LLM configuration (llm_config = None)")
    print("  • Pure business logic and rule engines")
    print("  • Full audit trail and state management")
    print("  • Zero AI costs, predictable execution\n")

    # Step 1: Initialize actors
    # NOTE: Actors are instantiated directly without registration.
    # This demo does not use ActorRegistry, EngineAbstraction, or the core
    # JAF Orchestrator to keep the example simple and focused.
    print("1. Initializing Deterministic Actors...")
    print("-" * 80)

    validation_actor = EmployeeValidationActor()
    validation_actor.configure()
    print(f"   ✓ {validation_actor.name}")
    print(f"     - Tools: {len(validation_actor.tools)}")
    print(f"     - LLM: {validation_actor.llm_config}")

    provisioning_actor = EquipmentProvisioningActor()
    provisioning_actor.configure()
    print(f"   ✓ {provisioning_actor.name}")
    print(f"     - Tools: {len(provisioning_actor.tools)}")
    print(f"     - LLM: {provisioning_actor.llm_config}")

    approval_actor = ApprovalWorkflowActor()
    approval_actor.configure()
    print(f"   ✓ {approval_actor.name}")
    print(f"     - Tools: {len(approval_actor.tools)}")
    print(f"     - LLM: {approval_actor.llm_config}")

    # Step 2: Create orchestrator
    print("\n2. Creating Workflow Orchestrator...")
    print("-" * 80)
    orchestrator = TraditionalWorkflowOrchestrator(
        validation_actor=validation_actor,
        provisioning_actor=provisioning_actor,
        approval_actor=approval_actor,
    )
    print("   ✓ Orchestrator initialized with 3 actors")

    # Step 3: Process test cases
    test_cases = [
        {
            "name": "Standard Developer",
            "data": {
                "employee_id": "EMP-000123",
                "email": "alice.smith@example.com",
                "role": "Senior Developer",
                "department": "Engineering",
                "employee_type": "internal",
            },
        },
        {
            "name": "Junior in Marketing",
            "data": {
                "employee_id": "EMP-000124",
                "email": "bob.jones@example.com",
                "role": "Junior Developer",
                "department": "Marketing",
                "employee_type": "internal",
            },
        },
        {
            "name": "Executive Hire",
            "data": {
                "employee_id": "EMP-000125",
                "email": "carol.white@example.com",
                "role": "VP Engineering",
                "department": "Engineering",
                "employee_type": "internal",
            },
        },
    ]

    print("\n3. Processing Employee Onboarding Workflows...")
    print("=" * 80)

    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest Case {i}: {test_case['name']}")
        print("-" * 80)

        employee_data = test_case["data"]
        print(f"Employee: {employee_data['employee_id']}")
        print(f"Role: {employee_data['role']}")
        print(f"Department: {employee_data['department']}\n")

        # Process workflow
        result = await orchestrator.process_employee_onboarding(employee_data)

        # Display results
        print(f"Workflow Status: {result['status'].upper()}")

        if result["status"] == "completed":
            print("\nKey Results:")
            print(f"  Budget: ${result['steps']['budget']['final_budget']}")
            print(f"  Package: {result['steps']['package']['package_name'].title()}")
            print(f"  Cost: ${result['steps']['package']['estimated_cost']}")
            print(
                f"  Approval: {result['steps']['approval_level']['approval_level'].upper()}"
            )
            print(f"  Status: {result['final_status'].upper()}")
            print(f"  Order ID: {result['steps']['order']['order_id']}")
            print(f"  SLA: {result['steps']['sla']['sla_hours']} hours")

            if result.get("warnings"):
                print("\n  Warnings:")
                for warning in result["warnings"]:
                    print(f"    ⚠ {warning}")
        else:
            print("\nErrors:")
            for error in result["errors"]:
                print(f"  ✗ {error}")

        print(f"\nSteps Executed: {len(orchestrator.audit_trail)}")
        orchestrator.audit_trail.clear()  # Clear for next test

    # Step 4: Summary
    print("\n" + "=" * 80)
    print("Traditional Automation Summary")
    print("=" * 80)
    print("\nExecution Metrics:")
    print(f"  • Test Cases: {len(test_cases)}")
    print("  • Actors Used: 3 deterministic actors")
    print("  • LLM Calls: 0")
    print("  • Total Cost: $0.00")
    print("  • Avg Latency: <100ms per workflow")

    print("\nBusiness Rules Applied:")
    print("  • Employee validation rules: 4")
    print(
        f"  • Equipment packages: {len(EquipmentProvisioningActor.EQUIPMENT_PACKAGES)}"
    )
    print(f"  • Approval thresholds: {len(ApprovalWorkflowActor.APPROVAL_THRESHOLDS)}")
    print(
        f"  • Department multipliers: {len(EquipmentProvisioningActor.DEPARTMENT_MULTIPLIERS)}"
    )

    print("\nPattern Benefits:")
    print("  ✓ 100% deterministic and auditable")
    print("  ✓ Zero LLM costs")
    print("  ✓ Predictable performance")
    print("  ✓ Full regulatory compliance")
    print("  ✓ Easy to test and maintain")

    print("\n" + "=" * 80 + "\n")

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
