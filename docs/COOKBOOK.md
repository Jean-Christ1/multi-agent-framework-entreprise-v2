# Cookbook – Common Patterns

This cookbook provides recipes for common patterns when working with the JAF framework using deterministic Actors and the NativeEngine.

Covered patterns:

- Error handling in actors
- Testing actors with mocks
- Parallel step execution
- Passing data between steps
- Custom plan builders
- Retries

All examples are aligned with the current Actor, ActorRegistry, NativeEngine, Plan, and PlanStep models.

---

# 1. Recipe: Error Handling in Actors

## How NativeEngine handles errors

When a tool raises an exception:

- NativeEngine catches it
- Returns `StepResult(status="error")`
- The plan is marked FAILED
- Execution stops

Use exceptions for hard failures and invalid states.

## Fail-fast pattern (recommended)

Raise exceptions when validation or critical operations fail.

```python
from framework.actor.base_actor import Actor

class BillingActor(Actor):
    def configure(self):
        self.name = "billing"
        self.description = "Charge credit cards"
        self.goal = "Collect payments"
        self.tools = [self.charge_card]

    def charge_card(self, user_id: str, amount: int) -> dict:
        if amount <= 0:
            raise ValueError("amount must be > 0")

        if provider_declined:
            raise RuntimeError("card declined")

        return {"charge_id": "ch_123"}
```

## Soft-failure pattern (structured result)

Return structured output instead of raising when failure is acceptable.

```python
def enrich(self, email: str) -> dict:
    try:
        data = external_lookup(email)
        return {
            "enrichment": data,
            "ok": True
        }
    except TimeoutError as e:
        return {
            "ok": False,
            "error": str(e),
            "enrichment": None
        }
```

# 2. Recipe: Testing Actors with Mocks

## ActorRegistry behavior in tests

ActorRegistry registers classes, not instances. Each get() call creates a new configured actor.

```python
ActorRegistry.register("name", ActorClass)
actor = ActorRegistry.get("name")  # creates new instance and calls configure()

# Always reset between tests:
ActorRegistry.clear()

# Unit test with patch

from unittest.mock import patch

def test_enrich_success():
    actor = EnrichmentActor()
    actor.configure()

    with patch("my_module.external_lookup") as lookup:
        lookup.return_value = {"name": "Ana"}
        result = actor.enrich("a@x.com")

    assert result["ok"] is True

# Engine + Plan test

import pytest
from framework.types import Plan, PlanStep
from framework.engine.native_engine import NativeEngine
from framework.actor.registry import ActorRegistry
from framework.actor.base_actor import Actor

@pytest.mark.asyncio
async def test_context_flow():
    ActorRegistry.clear()

    class A1(Actor):
        def configure(self):
            self.name = "a1"
            self.tools = [self.make]

        def make(self):
            return {"user_id": "u1"}

    class A2(Actor):
        def configure(self):
            self.name = "a2"
            self.tools = [self.use]

        def use(self, user_id: str):
            return {"seen": user_id}

    ActorRegistry.register("a1", A1)
    ActorRegistry.register("a2", A2)

    plan = Plan(steps=[
        PlanStep(actor_name="a1", tool_name="make", parameters={}),
        PlanStep(
            actor_name="a2",
            tool_name="use",
            parameters={"user_id": "{context.user_id}"}
        )
    ])

    engine = NativeEngine(default_plan=plan)
    ctx = await engine.execute_plan(plan, context={})

    assert ctx["seen"] == "u1"
```

## Mocking a tool (recommended approach)

NativeEngine discovers the tool to run by iterating `actor.tools` and matching by `tool.__name__`.
If you replace the tool itself with a `Mock`, it may not have a `__name__` attribute and tool lookup can fail.

Recommended approach: keep the tool as a real function and patch a dependency that the tool calls.

```python
from unittest.mock import patch
from framework.actor.base_actor import Actor

# Dependency that would normally call an external provider.
def provider_call(user_id: str, amount: int) -> dict:
    return {"charge_id": "real"}

class BillingActor(Actor):
    def configure(self):
        self.name = "billing"
        self.description = "Charge credit cards"
        self.goal = "Collect payments"
        self.tools = [self.charge_card]
        self.llm_config = None

    def charge_card(self, user_id: str, amount: int) -> dict:
        # Keep the tool callable intact so NativeEngine can match by __name__.
        return provider_call(user_id, amount)

# Patch the dependency (NOT the tool function)
with patch("path.to.module.provider_call", return_value={"charge_id": "test"}):
    ctx = await engine.execute_plan(plan, context={})

assert ctx["charge_id"] == "test"
```

## Fake actor for tests

```python
class FakeBilling(Actor):
    def configure(self):
        self.name = "billing"
        self.tools = [self.charge]

    def charge(self, **_):
        return {"charge_id": "fake"}

ActorRegistry.register("billing", FakeBilling)
```

# 3. Recipe: Parallel Step Execution

Steps with the same parallel_group value run concurrently.

Rules:

- Consecutive steps with same group run in parallel
- Engine uses asyncio.gather
- Any failure fails the entire group
- Results are merged into context

