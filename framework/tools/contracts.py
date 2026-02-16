"""
contracts.py (framework/tools) JAF-82: Tool contract metadata and decorator for JAF tools.

- Defines ToolContract: a metadata-only class for declaring input/output schemas on tool functions.
- Provides @tool_contract decorator to attach schema metadata to tools without enforcing validation or runtime wrapping.
- This file is independent of core data contracts to avoid circular dependencies and to allow tool contracts to be used in any context (including plugins or extensions) without importing the full data layer.
- All type checks are runtime-only; no static type enforcement.
"""

from __future__ import annotations

from typing import Optional, Type

# =============================================================================
# ToolContract (METADATA ONLY)
# =============================================================================


class ToolContract:
    """
    Metadata object attached to a tool function.

    - Declares input/output schema types (DataContract subclasses)
    - Does NOT perform execution wrapping
    - Validation is orchestrated by the engine
    - Used for documentation, registry inspection, and runtime checks
    """

    def __init__(
        self,
        *,
        input: Optional[Type] = None,
        output: Optional[Type] = None,
    ):
        self.input = input
        self.output = output

    # -------------------------------------------------------------------------
    # Validation helpers (called by engine, not decorator)
    # -------------------------------------------------------------------------

    def validate_input(self, value):
        """
        Validate input data using the declared input DataContract.
        Raises DataValidationError on failure.
        """
        if not self.input:
            return value

        try:
            return self.input.model_validate(value)
        except Exception as ve:
            from framework.data.validation import DataValidationError

            raise DataValidationError(
                direction="input",
                tool=getattr(self.input, "__name__", str(self.input)),
                message=str(ve),
                details=ve.errors() if hasattr(ve, "errors") else {},
            )

    def validate_output(self, value):
        """
        Validate output data using the declared output DataContract.
        Raises DataValidationError on failure.
        """
        if not self.output:
            return value

        try:
            return self.output.model_validate(value)
        except Exception as ve:
            from framework.data.validation import DataValidationError

            raise DataValidationError(
                direction="output",
                tool=getattr(self.output, "__name__", str(self.output)),
                message=str(ve),
                details=ve.errors() if hasattr(ve, "errors") else {},
            )

    # -------------------------------------------------------------------------
    # Schema & metadata accessors
    # -------------------------------------------------------------------------

    @property
    def input_schema_json(self):
        """
        Returns the JSON schema of the input DataContract, or None if not set.
        Usage: tool.__tool_contract__.input_schema_json
        """
        if self.input and hasattr(self.input, "model_json_schema"):
            return self.input.model_json_schema()
        return None

    @property
    def output_schema_json(self):
        """
        Returns the JSON schema of the output DataContract, or None if not set.
        Usage: tool.__tool_contract__.output_schema_json
        """
        if self.output and hasattr(self.output, "model_json_schema"):
            return self.output.model_json_schema()
        return None

    def to_schema_dict(self) -> dict:
        """
        Returns a standard dict with input/output schema info for registry use.
        """
        return {
            "input_schema": self.input_schema_json,
            "output_schema": self.output_schema_json,
            "input_type": getattr(self.input, "__name__", None),
            "output_type": getattr(self.output, "__name__", None),
        }

    def __repr__(self) -> str:
        """
        Developer-friendly representation for debugging & logs.
        """
        return (
            f"ToolContract(input={getattr(self.input, '__name__', None)}, "
            f"output={getattr(self.output, '__name__', None)})"
        )


# =============================================================================
# @tool_contract decorator
# =============================================================================


def tool_contract(
    *,
    input: Optional[Type] = None,
    output: Optional[Type] = None,
):
    """
    Declare typed input/output schemas for a tool.

    Example:
        @tool_contract(input=EmployeeData, output=EquipmentOrder)
        def create_order(self, data: EmployeeData) -> EquipmentOrder:
            ...

    NOTES:
    - Metadata only (no wrapping)
    - Validation happens in the engine
    - Untyped tools continue to work
    """

    # -------------------------------------------------------------------------
    # Validation at DECORATION TIME
    # -------------------------------------------------------------------------
    from framework.data.contracts import DataContract

    if input is not None:
        if not isinstance(input, type) or not issubclass(input, DataContract):
            raise TypeError("tool_contract 'input' must be a DataContract subclass")

    if output is not None:
        if not isinstance(output, type) or not issubclass(output, DataContract):
            raise TypeError("tool_contract 'output' must be a DataContract subclass")

    contract = ToolContract(input=input, output=output)

    def decorator(func):
        func.__tool_contract__ = contract
        return func

    return decorator
