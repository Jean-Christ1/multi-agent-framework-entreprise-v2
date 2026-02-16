"""
Orchestrator Utilities - Helper functions for the orchestrator
"""

from typing import Dict, Any, Callable, List, Tuple
from crewai.tools import BaseTool
import sys
import os
from datetime import datetime, timezone
from uuid import uuid4

# Add project root to path for imports
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from utils.observability import StructuredLogger, trace_operation
from .session import get_trace_id


class ToolExecutionGuardError(Exception):
    """Raised when a tool is executed without required preconditions."""

    pass


class TraceSession:
    """Maintain execution context for a trace."""

    def __init__(self):
        self.discovery_called = False
        self.executed_tools = []
        self.event_listeners: List[Tuple[str, Callable[[Dict[str, Any]], None]]] = []


_trace_sessions: Dict[str, TraceSession] = {}


def get_trace_session() -> TraceSession:
    """Return session for current trace, creating it if necessary."""

    trace_id = get_trace_id()
    if not trace_id:
        raise ToolExecutionGuardError(
            "Trace ID not set; orchestrator must set current trace before executing tools."
        )

    if trace_id not in _trace_sessions:
        _trace_sessions[trace_id] = TraceSession()
    return _trace_sessions[trace_id]


def reset_trace_session(trace_id: str):
    """Remove stored session for the given trace identifier."""

    if trace_id in _trace_sessions:
        del _trace_sessions[trace_id]


def register_trace_event_callback(
    callback: Callable[[Dict[str, Any]], None], trace_id: str | None = None
) -> str:
    """Register a callback to receive structured events for the current trace.

    Returns a listener identifier that can be used to unregister later.
    """

    if trace_id:
        session = _trace_sessions.setdefault(trace_id, TraceSession())
    else:
        session = get_trace_session()
    listener_id = str(uuid4())
    session.event_listeners.append((listener_id, callback))
    logger.debug("Registered trace event callback", listener_id=listener_id)
    return listener_id


def unregister_trace_event_callback(listener_id: str, trace_id: str | None = None):
    """Remove a previously registered trace event callback for the current trace."""

    if trace_id:
        session = _trace_sessions.get(trace_id)
        if not session:
            return
    else:
        session = get_trace_session()
    before = len(session.event_listeners)
    session.event_listeners = [
        (lid, cb) for (lid, cb) in session.event_listeners if lid != listener_id
    ]
    if len(session.event_listeners) != before:
        logger.debug("Unregistered trace event callback", listener_id=listener_id)


def emit_trace_event(event_type: str, payload: Dict[str, Any] | None = None):
    """Emit a structured event to all listeners registered for the current trace."""

    try:
        session = get_trace_session()
    except ToolExecutionGuardError:
        # If emitted outside an active trace, silently ignore to maintain backward compatibility
        return

    if not session.event_listeners:
        return

    event_payload = payload.copy() if payload else {}
    event = {
        "type": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **event_payload,
    }

    for listener_id, callback in list(session.event_listeners):
        try:
            callback(event)
        except Exception as exc:
            logger.warning(
                "Trace event callback error",
                listener_id=listener_id,
                error=str(exc),
                event_type=event_type,
            )


logger = StructuredLogger(__name__)