```python
from framework.types import Plan, PlanStep

plan = Plan(steps=[
    PlanStep(
        actor_name="fetcher",
        tool_name="fetch_user",
        parameters={"id": "{context.id}"},
        parallel_group="fetch"
    ),
    PlanStep(
        actor_name="fetcher",
        tool_name="fetch_orders",
        parameters={"id": "{context.id}"},
        parallel_group="fetch"
    ),
    PlanStep(
        actor_name="builder",
        tool_name="build_report",
        parameters={
            "user": "{context.user}",
            "orders": "{context.orders}"
        }
    )
])
```

# 4. Recipe: Passing Data Between Steps

## Context placeholders

Parameters can reference previous outputs using:

```
{context.key}
```

Engine resolves these values at runtime.
Recommended: return dict from tools

```python
def load_user(self, user_id: str) -> dict:
    return {"user": {...}}
```

# Next step:

```python
PlanStep(
    actor_name="mailer",
    tool_name="send",
    parameters={"user": "{context.user}"}
)
```

Non-dict return values
Non-dict results are wrapped as:

```python
{"result": value}
```

Prefer returning dicts to avoid overwriting keys.
Avoid key collisions
Use unique or namespaced keys:

```python
{"fetch_user.user": ...}
```

# 5. Recipe: Custom Plan Builders

NativeEngine supports custom plan builders.

Builder API

```python
engine.set_plan_builder(builder_fn)

# Signature:

(goal: str, actors: List[Actor]) -> Plan

# Simple builder example

from framework.types import Plan, PlanStep

def simple_builder(goal, actors):
    steps = []

    for actor in actors:
        for tool in actor.tools:
            if tool.__name__ == "build_report":
                steps.append(PlanStep(
                    actor_name=actor.name,
                    tool_name="build_report",
                    parameters={}
                ))

    return Plan(steps=steps)

# Builder with parallel groups

def parallel_builder(goal, actors):
    return Plan(steps=[
        PlanStep("fetcher", "fetch_user", {}, parallel_group="fetch"),
        PlanStep("fetcher", "fetch_orders", {}, parallel_group="fetch"),
        PlanStep("builder", "build_report", {})
    ])
```

# 6. Recipe: Retries

NativeEngine does not include built-in retries. Recommended approach: implement retry inside tools.

```python
import time

def retry(fn, retries=3, backoff=0.2):
    last = None
    for i in range(retries):
        try:
            return fn()
        except Exception as e:
            last = e
            time.sleep(backoff * (2 ** i))
    raise last

# Usage:

def fetch_user(self, user_id: str) -> dict:
    user = retry(lambda: flaky_call(user_id))
    return {"user": user}
```

---

## Plan Visualization (Mermaid)

You can render an execution plan as a Mermaid flowchart: one node per step (labeled `actor_name.tool_name`), parallel groups as parallel branches, and node colors by step status (pending = gray, executing = blue, completed = green, failed = red).

### Example

```python
from framework.types import Plan, PlanStep

# Build a small plan: one sequential step, then two parallel steps, then one sequential
plan = Plan(
    steps=[
        PlanStep(
            actor_name="ProvisioningActor",
            tool_name="validate_request",
            parameters={},
            status="completed",
            parallel_group=None,
        ),
        PlanStep(
            actor_name="InventoryActor",
            tool_name="check_stock",
            parameters={"sku": "MBP-001"},
            status="completed",
            parallel_group="fetch",
        ),
        PlanStep(
            actor_name="VendorActor",
            tool_name="get_quote",
            parameters={"sku": "MBP-001"},
            status="completed",
            parallel_group="fetch",
        ),
        PlanStep(
            actor_name="ProvisioningActor",
            tool_name="create_order",
            parameters={},
            status="pending",
            parallel_group=None,
        ),
    ],
    status="EXECUTING",
)

mermaid_str = plan.to_mermaid()
print(mermaid_str)
```

### Sample output

```
flowchart TD
  s0["ProvisioningActor.validate_request"]
  s1["InventoryActor.check_stock"]
  s2["VendorActor.get_quote"]
  s3["ProvisioningActor.create_order"]
  s0 --> s1
  s0 --> s2
  s1 --> s3
  s2 --> s3
  style s0 fill:#c8e6c9
  style s1 fill:#c8e6c9
  style s2 fill:#c8e6c9
  style s3 fill:#e0e0e0
```

### How to view the diagram

1. **Automatic (local browser):** From the repo root, run:

   ```bash
   python scripts/view_plan_mermaid.py
   ```

   This generates a temporary HTML file with the example plan(s) and opens it in your default browser. You can show **multiple flows** on the same page by editing `EXAMPLE_FLOWS` in `scripts/view_plan_mermaid.py`: it is a list of `(title, plan)`; each plan is rendered as a separate diagram with its title.

2. **GitHub / GitLab:** Paste the output inside a fenced code block with language `mermaid` in a Markdown file; the wiki or MR preview will render it.
3. **Mermaid Live Editor:** Copy the string into [mermaid.live](https://mermaid.live) to edit and export as PNG/SVG.
4. **Docs / Notion:** Many tools support ` ```mermaid ` code blocks and will render the flowchart.

### Status colors

| Status    | Color | Hex       |
| --------- | ----- | --------- |
| pending   | Gray  | `#e0e0e0` |
| executing | Blue  | `#bbdefb` |
| completed | Green | `#c8e6c9` |
| failed    | Red   | `#ffcdd2` |
