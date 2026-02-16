"""
Agentic Flow Example (Demo Outcome #1)
======================================

This document explains the **Agentic Flow** example implemented in
`examples/agentic_flow.py`. It is the primary "demo artifact" for
stakeholders and a reference pattern for developers.

The core idea: **a single orchestrator actor uses multiple tools
sequentially to achieve a goal, without delegating to other agents.**

1. High-Level Overview

---

**Scenario:** Onboarding a new developer with laptop provisioning.

- **Actor:** `ProvisionningAgent`
- **Mode:** Agentic (single actor, multiple tools)
- **Goal:** Provision equipment for a new employee end-to-end
- **External systems (mocked for the demo):**
  - Provisioning rules service
  - Order management / logistics
  - Hardware inventory
  - Manager notification frontend

What this demo shows:

- How a single actor can orchestrate a realistic business workflow
  just by calling its tools.
- How to use `EventBus` + `AgentAction` for real-time UI / console updates.
- How to build reproducible demos using mock HTTP responses.

2. How to Run the Demo

---

From the project root:

```bash
python examples/agentic_flow.py
```

What you should see:

- A header describing the scenario (new developer onboarding).
- Four clearly labeled steps:
  1. Check Employee Eligibility
  2. Select Equipment Model
  3. Place Order
  4. Notify Manager
- Real-time events logged to the console, e.g.:
  - `workflow_started`
  - `tool_call`
  - `eligibility_verified`
  - `model_selected`
  - `order_placed`
  - `manager_notified`
  - `workflow_completed`
- A final summary block showing:
  - Employee ID / name
  - Selected equipment model
  - Order number
  - Tracking number
  - Expected delivery date

3. Actor: ProvisionningAgent

---

The orchestrator in this flow is `ProvisionningAgent`
(`agents/provisionning_agent.py`).

Key points:

- It subclasses the framework `Actor` base class.
- In `configure()`, it:
  - Sets `name`, `description`, and `goal`.
  - Registers multiple **tools** in `self.tools`:
    - `verifier_eligibilite_collaborateur_offre_A`
    - `selectionner_modele_attribue`
    - `commander_produit`
    - `notifier_manager_statut_livraison`
    - (and others used in more complex workflows)
  - Sets `llm_config = None` (deterministic actor, no LLM).

In the agentic flow demo, we explicitly exercise these tools in
sequence to implement the onboarding scenario.

4. Example Flow: Step-by-Step

---

The demo is implemented in `examples/agentic_flow.py`. It drives the
actor directly, without any higher-level engine, to make the pattern
easy to understand.

### 4.1 Setup

- Imports and paths are set up so the script can import from
  `framework.*` and `agents.*`.
- `EventBus` is initialized and a simple subscriber prints every
  `AgentAction` to the console.
- Input data is prepared:
  - Employee ID, name, role, department.
  - Manager ID.
  - Delivery address.
- A `ProvisionningAgent` instance is created and `configure()` is
  called so its tools are registered.

### 4.2 Mocked HTTP Calls

The real `ProvisionningAgent` methods use `requests` to talk to
external systems. For a deterministic demo, the script uses `unittest.mock`
to patch:

- `requests.get`
- `requests.post`
- `requests.put`

Each patched function returns a realistic JSON payload from
`MOCK_RESPONSES` (e.g. eligibility = true, specific laptop model,
order number, tracking number).

This makes the demo:

- Fully reproducible.
- Independent of any real backend.
- Safe to run in any environment.

### 4.3 Execution Steps

Inside the `with patch(...):` block, the demo performs four main steps
using tools on the same actor:

1. **Check Employee Eligibility**

   - Calls `verifier_eligibilite_collaborateur_offre_A(cuid)`.
   - Uses mocked responses to determine if the employee is eligible.
   - Prints a structured result (status, reasons, existing equipment).
   - Emits events:
     - `tool_call`
     - `eligibility_verified` (if eligible).

2. **Select Equipment Model**

   - Calls `selectionner_modele_attribue(cuid)`.
   - Uses mock data to choose a recommended laptop model and show
     alternatives and stock.
   - Emits:
     - `tool_call`
     - `model_selected`.

3. **Place Order**

   - Calls `commander_produit(cuid, modele, adresse_livraison)`.
   - Mocked POST returns:
     - Order number.
     - Status.
     - Expected delivery date.
     - Carrier and tracking number.
   - Emits:
     - `tool_call`
     - `order_placed`.

4. **Notify Manager**

   - Calls `notifier_manager_statut_livraison(cuid, numero_commande, manager_cuid)`.
   - Mocked calls simulate:
     - Current order status.
     - A notification being sent to the manager.
   - Emits:
     - `tool_call`
     - `manager_notified`.

At the beginning and end of the process, the demo also emits:

- `workflow_started`
- `workflow_completed`

These events clearly delimit the full flow in any UI or log viewer
subscribed to the `EventBus`.

5. Pattern for Developers

---

This example illustrates a reusable **Agentic Flow Pattern**.

### 5.1 When to Use This Pattern

- You have a **single business capability** that can be modeled as one
  actor.
- The actor needs to perform several sequential steps (tools) to reach
  a goal.
- There is no strong need to split responsibility across multiple
  specialized actors.
- You want a simple, deterministic, and cost-effective flow.

### 5.2 Steps to Create Your Own Agentic Flow

1. **Define Your Actor**

   - Subclass the framework `Actor` base class.
   - Implement `configure()`:
     - Set `name`, `description`, and `goal`.
     - Register your tools in `self.tools`.
     - Set `llm_config` to either `None` (deterministic) or an `LLMConfig`
       instance if you need an LLM.

2. **Implement Tools as Plain Methods**

   - Each tool should be a method on your actor.
   - Keep tools deterministic where possible (easy to test and mock).
   - Prefer returning structured `dict` outputs rather than free-form
     text.

3. **Write a Small Orchestration Script**

   - Create a script in `examples/` (like `agentic_flow.py`).
   - Instantiate your actor and call `configure()`.
   - Drive your tools in the order that matches your business scenario.
   - Add print helpers to show intermediate and final results.

4. **Use EventBus for Real-Time Feedback**

   - Subscribe a simple console logger to `get_event_bus()`.
   - Emit `AgentAction` events at important milestones:
     - Workflow start / end.
     - Before and after each tool call.
     - On errors (with status = `"error"`).

5. **Mock External Dependencies for Demos**

   - Use `unittest.mock.patch` to replace network calls or other
     external dependencies.
   - Provide realistic `MOCK_RESPONSES` so the flow feels real but
     remains deterministic.

6. How This Fits into the Bigger Picture

---

In the broader JAF architecture:

- **Agentic Flow** is the simplest and most cost-effective mode,
  where:
  - One actor handles the whole process.
  - No multi-agent planning or delegation is involved.
- More advanced examples (multi-agent flow, event-bus driven flows,
  CrewAI-based planning) build on the same primitives:
  - Actors with tools.
  - Engines that call `execute_step()`.
  - EventBus for observability.

"""
