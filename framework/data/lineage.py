"""
Data lineage tracking for workflow execution.

Tracks which actor created each data key, which steps consumed it,
and how it was derived from other keys. Optional and disabled by default for performance.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# LineageNode
# ---------------------------------------------------------------------------


@dataclass
class LineageNode:
    """A single node in the data lineage graph."""

    key: str
    created_by: str  # Actor name
    created_at: datetime
    step_id: str
    source_keys: List[str]  # Keys this was derived from

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for process context (datetime as ISO string)."""
        return {
            "key": self.key,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "step_id": self.step_id,
            "source_keys": list(self.source_keys),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> LineageNode:
        """Deserialize from process context."""
        created_at = data["created_at"]
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        return cls(
            key=data["key"],
            created_by=data["created_by"],
            created_at=created_at,
            step_id=data["step_id"],
            source_keys=list(data.get("source_keys", [])),
        )


# ---------------------------------------------------------------------------
# Access record (for "who read what" debugging)
# ---------------------------------------------------------------------------


@dataclass
class LineageAccess:
    """Record of an actor/step reading a key."""

    key: str
    actor: str
    step_id: str
    at: datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "actor": self.actor,
            "step_id": self.step_id,
            "at": self.at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> LineageAccess:
        at = data["at"]
        if isinstance(at, str):
            at = datetime.fromisoformat(at.replace("Z", "+00:00"))
        return cls(
            key=data["key"],
            actor=data["actor"],
            step_id=data["step_id"],
            at=at,
        )


# ---------------------------------------------------------------------------
# LineageTracker
# ---------------------------------------------------------------------------

# Key used in process context to persist lineage for debugging
LINEAGE_CONTEXT_KEY = "_lineage"


class LineageTracker:
    """
    Tracks data provenance through workflow execution.

    - record_creation: log when a key is produced by an actor/step from optional source keys.
    - record_access: log when a key is read by an actor/step.
    - get_lineage: return the full provenance chain for a key.
    - to_mermaid: generate a Mermaid diagram of the data flow.

    Optional and disabled by default for performance. When disabled, recording is a no-op
    and get_lineage / to_mermaid return empty/default.
    """

    def __init__(self, enabled: bool = False):
        self._enabled = enabled
        self._nodes: Dict[str, LineageNode] = {}
        self._accesses: List[LineageAccess] = []

    @property
    def enabled(self) -> bool:
        return self._enabled

    def record_creation(
        self,
        key: str,
        actor: str,
        step_id: str,
        sources: Optional[List[str]] = None,
    ) -> None:
        """Record that a data key was created by an actor at a step, optionally from source keys."""
        if not self._enabled:
            return
        self._nodes[key] = LineageNode(
            key=key,
            created_by=actor,
            created_at=datetime.now(timezone.utc),
            step_id=step_id,
            source_keys=list(sources or []),
        )

    def record_access(self, key: str, actor: str, step_id: str) -> None:
        """Record that an actor/step read a data key."""
        if not self._enabled:
            return
        self._accesses.append(
            LineageAccess(
                key=key,
                actor=actor,
                step_id=step_id,
                at=datetime.now(timezone.utc),
            )
        )

    def get_lineage(self, key: str) -> List[LineageNode]:
        """
        Return the full provenance chain for a key (this key and all keys it was derived from).

        Order: dependency order (sources before derived), then the node for key last.
        """
        if not self._enabled:
            return []
        result: List[LineageNode] = []
        seen: set[str] = set()

        def collect(k: str) -> None:
            if k in seen:
                return
            node = self._nodes.get(k)
            if node is None:
                return
            seen.add(k)
            for src in node.source_keys:
                collect(src)
            result.append(node)

        collect(key)
        return result

    def to_mermaid(self) -> str:
        """Generate a Mermaid flowchart of data flow (key -> key derivations)."""
        if not self._enabled or not self._nodes:
            return "%% Lineage tracking disabled or no data recorded"

        lines = ["flowchart LR", "    %% Data lineage (key -> derived from)"]
        node_ids: Dict[str, str] = {}
        for i, k in enumerate(self._nodes):
            node_ids[k] = f"K{i}"

        for node in self._nodes.values():
            label = f"{node.key}"
            if node.created_by:
                label += f"\\n({node.created_by})"
            sid = node_ids[node.key]
            lines.append(f'    {sid}["{label}"]')
            for src in node.source_keys:
                if src in node_ids:
                    lines.append(f"    {node_ids[src]} --> {sid}")

        return "\n".join(lines)

    def to_context(self) -> Dict[str, Any]:
        """Serialize lineage for persisting in process context (debugging)."""
        if not self._enabled:
            return {"enabled": False, "nodes": [], "accesses": []}
        return {
            "enabled": True,
            "nodes": [n.to_dict() for n in self._nodes.values()],
            "accesses": [a.to_dict() for a in self._accesses],
        }

    @classmethod
    def from_context(cls, data: Dict[str, Any]) -> LineageTracker:
        """Restore a tracker from process context."""
        tracker = cls(enabled=bool(data.get("enabled", False)))
        if not tracker._enabled:
            return tracker
        for n in data.get("nodes", []):
            node = LineageNode.from_dict(n)
            tracker._nodes[node.key] = node
        for a in data.get("accesses", []):
            tracker._accesses.append(LineageAccess.from_dict(a))
        return tracker
