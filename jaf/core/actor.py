"""
JAF Actor Base Class

The Actor is the atomic unit of functionality in JAF.
It encapsulates state, capabilities (tools), and optional LLM configuration.

Key Principles (from Actor Model):
1. Share Nothing: Actors don't share memory
2. Message Passing: Communication via async messages
3. Supervision: Parent actors manage child failures
4. Location Transparency: Actors can be local or remote

Actor Types:
- Intelligent Actor: Has LLM config, makes decisions
- Deterministic Actor: No LLM, hardcoded logic (traditional automation)
"""

from abc import ABC
from typing import Any, Callable, Dict, List, Optional, Type
import inspect
import logging

from jaf.core.models import LLMConfig


logger = logging.getLogger(__name__)


class Tool:
    """
    Decorator and wrapper for actor tools.
    
    Tools are deterministic functions that actors can invoke.
    They are the "hands" of the actor - how it affects the world.
    
    Usage:
        ```python
        @Tool(description="Check if employee is eligible for equipment")
        def check_eligibility(employee_id: str) -> bool:
            # Implementation
            return True
        ```
    """
    
    def __init__(
        self,
        description: str = "",
        returns: str = "",
    ):
        """
        Initialize tool decorator.
        
        Args:
            description: Human-readable description of what the tool does
            returns: Description of the return value
        """
        self.description = description
        self.returns = returns
        self._func: Optional[Callable] = None
    
    def __call__(self, func: Callable) -> "Tool":
        """Apply decorator to function."""
        self._func = func
        self.name = func.__name__
        
        # Extract description from docstring if not provided
        if not self.description and func.__doc__:
            self.description = func.__doc__.strip().split("\n")[0]
        
        return self
    
    def invoke(self, *args, **kwargs) -> Any:
        """Invoke the wrapped function."""
        if self._func is None:
            raise RuntimeError("Tool function not set")
        return self._func(*args, **kwargs)
    
    async def ainvoke(self, *args, **kwargs) -> Any:
        """Invoke the wrapped function (async-safe)."""
        if self._func is None:
            raise RuntimeError("Tool function not set")
        
        if inspect.iscoroutinefunction(self._func):
            return await self._func(*args, **kwargs)
        return self._func(*args, **kwargs)
    
    def to_schema(self) -> Dict[str, Any]:
        """
        Convert tool to JSON schema for LLM function calling.
        
        Returns:
            OpenAI-compatible function schema
        """
        if self._func is None:
            return {}
        
        # Extract parameters from function signature
        sig = inspect.signature(self._func)
        parameters = {
            "type": "object",
            "properties": {},
            "required": [],
        }
        
        for name, param in sig.parameters.items():
            if name == "self":
                continue
            
            # Basic type mapping
            type_map = {
                str: "string",
                int: "integer",
                float: "number",
                bool: "boolean",
                list: "array",
                dict: "object",
            }
            
            param_type = "string"  # default
            if param.annotation != inspect.Parameter.empty:
                param_type = type_map.get(param.annotation, "string")
            
            parameters["properties"][name] = {
                "type": param_type,
                "description": f"Parameter: {name}",
            }
            
            if param.default == inspect.Parameter.empty:
                parameters["required"].append(name)
        
        return {
            "name": self.name,
            "description": self.description,
            "parameters": parameters,
        }


