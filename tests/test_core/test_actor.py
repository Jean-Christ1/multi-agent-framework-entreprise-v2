"""
Tests for JAF Actor System

Tests for Actor base class, Tool decorator, and ActorRegistry.
"""

import pytest

from framework.actor import Actor, ActorRegistry
from framework.types import LLMConfig


class TestTool:
    """Tests for Tool decorator."""

    def test_tool_decorator(self):
        """Tool should decorate functions."""

        @Tool(description="Test tool")
        def my_tool(x: int) -> int:
            return x * 2

        assert my_tool.name == "my_tool"
        assert my_tool.description == "Test tool"

    def test_tool_invoke(self):
        """Tool.invoke should call the wrapped function."""

        @Tool(description="Multiply by 2")
        def double(x: int) -> int:
            return x * 2

        result = double.invoke(5)
        assert result == 10

    @pytest.mark.asyncio
    async def test_tool_ainvoke(self):
        """Tool.ainvoke should work with sync functions."""

        @Tool(description="Add numbers")
        def add(a: int, b: int) -> int:
            return a + b

        result = await add.ainvoke(3, 4)
        assert result == 7

    @pytest.mark.asyncio
    async def test_tool_ainvoke_async(self):
        """Tool.ainvoke should work with async functions."""

        @Tool(description="Async greet")
        async def greet(name: str) -> str:
            return f"Hello, {name}!"

        result = await greet.ainvoke("World")
        assert result == "Hello, World!"

    def test_tool_to_schema(self):
        """Tool.to_schema should generate OpenAI-compatible schema."""

        @Tool(description="Add two numbers")
        def add(a: int, b: int) -> int:
            return a + b

        schema = add.to_schema()
        assert schema["name"] == "add"
        assert schema["description"] == "Add two numbers"
        assert "parameters" in schema
        assert "a" in schema["parameters"]["properties"]
        assert "b" in schema["parameters"]["properties"]


class TestActor:
    """Tests for Actor base class."""

    def test_actor_with_tools(self):
        """Actor should discover decorated tools."""

        class TestActor(Actor):
            name = "TestActor"
            description = "Test actor"
            goal = "Test goal"

            @Tool(description="Do something")
            def do_something(self, x: str) -> str:
                return f"Did: {x}"

        actor = TestActor()
        assert actor.name == "TestActor"
        assert "do_something" in actor.tool_names
        assert len(actor.tools) == 1

    def test_actor_with_llm_config(self):
        """Actor can have LLM configuration."""

        class IntelligentActor(Actor):
            name = "IntelligentActor"
            description = "Smart actor"
            goal = "Be intelligent"
            llm_config = LLMConfig(model="gpt-4o")

        actor = IntelligentActor()
        assert actor.is_intelligent
        assert actor.llm_config.model == "gpt-4o"

    def test_actor_without_llm_config(self):
        """Actor without LLM should not be intelligent."""

        class SimpleActor(Actor):
            name = "SimpleActor"
            description = "Simple"
            goal = "Simple goal"

        actor = SimpleActor()
        assert not actor.is_intelligent
        assert actor.llm_config is None

    @pytest.mark.asyncio
    async def test_actor_execute(self):
        """Actor.execute should invoke tools."""

        class CalcActor(Actor):
            name = "CalcActor"
            description = "Calculator"
            goal = "Calculate"

            @Tool(description="Add numbers")
            def add(self, a: int, b: int) -> int:
                return a + b

        actor = CalcActor()
        result = await actor.execute("add", {"a": 5, "b": 3})
        assert result == 8

    @pytest.mark.asyncio
    async def test_actor_execute_unknown_tool(self):
        """Actor.execute should raise for unknown tools."""

        class EmptyActor(Actor):
            name = "EmptyActor"
            description = "Empty"
            goal = "Nothing"

        actor = EmptyActor()
        with pytest.raises(ValueError, match="not found"):
            await actor.execute("unknown_tool", {})

    def test_actor_get_tools_schema(self):
        """Actor should return schemas for all tools."""

        class MultiToolActor(Actor):
            name = "MultiToolActor"
            description = "Has tools"
            goal = "Use tools"

            @Tool(description="Tool A")
            def tool_a(self) -> str:
                return "A"

            @Tool(description="Tool B")
            def tool_b(self, x: int) -> int:
                return x

        actor = MultiToolActor()
        schemas = actor.get_tools_schema()
        assert len(schemas) == 2
        names = {s["name"] for s in schemas}
        assert names == {"tool_a", "tool_b"}


class TestActorDecorator:
    """Tests for @actor decorator."""

    def test_actor_decorator_basic(self):
        """@actor decorator should set attributes."""

        @actor(
            name="DecoratedActor",
            description="A decorated actor",
            goal="Demonstrate decoration",
        )
        class MyActor(Actor):
            pass

        instance = MyActor()
        assert instance.name == "DecoratedActor"
        assert instance.description == "A decorated actor"
        assert instance.goal == "Demonstrate decoration"

    def test_actor_decorator_with_llm(self):
        """@actor decorator should accept llm_config."""

        @actor(
            name="SmartActor",
            description="Smart",
            goal="Be smart",
            llm_config=LLMConfig(model="gpt-4o"),
        )
        class SmartActor(Actor):
            pass

        instance = SmartActor()
        assert instance.is_intelligent
        assert instance.llm_config.model == "gpt-4o"


class TestActorRegistry:
    """Tests for ActorRegistry."""

    def test_registry_register(self):
        """ActorRegistry should register actors."""

        class RegActor(Actor):
            name = "RegActor"
            description = "Test"
            goal = "Test"

        ActorRegistry.clear()
        actor = RegActor()  # Auto-registers

        assert ActorRegistry.count() == 1
        assert ActorRegistry.get("RegActor") == actor

    def test_registry_all(self):
        """ActorRegistry.all should return all actors."""

        class Actor1(Actor):
            name = "Actor1"
            description = "One"
            goal = "One"

        class Actor2(Actor):
            name = "Actor2"
            description = "Two"
            goal = "Two"

        ActorRegistry.clear()
        Actor1()
        Actor2()

        all_actors = ActorRegistry.all()
        assert len(all_actors) == 2
        names = {a.name for a in all_actors}
        assert names == {"Actor1", "Actor2"}

    def test_registry_unregister(self):
        """ActorRegistry should unregister actors."""

        class TempActor(Actor):
            name = "TempActor"
            description = "Temporary"
            goal = "Test"

        ActorRegistry.clear()
        TempActor()
        assert ActorRegistry.count() == 1

        ActorRegistry.unregister("TempActor")
        assert ActorRegistry.count() == 0

    def test_registry_clear(self):
        """ActorRegistry.clear should remove all actors."""

        class ClearActor(Actor):
            name = "ClearActor"
            description = "Clear"
            goal = "Clear"

        ClearActor()
        assert ActorRegistry.count() > 0

        ActorRegistry.clear()
        assert ActorRegistry.count() == 0
