"""
Evaluation Tool - Assesses execution quality and success metrics for the orchestrator
"""

import json
from typing import Dict, Any, List
from crewai.tools import BaseTool
from pydantic import Field
from datetime import datetime, timezone
import sys
import os

# Add project root to path for imports
sys.path.append(
    os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    )
)

from utils.observability import StructuredLogger

logger = StructuredLogger(__name__)


class EvaluationTool(BaseTool):
    """Tool for evaluating orchestrator execution quality and success metrics"""

    name: str = "evaluate_execution"
    description: str = "Evaluate the quality and success of the orchestrator's execution, providing metrics and improvement suggestions"
    orchestrator: Any = Field(default=None, exclude=True)
    evaluation_history: List = Field(default_factory=list, exclude=True)

    def __init__(self, orchestrator_instance, **kwargs):
        super().__init__(**kwargs)
        self.orchestrator = orchestrator_instance
        self.evaluation_history = []

    def _run(self, *args, **kwargs) -> str:
        """Execute evaluation of current orchestrator state and recent executions"""
        try:
            evaluation_data = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "system_health": self._evaluate_system_health(),
                "agent_performance": self._evaluate_agent_performance(),
                "tool_effectiveness": self._evaluate_tool_effectiveness(),
                "llm_performance": self._evaluate_llm_performance(),
                "recommendations": self._generate_recommendations(),
            }

            # Store in history for trending
            self.evaluation_history.append(evaluation_data)

            # Keep only last 10 evaluations
            if len(self.evaluation_history) > 10:
                self.evaluation_history = self.evaluation_history[-10:]

            logger.info(
                "Execution evaluation completed",
                overall_score=evaluation_data.get("overall_score", "N/A"),
                recommendations_count=len(evaluation_data.get("recommendations", [])),
            )

            return json.dumps(evaluation_data, indent=2)

        except Exception as e:
            error_msg = f"Evaluation failed: {str(e)}"
            logger.error("Evaluation tool error", error=error_msg)
            return f"ERROR: {error_msg}"

    def _evaluate_system_health(self) -> Dict[str, Any]:
        """Evaluate overall system health"""
        health_status = self.orchestrator.get_agent_health_status()

        total_agents = health_status["total_agents_configured"]
        loaded_agents = health_status["agents_loaded"]
        healthy_agents = health_status["agents_healthy"]

        # Calculate health scores
        load_rate = (loaded_agents / total_agents) * 100 if total_agents > 0 else 0
        health_rate = (healthy_agents / loaded_agents) * 100 if loaded_agents > 0 else 0

        return {
            "total_agents_configured": total_agents,
            "agents_loaded": loaded_agents,
            "agents_healthy": healthy_agents,
            "load_success_rate": round(load_rate, 2),
            "health_success_rate": round(health_rate, 2),
            "overall_system_score": round((load_rate + health_rate) / 2, 2),
            "status": (
                "healthy"
                if health_rate > 80
                else "degraded"
                if health_rate > 50
                else "critical"
            ),
        }

    def _evaluate_agent_performance(self) -> Dict[str, Any]:
        """Evaluate individual agent performance"""
        agent_scores = {}
        total_tools = 0

        for agent_name, agent_instance in self.orchestrator.agent_instances.items():
            # Count tools for this agent
            agent_tools = [
                t
                for t in self.orchestrator.tools
                if t.name.startswith(f"{agent_name}_")
            ]
            tool_count = len(agent_tools)
            total_tools += tool_count

            # Basic performance metrics
            has_description = hasattr(agent_instance, "description") and bool(
                agent_instance.description
            )
            has_tools = tool_count > 0

            # Calculate score based on available metrics
            score = 0
            if has_description:
                score += 40
            if has_tools:
                score += 40
            if tool_count > 3:  # Bonus for rich tool set
                score += 20

            agent_scores[agent_name] = {
                "tool_count": tool_count,
                "has_description": has_description,
                "performance_score": score,
                "status": (
                    "excellent"
                    if score >= 80
                    else "good"
                    if score >= 60
                    else "needs_improvement"
                ),
            }

        # Calculate overall agent performance
        if agent_scores:
            avg_score = sum(
                agent["performance_score"] for agent in agent_scores.values()
            ) / len(agent_scores)
        else:
            avg_score = 0

        return {
            "individual_agents": agent_scores,
            "total_tools_available": total_tools,
            "average_agent_score": round(avg_score, 2),
            "agent_count": len(agent_scores),
        }

    def _evaluate_tool_effectiveness(self) -> Dict[str, Any]:
        """Evaluate tool configuration and effectiveness"""
        tool_analysis = {
            "total_tools": len(self.orchestrator.tools),
            "orchestrator_tools": len(self.orchestrator.orchestrator_tools),
            "agent_tools": len(self.orchestrator.tools),
            "tool_categories": {},
        }

        # Categorize tools by type
        categories = {
            "read": ["get", "list", "read", "fetch", "retrieve"],
            "write": ["create", "update", "set", "write", "add", "modify"],
            "search": ["search", "find", "query", "lookup"],
            "notify": ["send", "notify", "email", "message", "alert"],
            "analyze": ["analyze", "report", "check", "verify"],
            "manage": ["manage", "control", "admin", "configure"],
        }

        for category, keywords in categories.items():
            tool_analysis["tool_categories"][category] = 0

            for tool in self.orchestrator.tools:
                tool_name_lower = tool.name.lower()
                tool_desc_lower = tool.description.lower()

                if any(
                    keyword in tool_name_lower + tool_desc_lower for keyword in keywords
                ):
                    tool_analysis["tool_categories"][category] += 1

        # Calculate effectiveness score
        total_categorized = sum(tool_analysis["tool_categories"].values())
        coverage_score = (
            len([c for c in tool_analysis["tool_categories"].values() if c > 0])
            / len(categories)
        ) * 100

        tool_analysis["categorization_coverage"] = round(coverage_score, 2)
        tool_analysis["tools_categorized"] = total_categorized
        tool_analysis["effectiveness_score"] = round(coverage_score, 2)

        return tool_analysis

    def _evaluate_llm_performance(self) -> Dict[str, Any]:
        """Evaluate LLM and quota manager performance"""
        llm_stats = {}

        if hasattr(self.orchestrator, "quota_manager"):
            stats = self.orchestrator.quota_manager.get_stats()

            total_requests = stats.get("total_requests", 0)
            total_failures = stats.get("total_failures", 0)

            success_rate = (
                ((total_requests - total_failures) / total_requests * 100)
                if total_requests > 0
                else 100
            )

            llm_stats = {
                "total_requests": total_requests,
                "total_failures": total_failures,
                "success_rate": round(success_rate, 2),
                "models_available": len(stats.get("models", {})),
                "quota_exceeded_models": len(
                    [
                        m
                        for m, data in stats.get("models", {}).items()
                        if data.get("quota_exceeded", False)
                    ]
                ),
                "performance_score": round(success_rate, 2),
            }
        else:
            llm_stats = {
                "quota_manager_available": False,
                "performance_score": 50,  # Default score when no quota manager
            }

        return llm_stats

    def _generate_recommendations(self) -> List[Dict[str, Any]]:
        """Generate recommendations for improvement"""
        recommendations = []

        # System health recommendations
        health = self._evaluate_system_health()
        if health["load_success_rate"] < 100:
            recommendations.append(
                {
                    "category": "system_health",
                    "priority": "high",
                    "issue": "Some agents failed to load",
                    "recommendation": "Check agent configurations and dependencies. Use reload_failed_agents() to retry loading.",
                    "impact": "Reduced system capabilities",
                }
            )

        if health["health_success_rate"] < 80:
            recommendations.append(
                {
                    "category": "system_health",
                    "priority": "medium",
                    "issue": "Some loaded agents are not responding properly",
                    "recommendation": "Verify agent health status and restart unhealthy agents",
                    "impact": "Potential execution failures",
                }
            )

        # Tool effectiveness recommendations
        tool_eval = self._evaluate_tool_effectiveness()
        if tool_eval["categorization_coverage"] < 50:
            recommendations.append(
                {
                    "category": "tool_effectiveness",
                    "priority": "medium",
                    "issue": "Limited tool category coverage",
                    "recommendation": "Consider adding more diverse tools to cover read, write, search, notify, analyze, and manage operations",
                    "impact": "Limited workflow capabilities",
                }
            )

        # LLM performance recommendations
        llm_eval = self._evaluate_llm_performance()
        if llm_eval.get("success_rate", 100) < 90:
            recommendations.append(
                {
                    "category": "llm_performance",
                    "priority": "high",
                    "issue": "High LLM failure rate",
                    "recommendation": "Check API key validity, rate limits, and network connectivity. Consider enabling enhanced LLM with quota management.",
                    "impact": "Execution failures and poor user experience",
                }
            )

        if llm_eval.get("quota_exceeded_models", 0) > 0:
            recommendations.append(
                {
                    "category": "llm_performance",
                    "priority": "medium",
                    "issue": "Some models have exceeded quotas",
                    "recommendation": "Monitor usage patterns and consider upgrading API limits or using model fallback strategies",
                    "impact": "Reduced model availability",
                }
            )

        return recommendations
