"""
Test actors for end-to-end integration tests.

These actors are deterministic (no LLM) and designed to exercise
the full framework capabilities.
"""

from typing import Dict, Any
from framework.actor.base_actor import Actor


class CalculatorActor(Actor):
    """Actor that performs arithmetic operations."""

    def configure(self) -> None:
        self.name = "CalculatorActor"
        self.description = "Performs arithmetic calculations"
        self.goal = "Execute mathematical operations accurately"
        self.tools = [self.add, self.multiply, self.divide]
        self.utilities = []
        self.llm_config = None  # Deterministic actor

    def add(self, a: float, b: float) -> Dict[str, Any]:
        """Add two numbers."""
        result = a + b
        return {
            "operation": "add",
            "inputs": {"a": a, "b": b},
            "result": result,
            "success": True,
        }

    def multiply(self, a: float, b: float) -> Dict[str, Any]:
        """Multiply two numbers."""
        result = a * b
        return {
            "operation": "multiply",
            "inputs": {"a": a, "b": b},
            "result": result,
            "success": True,
        }

    def divide(self, a: float, b: float) -> Dict[str, Any]:
        """Divide two numbers."""
        if b == 0:
            return {
                "operation": "divide",
                "inputs": {"a": a, "b": b},
                "error": "Division by zero",
                "success": False,
            }
        result = a / b
        return {
            "operation": "divide",
            "inputs": {"a": a, "b": b},
            "result": result,
            "success": True,
        }


class ValidatorActor(Actor):
    """Actor that validates computation results."""

    def configure(self) -> None:
        self.name = "ValidatorActor"
        self.description = "Validates computation results"
        self.goal = "Ensure results meet quality criteria"
        self.tools = [self.validate_positive, self.validate_range, self.validate_type]
        self.utilities = []
        self.llm_config = None  # Deterministic actor

    def validate_positive(self, value: float) -> Dict[str, Any]:
        """Validate that a value is positive."""
        is_valid = value > 0
        return {
            "validation": "positive",
            "value": value,
            "is_valid": is_valid,
            "message": "Value is positive" if is_valid else "Value must be positive",
        }

    def validate_range(
        self, value: float, min_val: float, max_val: float
    ) -> Dict[str, Any]:
        """Validate that a value is within a range."""
        is_valid = min_val <= value <= max_val
        return {
            "validation": "range",
            "value": value,
            "range": {"min": min_val, "max": max_val},
            "is_valid": is_valid,
            "message": (
                f"Value is in range [{min_val}, {max_val}]"
                if is_valid
                else f"Value must be between {min_val} and {max_val}"
            ),
        }

    def validate_type(self, value: Any, expected_type: str) -> Dict[str, Any]:
        """Validate that a value is of expected type."""
        type_map = {
            "int": int,
            "float": float,
            "str": str,
            "bool": bool,
        }
        expected = type_map.get(expected_type)
        if expected is None:
            return {
                "validation": "type",
                "value": value,
                "is_valid": False,
                "message": f"Unknown type: {expected_type}",
            }

        is_valid = isinstance(value, expected)
        return {
            "validation": "type",
            "value": value,
            "expected_type": expected_type,
            "actual_type": type(value).__name__,
            "is_valid": is_valid,
            "message": (
                f"Value is {expected_type}"
                if is_valid
                else f"Value must be {expected_type}"
            ),
        }


class DataProcessorActor(Actor):
    """Actor that processes and transforms data."""

    def configure(self) -> None:
        self.name = "DataProcessorActor"
        self.description = "Processes and transforms data"
        self.goal = "Clean and transform data efficiently"
        self.tools = [self.normalize, self.aggregate, self.filter_data]
        self.utilities = []
        self.llm_config = None  # Deterministic actor

    def normalize(self, values: list[float]) -> Dict[str, Any]:
        """Normalize a list of values to 0-1 range."""
        if not values:
            return {
                "operation": "normalize",
                "error": "Empty list",
                "success": False,
            }

        min_val = min(values)
        max_val = max(values)

        if min_val == max_val:
            normalized = [0.5] * len(values)
        else:
            normalized = [(v - min_val) / (max_val - min_val) for v in values]

        return {
            "operation": "normalize",
            "input_count": len(values),
            "output": normalized,
            "range": {"min": min_val, "max": max_val},
            "success": True,
        }

    def aggregate(self, values: list[float], operation: str = "sum") -> Dict[str, Any]:
        """Aggregate a list of values."""
        if not values:
            return {
                "operation": f"aggregate_{operation}",
                "error": "Empty list",
                "success": False,
            }

        operations = {
            "sum": sum(values),
            "avg": sum(values) / len(values),
            "min": min(values),
            "max": max(values),
        }

        if operation not in operations:
            return {
                "operation": f"aggregate_{operation}",
                "error": f"Unknown operation: {operation}",
                "success": False,
            }

        return {
            "operation": f"aggregate_{operation}",
            "input_count": len(values),
            "result": operations[operation],
            "success": True,
        }

    def filter_data(
        self, values: list[float], threshold: float, condition: str = "gt"
    ) -> Dict[str, Any]:
        """Filter values based on a condition."""
        conditions = {
            "gt": lambda x: x > threshold,
            "gte": lambda x: x >= threshold,
            "lt": lambda x: x < threshold,
            "lte": lambda x: x <= threshold,
            "eq": lambda x: x == threshold,
        }

        if condition not in conditions:
            return {
                "operation": f"filter_{condition}",
                "error": f"Unknown condition: {condition}",
                "success": False,
            }

        filtered = [v for v in values if conditions[condition](v)]

        return {
            "operation": f"filter_{condition}",
            "input_count": len(values),
            "output": filtered,
            "output_count": len(filtered),
            "threshold": threshold,
            "success": True,
        }
