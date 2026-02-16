"""
Discovery Tool - Agent discovery and capability analysis for the orchestrator
"""

import json
from typing import Dict, Any
from crewai.tools import BaseTool
from pydantic import Field
import sys
import os

# Add project root to path for imports
sys.path.append(
    os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    )
)

from utils.observability import StructuredLogger
from ..utils import get_trace_session

logger = StructuredLogger(__name__)


class DiscoveryTool(BaseTool):
    """Tool for discovering available agents and analyzing their capabilities"""

    name: str = "discover_agents"
    description: str = "MANDATORY FIRST TOOL: Returns up-to-date registry of available agents with their capabilities, tools, and schemas. Must be called before any other action."
    orchestrator: Any = Field(default=None, exclude=True)

    def __init__(self, orchestrator_instance, **kwargs):
        super().__init__(**kwargs)
        self.orchestrator = orchestrator_instance

    def _run(self, *args, **kwargs) -> str:
        """Execute agent discovery and capability analysis"""
        try:
            # Use the orchestrator instance to get discovery info
            discovery_info = self.orchestrator.discover_agents_enhanced()

            # Update trace session guard
            session = get_trace_session()
            session.discovery_called = True

            # Dynamically analyze capabilities to suggest patterns
            capability_patterns = self._analyze_capability_patterns(discovery_info)

            # Add dynamic guidance based on discovered capabilities
            discovery_info["dynamic_patterns"] = capability_patterns
            discovery_info["usage_guidance"] = {
                "next_steps": "After reviewing this agent/tool inventory, use the appropriate tools to fulfill the user's request",
                "pattern_note": "The 'dynamic_patterns' section suggests workflows based on YOUR SPECIFIC agents",
                "important_note": "You MUST use these tools to get actual data. Do not provide answers without using tools.",
            }

            logger.info(
                "Agent discovery completed",
                total_agents=discovery_info.get("total_agents", 0),
                total_tools=discovery_info.get("total_tools", 0),
            )

            return json.dumps(discovery_info, indent=2)

        except Exception as e:
            error_msg = f"Agent discovery failed: {str(e)}"
            logger.error("Discovery tool error", error=error_msg)
            return f"ERROR: {error_msg}"

    def _analyze_capability_patterns(
        self, discovery_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze discovered agents to suggest dynamic patterns based on capabilities"""
        patterns = {
            "discovered_capabilities": [],
            "suggested_workflows": [],
            "tool_relationships": [],
        }

        # Analyze tools to find capabilities
        tools_by_type = {
            "read": [],
            "write": [],
            "search": [],
            "notify": [],
            "analyze": [],
            "manage": [],
        }

        for agent_info in discovery_info.get("agents", []):
            agent_name = agent_info.get("name", "Unknown")
            for tool in agent_info.get("tools", []):
                tool_name = tool["name"].lower()
                tool_desc = tool["description"].lower()

                # Categorize tools by their apparent function
                if any(
                    word in tool_name + tool_desc
                    for word in ["get", "list", "read", "fetch", "retrieve"]
                ):
                    tools_by_type["read"].append(f"{agent_name}.{tool['name']}")
                if any(
                    word in tool_name + tool_desc
                    for word in ["create", "update", "set", "write", "add", "modify"]
                ):
                    tools_by_type["write"].append(f"{agent_name}.{tool['name']}")
                if any(
                    word in tool_name + tool_desc
                    for word in ["search", "find", "query", "lookup"]
                ):
                    tools_by_type["search"].append(f"{agent_name}.{tool['name']}")
                if any(
                    word in tool_name + tool_desc
                    for word in ["send", "notify", "email", "message", "alert"]
                ):
                    tools_by_type["notify"].append(f"{agent_name}.{tool['name']}")
                if any(
                    word in tool_name + tool_desc
                    for word in ["analyze", "report", "check", "verify"]
                ):
                    tools_by_type["analyze"].append(f"{agent_name}.{tool['name']}")
                if any(
                    word in tool_name + tool_desc
                    for word in ["manage", "control", "admin", "configure"]
                ):
                    tools_by_type["manage"].append(f"{agent_name}.{tool['name']}")

        # Build capability summary
        for capability, tools in tools_by_type.items():
            if tools:
                patterns["discovered_capabilities"].append(
                    {
                        "capability": capability,
                        "tool_count": len(tools),
                        "examples": tools[:3],  # Show first 3 examples
                    }
                )

        # Suggest workflows based on tool combinations
        if tools_by_type["search"] and tools_by_type["read"]:
            patterns["suggested_workflows"].append(
                {
                    "pattern": "Information Discovery",
                    "description": "Search for entities, then read detailed information",
                    "tools_involved": ["search", "read"],
                }
            )

        if tools_by_type["write"] and tools_by_type["notify"]:
            patterns["suggested_workflows"].append(
                {
                    "pattern": "Create and Inform",
                    "description": "Create/modify resources and notify relevant parties",
                    "tools_involved": ["write", "notify"],
                }
            )

        if tools_by_type["read"] and tools_by_type["analyze"]:
            patterns["suggested_workflows"].append(
                {
                    "pattern": "Analyze and Report",
                    "description": "Gather data and analyze for insights",
                    "tools_involved": ["read", "analyze"],
                }
            )

        if tools_by_type["manage"] and tools_by_type["write"]:
            patterns["suggested_workflows"].append(
                {
                    "pattern": "Configuration Management",
                    "description": "Manage settings and apply changes",
                    "tools_involved": ["manage", "write"],
                }
            )

        # Identify potential tool chains
        patterns["tool_relationships"].append(
            {
                "note": "Tools with matching input/output types can be chained",
                "example": "If Tool A outputs 'user_id' and Tool B requires 'user_id', they can work together",
            }
        )

        return patterns
