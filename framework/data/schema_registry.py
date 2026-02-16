"""
schema_registry.py JAF-82: Centralized schema extraction for JAF tool contracts.

- Scans all registered actors and their tools for __tool_contract__ schema metadata.
- Aggregates input/output schemas for documentation, validation, and integration.
- Provides export as JSON and (stub) OpenAPI formats for external use.
"""

from typing import Dict, Any, List
from framework.actor.registry import ActorRegistry


class SchemaRegistry:
    """
    Central registry to collect input/output schemas from all registered tools.
    """

    @staticmethod
    def collect_tool_schemas() -> List[Dict[str, Any]]:
        schemas = []
        for actor_name in ActorRegistry.list():
            actor = ActorRegistry.get(actor_name)
            for tool in getattr(actor, "tools", []):
                contract = getattr(tool, "__tool_contract__", None)
                if contract and hasattr(contract, "to_schema_dict"):
                    schema_info = {"actor": actor_name, "tool": tool.__name__}
                    schema_info.update(contract.to_schema_dict())
                    schemas.append(schema_info)
        return schemas

    @staticmethod
    def export_json() -> List[Dict[str, Any]]:
        """Export all schemas as a JSON-serializable list."""
        return SchemaRegistry.collect_tool_schemas()

    @staticmethod
    def export_openapi() -> Dict[str, Any]:
        """
        Export schemas in OpenAPI 3.0 format.
        Each tool is mapped to a POST endpoint under /actors/{actor}/{tool}.
        """
        openapi = {
            "openapi": "3.0.0",
            "info": {"title": "JAF Tool API", "version": "1.0.0"},
            "paths": {},
            "components": {"schemas": {}},
        }
        schemas = SchemaRegistry.collect_tool_schemas()
        for s in schemas:
            path = f"/actors/{s['actor']}/{s['tool']}"
            # Register input/output schemas as components
            input_name = s.get("input_type") or f"{s['actor']}_{s['tool']}_Input"
            output_name = s.get("output_type") or f"{s['actor']}_{s['tool']}_Output"
            schemas_dict: dict[str, Any] = openapi["components"]["schemas"]  # type: ignore[assignment, index]
            if s.get("input_schema"):
                schemas_dict[input_name] = s["input_schema"]
            if s.get("output_schema"):
                schemas_dict[output_name] = s["output_schema"]
            # Define the path
            paths_dict: dict[str, Any] = openapi["paths"]  # type: ignore[assignment, index]
            paths_dict[path] = {
                "post": {
                    "summary": f"Invoke {s['actor']}.{s['tool']}",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": f"#/components/schemas/{input_name}"}
                            }
                        },
                    },
                }
            }