class Actor(ABC):
    """
    Base class for all actors in the JAF framework.
    
    An Actor encapsulates:
    - name: Unique identifier
    - description: What this actor does
    - goal: The actor's primary objective
    - tools: Deterministic functions the actor can invoke
    - llm_config: Optional LLM configuration for intelligent actors
    
    Example:
        ```python
        class ProvisioningActor(Actor):
            name = "ProvisioningActor"
            description = "Provisions hardware for employees"
            goal = "Provide appropriate PC and phone for new hires"
            
            llm_config = LLMConfig(model="gpt-5-nano", temperature=0)
            
            @Tool(description="Check if employee is eligible")
            def check_eligibility(self, employee_id: str) -> bool:
                return True
        ```
    """
    
    # Class attributes (override in subclasses)
    name: str = "BaseActor"
    description: str = "Base actor class"
    goal: str = "No specific goal"
    
    # Optional LLM configuration
    llm_config: Optional[LLMConfig] = None
    
    def __init__(self):
        """Initialize the actor and discover tools."""
        self._tools: Dict[str, Tool] = {}
        self._discover_tools()
        
        # Register with global registry
        ActorRegistry.register(self)
    
    def _discover_tools(self) -> None:
        """Discover all Tool-decorated methods on this actor.
        
        Creates bound copies of each Tool so that the actor instance
        is automatically passed as 'self' when the tool is invoked.
        The bound tools are also set as instance attributes so that
        ``actor.tool_name`` returns the bound version.
        """
        import copy
        import functools
        
        for attr_name in dir(self.__class__):
            if attr_name.startswith("_"):
                continue
            
            attr = getattr(self.__class__, attr_name, None)
            
            # Check if it's a Tool instance
            if isinstance(attr, Tool) and attr._func is not None:
                # Create a bound copy so invoke() passes the actor as 'self'
                bound_tool = copy.copy(attr)
                bound_tool._func = functools.partial(attr._func, self)
                self._tools[bound_tool.name] = bound_tool
                # Shadow the class attribute with the bound instance attribute
                object.__setattr__(self, attr_name, bound_tool)
                logger.debug(f"Discovered tool: {self.name}.{bound_tool.name}")
    
    @property
    def tools(self) -> List[Tool]:
        """Get list of available tools."""
        return list(self._tools.values())
    
    @property
    def tool_names(self) -> List[str]:
        """Get list of tool names."""
        return list(self._tools.keys())
    
    @property
    def is_intelligent(self) -> bool:
        """Check if this actor has LLM capabilities."""
        return self.llm_config is not None
    
    def get_tool(self, name: str) -> Optional[Tool]:
        """Get a tool by name."""
        return self._tools.get(name)
    
    def get_tools_schema(self) -> List[Dict[str, Any]]:
        """Get OpenAI-compatible function schemas for all tools."""
        return [tool.to_schema() for tool in self.tools]
    
    async def execute(
        self,
        action: str,
        parameters: Dict[str, Any],
    ) -> Any:
        """
        Execute a tool with given parameters.
        
        Args:
            action: Tool name to invoke
            parameters: Parameters to pass to the tool
            
        Returns:
            Tool output
            
        Raises:
            ValueError: If tool not found
            ExecutionError: If tool execution fails
        """
        tool = self.get_tool(action)
        if tool is None:
            raise ValueError(
                f"Tool '{action}' not found on {self.name}. "
                f"Available: {', '.join(self.tool_names)}"
            )
        
        logger.info(f"Executing {self.name}.{action} with {parameters}")
        
        try:
            result = await tool.ainvoke(**parameters)
            logger.info(f"Tool {action} returned: {result}")
            return result
        except Exception as e:
            logger.error(f"Tool {action} failed: {e}")
            raise
    
    def __repr__(self) -> str:
        """String representation."""
        tools_str = ", ".join(self.tool_names) if self.tool_names else "none"
        llm_str = self.llm_config.model if self.llm_config else "none"
        return (
            f"<{self.__class__.__name__} "
            f"name={self.name} "
            f"tools=[{tools_str}] "
            f"llm={llm_str}>"
        )


class ActorRegistry:
    """
    Global registry for actor instances.
    
    Provides discovery and lookup of actors by name.
    Used by engines to find actors referenced in plans.
    
    Usage:
        ```python
        # Actors auto-register on instantiation
        provisioning = ProvisioningActor()
        
        # Lookup by name
        actor = ActorRegistry.get("ProvisioningActor")
        
        # List all actors
        all_actors = ActorRegistry.all()
        ```
    """
    
    _actors: Dict[str, Actor] = {}
    
    @classmethod
    def register(cls, actor: Actor) -> None:
        """
        Register an actor instance.
        
        Args:
            actor: Actor instance to register
        """
        cls._actors[actor.name] = actor
        logger.info(f"Registered actor: {actor.name}")
    
    @classmethod
    def unregister(cls, name: str) -> Optional[Actor]:
        """
        Unregister an actor by name.
        
        Args:
            name: Actor name
            
        Returns:
            Removed actor or None
        """
        return cls._actors.pop(name, None)
    
    @classmethod
    def get(cls, name: str) -> Optional[Actor]:
        """
        Get an actor by name.
        
        Args:
            name: Actor name
            
        Returns:
            Actor instance or None
        """
        return cls._actors.get(name)
    
    @classmethod
    def all(cls) -> List[Actor]:
        """Get all registered actors."""
        return list(cls._actors.values())
    
    @classmethod
    def names(cls) -> List[str]:
        """Get all registered actor names."""
        return list(cls._actors.keys())
    
    @classmethod
    def clear(cls) -> None:
        """Clear all registered actors (for testing)."""
        cls._actors.clear()
    
    @classmethod
    def count(cls) -> int:
        """Get number of registered actors."""
        return len(cls._actors)


def actor(
    name: Optional[str] = None,
    description: Optional[str] = None,
    goal: Optional[str] = None,
    llm_config: Optional[LLMConfig] = None,
) -> Callable[[Type], Type[Actor]]:
    """
    Class decorator for creating actors.
    
    Usage:
        ```python
        @actor(
            name="MyActor",
            description="Does something useful",
            goal="Accomplish the task",
            llm_config=LLMConfig(model="gpt-5-nano"),
        )
        class MyActor(Actor):
            @Tool(description="Do the thing")
            def do_thing(self, input: str) -> str:
                return f"Done: {input}"
        ```
    """
    def decorator(cls: Type) -> Type[Actor]:
        # Set class attributes if provided
        if name:
            cls.name = name
        elif not hasattr(cls, "name") or cls.name == "BaseActor":
            cls.name = cls.__name__
        
        if description:
            cls.description = description
        elif not hasattr(cls, "description"):
            cls.description = cls.__doc__ or "No description"
        
        if goal:
            cls.goal = goal
        
        if llm_config:
            cls.llm_config = llm_config
        
        return cls
    
    return decorator

