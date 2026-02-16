# Getting Started with JAF

Welcome to the JAF (Jems Agent Framework)! This guide will help you get up and running with your first automation workflow.

## Prerequisites

Before you begin, ensure you have:

- **Python 3.11+** installed

  ```bash
  python3 --version
  ```

- **PostgreSQL** (optional, only needed for database persistence)

  - For standalone examples, PostgreSQL is not required
  - For full orchestrator features, install PostgreSQL 12+

- **Git** for cloning the repository

> **Note:** JAF uses tiered dependencies. Install only what you need:
> - `requirements-core.txt` - Core framework (recommended for getting started)
> - `requirements-llm.txt` - Adds LLM support for agentic workflows

## Clone & Setup

### 1. Clone the Repository

```bash
git clone https://gitlab.jems-group.com/jems/interne/jems-multi-agent-framework/jems-multi-agent-framework.git
cd jems-multi-agent-framework
```

### 2. Create a Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate it
# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

### 3. Install Dependencies

JAF offers tiered dependency installation based on your needs:

```bash
# Core only (recommended for getting started)
pip install -r requirements-core.txt

# With LLM support (for agentic flows)
pip install -r requirements-llm.txt

# Optional: Install ETL demo dependencies (for running the ETL demo)
pip install pyarrow pandas faker pyyaml lxml
```

### 4. Set Up Environment Variables (Optional)

For database persistence features:

```bash
# Copy example environment file
cp env.example .env

# Edit .env and set your DATABASE_URL
# DATABASE_URL=postgresql+asyncpg://user:password@localhost/jaf_dev
```

> **Note:** For the "Hello World" example below, you don't need a database. Database setup is only required for full orchestrator features.

## Hello World: Your First Actor with NativeEngine

Let's create a simple actor and run it with NativeEngine. This example demonstrates the core concepts without requiring a database or LLM API keys.

### Step 1: Create Your Actor

Create a file `hello_world.py`:

```python
#!/usr/bin/env python3
"""
Hello World example for JAF Framework.

This demonstrates:
- Creating a simple actor
- Running it with NativeEngine
- Executing a plan step-by-step
"""

import asyncio
from framework import Actor, ActorRegistry, NativeEngine, Plan, PlanStep
from framework import get_event_bus, console_subscriber


class CalculatorActor(Actor):
    """A simple calculator actor for demonstration."""

    def configure(self) -> None:
        self.name = "CalculatorActor"
        self.description = "Performs basic arithmetic operations"
        self.goal = "Calculate mathematical expressions"
        self.tools = [self.add, self.multiply, self.greet]
        self.llm_config = None  # Deterministic actor (no LLM needed)

    def add(self, a: int, b: int) -> int:
        """Add two numbers."""
        return a + b

    def multiply(self, x: int, y: int) -> int:
        """Multiply two numbers."""
        return x * y

    def greet(self, name: str) -> str:
        """Greet someone."""
        return f"Hello, {name}! Welcome to JAF!"


async def main():
    """Run the Hello World example."""
    print("=" * 60)
    print("JAF Hello World Example")
    print("=" * 60)
    print()

    # 1. Register the actor
    print("Step 1: Registering CalculatorActor...")
    ActorRegistry.register("CalculatorActor", CalculatorActor)
    print("   ✓ Actor registered")
    print()

    # 2. Set up event bus for real-time updates
    print("Step 2: Setting up event bus...")
    event_bus = get_event_bus()
    event_bus.subscribe(console_subscriber)
    print("   ✓ Event bus configured")
    print()

    # 3. Create a simple plan
    print("Step 3: Creating execution plan...")
    plan = Plan(
        steps=[
            PlanStep(
                actor_name="CalculatorActor",
                tool_name="greet",
                parameters={"name": "Developer"},
                status="pending",
            ),
            PlanStep(
                actor_name="CalculatorActor",
                tool_name="add",
                parameters={"a": 10, "b": 20},
                status="pending",
            ),
            PlanStep(
                actor_name="CalculatorActor",
                tool_name="multiply",
                parameters={"x": 5, "y": 6},
                status="pending",
            ),
        ],
        status="PLANNING",
    )
    print(f"   ✓ Plan created with {len(plan.steps)} steps")
    print()

    # 4. Create NativeEngine and execute the plan
    print("Step 4: Executing plan with NativeEngine...")
    print("-" * 60)

    engine = NativeEngine(default_plan=plan)
    context = {}

    # Execute each step
    for i, step in enumerate(plan.steps, 1):
        print(f"\nExecuting Step {i}: {step.actor_name}.{step.tool_name}()")
        result = await engine.execute_step(step, context)

        if result.status == "success":
            print(f"   ✓ Success: {result.output}")
            # Store result in context for next steps
            context[f"step_{i-1}_result"] = result.output
            context["last_result"] = result.output
        else:
            print(f"   ✗ Error: {result.error}")
            break

    print()
    print("-" * 60)
    print("Example completed successfully!")
    print()
    print("What happened:")
    print("  1. We created a CalculatorActor with 3 tools")
    print("  2. We registered it with ActorRegistry")
    print("  3. We created a Plan with 3 steps")
    print("  4. NativeEngine executed each step sequentially")
    print("  5. Results were stored in context for potential future steps")
    print()


if __name__ == "__main__":
    asyncio.run(main())
```

### Step 2: Run Your First Example

```bash
# Make sure you're in the project root
python hello_world.py
```

**Expected Output:**

