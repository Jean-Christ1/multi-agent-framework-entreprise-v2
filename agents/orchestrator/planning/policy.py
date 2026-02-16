"""
Policy template loader and matching utilities.
"""

from __future__ import annotations

import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..utils import StructuredLogger

logger = StructuredLogger(__name__)


@dataclass
class PolicyTemplate:
    """Represents a policy-driven orchestration template."""

    scenario: str
    domain: str
    version: str
    triggers: Dict[str, Any] = field(default_factory=dict)
    requirements: Dict[str, Any] = field(default_factory=dict)
    workflow: Dict[str, Any] = field(default_factory=dict)
    raw: Dict[str, Any] = field(default_factory=dict)

    def matches(self, prompt: str) -> bool:
        """Return True if the prompt satisfies trigger rules."""
        prompt_lower = prompt.lower()

        keywords = self.triggers.get("keywords", [])
        if keywords and any(keyword.lower() in prompt_lower for keyword in keywords):
            return True

        expressions = self.triggers.get("intent_classifiers", [])
        for expr in expressions:
            pattern = expr.get("pattern")
            if not pattern:
                continue
            try:
                import re

                if re.search(pattern, prompt, flags=re.IGNORECASE):
                    return True
            except re.error as err:
                logger.warning(
                    "Invalid policy regex pattern",
                    pattern=pattern,
                    error=str(err),
                    scenario=self.scenario,
                )
        return False


class PolicyRepository:
    """Loads and caches policy templates from disk."""

    def __init__(self, base_path: str = "config/policies"):
        self.base_path = Path(base_path)
        self._policies: List[PolicyTemplate] = []

    def load(self):
        """Load all YAML policy files from disk."""
        if not self.base_path.exists():
            logger.debug("Policy directory does not exist", path=str(self.base_path))
            return

        for yaml_path in self.base_path.rglob("*.yaml"):
            try:
                with yaml_path.open("r", encoding="utf-8") as handle:
                    payload = yaml.safe_load(handle)
            except Exception as exc:
                logger.warning(
                    "Failed to load policy file", path=str(yaml_path), error=str(exc)
                )
                continue

            metadata = payload.get("metadata", {})
            scenario = metadata.get("scenario")
            domain = metadata.get("domain", "general")
            version = str(metadata.get("version", "1"))

            if not scenario:
                logger.warning("Policy missing scenario metadata", path=str(yaml_path))
                continue

            policy = PolicyTemplate(
                scenario=scenario,
                domain=domain,
                version=version,
                triggers=payload.get("triggers", {}),
                requirements=payload.get("requirements", {}),
                workflow=payload.get("workflow", {}),
                raw=payload,
            )
            self._policies.append(policy)

        logger.info(
            "Policy templates loaded",
            count=len(self._policies),
            base_path=str(self.base_path),
        )

    def find_matching(self, prompt: str) -> Optional[PolicyTemplate]:
        """Return the first policy matching the prompt."""
        for policy in self._policies:
            try:
                if policy.matches(prompt):
                    return policy
            except Exception as exc:
                logger.warning(
                    "Policy evaluation error",
                    scenario=policy.scenario,
                    error=str(exc),
                )
        return None

    def all(self) -> List[PolicyTemplate]:
        return list(self._policies)
