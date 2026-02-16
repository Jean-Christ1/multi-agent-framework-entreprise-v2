"""
Orchestrator Agent - Main orchestrator system for multi-agent coordination

This module contains the main OrchestratorAgent class that was extracted from main.py.
It manages and coordinates all agents in the multi-agent system using CrewAI.
"""

import os
import yaml
import importlib
import asyncio
import uuid
import sys
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# Disable telemetry
os.environ["CREWAI_TELEMETRY_ENABLED"] = "false"
os.environ["CREWAI_TELEMETRY_OPT_OUT"] = "true"

# Add project root to path for imports
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

# CrewAI imports
from crewai import Agent, Task, Crew, Process
from crewai.tools import BaseTool
from langchain.memory import ConversationBufferMemory
from langchain_openai import ChatOpenAI

# Local imports
from config.service_config import config
from utils.observability import StructuredLogger, trace_operation
from .session import set_trace_id, reset_trace_id
from .utils import reset_trace_session, get_trace_session, emit_trace_event
from .scenario_classifier import classify_scenario
from .planning import (
    OrchestrationIntent,
    PlannerContext,
    PlannerRegistry,
    DeterministicPlanner,
    PlanningError,
    CrewAIPlanner,
)
from .planning.policy import PolicyRepository, PolicyTemplate

# Orchestrator specific imports
from .llm_manager import LLMQuotaManager, EnhancedChatOpenAI
from .utils import create_tool_from_method
from .tools.discovery_tool import DiscoveryTool
from .tools.evaluation_tool import EvaluationTool

logger = StructuredLogger(__name__)

# Global executor for async operations
executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="orchestrator")


