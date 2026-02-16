#!/usr/bin/env python3
"""
JAF Example: Simple Actor Tutorial

This is a minimal example showing how to create and run a custom actor in JAF.

It demonstrates:
- Creating an Actor class
- Implementing the configure() method
- Defining tools (callable functions)
- Registering the actor with ActorRegistry
- Running the actor standalone (no database required)

Usage:
    python examples/simple_actor_example.py

No external dependencies required - runs completely standalone.
"""

import sys

from framework.actor.base_actor import Actor
from framework.actor.registry import ActorRegistry

# =============================================================================
# STEP 1: Define Your Actor Class
# =============================================================================


class CalculatorActor(Actor):
    """
    A simple calculator actor that performs basic math operations.

    This actor demonstrates:
    - How to inherit from Actor
    - How to implement configure()
    - How to define tools
    - How to make a deterministic actor (no LLM)
    """

    def configure(self) -> None:
        """
        Configure the actor.

        This method is called ONCE by the ActorRegistry when you retrieve
        an actor instance. It's where you set up all actor metadata and tools.

        Required attributes:
        - self.name: Unique identifier for the actor
        - self.description: Human-readable description
        - self.goal: High-level purpose of the actor
        - self.tools: List of callable functions (tools)
        - self.llm_config: Optional LLMConfig (None = deterministic actor)
        """
        # Set actor metadata
        self.name = "CalculatorActor"
        self.description = "A simple calculator that performs basic math operations"
        self.goal = "Provide accurate mathematical calculations"

        # Register tools - these are the functions the actor can execute
        # Tools are just regular methods that you add to the tools list
        self.tools = [
            self.add,
            self.subtract,
            self.multiply,
            self.divide,
        ]

        # Set LLM configuration
        # None = deterministic actor (no AI, pure logic)
        # LLMConfig(...) = probabilistic actor (uses AI for decision-making)
        self.llm_config = None  # This is a deterministic actor

    # =========================================================================
    # STEP 2: Define Your Tools
    # =========================================================================

    def add(self, a: float, b: float) -> float:
        return a + b

    def subtract(self, a: float, b: float) -> float:
        return a - b

    def multiply(self, a: float, b: float) -> float:
        return a * b

    def divide(self, a: float, b: float) -> float:
        if b == 0:
            raise ValueError("Cannot divide by zero")
        return a / b


# =============================================================================
# STEP 3: Register and Use Your Actor
# =============================================================================


def main():
    """
    Main function demonstrating how to use the actor.

    Steps:
    1. Register the actor class with ActorRegistry
    2. Retrieve a configured instance
    3. Use the actor's tools
    4. List all registered actors
    """

    print("=" * 70)
    print("JAF Simple Actor Tutorial")
    print("=" * 70)
    print()

    # -------------------------------------------------------------------------
    # STEP 3.1: Register the Actor
    # -------------------------------------------------------------------------
    print("Step 1: Registering CalculatorActor with ActorRegistry...")
    ActorRegistry.register("CalculatorActor", CalculatorActor)
    print("   ✓ Registered!")
    print()

    # -------------------------------------------------------------------------
    # STEP 3.2: Retrieve a Configured Instance
    # -------------------------------------------------------------------------
    print("Step 2: Retrieving configured actor instance...")
    # ActorRegistry.get() will:
    #   1. Instantiate the actor class
    #   2. Call configure() automatically
    #   3. Return the configured instance
    actor = ActorRegistry.get("CalculatorActor")

    print(f"   Actor Name: {actor.name}")
    print(f"   Description: {actor.description}")
    print(f"   Goal: {actor.goal}")
    print(f"   Number of Tools: {len(actor.tools)}")
    print(f"   Tools: {[tool.__name__ for tool in actor.tools]}")
    print(f"   Has LLM: {actor.llm_config is not None}")
    print()

    # -------------------------------------------------------------------------
    # STEP 3.3: Use the Actor's Tools
    # -------------------------------------------------------------------------
    print("Step 3: Using actor tools...")
    print()

    result1 = actor.add(10, 5)
    print(f"   {actor.name}.add(10, 5) = {result1}")

    result2 = actor.subtract(10, 5)
    print(f"   {actor.name}.subtract(10, 5) = {result2}")

    result3 = actor.multiply(10, 5)
    print(f"   {actor.name}.multiply(10, 5) = {result3}")

    result4 = actor.divide(10, 5)
    print(f"   {actor.name}.divide(10, 5) = {result4}")
    print()

    # -------------------------------------------------------------------------
    # STEP 3.4: List All Registered Actors
    # -------------------------------------------------------------------------
    print("Step 4: Listing all registered actors...")
    registered_actors = ActorRegistry.list()
    print(f"   Registered actors: {registered_actors}")
    print()

    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