```
============================================================
JAF Hello World Example
============================================================

Step 1: Registering CalculatorActor...
   ✓ Actor registered

Step 2: Setting up event bus...
   ✓ Event bus configured

Step 3: Creating execution plan...
   ✓ Plan created with 3 steps

Step 4: Executing plan with NativeEngine...
------------------------------------------------------------

Executing Step 1: CalculatorActor.greet()
   ✓ Success: {'result': 'Hello, Developer! Welcome to JAF!'}

Executing Step 2: CalculatorActor.add()
   ✓ Success: {'result': 30}

Executing Step 3: CalculatorActor.multiply()
   ✓ Success: {'result': 30}

------------------------------------------------------------
Example completed successfully!

What happened:
  1. We created a CalculatorActor with 3 tools
  2. We registered it with ActorRegistry
  3. We created a Plan with 3 steps
  4. NativeEngine executed each step sequentially
  5. Results were stored in context for potential future steps
```

### Understanding the Example

**Key Concepts:**

1. **Actor**: A self-contained unit with tools (methods) that can be executed

   - `CalculatorActor` has 3 tools: `add`, `multiply`, `greet`
   - `llm_config = None` means it's deterministic (no AI needed)

2. **ActorRegistry**: A singleton that manages all actors

   - Register actors: `ActorRegistry.register(name, ActorClass)`
   - Get actors: `ActorRegistry.get(name)`

3. **Plan**: A sequence of steps to execute

   - Each step specifies: actor, tool, and parameters
   - Status tracks execution state: `pending`, `completed`, `error`

4. **NativeEngine**: Executes plans without LLM dependencies

   - Perfect for deterministic workflows
   - Fast and cost-free ($0.00 per execution)

5. **Context**: A dictionary that stores intermediate results
   - Results from previous steps can be used in later steps
   - Example: `parameters={"value": "{context.step_0_result}"}`

## Running the ETL Demo

The ETL demo showcases a more complex workflow: parsing SAP BODS XML metadata and generating test datasets.

### Prerequisites for ETL Demo

```bash
# Install ETL demo dependencies
pip install pyarrow pandas faker pyyaml lxml
```

### Run the Demo

```bash
# Standalone mode (no database required)
python -m examples.etl_demo.run_demo --standalone

# With custom options
python -m examples.etl_demo.run_demo --standalone --count 100 --seed 42

# With orchestrator (requires database)
export DATABASE_URL="postgresql+asyncpg://user:pass@localhost/jaf_dev"
python -m examples.etl_demo.run_demo --count 75
```

**What the ETL Demo Does:**

1. **BODSParserActor**: Parses SAP BODS XML and extracts table schemas
2. **DataGeneratorActor**: Generates realistic aviation test data
3. **ParquetWriterActor**: Writes Parquet files for input/expected outputs

**Output:**

- `tests/fixtures/trafic_ascend/schemas/ascend_schema.yaml` - Table definitions
- `tests/fixtures/trafic_ascend/inputs/*.parquet` - Source data
- `tests/fixtures/trafic_ascend/expected/*.parquet` - Target data

For more details, see [ETL Demo README](../examples/etl_demo/README.md).

## Next Steps

### Learn More

- **[Architecture Guide](ARCHITECTURE.md)**: Deep dive into JAF's architecture
- **[Agentic Flow Example](../examples/agentic_flow.py)**: Single orchestrator with tools
- **[Multi-Agent Flow Example](../examples/multi_agent_flow.py)**: Multiple specialized actors
- **[Traditional Automation Example](../examples/traditional_automation_complete.py)**: Rule-based workflows

### Explore Examples

```bash
# Agentic flow (single actor, multiple tools)
python examples/agentic_flow.py

# Multi-agent flow (multiple actors, LLM orchestration)
# Requires OPENAI_API_KEY
export OPENAI_API_KEY="sk-your-key-here"
python examples/multi_agent_flow.py
```

### Build Your Own Actor

1. **Create a new actor class** inheriting from `Actor`
2. **Implement `configure()`** to set name, description, goal, and tools
3. **Define tools** as methods on your actor
4. **Register** with `ActorRegistry`
5. **Create a plan** and execute with `NativeEngine` or `CrewAIAdapter`

### Common Patterns

**Deterministic Actor (No LLM):**

```python
class MyActor(Actor):
    def configure(self):
        self.name = "MyActor"
        self.tools = [self.my_tool]
        self.llm_config = None  # Deterministic

    def my_tool(self, param: str) -> str:
        return f"Processed: {param}"
```

**LLM-Powered Actor:**

```python
from framework import Actor, LLMConfig

class MyActor(Actor):
    def configure(self):
        self.name = "MyActor"
        self.tools = [self.my_tool]
        self.llm_config = LLMConfig(
            model="gpt-4o-mini",
            temperature=0.7
        )
```

## Troubleshooting

### ModuleNotFoundError

```bash
# Ensure you're in the project root
pwd  # Should show: .../jems-multi-agent-framework

# Install dependencies
# For getting started examples:
pip install -r requirements-core.txt

# For LLM-powered examples:
pip install -r requirements-llm.txt
```

### Database Connection Error

```bash
# For standalone examples, database is not required
# Only needed for full orchestrator features

# If using database, verify connection:
export DATABASE_URL="postgresql+asyncpg://user:pass@localhost/jaf_dev"
psql $DATABASE_URL -c "SELECT 1"
```

### Import Errors

```bash
# Make sure you're using Python 3.11+
python3 --version

# Verify virtual environment is activated
which python  # Should point to venv/bin/python
```

## Getting Help

- **Documentation**: See [ARCHITECTURE.md](ARCHITECTURE.md) for technical details
- **Examples**: Check `examples/` directory for working code
- **Tests**: See `tests/` for usage patterns

---

**Ready to build?** Start with the Hello World example above, then explore the more complex examples in the `examples/` directory!