class OrchestratorAgent:
    """
    Main orchestrator system using CrewAI 0.134.0 with improved architecture.

    This class manages all agents, tools, and coordination in the multi-agent system.
    It was extracted from the RefactoredOrchestratorSystem in main.py for better organization.
    """

    def __init__(self, quota_manager: Optional[LLMQuotaManager] = None):
        logger.info("Initializing orchestrator agent with CrewAI 0.134.0")
        self.logger = logger

        # Initialize shared memory for all agents
        self.shared_memory = ConversationBufferMemory(return_messages=True)
        self.conversation_memory = {}

        # Initialize LLM with optional enhancement
        use_enhanced_llm = config.use_enhanced_llm

        # Debug OpenAI configuration (don't log the actual key)
        openai_key_available = bool(
            config.openai_api_key and config.openai_api_key.strip()
        )
        openai_key_length = len(config.openai_api_key) if config.openai_api_key else 0
        logger.info(
            "OpenAI configuration",
            key_available=openai_key_available,
            key_length=openai_key_length,
            model=config.openai_model,
            enhanced_features_available=True,
            enhanced_features_enabled=use_enhanced_llm,
        )

        if not openai_key_available:
            logger.warning(
                "OpenAI API key not available - AI functionality will be limited"
            )

        # Initialize quota manager if not provided
        if quota_manager is None:
            quota_manager = LLMQuotaManager()
        self.quota_manager = quota_manager

        # Initialize LLM for orchestrator with tool calling optimizations
        if use_enhanced_llm:
            try:
                self.llm = EnhancedChatOpenAI(
                    quota_manager=self.quota_manager,
                    model=config.openai_model,
                    temperature=0.0,  # Zero temperature for deterministic tool execution
                    openai_api_key=config.openai_api_key,
                    # Cloud Run specific configurations - increased timeouts
                    request_timeout=120,  # 2 minutes for Cloud Run + VPC latency
                    max_retries=2,
                    default_headers={"User-Agent": "Orange-DISU-Agent/1.0"},
                    model_kwargs={"tool_choice": "auto"},  # Encourage tool use
                )
                logger.info(
                    "Using enhanced LLM with quota management for orchestrator",
                    model=config.openai_model,
                )
            except Exception as e:
                logger.warning(
                    "Enhanced LLM failed to initialize, falling back to standard",
                    error=str(e),
                )
                self.llm = self._create_standard_llm()
        else:
            self.llm = self._create_standard_llm()
            logger.info(
                "Using standard ChatOpenAI with Cloud Run optimizations for orchestrator",
                model=config.openai_model,
            )

        # Initialize separate LLM for individual agents (gpt-5-nano)
        if use_enhanced_llm:
            try:
                self.agent_llm = EnhancedChatOpenAI(
                    quota_manager=self.quota_manager,
                    model=config.agent_model,  # gpt-5-nano for agents
                    temperature=0.0,
                    openai_api_key=config.openai_api_key,
                    request_timeout=120,
                    max_retries=2,
                    default_headers={"User-Agent": "Orange-DISU-Agent/1.0"},
                )
                logger.info(
                    "Using enhanced LLM for individual agents", model=config.agent_model
                )
            except Exception as e:
                logger.warning(
                    "Enhanced agent LLM failed to initialize, falling back to standard",
                    error=str(e),
                )
                self.agent_llm = self._create_agent_standard_llm()
        else:
            self.agent_llm = self._create_agent_standard_llm()
            logger.info(
                "Using standard ChatOpenAI for individual agents",
                model=config.agent_model,
            )

        # Load system prompt and registry
        self._load_configuration()
        self._planner_registry = PlannerRegistry(
            default=getattr(config, "planner_default", "deterministic"),
            fallback=getattr(config, "planner_fallback", "deterministic"),
        )
        self._register_default_planners()
        self.policy_repository: Optional[PolicyRepository] = None
        if getattr(config, "enable_policy_templates", False):
            self.policy_repository = PolicyRepository()
            self.policy_repository.load()
            logger.info(
                "Policy repository enabled",
                policy_count=len(self.policy_repository.all()),
            )

        # Initialize agent instances dynamically from registry
        self.agent_instances = {}
        self._initialize_agents_from_registry()

        # Create tools from agents
        self.tools = self._create_tools()

        # Add orchestrator built-in tools for intelligent coordination
        self.orchestrator_tools = self._create_orchestrator_tools()

        # Create the orchestrator agent using intelligent prompt system
        dynamic_backstory = self._create_dynamic_backstory()

        # Configure orchestrator tools based on mode
        # In CrewAI planner mode (agentic flow), the orchestrator should NOT have domain tools
        # to force delegation to sub-agents.
        # In Deterministic mode, it might need them if it acts as a super-agent.

        planner_mode = getattr(config, "planner_default", "deterministic")

        if planner_mode == "crewai":
            # AGENTIC MODE: Orchestrator only manages, doesn't do
            orchestrator_tools_config = self.orchestrator_tools
            logger.info("🚀 Configuring Orchestrator for AGENTIC FLOW (Delegation Only)")
        else:
            # DETERMINISTIC MODE: Orchestrator does everything
            orchestrator_tools_config = self.tools + self.orchestrator_tools
            logger.info(
                "🛠️ Configuring Orchestrator for DIRECT EXECUTION (Super-Agent)"
            )

        self.orchestrator = Agent(
            role="Jems Orchestrator",
            goal="Autonomously deliver the best possible solution by planning, coordinating, and supervising a fleet of sub-agents to fulfill user requests",
            backstory=f"""{dynamic_backstory}

I am the Jems Orchestrator, using an intelligent prompt system that adapts to available agents:

🎯 MY SMART CLASSIFICATION SYSTEM:
1. FIRST: I analyze each request to determine the appropriate response approach
2. For simple conversational interactions (greetings, thanks, casual chat) → I respond directly with friendly assistance
3. For operational/technical requests (identity lookups, system operations) → I use full agent orchestration

🤖 SIMPLE CONVERSATIONAL RESPONSES:
- Greetings: "Hi! I'm the Jems Orchestrator, your intelligent assistant for system operations. I coordinate different agents to help you accomplish your tasks. How can I help you today?"
- Thanks: "Thank you! I'm here whenever you need assistance. I can discover what services are available and coordinate them to help you."
- About me: "I'm the Jems Orchestrator - I coordinate a fleet of specialized agents to help with various tasks. I discover available capabilities dynamically and plan accordingly."

🔧 FULL ORCHESTRATION FOR OPERATIONAL REQUESTS:
- Dynamic agent discovery and capability assessment
- Intelligent planning based on available tools
- Actual tool execution (never just descriptions)
- Plan adaptation based on intermediate results
- Memory management for context and continuity

❌ I NEVER:
- Use tools for simple greetings or conversational interactions
- Plan specific agent names BEFORE calling discover_agents()
- Make assumptions about which agents exist
- Hard-code agent names or tool sequences
- Just describe what I would do without executing (for operational requests)
- Give final answers without using tools (for operational requests)

✅ I ALWAYS:
- Respond appropriately based on request classification
- For operational requests: discover_agents() FIRST → then plan based on discoveries → execute → deliver results
- For conversational requests: respond directly with helpful, friendly guidance
- Adapt my approach based on what agents are actually available
- Make decisions dynamically after seeing available capabilities

🚨 CRITICAL RULES:
- Simple conversation = Direct response
- Operational tasks = Must use tools and agents""",
            memory=True,
            verbose=True,
            allow_delegation=True,
            tools=orchestrator_tools_config,
            llm=self.llm,
            max_iter=10,  # Allow more iterations for tool execution
            max_execution_time=300,  # 300 seconds (5 min) timeout for complex workflows
        )

        # Create agents from registry manifest - fully dynamic
        self.registry_agents = self._create_registry_agents()

        logger.info(
            "Orchestrator agent initialized",
            agent_instances=len(self.agent_instances),
            tools=len(self.tools),
            registry_agents=len(self.registry_agents),
        )

    def _create_standard_llm(self) -> ChatOpenAI:
        """Create standard ChatOpenAI instance for orchestrator"""
        return ChatOpenAI(
            model=config.openai_model,
            temperature=0.0,  # Zero temperature for deterministic tool execution
            openai_api_key=config.openai_api_key,
            # Cloud Run specific configurations - increased timeouts
            request_timeout=120,  # 2 minutes for Cloud Run VPC connectivity
            max_retries=2,  # Reduced retries to avoid long delays
            default_headers={
                "User-Agent": "Orange-DISU-Agent/1.0",
                "Content-Type": "application/json",
            },
            model_kwargs={"tool_choice": "auto"},  # Encourage tool use
        )

    def _create_agent_standard_llm(self) -> ChatOpenAI:
        """Create standard ChatOpenAI instance for individual agents"""
        return ChatOpenAI(
            model=config.agent_model,  # gpt-5-nano for agents
            temperature=0.0,  # Zero temperature for deterministic tool execution
            openai_api_key=config.openai_api_key,
            # Cloud Run specific configurations - increased timeouts
            request_timeout=120,  # 2 minutes for Cloud Run VPC connectivity
            max_retries=2,  # Reduced retries to avoid long delays
            default_headers={
                "User-Agent": "Orange-DISU-Agent/1.0",
                "Content-Type": "application/json",
            },
        )

    def _load_configuration(self):
        """Load system prompts and agent registry dynamically"""
        # Load agent registry first
        with open("agents.yaml", "r") as f:
            registry_data = yaml.safe_load(f)
            self.registry = registry_data.get("agents", [])

        # Import and use the prompt builder for intelligent prompt generation
        try:
            sys.path.append(
                str(Path(__file__).parent.parent.parent / "config" / "prompts")
            )
            from prompt_builder import OrchestrationPromptBuilder

            # Create intelligent prompt based on actual available agents
            prompt_builder = OrchestrationPromptBuilder()
            capabilities = prompt_builder.get_agent_capabilities(registry_data)

            # Check for complex workflow indicators in the system
            self.is_complex_workflow_mode = self._detect_complex_workflow_indicators()

            if self.is_complex_workflow_mode:
                self.system_prompt = prompt_builder.build_complex_workflow_prompt(
                    registry_data
                )
                logger.info("🧠 Using intelligent complex workflow orchestrator prompt")
            elif "workflow_automation" in capabilities or "full_crud" in capabilities:
                # Use enhanced prompt for systems with rich capabilities
                self.system_prompt = prompt_builder.build_prompt(
                    example_files=[
                        "orchestrator_examples.md",
                        "orchestrator_examples_complex.md",
                    ],
                    agent_registry=registry_data,
                    context="System has rich automation capabilities. Orchestrator will adapt dynamically.",
                )
                logger.info(
                    "🧠 Using enhanced orchestrator prompt for rich capabilities"
                )
            else:
                # Use basic prompt for simple systems
                self.system_prompt = prompt_builder.build_general_prompt(registry_data)
                logger.info("🧠 Using general orchestrator prompt")

        except ImportError as e:
            logger.warning(
                f"Prompt builder not available, falling back to static prompt: {e}"
            )
            # Fallback to static prompt if prompt builder fails
            with open("config/prompts/orchestrator_general.md", "r") as f:
                self.system_prompt = f.read()

        self.base_system_prompt = self.system_prompt

    def _register_default_planners(self):
        """Register built-in planner implementations."""
        try:
            self._planner_registry.register(DeterministicPlanner(self))
            logger.info("Registered deterministic planner", planner="deterministic")
        except PlanningError as exc:
            logger.debug("Deterministic planner registration skipped", error=str(exc))

        try:
            self._planner_registry.register(CrewAIPlanner(self))
            logger.info("Registered CrewAI planner", planner="crewai")
        except PlanningError as exc:
            logger.debug("CrewAI planner registration skipped", error=str(exc))

    def _resolve_scenario(
        self, user_prompt: str
    ) -> Tuple[Optional[str], Optional[PolicyTemplate]]:
        """Resolve scenario using policy templates when available, otherwise fallback."""
        if self.policy_repository:
            policy = self.policy_repository.find_matching(user_prompt)
            if policy:
                logger.info(
                    "Scenario resolved via policy repository",
                    scenario=policy.scenario,
                    policy_version=policy.version,
                )
                return policy.scenario, policy
        return classify_scenario(user_prompt), None

    def _detect_complex_workflow_indicators(self) -> bool:
        """Detect if the system should use complex workflow mode"""
        # Check environment variable
        if os.getenv("COMPLEX_WORKFLOWS", "false").lower() == "true":
            return True

        # Check if running complex scenarios script
        if any("complex_scenarios" in arg for arg in sys.argv):
            return True

        # Check if multiple agents are available (indicating complex setup)
        if len(self.registry) > 3:
            return True

        return False

    def _initialize_agents_from_registry(self):
        """Initialize agent instances from registry with fault tolerance"""
        agents_module = importlib.import_module("agents")

        successful_agents = {}
        failed_agents = []

        for agent_def in self.registry:
            agent_name = agent_def["name"]
            try:
                # Isolate each agent loading to prevent cascade failures
                agent_instance = self._load_agent_safely(agents_module, agent_name)

                if agent_instance is not None:
                    successful_agents[agent_name] = agent_instance
                    logger.info(
                        "✅ Agent loaded successfully",
                        agent=agent_name,
                        agent_type=type(agent_instance).__name__,
                    )
                else:
                    failed_agents.append(agent_name)
                    logger.warning(
                        "⚠️ Agent failed to load but system continues", agent=agent_name
                    )

            except Exception as e:
                failed_agents.append(agent_name)
                logger.error(
                    "❌ Agent loading failed with exception",
                    agent=agent_name,
                    error=str(e),
                    error_type=type(e).__name__,
                )
                # Continue with other agents - don't let one failure break everything
                continue

        # Set successful agents
        self.agent_instances = successful_agents

        # Log summary
        logger.info(
            "🔄 Agent initialization complete",
            successful_count=len(successful_agents),
            failed_count=len(failed_agents),
            successful_agents=list(successful_agents.keys()),
            failed_agents=failed_agents,
        )

        # Warn if critical agents failed to load
        if failed_agents:
            logger.warning(
                "⚠️ Some agents failed to initialize - system will continue with reduced capabilities",
                failed_agents=failed_agents,
                available_capabilities=len(successful_agents),
            )

    def _load_agent_safely(
        self, agents_module, agent_name: str, timeout_seconds: int = 10
    ):
        """Safely load a single agent with timeout and error handling"""

        def load_agent():
            try:
                # Try to get the agent class from the agents module
                agent_class_or_instance = getattr(agents_module, agent_name)

                # Instantiate the agent, passing base_url when supported
                import inspect

                try:
                    sig = inspect.signature(agent_class_or_instance.__init__)
                    if "base_url" in sig.parameters:
                        mock_url = config.mock_service_url
                        logger.info(
                            f"Instantiating {agent_name} with mock URL: {mock_url}"
                        )
                        return agent_class_or_instance(base_url=mock_url)
                    return agent_class_or_instance()
                except Exception:
                    # Fallback to default instantiation
                    return agent_class_or_instance()

            except AttributeError:
                logger.warning("Agent class not found in module", agent=agent_name)
                return None
            except Exception as e:
                logger.error(
                    "Agent instantiation failed", agent=agent_name, error=str(e)
                )
                return None

        # Use thread pool to enforce timeout
        with ThreadPoolExecutor(
            max_workers=1, thread_name_prefix=f"load-{agent_name}"
        ) as executor:
            try:
                future = executor.submit(load_agent)
                return future.result(timeout=timeout_seconds)
            except Exception as e:
                logger.error(
                    "Agent loading executor error", agent=agent_name, error=str(e)
                )
                return None

    def get_agent_health_status(self) -> Dict[str, Any]:
        """Get health status of all agents for monitoring"""
        health_status = {
            "total_agents_configured": len(self.registry),
            "agents_loaded": len(self.agent_instances),
            "agents_healthy": 0,
            "agents": {},
        }

        for agent_name, agent_instance in self.agent_instances.items():
            try:
                # Try to call a simple method to verify agent is responsive
                agent_status = {
                    "loaded": True,
                    "responsive": False,
                    "error": None,
                    "last_checked": datetime.now(timezone.utc).isoformat(),
                }

                # Simple health check - just verify the agent has expected attributes
                if hasattr(agent_instance, "name") and hasattr(
                    agent_instance, "description"
                ):
                    agent_status["responsive"] = True
                    health_status["agents_healthy"] += 1

                health_status["agents"][agent_name] = agent_status

            except Exception as e:
                health_status["agents"][agent_name] = {
                    "loaded": True,
                    "responsive": False,
                    "error": str(e),
                    "last_checked": datetime.now(timezone.utc).isoformat(),
                }

        # Add information about agents that failed to load
        for agent_def in self.registry:
            agent_name = agent_def["name"]
            if agent_name not in self.agent_instances:
                health_status["agents"][agent_name] = {
                    "loaded": False,
                    "responsive": False,
                    "error": "Failed to load during initialization",
                    "last_checked": datetime.now(timezone.utc).isoformat(),
                }

        return health_status

    def reload_failed_agents(self) -> Dict[str, bool]:
        """Attempt to reload agents that failed during initialization"""
        agents_module = importlib.import_module("agents")
        reload_results = {}

        # Find agents that should be loaded but aren't
        expected_agents = {agent_def["name"] for agent_def in self.registry}
        loaded_agents = set(self.agent_instances.keys())
        failed_agents = expected_agents - loaded_agents

        logger.info(
            "🔄 Attempting to reload failed agents", failed_agents=list(failed_agents)
        )

        for agent_name in failed_agents:
            try:
                agent_instance = self._load_agent_safely(agents_module, agent_name)
                if agent_instance is not None:
                    self.agent_instances[agent_name] = agent_instance
                    reload_results[agent_name] = True
                    logger.info("✅ Agent reloaded successfully", agent=agent_name)

                    # Recreate tools with the new agent
                    self._update_tools_for_agent(agent_name, agent_instance)
                else:
                    reload_results[agent_name] = False
                    logger.warning("⚠️ Agent reload failed", agent=agent_name)

            except Exception as e:
                reload_results[agent_name] = False
                logger.error("❌ Agent reload error", agent=agent_name, error=str(e))

        return reload_results

    def _update_tools_for_agent(self, agent_name: str, agent_instance):
        """Update tools list when an agent is reloaded"""
        # Remove old tools for this agent
        self.tools = [
            tool for tool in self.tools if not tool.name.startswith(f"{agent_name}_")
        ]

        # Add new tools for the reloaded agent
        agent_def = next((a for a in self.registry if a["name"] == agent_name), None)
        if agent_def:
            for method_name in dir(agent_instance):
                if (
                    not method_name.startswith("_")
                    and method_name != "name"
                    and method_name != "description"
                ):
                    method = getattr(agent_instance, method_name)
                    if callable(method):
                        tool_info = next(
                            (
                                t
                                for t in agent_def.get("tools", [])
                                if t["name"] == method_name
                            ),
                            None,
                        )

                        description = (
                            tool_info["description"]
                            if tool_info
                            else method.__doc__
                            or f"Execute {method_name} on {agent_name}"
                        )

                        input_schema = (
                            tool_info.get("input_schema") if tool_info else None
                        )

                        # Don't force any tools to be final answers - let orchestrator decide
                        force_result = False  # Removed early termination to allow proper orchestration

                        tool = create_tool_from_method(
                            agent_instance,
                            method_name,
                            description,
                            input_schema,
                            result_as_answer=force_result,
                        )
                        self.tools.append(tool)

        logger.info(
            "🔧 Tools updated for reloaded agent",
            agent=agent_name,
            new_tool_count=len(
                [t for t in self.tools if t.name.startswith(f"{agent_name}_")]
            ),
        )

    def _create_tools(self) -> List[BaseTool]:
        """Dynamically create tools from all agent methods."""
        tools = []

        # Create a mapping of agent names to their tool descriptions
        agent_tool_info = {}
        for agent_def in self.registry:
            agent_name = agent_def["name"]
            agent_tool_info[agent_name] = {}
            for tool_def in agent_def.get("tools", []):
                agent_tool_info[agent_name][tool_def["name"]] = tool_def["description"]

        # Dynamically create tools from all agent instances
        for agent_name, agent_instance in self.agent_instances.items():
            # Find the agent definition in registry
            agent_def = next(
                (a for a in self.registry if a["name"] == agent_name), None
            )

            # Get all public methods from the agent
            for method_name in dir(agent_instance):
                if (
                    not method_name.startswith("_")
                    and method_name != "name"
                    and method_name != "description"
                ):
                    method = getattr(agent_instance, method_name)
                    if callable(method):
                        # Get description and schema from registry
                        tool_info = None
                        if agent_def:
                            tool_info = next(
                                (
                                    t
                                    for t in agent_def.get("tools", [])
                                    if t["name"] == method_name
                                ),
                                None,
                            )

                        description = (
                            tool_info["description"]
                            if tool_info
                            else method.__doc__
                            or f"Execute {method_name} on {agent_name}"
                        )

                        input_schema = (
                            tool_info.get("input_schema") if tool_info else None
                        )

                        # Don't force any tools to be final answers - let orchestrator decide
                        force_result = False  # Removed early termination to allow proper orchestration

                        tool = create_tool_from_method(
                            agent_instance,
                            method_name,
                            description,
                            input_schema,
                            result_as_answer=force_result,
                        )
                        tools.append(tool)

        return tools

    def _create_orchestrator_tools(self) -> List[BaseTool]:
        """Create built-in orchestrator tools for intelligent coordination"""
        return [DiscoveryTool(self), EvaluationTool(self)]

    def _create_dynamic_backstory(self) -> str:
        """Create a dynamic system prompt based on available agents and tools"""
        # The system prompt is now built intelligently by the prompt builder
        # This method adds session-specific dynamic information

        # Add dynamic agent information
        agent_descriptions = []
        for agent_name, instance in self.agent_instances.items():
            agent_descriptions.append(f"- {agent_name}: {instance.description}")

        # Add dynamic tool information
        tool_summaries = {}
        for tool in self.tools:
            agent_name = tool.name.split("_")[0]
            if agent_name not in tool_summaries:
                tool_summaries[agent_name] = []
            tool_summaries[agent_name].append(f"  * {tool.name}: {tool.description}")

        dynamic_section = f"""

RUNTIME SESSION INFORMATION:

🤖 Currently Loaded Agents ({len(self.agent_instances)}):
{chr(10).join(agent_descriptions)}

🔧 Available Tools by Agent ({len(self.tools)} total):
"""

        for agent_name, tools in tool_summaries.items():
            dynamic_section += f"\n{agent_name}:\n" + "\n".join(tools) + "\n"

        dynamic_section += """
🧠 INTELLIGENT ADAPTATION:
- My prompt was built dynamically based on the agents actually available
- I adapt my behavior to match the specific capabilities of this session
- I use real-time agent discovery to make informed decisions
- When tools fail, I analyze errors and try alternative approaches
"""

        return dynamic_section

    def _create_registry_agents(self) -> List[Agent]:
        """Create agents dynamically from registry manifest - no hardcoding!"""
        agents = []

        # Create agents directly from the registry manifest
        for agent_def in self.registry:
            agent_name = agent_def["name"]

            # Skip if we don't have the instance loaded
            if agent_name not in self.agent_instances:
                continue

            # Get tools for this specific agent
            agent_tools = [t for t in self.tools if t.name.startswith(f"{agent_name}_")]

            # Create CrewAI Agent using manifest definition
            # Use lowercase role for CrewAI delegation compatibility
            description = agent_def["description"]
            crew_agent = Agent(
                role=description,
                goal=f"Handle {description.lower()} operations efficiently",
                backstory=f"I am {agent_name}. {description}. I use my specialized tools to help with specific tasks in my domain.",
                memory=True,
                verbose=True,
                tools=agent_tools,
                llm=self.agent_llm,  # Use agent-specific LLM (gpt-5-nano)
                allow_delegation=True,
            )

            agents.append(crew_agent)
            logger.info(
                "Created specialized agent from manifest",
                agent=agent_name,
                tools=len(agent_tools),
            )

        return agents

    def discover_agents_enhanced(self) -> Dict[str, Any]:
        """Enhanced agent discovery with registry metadata"""
        discovery_info = {
            "total_agents": len(self.agent_instances),
            "total_tools": len(self.tools),
            "registry_agents": len(self.registry_agents),
            "agents": [],
            "system_info": {
                "crewai_version": "0.134.0",
                "enhanced_orchestration": True,
                "dynamic_registry": True,
                "memory_enabled": True,
            },
        }

        for name, instance in self.agent_instances.items():
            tools = []
            for method_name in dir(instance):
                method = getattr(instance, method_name)
                if callable(method) and not method_name.startswith("_"):
                    tools.append(
                        {
                            "name": method_name,
                            "description": method.__doc__ or "No description available",
                        }
                    )

            agent_info = {
                "name": name,
                "description": instance.description,
                "tools": tools,
                "tool_count": len(tools),
            }
            discovery_info["agents"].append(agent_info)

        return discovery_info

    async def _execute_deterministic_flow(
        self,
        intent: OrchestrationIntent,
        context: PlannerContext,
    ) -> Dict[str, Any]:
        """Execute the legacy deterministic orchestration flow."""
        user_prompt = intent.prompt
        trace_id = context.trace_id or ""
        scenario = intent.scenario
        step_callback = context.step_callback
        discovery_info = context.discovery or self.discover_agents_enhanced()
        start_time = (
            datetime.fromtimestamp(context.start_time_ms / 1000.0)
            if context.start_time_ms
            else datetime.now()
        )

        session = get_trace_session()
        session.discovery_called = True

        # Build concise agent summary for prompt injection
        agents_summary = []
        for agent in discovery_info.get("agents", []):
            agent_name = agent.get("name", "Unknown")
            tool_count = agent.get("tool_count", 0)
            agents_summary.append(f"  • {agent_name} ({tool_count} tools)")

        discovery_context = (
            "\n\n### AVAILABLE AGENTS\n" + "\n".join(agents_summary)
            if agents_summary
            else ""
        )

        emit_trace_event(
            "deterministic_flow_start",
            {
                "scenario": scenario,
                "prompt": user_prompt,
                "agents": [
                    {
                        "name": agent.get("name"),
                        "tool_count": agent.get("tool_count", 0),
                    }
                    for agent in discovery_info.get("agents", [])
                ],
            },
        )

        with ThreadPoolExecutor(max_workers=2) as executor:
            execution_task_description = f"""
                USER REQUEST: {user_prompt}

                Your job is to fulfill this request by ACTUALLY EXECUTING the appropriate tools.

                CRITICAL EXECUTION RULES:
                1. You MUST call the actual tools - never just describe what you would do
                2. Use the tools that match the requirements dynamically
                3. Return REAL DATA from tool execution, not hypothetical responses
                4. If a tool fails, try alternatives or ask for clarification
                {discovery_context}

                REMEMBER: Execute tools, don't describe them. The user expects actual results, not plans.
                """
            execution_task = Task(
                description=execution_task_description,
                agent=self.orchestrator,
                expected_output=f"""Based on ACTUAL tool execution results for: {user_prompt}

                Provide a clear response that includes:
                - The real data retrieved from tool executions
                - Confirmation of actions taken
                - Any relevant details from the tool outputs

                Be specific and factual based on what the tools returned.""",
            )

            all_agents = [self.orchestrator] + self.registry_agents
            agents_used = [agent.role for agent in all_agents]

            def combined_callback(step):
                logger.info(f"Tool execution step: {step}")
                if step_callback:
                    try:
                        step_callback(step)
                    except Exception as exc:
                        logger.warning(f"Step callback error: {exc}")

            execution_crew = Crew(
                name="multi-agent-disu",
                agents=all_agents,
                tasks=[execution_task],
                process=Process.sequential,
                verbose=True,
                memory=True,
                full_output=True,
                step_callback=combined_callback,
                planning=False,
                max_iter=25,
            )

            try:
                result = await asyncio.get_event_loop().run_in_executor(
                    executor, execution_crew.kickoff
                )
            except Exception as openai_error:
                error_msg = str(openai_error)
                logger.error(
                    "OpenAI execution failed",
                    error=error_msg,
                    trace_id=trace_id,
                    openai_key_configured=bool(config.openai_api_key),
                    model=config.openai_model,
                )
                emit_trace_event(
                    "deterministic_flow_error",
                    {
                        "scenario": scenario,
                        "trace_id": trace_id,
                        "error": error_msg,
                    },
                )

                return {
                    "answer": f"OpenAI API Error: {error_msg}\n\nDetails:\n- Model: {config.openai_model}\n- Error Type: {type(openai_error).__name__}\n- Please check your API key and rate limits.",
                    "trace_id": trace_id,
                    "agents_used": agents_used,
                    "execution_time_ms": (datetime.now() - start_time).total_seconds()
                    * 1000,
                    "plan": "Error during AI execution",
                    "system_status": {
                        "agents_loaded": len(self.agent_instances),
                        "tools_available": len(self.tools),
                        "orchestrator_ready": True,
                        "ai_processing": False,
                        "error_details": error_msg,
                    },
                    "errors": [error_msg],
                }

        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        execution_trace = {
            "scenario": scenario,
            "tools_executed": session.executed_tools,
            "tool_count": len(session.executed_tools),
            "discovery_called": session.discovery_called,
        }
        answer = str(result)

        emit_trace_event(
            "deterministic_flow_complete",
            {
                "scenario": scenario,
                "trace_id": trace_id,
                "execution_time_ms": execution_time,
                "tools_executed": session.executed_tools,
                "answer": answer,
            },
        )

        logger.info(
            "Deterministic orchestrator request completed",
            trace_id=trace_id,
            execution_time_ms=execution_time,
            agents_used=len(agents_used),
            scenario=scenario,
            tools_executed=session.executed_tools,
            tool_count=len(session.executed_tools),
        )

        return {
            "answer": answer,
            "trace_id": trace_id,
            "agents_used": agents_used,
            "execution_time_ms": execution_time,
            "plan": "Intelligent orchestration using dynamic prompt system",
            "execution_trace": execution_trace,
        }

    async def handle_request_async(
        self,
        user_prompt: str,
        trace_id: str = "",
        memory_context: Dict = None,
        step_callback=None,
    ) -> Dict[str, Any]:
        """Enhanced async request handling with planner abstraction."""
        start_time = datetime.now()

        if not trace_id:
            trace_id = str(uuid.uuid4())

        token = set_trace_id(trace_id)
        try:
            with trace_operation(
                "orchestrator.handle_request",
                attributes={"prompt": user_prompt[:100], "trace_id": trace_id},
            ):
                logger.info(
                    "Processing orchestrator request",
                    prompt=user_prompt[:100],
                    trace_id=trace_id,
                    memory_context=bool(memory_context),
                )

                if memory_context:
                    try:
                        for key, value in memory_context.items():
                            self.conversation_memory[f"{trace_id}_{key}"] = value
                    except Exception as exc:
                        logger.warning("Failed to store memory context", error=str(exc))

                scenario, policy = self._resolve_scenario(user_prompt)
                discovery_info = self.discover_agents_enhanced()
                emit_trace_event(
                    "agents_discovered",
                    {
                        "trace_id": trace_id,
                        "scenario": scenario,
                        "total_agents": len(discovery_info.get("agents", [])),
                        "agents": [
                            {
                                "name": agent.get("name"),
                                "tool_count": agent.get("tool_count", 0),
                            }
                            for agent in discovery_info.get("agents", [])
                        ],
                    },
                )

                metadata = {
                    "trace_id": trace_id,
                    "planner_preference": getattr(
                        config, "planner_default", "deterministic"
                    ),
                }
                if policy:
                    metadata["policy_version"] = policy.version
                    metadata["policy_domain"] = policy.domain
                    metadata["policy"] = policy.raw

                intent = OrchestrationIntent(
                    prompt=user_prompt,
                    scenario=scenario,
                    metadata=metadata,
                )

                context = PlannerContext(
                    orchestrator=self,
                    discovery=discovery_info,
                    memory_context=memory_context,
                    step_callback=step_callback,
                    start_time_ms=start_time.timestamp() * 1000,
                    trace_id=trace_id,
                )

                preferred_planner = getattr(config, "planner_default", None)
                try:
                    planner = self._planner_registry.select(preferred_planner)
                except PlanningError as exc:
                    logger.warning(
                        "Planner selection failed; using fallback",
                        error=str(exc),
                        preferred_planner=preferred_planner,
                    )
                    planner = self._planner_registry.select("deterministic")

                emit_trace_event(
                    "planning_start",
                    {
                        "trace_id": trace_id,
                        "scenario": scenario,
                        "planner": planner.name,
                    },
                )
                plan_graph = await planner.plan(intent, context)
                emit_trace_event(
                    "planning_complete",
                    {
                        "trace_id": trace_id,
                        "scenario": scenario,
                        "planner": planner.name,
                        "plan_steps": (
                            plan_graph.steps if hasattr(plan_graph, "steps") else None
                        ),
                    },
                )
                report = await planner.execute(plan_graph, intent, context)
                emit_trace_event(
                    "execution_complete",
                    {
                        "trace_id": trace_id,
                        "scenario": scenario,
                        "planner": planner.name,
                        "errors": report.errors,
                    },
                )

                result = dict(report.metadata or {})
                result.setdefault("answer", report.answer)
                result.setdefault("plan", plan_graph.description)
                result["planner_used"] = planner.name
                result.setdefault("trace_id", trace_id)
                if policy:
                    result.setdefault("policy", metadata.get("policy"))
                    result.setdefault("policy_version", policy.version)
                    result.setdefault("policy_domain", policy.domain)
                result.setdefault(
                    "execution_time_ms",
                    (datetime.now() - start_time).total_seconds() * 1000,
                )

                if report.errors:
                    emit_trace_event(
                        "final_result",
                        {
                            "trace_id": trace_id,
                            "status": "error",
                            "errors": report.errors,
                            "answer": result.get("answer"),
                        },
                    )
                else:
                    emit_trace_event(
                        "final_result",
                        {
                            "trace_id": trace_id,
                            "status": "success",
                            "answer": result.get("answer"),
                        },
                    )

                return result
        except Exception as exc:
            logger.error("Request processing failed", error=str(exc), trace_id=trace_id)
            emit_trace_event(
                "final_result",
                {
                    "trace_id": trace_id,
                    "status": "exception",
                    "error": str(exc),
                },
            )
            return {
                "answer": f"Error processing request: {str(exc)}",
                "trace_id": trace_id,
                "agents_used": [],
                "execution_time_ms": (datetime.now() - start_time).total_seconds()
                * 1000,
                "plan": "Error during execution",
                "errors": [str(exc)],
            }
        finally:
            reset_trace_session(trace_id)
            reset_trace_id(token)

    def handle_request_sync(
        self, user_prompt: str, trace_id: str = "", memory_context: Dict = None
    ) -> Dict[str, Any]:
        """Synchronous wrapper for async request handling"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(
                self.handle_request_async(user_prompt, trace_id, memory_context)
            )
            loop.close()
            return result
        except Exception as e:
            logger.error(
                "Sync request handling failed", error=str(e), trace_id=trace_id
            )
            return {
                "answer": f"Error processing request: {str(e)}",
                "trace_id": trace_id,
                "agents_used": [],
                "execution_time_ms": 0,
                "plan": "Error during execution",
            }
