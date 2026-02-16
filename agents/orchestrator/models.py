"""
Orchestrator Models - Request/Response schemas for the orchestrator
"""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    prompt: str
    trace_id: Optional[str] = Field(
        default=None, description="Optional trace ID for correlation"
    )
    memory_context: Optional[Dict[str, Any]] = Field(
        default=None, description="Optional memory context"
    )


class AskResponse(BaseModel):
    answer: str
    correlation_id: str = Field(default="", description="Request correlation ID")
    trace_id: str = Field(default="", description="Trace ID for debugging")
    agents_used: List[str] = Field(
        default=[], description="List of agents that participated"
    )
    execution_time_ms: float = Field(
        default=0.0, description="Execution time in milliseconds"
    )
    plan: Optional[str] = Field(default=None, description="Generated execution plan")
