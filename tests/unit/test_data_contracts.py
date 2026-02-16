"""
Unit tests for DataContract and DataEnvelope in framework.data.contracts
"""

import pytest
from pydantic import ValidationError
from framework.data import DataContract, DataEnvelope
from typing import Dict, Any
from datetime import datetime


class ExampleContract(DataContract):
    foo: int
    bar: str


def test_datacontract_to_from_context_roundtrip():
    data = ExampleContract(foo=123, bar="baz")
    ctx: Dict[str, Any] = data.to_context()
    restored = ExampleContract.from_context(ctx)
    assert restored == data
    assert isinstance(restored, ExampleContract)


def test_datacontract_validation_error():
    with pytest.raises(ValidationError) as exc:
        ExampleContract(foo="not-an-int", bar=123)  # type: ignore
    assert "foo" in str(exc.value) or "bar" in str(exc.value)


def test_datacontract_extra_field_forbidden():
    with pytest.raises(ValidationError) as exc:
        ExampleContract(foo=1, bar="ok", extra_field=42)  # type: ignore
    assert "extra_field" in str(exc.value)


def test_dataenvelope_metadata():
    data = ExampleContract(foo=1, bar="ok")
    env = DataEnvelope(
        payload=data,
        created_by="test_actor",
        source_step_id="step-1",
        schema_version="1.0",
    )
    assert env.payload == data
    assert env.created_by == "test_actor"
    assert env.source_step_id == "step-1"
    assert env.schema_version == "1.0"
    assert isinstance(env.created_at, datetime)
