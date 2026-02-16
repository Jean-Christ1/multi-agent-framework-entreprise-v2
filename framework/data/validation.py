"""
validation.py JAF-82: Custom exception for data contract validation errors in JAF.

- Defines DataValidationError for structured reporting of input/output schema validation failures in tools.
- Captures direction (input/output), tool name, error message, and optional details for debugging.
"""

from typing import Optional


class DataValidationError(Exception):
    """
    Raised when input or output data fails validation against a DataContract schema.
    Includes structured context for debugging and reporting.
    """

    def __init__(
        self, *, direction: str, tool: str, message: str, details: Optional[dict] = None
    ):
        self.direction = direction  # 'input' or 'output'
        self.tool = tool
        self.message = message
        self.details = details or {}
        super().__init__(self.__str__())

    def __str__(self):
        base = f"[{self.direction}] Validation failed in tool '{self.tool}': {self.message}"
        if self.details:
            base += f"\nDetails: {self.details}"
        return base
