"""
Actor ABC for the JAF framework.

Ticket: JAF-15, JAF-16, JAF-17
"""

from abc import ABC, abstractmethod
from typing import List, Callable, Optional

from framework.types import LLMConfig


class Actor(ABC):
    """
    Abstract Actor definition for the JAF framework.

    An Actor is the atomic unit of business logic.
    It defines WHAT can be done (tools) and optionally
    HOW decisions are made (LLM or deterministic).

    Every Actor must define:
    - name: Unique identifier
    - description: Human-readable description
    - goal: High-level purpose
    - tools: List of deterministic callables
    - llm_config: Optional LLMConfig (None = deterministic actor)

    Subclasses must implement `configure()` where:
    - All metadata is assigned
    - Tools & utilities are registered
    - LLM vs deterministic mode is chosen
    """

    # Required metadata (assigned in configure)
    name: str
    description: str
    goal: str

    # Execution components
    tools: List[Callable]
    utilities: List[Callable]
    llm_config: Optional[LLMConfig]

    def __init__(self) -> None:
        """
        Initialize instance-level attributes.

        IMPORTANT:
        - Avoid shared mutable state between actor instances
        - `configure()` is NOT called here
        """
        self.name = ""
        self.description = ""
        self.goal = ""
        self.tools = []
        self.utilities = []
        self.llm_config = None

    @abstractmethod
    def configure(self) -> None:
        """
        Configure the Actor.

        Subclasses MUST override this method to:
        - Set name, description, and goal
        - Register tools: self.tools = [self.tool1, self.tool2, ...]
        - Optionally register utilities
        - Define llm_config (LLMConfig or None)

        This method is called ONCE by the ActorRegistry
        after instantiation.

        Do NOT call configure() manually in __init__.
        """
        pass
