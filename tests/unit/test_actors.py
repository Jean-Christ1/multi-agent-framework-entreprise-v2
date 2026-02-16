"""
Unit tests for Actor and ActorRegistry.

Tickets: JAF-17, JAF-18, JAF-19, JAF-20
"""

import tempfile
from pathlib import Path

import pytest
import yaml

from framework.actor import Actor, ActorRegistry
from framework.types import LLMConfig


class DummyActor(Actor):
    """Test actor for unit tests."""

    def configure(self) -> None:
        self.name = "DummyActor"
        self.description = "A test actor"
        self.goal = "Testing purposes"
        self.tools = [self.dummy_tool]
        self.llm_config = None

    def dummy_tool(self, input_value: str) -> str:
        """A simple test tool."""
        return f"processed: {input_value}"


class LLMEnabledActor(Actor):
    """Test actor with LLM config."""

    def configure(self) -> None:
        self.name = "LLMEnabledActor"
        self.description = "An actor with LLM"
        self.goal = "Testing LLM config"
        self.tools = []
        self.llm_config = LLMConfig(model="gpt-4o", temperature=0.7)


@pytest.fixture(autouse=True)
def clear_registry():
    """Clear registry before each test."""
    ActorRegistry.clear()
    yield
    ActorRegistry.clear()


class TestActor:
    """Tests for the Actor ABC."""

    def test_actor_init_creates_empty_lists(self):
        """Actor.__init__ should create instance-level empty lists."""
        actor = DummyActor()
        # Before configure, tools should be empty list
        assert actor.tools == []
        assert actor.utilities == []

    def test_actor_configure_sets_fields(self):
        """configure() should set all required fields."""
        actor = DummyActor()
        actor.configure()

        assert actor.name == "DummyActor"
        assert actor.description == "A test actor"
        assert actor.goal == "Testing purposes"
        assert len(actor.tools) == 1
        assert actor.llm_config is None

    def test_deterministic_actor_has_no_llm_config(self):
        """Deterministic actors should have llm_config=None."""
        actor = DummyActor()
        actor.configure()
        assert actor.llm_config is None

    def test_llm_actor_has_llm_config(self):
        """LLM-enabled actors should have a valid LLMConfig."""
        actor = LLMEnabledActor()
        actor.configure()

        assert actor.llm_config is not None
        assert actor.llm_config.model == "gpt-4o"
        assert actor.llm_config.temperature == 0.7


class TestActorRegistry:
    """Tests for ActorRegistry."""

    def test_register_actor(self):
        """register() should add actor to registry."""
        ActorRegistry.register("TestActor", DummyActor)
        assert "TestActor" in ActorRegistry.list()

    def test_register_non_actor_raises_error(self):
        """register() should reject non-Actor classes."""
        with pytest.raises(TypeError):
            ActorRegistry.register("Invalid", str)

    def test_get_returns_configured_instance(self):
        """get() should return a configured actor instance."""
        ActorRegistry.register("TestActor", DummyActor)
        actor = ActorRegistry.get("TestActor")

        assert isinstance(actor, DummyActor)
        assert actor.name == "DummyActor"
        assert len(actor.tools) == 1

    def test_get_unknown_actor_raises_error(self):
        """get() should raise KeyError for unknown actors."""
        with pytest.raises(KeyError):
            ActorRegistry.get("NonExistent")

    def test_list_returns_registered_names(self):
        """list() should return all registered actor names."""
        ActorRegistry.register("Actor1", DummyActor)
        ActorRegistry.register("Actor2", LLMEnabledActor)

        names = ActorRegistry.list()
        assert "Actor1" in names
        assert "Actor2" in names

    def test_clear_removes_all_actors(self):
        """clear() should remove all registered actors."""
        ActorRegistry.register("TestActor", DummyActor)
        ActorRegistry.clear()
        assert ActorRegistry.list() == []


class TestYAMLGeneration:
    """Tests for YAML generation (JAF-20)."""

    def test_generate_yaml_creates_file(self):
        """generate_yaml() should create a valid YAML file."""
        ActorRegistry.register("TestActor", DummyActor)

        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
            output_path = f.name

        try:
            ActorRegistry.generate_yaml(output_path)

            assert Path(output_path).exists()

            with open(output_path) as f:
                data = yaml.safe_load(f)

            assert isinstance(data, list)
            assert len(data) == 1
            assert data[0]["name"] == "TestActor"
        finally:
            Path(output_path).unlink(missing_ok=True)

    def test_generate_yaml_includes_tools(self):
        """Generated YAML should include tool metadata."""
        ActorRegistry.register("TestActor", DummyActor)

        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
            output_path = f.name

        try:
            ActorRegistry.generate_yaml(output_path)

            with open(output_path) as f:
                data = yaml.safe_load(f)

            tools = data[0]["tools"]
            assert len(tools) == 1
            assert tools[0]["name"] == "dummy_tool"
            assert "input_schema" in tools[0]
        finally:
            Path(output_path).unlink(missing_ok=True)


class TestYAMLDiscovery:
    """Tests for YAML discovery (JAF-20)."""

    def test_discover_from_yaml_loads_actors(self):
        """discover_from_yaml() should register actors from YAML."""
        yaml_content = """
- name: DiscoveredActor
  module: tests.unit.test_actors
  class: DummyActor
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            yaml_path = f.name

        try:
            ActorRegistry.discover_from_yaml(yaml_path)
            assert "DiscoveredActor" in ActorRegistry.list()
        finally:
            Path(yaml_path).unlink(missing_ok=True)

    def test_discover_skips_metadata_only_entries(self):
        """discover_from_yaml() should skip entries without module/class."""
        yaml_content = """
- name: MetadataOnlyActor
  description: Just metadata, no module
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            yaml_path = f.name

        try:
            ActorRegistry.discover_from_yaml(yaml_path)
            # Should not crash, but actor should not be registered
            assert "MetadataOnlyActor" not in ActorRegistry.list()
        finally:
            Path(yaml_path).unlink(missing_ok=True)
