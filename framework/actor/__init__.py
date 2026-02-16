"""
Actor module for the JAF framework.

Exports:
- Actor: Abstract base class for all actors
- ActorRegistry: Singleton registry for actor management
"""

from framework.actor.base_actor import Actor
from framework.actor.registry import ActorRegistry

__all__ = ["Actor", "ActorRegistry"]
