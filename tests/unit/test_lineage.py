"""Unit tests for data lineage tracking."""

from __future__ import annotations

from datetime import datetime, timezone

from framework.data.lineage import (
    LINEAGE_CONTEXT_KEY,
    LineageNode,
    LineageTracker,
)


# ---------------------------------------------------------------------------
# LineageNode
# ---------------------------------------------------------------------------


def test_lineage_node_to_dict_roundtrip() -> None:
    node = LineageNode(
        key="result",
        created_by="ActorA",
        created_at=datetime.now(timezone.utc),
        step_id="step-1",
        source_keys=["input_a", "input_b"],
    )
    data = node.to_dict()
    assert data["key"] == "result"
    assert data["created_by"] == "ActorA"
    assert data["step_id"] == "step-1"
    assert data["source_keys"] == ["input_a", "input_b"]
    assert "created_at" in data

    restored = LineageNode.from_dict(data)
    assert restored.key == node.key
    assert restored.created_by == node.created_by
    assert restored.step_id == node.step_id
    assert restored.source_keys == node.source_keys


# ---------------------------------------------------------------------------
# LineageTracker - disabled by default
# ---------------------------------------------------------------------------


def test_tracker_disabled_by_default() -> None:
    tracker = LineageTracker()
    assert tracker.enabled is False


def test_tracker_disabled_no_op_recording() -> None:
    tracker = LineageTracker()
    tracker.record_creation("k", "A", "s1", sources=["x"])
    tracker.record_access("k", "A", "s1")
    assert tracker.get_lineage("k") == []
    assert (
        "disabled" in tracker.to_mermaid().lower()
        or "no data" in tracker.to_mermaid().lower()
    )


def test_tracker_disabled_to_context() -> None:
    tracker = LineageTracker()
    ctx = tracker.to_context()
    assert ctx["enabled"] is False
    assert ctx["nodes"] == []
    assert ctx["accesses"] == []


# ---------------------------------------------------------------------------
# LineageTracker - enabled, record and get_lineage
# ---------------------------------------------------------------------------


def test_record_creation_and_get_lineage() -> None:
    tracker = LineageTracker(enabled=True)
    tracker.record_creation("out", "Actor1", "step-1", sources=["in1", "in2"])
    chain = tracker.get_lineage("out")
    assert len(chain) == 1
    assert chain[0].key == "out"
    assert chain[0].created_by == "Actor1"
    assert chain[0].step_id == "step-1"
    assert chain[0].source_keys == ["in1", "in2"]


def test_get_lineage_full_chain() -> None:
    tracker = LineageTracker(enabled=True)
    tracker.record_creation("a", "A", "s1", sources=[])
    tracker.record_creation("b", "A", "s2", sources=["a"])
    tracker.record_creation("c", "A", "s3", sources=["b"])
    chain = tracker.get_lineage("c")
    assert len(chain) == 3
    keys = [n.key for n in chain]
    assert keys == ["a", "b", "c"]


def test_get_lineage_unknown_key_returns_empty() -> None:
    tracker = LineageTracker(enabled=True)
    tracker.record_creation("x", "A", "s1", sources=[])
    assert tracker.get_lineage("nonexistent") == []


def test_record_access() -> None:
    tracker = LineageTracker(enabled=True)
    tracker.record_creation("k", "Producer", "s1", sources=[])
    tracker.record_access("k", "Consumer", "s2")
    ctx = tracker.to_context()
    assert len(ctx["accesses"]) == 1
    assert ctx["accesses"][0]["key"] == "k"
    assert ctx["accesses"][0]["actor"] == "Consumer"
    assert ctx["accesses"][0]["step_id"] == "s2"


# ---------------------------------------------------------------------------
# to_mermaid
# ---------------------------------------------------------------------------


def test_to_mermaid_generates_flowchart() -> None:
    tracker = LineageTracker(enabled=True)
    tracker.record_creation("a", "A", "s1", sources=[])
    tracker.record_creation("b", "A", "s2", sources=["a"])
    mermaid = tracker.to_mermaid()
    assert "flowchart" in mermaid
    assert "a" in mermaid or "K0" in mermaid
    assert "b" in mermaid or "K1" in mermaid
    assert "-->" in mermaid


# ---------------------------------------------------------------------------
# Persist in process context (to_context / from_context)
# ---------------------------------------------------------------------------


def test_to_context_from_context_roundtrip() -> None:
    tracker = LineageTracker(enabled=True)
    tracker.record_creation("x", "ActorX", "step-x", sources=["y"])
    tracker.record_access("y", "ActorX", "step-x")
    data = tracker.to_context()
    assert data["enabled"] is True
    assert len(data["nodes"]) == 1
    assert len(data["accesses"]) == 1

    restored = LineageTracker.from_context(data)
    assert restored.enabled is True
    chain = restored.get_lineage("x")
    assert len(chain) == 1
    assert chain[0].key == "x"
    assert chain[0].created_by == "ActorX"
    assert chain[0].source_keys == ["y"]


def test_lineage_context_key_constant() -> None:
    assert LINEAGE_CONTEXT_KEY == "_lineage"
