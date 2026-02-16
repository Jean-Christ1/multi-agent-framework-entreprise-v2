"""Simple heuristic-based scenario classifier for deterministic workflows."""

from typing import Optional


def classify_scenario(prompt: str) -> Optional[str]:
    """Return scenario key ('onboarding', 'offboarding', 'replacement') or None."""

    if not prompt:
        return None

    text = prompt.lower()

    onboarding_indicators = [
        "onboard",
        "nouvelle embauche",
        "nouvel employé",
        "offre onboarding",
        "j-3",
        "j0",
        "start date",
        "manager picks offre",
        "habilitation",  # combined with other cues often
    ]

    offboarding_indicators = [
        "offboard",
        "offboarding",
        "sortie",
        "restitution",
        "dernier jour",
        "j-0",
        "désactivation",
        "revoker",
        "revocation",
    ]

    replacement_indicators = [
        "remplacement",
        "replace pc",
        "défectueux",
        "defective",
        "swap",
        "ticket",
        "urgence pc",
        "pc de remplacement",
    ]

    if any(token in text for token in replacement_indicators):
        return "replacement"

    if any(token in text for token in offboarding_indicators):
        return "offboarding"

    if any(token in text for token in onboarding_indicators):
        return "onboarding"

    return None


__all__ = ["classify_scenario"]
