from __future__ import annotations

import pytest

from framework.data.context import TypedContext
from framework.data.contracts import DataContract


# ---------------------------------------------------------------------
# Test contracts (minimal DataContract impl for tests)
# ---------------------------------------------------------------------
class FooContract(DataContract):
    foo: str

    @classmethod
    def schema_version(cls) -> str:
        return "1.0"


class BarContract(DataContract):
    bar: int

    @classmethod
    def schema_version(cls) -> str:
        return "2.0"


# ---------------------------------------------------------------------
# Typed API tests
# ---------------------------------------------------------------------
def test_set_wraps_in_envelope_with_provenance() -> None:
    ctx = TypedContext()

    ctx.set("x", FooContract(foo="hello"), actor_name="ActorA", source_step_id="S1")

    env = ctx.get_envelope("x")
    assert env.created_by == "ActorA"
    assert env.source_step_id == "S1"
    assert env.schema_version == "1.0"
    assert isinstance(env.payload, FooContract)
    assert env.payload.foo == "hello"


def test_set_with_source_keys_links_envelope_to_sources() -> None:
    """DataEnvelope can link to source context keys for lineage."""
    ctx = TypedContext()
    ctx.set(
        "derived",
        FooContract(foo="from_a_b"),
        actor_name="ActorB",
        source_step_id="S2",
        source_keys=["input_a", "input_b"],
    )
    env = ctx.get_envelope("derived")
    assert env.source_keys == ["input_a", "input_b"]


def test_get_returns_typed_payload() -> None:
    ctx = TypedContext()
    ctx.set("x", FooContract(foo="hello"), actor_name="ActorA")

    payload = ctx.get("x", FooContract)
    assert isinstance(payload, FooContract)
    assert payload.foo == "hello"


def test_get_raises_key_error_when_missing() -> None:
    ctx = TypedContext()
    with pytest.raises(KeyError):
        ctx.get("missing", FooContract)


def test_get_raises_type_error_on_wrong_type() -> None:
    ctx = TypedContext()
    ctx.set("x", FooContract(foo="hello"), actor_name="ActorA")

    with pytest.raises(TypeError):
        ctx.get("x", BarContract)


def test_get_raw_returns_model_dump_for_typed_data() -> None:
    ctx = TypedContext()
    ctx.set("x", FooContract(foo="hello"), actor_name="ActorA")

    raw = ctx.get_raw("x")
    assert raw == {"foo": "hello"}


def test_get_raw_falls_back_to_raw_storage() -> None:
    ctx = TypedContext(initial={"legacy": {"a": 1}})

    assert ctx.get_raw("legacy") == {"a": 1}
    assert ctx.get_raw("missing", default=123) == 123


# ---------------------------------------------------------------------
# MutableMapping / backward-compat behavior
# ---------------------------------------------------------------------
def test_mapping_getitem_returns_raw_for_typed_payload() -> None:
    ctx = TypedContext()
    ctx.set("x", FooContract(foo="hello"), actor_name="ActorA")

    assert ctx["x"] == {"foo": "hello"}


def test_mapping_setitem_with_raw_goes_to_raw_and_removes_typed_if_present() -> None:
    ctx = TypedContext()
    ctx.set("x", FooContract(foo="hello"), actor_name="ActorA")

    ctx["x"] = {"legacy": True}
    assert ctx.has_typed("x") is False
    assert ctx.get_raw("x") == {"legacy": True}
    assert ctx["x"] == {"legacy": True}


def test_mapping_setitem_with_datacontract_stores_typed_with_unknown_provenance() -> (
    None
):
    ctx = TypedContext()
    ctx["x"] = FooContract(foo="hello")

    env = ctx.get_envelope("x")
    assert env.created_by == "unknown"
    assert env.payload.foo == "hello"


def test_delitem_removes_from_typed_or_raw() -> None:
    ctx = TypedContext(initial={"legacy": 1})
    ctx.set("x", FooContract(foo="hello"), actor_name="ActorA")

    del ctx["x"]
    assert ctx.has_typed("x") is False

    del ctx["legacy"]
    with pytest.raises(KeyError):
        _ = ctx["legacy"]

    with pytest.raises(KeyError):
        del ctx["missing"]


def test_iter_len_union_of_keys() -> None:
    ctx = TypedContext(initial={"a": 1, "b": 2})
    ctx.set("x", FooContract(foo="hello"), actor_name="ActorA")

    keys = set(iter(ctx))
    assert keys == {"a", "b", "x"}
    assert len(ctx) == 3


def test_to_dict_merges_raw_and_typed_as_raw_payloads() -> None:
    ctx = TypedContext(initial={"a": 1})
    ctx.set("x", FooContract(foo="hello"), actor_name="ActorA")

    out = ctx.to_dict()
    assert out["a"] == 1
    assert out["x"] == {"foo": "hello"}
