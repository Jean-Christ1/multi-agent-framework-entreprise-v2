"""
Integration tests for Traditional Automation Pattern.

Tests the complete workflow of deterministic actors without LLM involvement.
Validates business rules, workflow orchestration, and data validation.
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from framework.actor.base_actor import Actor
from framework.actor.registry import ActorRegistry

# ============================================================================
# Test Actors
# ============================================================================


class TestValidationActor(Actor):
    """Test actor for validation operations."""

    def configure(self) -> None:
        self.name = "TestValidationActor"
        self.description = "Test validation actor"
        self.goal = "Validate test data"
        self.llm_config = None  # Deterministic
        self.tools = [
            self.validate_format,
            self.validate_range,
        ]
        self.utilities = []

    def validate_format(self, value: str, pattern: str) -> dict:
        """Validate string format."""
        import re

        is_valid = bool(re.match(pattern, value))
        return {
            "value": value,
            "pattern": pattern,
            "valid": is_valid,
        }

    def validate_range(self, value: int, min_val: int, max_val: int) -> dict:
        """Validate numeric range."""
        is_valid = min_val <= value <= max_val
        return {
            "value": value,
            "min": min_val,
            "max": max_val,
            "valid": is_valid,
        }


class TestBusinessRulesActor(Actor):
    """Test actor for business rule execution."""

    DISCOUNT_TIERS = {
        "bronze": 0.05,
        "silver": 0.10,
        "gold": 0.15,
        "platinum": 0.20,
    }

    def configure(self) -> None:
        self.name = "TestBusinessRulesActor"
        self.description = "Test business rules actor"
        self.goal = "Execute test business rules"
        self.llm_config = None
        self.tools = [
            self.calculate_discount,
            self.apply_business_rule,
        ]
        self.utilities = []

    def calculate_discount(self, tier: str, amount: float) -> dict:
        """Calculate discount based on tier."""
        discount_rate = self.DISCOUNT_TIERS.get(tier, 0.0)
        discount_amount = amount * discount_rate
        final_amount = amount - discount_amount

        return {
            "tier": tier,
            "original_amount": amount,
            "discount_rate": discount_rate,
            "discount_amount": discount_amount,
            "final_amount": final_amount,
        }

    def apply_business_rule(self, condition: str, value: int) -> dict:
        """Apply conditional business rule."""
        result = {
            "condition": condition,
            "value": value,
            "action": None,
        }

        if condition == "high_value" and value > 1000:
            result["action"] = "escalate"
        elif condition == "medium_value" and 500 <= value <= 1000:
            result["action"] = "review"
        else:
            result["action"] = "auto_approve"

        return result


# ============================================================================
# Test Cases
# ============================================================================


class TestDeterministicActors:
    """Test suite for deterministic actor behavior."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Setup and teardown for each test."""
        ActorRegistry.clear()
        yield
        ActorRegistry.clear()

    def test_actor_has_no_llm_config(self):
        """Test that traditional actors have no LLM configuration."""
        actor = TestValidationActor()
        actor.configure()

        assert actor.llm_config is None
        assert actor.name == "TestValidationActor"
        assert len(actor.tools) == 2

    def test_validation_actor_format_check(self):
        """Test format validation with regex patterns."""
        actor = TestValidationActor()
        actor.configure()

        # Valid email format
        result = actor.validate_format(
            value="user@example.com",
            pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
        )
        assert result["valid"] is True

        # Invalid email format
        result = actor.validate_format(
            value="invalid-email",
            pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
        )
        assert result["valid"] is False

    def test_validation_actor_range_check(self):
        """Test numeric range validation."""
        actor = TestValidationActor()
        actor.configure()

        # Within range
        result = actor.validate_range(value=50, min_val=0, max_val=100)
        assert result["valid"] is True

        # Below range
        result = actor.validate_range(value=-10, min_val=0, max_val=100)
        assert result["valid"] is False

        # Above range
        result = actor.validate_range(value=150, min_val=0, max_val=100)
        assert result["valid"] is False

        # Edge cases: exactly at boundaries
        result = actor.validate_range(value=0, min_val=0, max_val=100)
        assert result["valid"] is True

        result = actor.validate_range(value=100, min_val=0, max_val=100)
        assert result["valid"] is True

    def test_business_rules_discount_calculation(self):
        """Test discount calculation by tier."""
        actor = TestBusinessRulesActor()
        actor.configure()

        # Bronze tier (5% discount)
        result = actor.calculate_discount(tier="bronze", amount=1000.0)
        assert result["discount_rate"] == 0.05
        assert result["discount_amount"] == 50.0
        assert result["final_amount"] == 950.0

        # Gold tier (15% discount)
        result = actor.calculate_discount(tier="gold", amount=1000.0)
        assert result["discount_rate"] == 0.15
        assert result["discount_amount"] == 150.0
        assert result["final_amount"] == 850.0

        # Unknown tier (0% discount)
        result = actor.calculate_discount(tier="unknown", amount=1000.0)
        assert result["discount_rate"] == 0.0
        assert result["discount_amount"] == 0.0
        assert result["final_amount"] == 1000.0

    def test_business_rules_conditional_logic(self):
        """Test conditional business rule execution."""
        actor = TestBusinessRulesActor()
        actor.configure()

        # High value - escalate
        result = actor.apply_business_rule(condition="high_value", value=1500)
        assert result["action"] == "escalate"

        # Medium value - review
        result = actor.apply_business_rule(condition="medium_value", value=750)
        assert result["action"] == "review"

        # Low value - auto approve
        result = actor.apply_business_rule(condition="low_value", value=100)
        assert result["action"] == "auto_approve"

    def test_deterministic_behavior(self):
        """Test that same input produces same output (determinism)."""
        actor = TestBusinessRulesActor()
        actor.configure()

        # Run same calculation multiple times
        results = []
        for _ in range(10):
            result = actor.calculate_discount(tier="silver", amount=2000.0)
            results.append(result)

        # All results should be identical
        first_result = results[0]
        for result in results[1:]:
            assert result == first_result


