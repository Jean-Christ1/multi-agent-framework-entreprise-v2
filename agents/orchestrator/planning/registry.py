"""
Planner registry manages available planners and selection logic.
"""

from __future__ import annotations

from typing import Dict, Optional

from .base import Planner, PlanningError


class PlannerRegistry:
    """Registry of orchestrator planners with selection helpers."""

    def __init__(self, default: str = "deterministic", fallback: Optional[str] = None):
        self._planners: Dict[str, Planner] = {}
        self.default = default
        self.fallback = fallback or default

    def register(self, planner: Planner):
        """Register a planner instance."""
        if planner.name in self._planners:
            raise PlanningError(f"Planner '{planner.name}' already registered.")
        self._planners[planner.name] = planner

    def get(self, name: str) -> Planner:
        """Return a planner by name or raise error."""
        if name not in self._planners:
            raise PlanningError(f"Planner '{name}' not found.")
        return self._planners[name]

    def select(self, preferred: Optional[str] = None) -> Planner:
        """Select a planner based on preference or defaults."""
        candidates = [preferred, self.default, self.fallback]
        for candidate in candidates:
            if not candidate:
                continue
            try:
                return self.get(candidate)
            except PlanningError:
                continue
        raise PlanningError("No planners available in registry.")

    def available(self) -> Dict[str, Planner]:
        """Return registered planners."""
        return dict(self._planners)
