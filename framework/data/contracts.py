"""
contracts.py JAF-81: Core data contract and schema utilities for JAF framework.

- Defines DataContract: base class for all typed data exchanged between actors/tools, enforcing strict validation and serialization.
- Defines DataEnvelope: wrapper for provenance metadata (created_by, source_step_id, etc) around DataContract payloads.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TypeVar, Generic, Dict, Any, List, Optional, Type

from pydantic import BaseModel, Field, ConfigDict, ValidationError

# ============================================================================
# Types
# ============================================================================

T = TypeVar("T", bound=BaseModel)

# ============================================================================
# Base DataContract
# ============================================================================


class DataContract(BaseModel):
    """
    Base class for typed data flowing between actors.

    All data passed between actors MUST inherit from this class.
    It enforces:
    - strict validation
    - immutability
    - explicit schemas
    - safe serialization at actor boundaries
    """

    model_config = ConfigDict(
        extra="forbid",  # Catch unknown / mistyped fields
        frozen=True,  # Immutable by default
        validate_assignment=True,  # Extra safety if ever copied
    )

    # ------------------------------------------------------------------
    # Serialization helpers
    # ------------------------------------------------------------------

    def to_context(self) -> Dict[str, Any]:
        """
        Serialize the contract for storage in execution context.
        Safe for persistence, logs, and transport.
        """
        return self.model_dump(mode="json")

    @classmethod
    def from_context(cls: Type[T], data: Dict[str, Any]) -> T:
        """
        Deserialize a contract from execution context.
        Raises a clear ValueError if schema mismatch occurs.
        """
        try:
            return cls.model_validate(data)
        except ValidationError as e:
            # Raise ValueError with details, since ValidationError cannot be reconstructed from string in Pydantic v2
            raise ValueError(
                f"Failed to deserialize {cls.__name__} from context: {e.errors()}"
            ) from e

    # ------------------------------------------------------------------
    # Introspection helpers
    # ------------------------------------------------------------------

    @classmethod
    def schema_name(cls) -> str:
        """Stable identifier for documentation & debugging."""
        return cls.__name__

    @classmethod
    def schema_version(cls) -> str:
        """Override in subclasses when breaking changes occur."""
        return "1.0"


# ============================================================================
# DataEnvelope
# ============================================================================


class DataEnvelope(BaseModel, Generic[T]):
    """
    Wrapper adding provenance metadata to a DataContract payload.

    Used when tracking:
    - who produced the data
    - when it was produced
    - from which step
    """

    payload: T

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when the payload was created",
    )

    created_by: str = Field(
        ..., min_length=1, description="Actor name that produced the payload"
    )

    source_step_id: Optional[str] = Field(
        default=None, description="Optional step identifier that generated the payload"
    )

    source_keys: Optional[List[str]] = Field(
        default=None,
        description="Optional data context keys this payload was derived from (lineage)",
    )

    schema_version: str = Field(
        default="1.0", description="Schema version of the payload"
    )

    model_config = ConfigDict(extra="forbid", frozen=True)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def unwrap(self) -> T:
        """Return the underlying payload."""
        return self.payload

    def to_context(self) -> Dict[str, Any]:
        """Serialize envelope + payload for context storage."""
        return self.model_dump(mode="json")

    @classmethod
    def from_context(cls, data: Dict[str, Any]) -> "DataEnvelope[T]":
        """Deserialize an envelope from context."""
        try:
            return cls.model_validate(data)
        except ValidationError as e:
            raise ValueError(
                f"Failed to deserialize DataEnvelope from context: {e.errors()}"
            ) from e