class TestWorkflowOrchestration:
    """Test workflow orchestration with multiple actors."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Setup and teardown for each test."""
        ActorRegistry.clear()
        yield
        ActorRegistry.clear()

    @pytest.fixture
    def actors(self):
        """Create test actors."""
        validation_actor = TestValidationActor()
        validation_actor.configure()

        business_actor = TestBusinessRulesActor()
        business_actor.configure()

        return {
            "validation": validation_actor,
            "business": business_actor,
        }

    def test_sequential_workflow(self, actors):
        """Test sequential execution of multiple actors."""
        # Step 1: Validate input
        email_validation = actors["validation"].validate_format(
            value="customer@example.com",
            pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
        )
        assert email_validation["valid"] is True

        # Step 2: Validate amount range
        amount = 1500
        range_validation = actors["validation"].validate_range(
            value=amount, min_val=100, max_val=10000
        )
        assert range_validation["valid"] is True

        # Step 3: Calculate discount
        discount = actors["business"].calculate_discount(
            tier="gold", amount=float(amount)
        )
        assert discount["final_amount"] == 1275.0  # 15% off 1500

        # Step 4: Apply business rule
        rule_result = actors["business"].apply_business_rule(
            condition="high_value", value=amount
        )
        assert rule_result["action"] == "escalate"

    def test_workflow_with_failure(self, actors):
        """Test workflow handling validation failure."""
        # Step 1: Invalid email
        email_validation = actors["validation"].validate_format(
            value="invalid-email",
            pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
        )
        assert email_validation["valid"] is False

        # Workflow should stop here - don't proceed with invalid data
        # In real implementation, this would raise exception or return error

    def test_parallel_validation(self, actors):
        """Test that multiple validations can run independently."""
        # These validations are independent
        validation1 = actors["validation"].validate_format(
            value="test@example.com",
            pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
        )

        validation2 = actors["validation"].validate_range(
            value=500, min_val=0, max_val=1000
        )

        # Both should succeed independently
        assert validation1["valid"] is True
        assert validation2["valid"] is True


