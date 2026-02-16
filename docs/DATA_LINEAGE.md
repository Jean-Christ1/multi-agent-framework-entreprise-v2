# Data Lineage Tracking

Data lineage tracks **which actor created each data key**, **which steps consumed it**, and **how it was derived** from other keys. It is **optional and disabled by default** for performance.

## Components

- **`LineageNode`** (dataclass): one node in the lineage graph (`key`, `created_by`, `created_at`, `step_id`, `source_keys`).
- **`LineageTracker`**: records creation/access and exposes `get_lineage(key)` and `to_mermaid()`.

## Usage

```python
from framework.data import LineageTracker, LINEAGE_CONTEXT_KEY

# Enable when needed (e.g. debugging)
tracker = LineageTracker(enabled=True)

# After a step produces data
tracker.record_creation("order_result", "OrderActor", step_id="step-2", sources=["request", "inventory"])

# When a step reads data
tracker.record_access("request", "OrderActor", "step-2")

# Full provenance chain for a key
chain = tracker.get_lineage("order_result")

# Mermaid diagram of data flow
mermaid = tracker.to_mermaid()
```

## Persisting in process context

For debugging, persist lineage in the process context so it is stored with the process:

```python
# After execution (e.g. in orchestrator)
context[LINEAGE_CONTEXT_KEY] = tracker.to_context()

# When restoring a process for inspection
tracker = LineageTracker.from_context(context.get(LINEAGE_CONTEXT_KEY, {}))
```

## DataEnvelope and source keys

When using **typed context** with lineage, you can link a stored value to the context keys it was derived from:

```python
ctx.set(
    "derived_key",
    MyContract(...),
    actor_name="MyActor",
    source_step_id=step.id,
    source_keys=["input_a", "input_b"],  # lineage: derived from these keys
)
```

`DataEnvelope` stores `source_keys` so each envelope can reference its source data keys; combine with `LineageTracker.record_creation(..., sources=source_keys)` when lineage is enabled.

## API summary

| Method                                               | Description                                                               |
|------------------------------------------------------|---------------------------------------------------------------------------|
| `record_creation(key, actor, step_id, sources=None)` | Log creation of a data key from optional source keys.                     |
| `record_access(key, actor, step_id)`                 | Log read of a key by an actor/step.                                       |
| `get_lineage(key)`                                   | Return full provenance chain (this key and all keys it was derived from). |
| `to_mermaid()`                                       | Generate Mermaid flowchart of data flow.                                  |
| `to_context()` / `from_context(data)`                | Serialize/restore for process context.                                    |

See `framework/data/lineage.py` and `tests/unit/test_lineage.py` for details.
