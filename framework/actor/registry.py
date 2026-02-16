"""
ActorRegistry singleton for the JAF framework.

Tickets: JAF-17, JAF-18, JAF-19, JAF-20
"""

from __future__ import annotations

import importlib
import inspect
import os
from typing import Dict, List, Type

from framework.actor.base_actor import Actor
from framework.logging import get_logger

logger = get_logger(__name__)


class ActorRegistry:
    """
    Singleton registry for all Actors.

    Responsibilities:
    - Register actors by name (explicit, authoritative)
    - Retrieve configured actor instances
    - List registered actors
    - Discover actors from agents.yaml (legacy / backward compatibility)
    - Generate agents.yaml from registered actors (JAF-20)

    Usage:
        ActorRegistry.register("MyActor", MyActorClass)
        actor = ActorRegistry.get("MyActor")
        names = ActorRegistry.list()
    """

    _registry: Dict[str, Type[Actor]] = {}

    # -------------------------------------------------------------------------
    # REGISTER
    # -------------------------------------------------------------------------

    @classmethod
    def register(cls, name: str, actor_class: Type[Actor]) -> None:
        """
        Register an actor class by name.

        Args:
            name: Unique name for this actor
            actor_class: Class that inherits from Actor

        Raises:
            TypeError: If actor_class does not inherit from Actor
        """
        if not issubclass(actor_class, Actor):
            raise TypeError(f"{actor_class} must inherit from Actor")

        cls._registry[name] = actor_class
        logger.debug(f"Registered actor: {name}")

    # -------------------------------------------------------------------------
    # GET
    # -------------------------------------------------------------------------

    @classmethod
    def get(cls, name: str, **kwargs) -> Actor:
        """
        Retrieve a configured actor instance by name.

        Args:
            name: Name of the registered actor
            **kwargs: Optional arguments to pass to actor constructor

        Returns:
            Configured Actor instance

        Raises:
            KeyError: If actor is not registered
        """
        if name not in cls._registry:
            raise KeyError(f"Actor '{name}' is not registered")

        instance = cls._registry[name](**kwargs)
        instance.configure()
        return instance

    # -------------------------------------------------------------------------
    # LIST
    # -------------------------------------------------------------------------

    @classmethod
    def list(cls) -> List[str]:
        """Return list of all registered actor names."""
        return list(cls._registry.keys())

    # -------------------------------------------------------------------------
    # CLEAR (for testing)
    # -------------------------------------------------------------------------

    @classmethod
    def clear(cls) -> None:
        """Clear all registered actors. Primarily for testing."""
        cls._registry.clear()

    # -------------------------------------------------------------------------
    # YAML GENERATION (LEGACY FORMAT)
    # -------------------------------------------------------------------------

    @classmethod
    def generate_yaml(cls, output_path: str = "agents.yaml") -> None:
        """
        Generate agents.yaml in the legacy structure.

        IMPORTANT:
        - The YAML name is the registry key (authoritative)
        - Schemas are TYPE METADATA ONLY (str, list, bool, etc.)

        Args:
            output_path: Path to write the YAML file
        """
        yaml_entries = []

        for registry_name, actor_class in cls._registry.items():
            instance = actor_class()
            instance.configure()

            # Description
            description = instance.description or ""
            if not description.endswith("\n"):
                description += "\n"

            tools_yaml = []

            for tool in instance.tools:
                sig = inspect.signature(tool)

                # Build input_schema as {param: type}
                input_schema = {}
                for param_name, param in sig.parameters.items():
                    if param_name == "self":
                        continue

                    if param.annotation != inspect._empty:
                        annotation = param.annotation
                        type_str = str(annotation)

                        # Normalize typing to YAML-safe primitives
                        if (
                            annotation is list
                            or "List" in type_str
                            or "list" in type_str
                        ):
                            input_schema[param_name] = "list"
                        elif "Dict" in type_str or "dict" in type_str:
                            input_schema[param_name] = "dict"
                        elif "Optional" in type_str:
                            input_schema[param_name] = "optional"
                        elif hasattr(annotation, "__name__"):
                            input_schema[param_name] = annotation.__name__.lower()
                        else:
                            input_schema[param_name] = "any"
                    else:
                        input_schema[param_name] = "any"

                # Legacy JAF convention: output_schema is always xml: str
                output_schema = {"xml": "str"}

                tools_yaml.append(
                    {
                        "name": tool.__name__,
                        "description": (tool.__doc__ or "").strip(),
                        "input_schema": input_schema,
                        "output_schema": output_schema,
                    }
                )

            yaml_entries.append(
                {
                    "name": registry_name,
                    "description": description,
                    "tools": tools_yaml,
                }
            )

        try:
            import yaml
        except ImportError:
            raise ImportError(
                "YAML generation requires 'pyyaml'. Install with: pip install pyyaml"
            )

        with open(output_path, "w", encoding="utf-8") as f:
            yaml.dump(
                yaml_entries,
                f,
                sort_keys=False,
                allow_unicode=True,
                default_flow_style=False,
            )

        logger.info(f"Generated legacy agents.yaml → {output_path}")

    # -------------------------------------------------------------------------
    # YAML DISCOVERY (LEGACY BACKWARD COMPAT)
    # -------------------------------------------------------------------------

    @classmethod
    def discover_from_yaml(cls, path: str = "agents.yaml") -> None:
        """
        Discover actors from a legacy agents.yaml file.

        NOTE:
        - YAML is NOT the source of execution logic
        - It is metadata only
        - We only auto-load actors if module + class are provided

        Args:
            path: Path to the agents.yaml file
        """
        if not os.path.exists(path):
            logger.warning(f"agents.yaml not found at {path}")
            return

        try:
            import yaml
        except ImportError:
            logger.warning(
                "YAML discovery requires 'pyyaml'. Install with: pip install pyyaml"
            )
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                actors_data = yaml.safe_load(f)
        except Exception as e:
            logger.warning(f"Failed to read agents.yaml: {e}")
            return

        if not isinstance(actors_data, list):
            logger.warning("Invalid YAML format: expected a list at root")
            return

        for entry in actors_data:
            try:
                name = entry.get("name")
                module_path = entry.get("module")
                class_name = entry.get("class")

                if not name:
                    logger.warning("Actor entry missing 'name', skipping.")
                    continue

                if not module_path or not class_name:
                    logger.debug(
                        f"Actor '{name}' declared without module/class (metadata-only)."
                    )
                    continue

                module = importlib.import_module(module_path)
                actor_class = getattr(module, class_name)

                cls.register(name, actor_class)
                logger.info(f"Discovered actor '{name}' from YAML")

            except Exception as e:
                logger.warning(f"Failed to load actor '{entry}': {e}")