class TestCompleteExample:
    """
    Test individual actors from the traditional automation example.

    NOTE: These tests validate isolated actor functionality using the ACTUAL
    actors from traditional_automation_complete.py. For complete end-to-end
    workflow validation, see TestWorkflowOrchestration below.
    """

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Setup and teardown for each test."""
        ActorRegistry.clear()
        yield
        ActorRegistry.clear()

    def test_employee_validation_actor(self):
        """Test EmployeeValidationActor from real implementation."""
        from examples.traditional_automation_complete import EmployeeValidationActor

        actor = EmployeeValidationActor()
        actor.configure()

        # Test valid employee ID
        result = actor.validate_employee_id("EMP-123456")
        assert result["valid"] is True
        assert result["employee_id"] == "EMP-123456"

        # Test invalid employee ID
        result = actor.validate_employee_id("INVALID")
        assert result["valid"] is False
        assert len(result["errors"]) > 0

    def test_equipment_provisioning_actor(self):
        """Test EquipmentProvisioningActor from real implementation."""
        from examples.traditional_automation_complete import EquipmentProvisioningActor

        actor = EquipmentProvisioningActor()
        actor.configure()

        # Test budget calculation
        result = actor.calculate_budget("Senior Developer", "Engineering")
        assert result["final_budget"] > 0
        assert "base_budget" in result
        assert "multiplier" in result
        assert result["multiplier"] > 0

        # Test package selection
        package = actor.select_package(3000)
        assert package["package_name"] in [
            "basic",
            "standard",
            "professional",
            "executive",
        ]
        assert len(package["items"]) > 0

    def test_approval_workflow_actor(self):
        """Test ApprovalWorkflowActor from real implementation."""
        from examples.traditional_automation_complete import ApprovalWorkflowActor

        actor = ApprovalWorkflowActor()
        actor.configure()

        # Test approval level determination
        result = actor.determine_approval_level(500, "internal")
        assert result["approval_level"] in [
            "auto_approve",
            "manager",
            "director",
            "vp",
            "cfo",
        ]
        assert "threshold" in result

        # Test SLA calculation
        sla = actor.calculate_sla("manager")
        assert "sla_hours" in sla
        assert sla["sla_hours"] > 0


class TestCompleteWorkflowOrchestration:
    """
    Test complete workflow orchestration end-to-end.

    These tests import and use the actual TraditionalWorkflowOrchestrator
    from the example to validate the complete workflow including:
    - Multi-actor coordination
    - Error propagation
    - State management
    - Audit trail generation
    """

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Setup and teardown for each test."""
        ActorRegistry.clear()
        yield
        ActorRegistry.clear()

    @pytest.mark.asyncio
    async def test_complete_onboarding_workflow(self):
        """Test complete employee onboarding workflow end-to-end."""
        # Import the actual example components
        from examples.traditional_automation_complete import (
            EmployeeValidationActor,
            EquipmentProvisioningActor,
            ApprovalWorkflowActor,
            TraditionalWorkflowOrchestrator,
        )

        # Initialize actors
        validation_actor = EmployeeValidationActor()
        validation_actor.configure()

        provisioning_actor = EquipmentProvisioningActor()
        provisioning_actor.configure()

        approval_actor = ApprovalWorkflowActor()
        approval_actor.configure()

        # Create orchestrator
        orchestrator = TraditionalWorkflowOrchestrator(
            validation_actor=validation_actor,
            provisioning_actor=provisioning_actor,
            approval_actor=approval_actor,
        )

        # Test employee data (use unique ID to avoid duplicate check failures)
        employee_data = {
            "employee_id": "EMP-999001",
            "email": "workflow.test@example.com",
            "role": "Senior Developer",
            "department": "Engineering",
            "employee_type": "internal",
        }

        # Process workflow
        result = await orchestrator.process_employee_onboarding(employee_data)

        # Validate workflow completed successfully
        assert result["status"] == "completed"
        assert result["employee_id"] == "EMP-999001"
        assert len(result["steps"]) > 0

        # Validate all workflow steps executed
        assert "id_validation" in result["steps"]
        assert "role_validation" in result["steps"]
        assert "department_validation" in result["steps"]
        assert "budget" in result["steps"]
        assert "package" in result["steps"]
        assert "order" in result["steps"]

        # Validate audit trail
        assert len(orchestrator.audit_trail) > 0

        # Validate business logic applied correctly
        assert result["steps"]["budget"]["final_budget"] > 0
        assert result["steps"]["package"]["package_name"] in [
            "basic",
            "standard",
            "professional",
            "executive",
        ]

    @pytest.mark.asyncio
    async def test_workflow_validation_failure(self):
        """Test workflow handles validation failures correctly."""
        from examples.traditional_automation_complete import (
            EmployeeValidationActor,
            EquipmentProvisioningActor,
            ApprovalWorkflowActor,
            TraditionalWorkflowOrchestrator,
        )

        # Initialize actors
        validation_actor = EmployeeValidationActor()
        validation_actor.configure()

        provisioning_actor = EquipmentProvisioningActor()
        provisioning_actor.configure()

        approval_actor = ApprovalWorkflowActor()
        approval_actor.configure()

        orchestrator = TraditionalWorkflowOrchestrator(
            validation_actor=validation_actor,
            provisioning_actor=provisioning_actor,
            approval_actor=approval_actor,
        )

        # Invalid employee data (bad ID format)
        employee_data = {
            "employee_id": "INVALID",
            "email": "test@example.com",
            "role": "Developer",
            "department": "Engineering",
        }

        # Process workflow
        result = await orchestrator.process_employee_onboarding(employee_data)

        # Validate workflow failed properly
        assert result["status"] == "failed"
        assert len(result["errors"]) > 0
        assert "id_validation" in result["steps"]
        assert result["steps"]["id_validation"]["valid"] is False

    @pytest.mark.asyncio
    async def test_workflow_audit_trail(self):
        """Test that workflow generates complete audit trail."""
        from examples.traditional_automation_complete import (
            EmployeeValidationActor,
            EquipmentProvisioningActor,
            ApprovalWorkflowActor,
            TraditionalWorkflowOrchestrator,
        )

        # Initialize actors
        validation_actor = EmployeeValidationActor()
        validation_actor.configure()

        provisioning_actor = EquipmentProvisioningActor()
        provisioning_actor.configure()

        approval_actor = ApprovalWorkflowActor()
        approval_actor.configure()

        orchestrator = TraditionalWorkflowOrchestrator(
            validation_actor=validation_actor,
            provisioning_actor=provisioning_actor,
            approval_actor=approval_actor,
        )

        employee_data = {
            "employee_id": "EMP-999999",
            "email": "audit.test@example.com",
            "role": "Manager",
            "department": "Sales",
            "employee_type": "internal",
        }

        # Process workflow
        await orchestrator.process_employee_onboarding(employee_data)

        # Validate audit trail captured all steps
        assert len(orchestrator.audit_trail) > 0

        # Check audit trail structure
        for entry in orchestrator.audit_trail:
            assert "timestamp" in entry
            assert "step" in entry
            assert "actor" in entry
            assert "result" in entry

        # Verify step names are meaningful
        step_names = [entry["step"] for entry in orchestrator.audit_trail]
        assert "validate_id" in step_names
        assert "calculate_budget" in step_names
        assert "create_order" in step_names