def create_tool_from_method(
    agent_instance,
    method_name: str,
    tool_description: str,
    input_schema: Dict = None,
    result_as_answer: bool = False,
) -> BaseTool:
    """Create a CrewAI Tool from an agent method with proper parameter schema"""
    method = getattr(agent_instance, method_name)
    tool_name = f"{agent_instance.name}_{method_name}"

    # Enhanced description with clear parameter info for CrewAI
    enhanced_description = tool_description
    if input_schema:
        params_list = []
        for key, value in input_schema.items():
            params_list.append(f"{key} ({value})")
        enhanced_description += f"\nRequired parameters: {', '.join(params_list)}"

    # Capture parameter in outer scope before class definition
    force_result_flag = result_as_answer
    agent_label = getattr(agent_instance, "name", "UnknownAgent")

    # Create a dynamic tool class for this method
    class DynamicTool(BaseTool):
        name: str = tool_name
        description: str = enhanced_description
        result_as_answer: bool = force_result_flag  # Force tool output as result

        def __init__(self):
            super().__init__()
            # Set the args_schema if we have input_schema
            if input_schema:
                from pydantic import create_model, Field

                # Convert input_schema to pydantic field definitions with validation
                fields = {}
                for field_name, field_type in input_schema.items():
                    if field_type == "str":
                        fields[field_name] = (
                            str,
                            Field(
                                ...,
                                max_length=1000,
                                description=f"String parameter {field_name}",
                            ),
                        )
                    elif field_type == "int":
                        fields[field_name] = (
                            int,
                            Field(
                                ...,
                                ge=-2147483648,
                                le=2147483647,
                                description=f"Integer parameter {field_name}",
                            ),
                        )
                    elif field_type == "bool":
                        fields[field_name] = (
                            bool,
                            Field(..., description=f"Boolean parameter {field_name}"),
                        )
                    elif field_type == "array" or field_type == "list":
                        from typing import List

                        fields[field_name] = (
                            List[str],
                            Field(..., description=f"Array parameter {field_name}"),
                        )
                    elif field_type == "object" or field_type == "dict":
                        fields[field_name] = (
                            dict,
                            Field(..., description=f"Object parameter {field_name}"),
                        )
                    else:
                        fields[field_name] = (
                            str,
                            Field(
                                ...,
                                max_length=1000,
                                description=f"Parameter {field_name}",
                            ),
                        )  # Default to string with limits

                # Create the schema model with validation
                ArgsSchema = create_model(f"{tool_name}Args", **fields)
                self.args_schema = ArgsSchema

        def _sanitize_input(self, value: Any) -> Any:
            """Sanitize input to prevent injection attacks"""
            if isinstance(value, str):
                # Remove potential injection patterns
                import re

                # Remove script tags, SQL injection patterns, etc.
                value = re.sub(
                    r"<script.*?</script>", "", value, flags=re.IGNORECASE | re.DOTALL
                )
                value = re.sub(
                    r"(union|select|insert|delete|drop|update|exec|execute)\s",
                    "",
                    value,
                    flags=re.IGNORECASE,
                )
                # Limit length to prevent buffer overflow
                value = value[:1000]
            elif isinstance(value, dict):
                # Recursively sanitize dictionary values
                return {
                    k: self._sanitize_input(v)
                    for k, v in value.items()
                    if len(str(k)) < 100
                }
            elif isinstance(value, list):
                # Limit list size and sanitize elements
                return [
                    self._sanitize_input(item) for item in value[:50]
                ]  # Max 50 items
            return value

        def _validate_and_extract_params(self, *args, **kwargs) -> Dict[str, Any]:
            """Safely validate and extract parameters with comprehensive error handling"""
            validated_params = {}

            # Start with provided kwargs
            if kwargs:
                validated_params.update(kwargs)

            # Process args with multiple extraction strategies
            for i, arg in enumerate(args):
                logger.info(
                    f"🔍 Processing ARG[{i}]: {tool_name}",
                    arg_value=str(arg)[:200],
                    arg_type=type(arg).__name__,
                )

                try:
                    # Strategy 1: JSON string parsing with validation
                    if isinstance(arg, str) and arg.strip().startswith("{"):
                        import json

                        try:
                            parsed = json.loads(arg)
                            if isinstance(parsed, dict):
                                # Validate against allowed parameters
                                if input_schema:
                                    filtered_parsed = {
                                        k: v
                                        for k, v in parsed.items()
                                        if k in input_schema
                                    }
                                    validated_params.update(filtered_parsed)
                                    logger.info(
                                        f"✅ JSON parsed and filtered: {tool_name}",
                                        params=list(filtered_parsed.keys()),
                                    )
                                else:
                                    validated_params.update(parsed)
                                    continue
                        except (json.JSONDecodeError, TypeError) as e:
                            logger.warning(
                                f"JSON parse failed: {tool_name}",
                                error=str(e),
                                arg=str(arg)[:100],
                            )

                    # Strategy 2: Direct dict handling
                    elif isinstance(arg, dict):
                        if input_schema:
                            filtered_dict = {
                                k: v for k, v in arg.items() if k in input_schema
                            }
                            validated_params.update(filtered_dict)
                        else:
                            validated_params.update(arg)
                        logger.info(
                            f"✅ Dict processed: {tool_name}", params=list(arg.keys())
                        )
                        continue

                    # Strategy 3: Query string style (key=value&key2=value2)
                    elif isinstance(arg, str) and "=" in arg:
                        try:
                            # Handle both URL-encoded and simple key=value pairs
                            if "&" in arg or "=" in arg:
                                pairs = arg.split("&") if "&" in arg else [arg]
                                for pair in pairs:
                                    if "=" in pair:
                                        key, value = pair.split("=", 1)
                                        key, value = key.strip(), value.strip()
                                        if not input_schema or key in input_schema:
                                            validated_params[key] = value
                                logger.info(
                                    f"✅ Query string parsed: {tool_name}",
                                    params=list(validated_params.keys()),
                                )
                        except Exception as e:
                            logger.warning(
                                f"Query string parse failed: {tool_name}", error=str(e)
                            )

                    # Strategy 4: Single value handling for single-parameter tools
                    elif input_schema and len(input_schema) == 1:
                        param_name = list(input_schema.keys())[0]
                        validated_params[param_name] = arg
                        logger.info(
                            f"✅ Single param mapped: {tool_name}", param=param_name
                        )

                except Exception as e:
                    logger.error(
                        f"Parameter extraction error: {tool_name}",
                        error=str(e),
                        arg_index=i,
                    )
                    continue

            # Sanitize all parameters
            sanitized_params = {}
            for key, value in validated_params.items():
                sanitized_params[key] = self._sanitize_input(value)

            return sanitized_params

        def _run(self, *args, **kwargs):
            """Execute the tool with enhanced security and error handling"""
            with trace_operation(
                f"tool.{tool_name}",
                attributes={
                    "tool": tool_name,
                    "args_count": len(args),
                    "kwargs_count": len(kwargs),
                },
            ):
                try:
                    logger.info(
                        f"🔧 EXECUTING TOOL: {tool_name}",
                        args_count=len(args),
                        kwargs_count=len(kwargs),
                    )

                    # Track tool execution for telemetry
                    try:
                        session = get_trace_session()
                        session.executed_tools.append(tool_name)
                        if tool_name == "discover_agents":
                            session.discovery_called = True
                    except ToolExecutionGuardError:
                        # Trace session not initialized - continue without tracking
                        pass

                    # Validate and extract parameters safely
                    validated_params = self._validate_and_extract_params(
                        *args, **kwargs
                    )
                    logger.info(
                        f"🔍 VALIDATED PARAMS: {tool_name}",
                        final_params=list(validated_params.keys()),
                        param_count=len(validated_params),
                    )
                    emit_trace_event(
                        "tool_validation",
                        {
                            "tool": tool_name,
                            "agent": agent_label,
                            "parameters": validated_params,
                        },
                    )

                    # Validate required parameters if schema exists
                    if input_schema:
                        missing_params = [
                            param
                            for param in input_schema.keys()
                            if param not in validated_params
                        ]
                        if missing_params:
                            error_msg = f"Missing required parameters: {missing_params}. Provided: {list(validated_params.keys())}. Expected: {list(input_schema.keys())}"
                            logger.error(
                                f"Tool {tool_name} parameter validation failed",
                                error=error_msg,
                            )
                            emit_trace_event(
                                "tool_error",
                                {
                                    "tool": tool_name,
                                    "agent": agent_label,
                                    "error": error_msg,
                                    "phase": "validation",
                                },
                            )
                            return f"ERROR: {error_msg}"

                        # Validate parameter types if possible
                        for param_name, param_type in input_schema.items():
                            if param_name in validated_params:
                                value = validated_params[param_name]
                                if param_type == "int":
                                    try:
                                        validated_params[param_name] = int(value)
                                    except (ValueError, TypeError):
                                        return f"ERROR: Parameter {param_name} must be an integer, got {type(value).__name__}"
                                elif param_type == "str":
                                    validated_params[param_name] = str(value)
                                elif param_type == "bool":
                                    # Handle boolean conversion
                                    if isinstance(value, bool):
                                        validated_params[param_name] = value
                                    elif isinstance(value, str):
                                        validated_params[
                                            param_name
                                        ] = value.lower() in ["true", "yes", "1"]
                                    else:
                                        validated_params[param_name] = bool(value)
                                elif param_type == "array" or param_type == "list":
                                    # Ensure it's a list
                                    if not isinstance(value, list):
                                        validated_params[param_name] = (
                                            [value] if value else []
                                        )
                                elif param_type == "object" or param_type == "dict":
                                    # Ensure it's a dict
                                    if not isinstance(value, dict):
                                        validated_params[param_name] = (
                                            {"value": value} if value else {}
                                        )

                    # Execute method with validated parameters
                    emit_trace_event(
                        "tool_execution",
                        {
                            "tool": tool_name,
                            "agent": agent_label,
                            "parameters": validated_params,
                        },
                    )
                    result = method(**validated_params)

                    logger.info(
                        f"✅ TOOL {tool_name} COMPLETED",
                        result_type=type(result).__name__,
                    )
                    emit_trace_event(
                        "tool_output",
                        {
                            "tool": tool_name,
                            "agent": agent_label,
                            "result": result,
                        },
                    )

                    # Return string for better CrewAI compatibility
                    if isinstance(result, dict):
                        return str(result)
                    else:
                        return str(result)

                except ToolExecutionGuardError as guard_error:
                    logger.error(
                        f"Tool {tool_name} blocked by execution guard",
                        error=str(guard_error),
                    )
                    emit_trace_event(
                        "tool_error",
                        {
                            "tool": tool_name,
                            "agent": agent_label,
                            "error": str(guard_error),
                            "phase": "guard",
                        },
                    )
                    return f"ERROR: {str(guard_error)}"
                except Exception as e:
                    error_msg = f"Tool execution failed: {str(e)}"
                    logger.error(
                        f"Tool {tool_name} execution error",
                        error=error_msg,
                        exception=str(e),
                    )
                    emit_trace_event(
                        "tool_error",
                        {
                            "tool": tool_name,
                            "agent": agent_label,
                            "error": error_msg,
                            "phase": "execution",
                        },
                    )
                    return f"ERROR: {error_msg}"

    return DynamicTool()


__all__ = [
    "create_tool_from_method",
    "ToolExecutionGuardError",
    "get_trace_session",
    "reset_trace_session",
    "register_trace_event_callback",
    "unregister_trace_event_callback",
    "emit_trace_event",
]
