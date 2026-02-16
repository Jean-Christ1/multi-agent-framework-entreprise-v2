"""
Unit tests for LLMConfig.

Ticket: JAF-17
"""

import pytest
from pydantic import ValidationError

from framework.types import LLMConfig


class TestLLMConfig:
    """Tests for LLMConfig data model."""

    def test_create_valid_config(self):
        """Should create a valid LLMConfig with all fields."""
        config = LLMConfig(
            model="gpt-4o",
            temperature=0.7,
            max_tokens=1000,
        )

        assert config.model == "gpt-4o"
        assert config.temperature == 0.7
        assert config.max_tokens == 1000

    def test_default_temperature(self):
        """Temperature should default to 0.0 (deterministic)."""
        config = LLMConfig(model="gpt-4o")

        assert config.temperature == 0.0

    def test_optional_max_tokens(self):
        """max_tokens should be optional (None by default)."""
        config = LLMConfig(model="gpt-4o")

        assert config.max_tokens is None

    def test_model_is_required(self):
        """model field is required."""
        with pytest.raises(ValidationError):
            LLMConfig()

    def test_temperature_lower_bound(self):
        """Temperature must be >= 0.0."""
        with pytest.raises(ValidationError):
            LLMConfig(model="gpt-4o", temperature=-0.1)

    def test_temperature_upper_bound(self):
        """Temperature must be <= 2.0."""
        with pytest.raises(ValidationError):
            LLMConfig(model="gpt-4o", temperature=2.1)

    def test_max_tokens_must_be_positive(self):
        """max_tokens must be > 0 if provided."""
        with pytest.raises(ValidationError):
            LLMConfig(model="gpt-4o", max_tokens=0)

        with pytest.raises(ValidationError):
            LLMConfig(model="gpt-4o", max_tokens=-100)

    def test_config_is_immutable(self):
        """LLMConfig instances should be frozen (immutable)."""
        config = LLMConfig(model="gpt-4o")

        with pytest.raises(ValidationError):
            config.model = "gpt-4o-mini"

    def test_any_model_name_accepted(self):
        """Any model string should be accepted (no hardcoded whitelist)."""
        # OpenAI models
        config1 = LLMConfig(model="gpt-4o")
        assert config1.model == "gpt-4o"

        # Anthropic models
        config2 = LLMConfig(model="claude-3-opus")
        assert config2.model == "claude-3-opus"

        # Custom/local models
        config3 = LLMConfig(model="llama-3-70b")
        assert config3.model == "llama-3-70b"

        # Future models
        config4 = LLMConfig(model="gpt-5-turbo")
        assert config4.model == "gpt-5-turbo"

    def test_config_equality(self):
        """Two configs with same values should be equal."""
        config1 = LLMConfig(model="gpt-4o", temperature=0.5)
        config2 = LLMConfig(model="gpt-4o", temperature=0.5)

        assert config1 == config2

    def test_config_serialization(self):
        """Config should serialize to dict correctly."""
        config = LLMConfig(
            model="gpt-4o",
            temperature=0.7,
            max_tokens=500,
        )

        data = config.model_dump()

        assert data["model"] == "gpt-4o"
        assert data["temperature"] == 0.7
        assert data["max_tokens"] == 500


class TestLLMConfigDeterministicVsProbabilistic:
    """Tests for deterministic vs probabilistic actor pattern."""

    def test_none_means_deterministic(self):
        """llm_config = None indicates a deterministic actor."""
        llm_config = None

        # This is how actors check for deterministic mode
        is_deterministic = llm_config is None
        assert is_deterministic is True

    def test_config_means_probabilistic(self):
        """llm_config = LLMConfig(...) indicates a probabilistic actor."""
        llm_config = LLMConfig(model="gpt-4o")

        # This is how actors check for LLM mode
        uses_llm = llm_config is not None
        assert uses_llm is True

    def test_zero_temperature_still_probabilistic(self):
        """Even temperature=0.0 with LLMConfig is probabilistic (uses LLM)."""
        llm_config = LLMConfig(model="gpt-4o", temperature=0.0)

        # Has LLM config = uses LLM (even if temperature is 0)
        uses_llm = llm_config is not None
        assert uses_llm is True