class TestPerformance:
    """Test performance characteristics of traditional automation."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Setup and teardown for each test."""
        ActorRegistry.clear()
        yield
        ActorRegistry.clear()

    def test_execution_speed(self):
        """Test that deterministic execution is fast."""
        import time

        actor = TestBusinessRulesActor()
        actor.configure()

        # Time 1000 executions
        start = time.time()
        for i in range(1000):
            actor.calculate_discount(tier="silver", amount=1000.0 + i)
        duration = time.time() - start

        # Should be very fast (< 1 second for 1000 executions)
        assert duration < 1.0

        # Calculate average time per execution
        avg_time = duration / 1000
        print(f"\nAverage execution time: {avg_time * 1000:.2f}ms")

    def test_zero_llm_calls(self):
        """Test that no LLM calls are made."""
        actor = TestValidationActor()
        actor.configure()

        # Execute multiple operations
        actor.validate_format("test@example.com", r"^.*@.*$")
        actor.validate_range(50, 0, 100)

        # Verify no LLM config exists
        assert actor.llm_config is None


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Setup and teardown for each test."""
        ActorRegistry.clear()
        yield
        ActorRegistry.clear()

    def test_empty_string_validation(self):
        """Test validation with empty strings."""
        actor = TestValidationActor()
        actor.configure()

        result = actor.validate_format(value="", pattern=r"^[a-zA-Z]+$")
        assert result["valid"] is False

    def test_boundary_values(self):
        """Test boundary value conditions."""
        actor = TestValidationActor()
        actor.configure()

        # Exactly at min boundary
        result = actor.validate_range(value=0, min_val=0, max_val=100)
        assert result["valid"] is True

        # Exactly at max boundary
        result = actor.validate_range(value=100, min_val=0, max_val=100)
        assert result["valid"] is True

        # Just below min
        result = actor.validate_range(value=-1, min_val=0, max_val=100)
        assert result["valid"] is False

        # Just above max
        result = actor.validate_range(value=101, min_val=0, max_val=100)
        assert result["valid"] is False

    def test_zero_amount_discount(self):
        """Test discount calculation with zero amount."""
        actor = TestBusinessRulesActor()
        actor.configure()

        result = actor.calculate_discount(tier="gold", amount=0.0)
        assert result["discount_amount"] == 0.0
        assert result["final_amount"] == 0.0

    def test_negative_amount_handling(self):
        """Test handling of negative amounts."""
        actor = TestBusinessRulesActor()
        actor.configure()

        # Negative amounts should still calculate (business logic dependent)
        result = actor.calculate_discount(tier="silver", amount=-100.0)
        assert result["discount_rate"] == 0.10
        # Note: Real implementation might reject negative amounts


class TestAuditTrail:
    """Test audit trail and logging capabilities."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Setup and teardown for each test."""
        ActorRegistry.clear()
        yield
        ActorRegistry.clear()

    def test_operation_returns_metadata(self):
        """Test that operations return rich metadata."""
        actor = TestValidationActor()
        actor.configure()

        result = actor.validate_format(value="test@example.com", pattern=r"^.*@.*$")

        # Should include all input parameters
        assert "value" in result
        assert "pattern" in result
        assert "valid" in result

        # All values should be present
        assert result["value"] == "test@example.com"
        assert result["pattern"] == r"^.*@.*$"

    def test_business_rule_includes_reasoning(self):
        """Test that business rules include reasoning."""
        actor = TestBusinessRulesActor()
        actor.configure()

        result = actor.calculate_discount(tier="platinum", amount=1000.0)

        # Should include all decision factors
        assert "tier" in result
        assert "discount_rate" in result
        assert "original_amount" in result
        assert "discount_amount" in result
        assert "final_amount" in result

        # Can reconstruct the calculation
        expected = result["original_amount"] * result["discount_rate"]
        assert abs(result["discount_amount"] - expected) < 0.01


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
