/**
 * JAF CEO Demo — Single Page Application
 *
 * Hash-based routing with 4 pages:
 *  #overview     — What JAF is, value proposition
 *  #architecture — Three-layer diagram, actor anatomy
 *  #build        — Step-by-step code examples
 *  #demos        — Live demo runner (handled by demos.js)
 */

// ── Router ──────────────────────────────────────────

function navigate() {
    const hash = location.hash.replace('#', '') || 'overview';
    const app = document.getElementById('app');

    // Update nav active state
    document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.toggle('active', link.dataset.page === hash);
    });

    // Render page
    const pages = { overview: renderOverview, architecture: renderArchitecture, build: renderBuild, demos: renderDemos, processes: renderProcesses };
    const renderFn = pages[hash] || renderOverview;
    app.innerHTML = renderFn();

    // Initialize processes page if needed
    if (hash === 'processes') {
        initProcessesPage();
    }

    // Initialize demos page if needed
    if (hash === 'demos' && typeof initDemos === 'function') {
        initDemos();
    }

    window.scrollTo(0, 0);
}

window.addEventListener('hashchange', navigate);
window.addEventListener('load', navigate);


// ── Syntax Highlighting (simple) ────────────────────

function hl(code) {
    return code
        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        .replace(/(#.*$)/gm, '<span class="comment">$1</span>')
        .replace(/("""[\s\S]*?"""|"[^"]*"|'[^']*')/g, '<span class="string">$1</span>')
        .replace(/\b(from|import|class|def|async|await|return|if|else|for|in|with|as|try|except|raise|None|True|False)\b/g, '<span class="keyword">$1</span>')
        .replace(/(@\w+)/g, '<span class="decorator">$1</span>')
        .replace(/\b(Actor|Tool|LLMConfig|NativeAdapter|ActorRegistry|Plan|PlanStep|StepResult)\b/g, '<span class="class-name">$1</span>');
}


// ── Page: Overview ──────────────────────────────────

function renderOverview() {
    return `
    <div class="page-header">
        <h1>Jems AI Framework</h1>
        <p class="subtitle">
            Enterprise-grade Actor-based orchestration framework.
            Build agentic, multi-agent, and traditional automation workflows
            from a single runtime.
        </p>
    </div>

    <div class="metrics">
        <div class="metric">
            <div class="metric-value">3</div>
            <div class="metric-label">Execution Modes</div>
        </div>
        <div class="metric">
            <div class="metric-value">50%</div>
            <div class="metric-label">Cost Reduction</div>
        </div>
        <div class="metric">
            <div class="metric-value">0</div>
            <div class="metric-label">Vendor Lock-in</div>
        </div>
        <div class="metric">
            <div class="metric-value">99.9%</div>
            <div class="metric-label">Reliability Target</div>
        </div>
    </div>

    <div class="section">
        <h2 class="section-title">Three Execution Modes</h2>
        <div class="card-grid">
            <div class="card">
                <div class="card-header">
                    <div class="card-icon accent">&#9672;</div>
                    <span class="card-title">Agentic Flow</span>
                    <span class="badge agentic">AI</span>
                </div>
                <p class="card-desc">
                    Single orchestrator with multiple deterministic tools.
                    The LLM decides which tools to call based on data context.
                    Cost-effective for routine tasks.
                </p>
            </div>
            <div class="card">
                <div class="card-header">
                    <div class="card-icon orange">&#9670;</div>
                    <span class="card-title">Multi-Agent Flow</span>
                    <span class="badge multi-agent">AI</span>
                </div>
                <p class="card-desc">
                    Orchestrator delegates to specialized agent actors.
                    Each agent has its own LLM and tools. Ideal for complex
                    multi-domain tasks.
                </p>
            </div>
            <div class="card">
                <div class="card-header">
                    <div class="card-icon green">&#9654;</div>
                    <span class="card-title">Traditional Automation</span>
                    <span class="badge traditional">NO LLM</span>
                </div>
                <p class="card-desc">
                    Deterministic workflows without LLM. BPMN-like execution
                    for compliance-critical tasks. Same framework, same API,
                    zero AI cost.
                </p>
            </div>
        </div>
    </div>

    <div class="section">
        <h2 class="section-title">Core Design Principles</h2>
        <div class="card-grid">
            <div class="card">
                <div class="card-header">
                    <div class="card-icon blue">&#8644;</div>
                    <span class="card-title">Actor Model</span>
                </div>
                <p class="card-desc">
                    Share-nothing architecture. Communication via async messages.
                    Enables fault tolerance, scalability, and location transparency.
                    Proven by Erlang/Akka systems.
                </p>
            </div>
            <div class="card">
                <div class="card-header">
                    <div class="card-icon cyan">&#9881;</div>
                    <span class="card-title">Engine Abstraction</span>
                </div>
                <p class="card-desc">
                    Actors never import execution frameworks directly.
                    Swap backends: CrewAI &rarr; Native &rarr; LangGraph &rarr; Vertex AI.
                    Zero vendor lock-in.
                </p>
            </div>
            <div class="card">
                <div class="card-header">
                    <div class="card-icon pink">&#9733;</div>
                    <span class="card-title">Hybrid Intelligence</span>
                </div>
                <p class="card-desc">
                    gpt-5-nano for tool routing (fastest, cheapest).
                    gpt-5-mini for planning &amp; reasoning.
                    No LLM for deterministic tasks. Optimal cost/intelligence ratio.
                </p>
            </div>
            <div class="card">
                <div class="card-header">
                    <div class="card-icon green">&#9745;</div>
                    <span class="card-title">Persistence-First</span>
                </div>
                <p class="card-desc">
                    Every state transition saved to Postgres. Resume after crash.
                    Human-in-the-loop. Long-running workflows (days/weeks).
                    Full audit trails.
                </p>
            </div>
            <div class="card">
                <div class="card-header">
                    <div class="card-icon orange">&#9736;</div>
                    <span class="card-title">Event-Driven Observability</span>
                </div>
                <p class="card-desc">
                    Engine emits events on every step. Frontend receives via SSE.
                    Real-time visibility into agent reasoning, tool calls,
                    and decision-making.
                </p>
            </div>
            <div class="card">
                <div class="card-header">
                    <div class="card-icon accent">&#9998;</div>
                    <span class="card-title">Data as First-Class Citizen</span>
                </div>
                <p class="card-desc">
                    Agents use business data to make specific, actionable decisions.
                    Not generic AI — intelligence grounded in your company's
                    actual data context.
                </p>
            </div>
        </div>
    </div>

    <div class="section">
        <h2 class="section-title">Who Is This For?</h2>
        <div class="card" style="max-width:700px">
            <p class="card-desc" style="font-size:0.92rem;line-height:1.8">
                JAF is a <strong style="color:var(--text)">reusable SDK</strong> for
                <strong style="color:var(--accent)">developers and tech leads</strong>
                who need to build agentic workflows for new projects.
                <br><br>
                Instead of building AI orchestration from scratch every time, teams get
                a proven foundation with actor isolation, engine abstraction, persistence,
                observability, and cost optimization built in.
                <br><br>
                <span class="mono text-sm" style="color:var(--green)">pip install jaf-framework</span>
                &rarr; Define actors &rarr; Add tools &rarr; Choose mode &rarr; Run.
            </p>
        </div>
    </div>
    `;
}


// ── Page: Architecture ──────────────────────────────

function renderArchitecture() {
    return `
    <div class="page-header">
        <h1>Architecture</h1>
        <p class="subtitle">
            Three-layer design separating interface, orchestration, and execution.
            Each layer is independently scalable and replaceable.
        </p>
    </div>

    <div class="section">
        <h2 class="section-title">Three-Layer Architecture</h2>
        <div class="diagram"><span class="layer-label">LAYER 1: THE FACE</span> <span class="dim">(API Gateway / UI Interface)</span>
<span class="dim">┌─────────────────────────────────────────────────────────────┐</span>
<span class="dim">│</span>  REST API          WebSocket/SSE        Webhooks            <span class="dim">│</span>
<span class="dim">│</span>  <span class="highlight">POST /process</span>     <span class="highlight">GET /stream/:id</span>     POST /webhook       <span class="dim">│</span>
<span class="dim">└─────────────────────────────────────────────────────────────┘</span>
                              <span class="dim">↓</span>
<span class="layer-label">LAYER 2: THE BRAIN</span> <span class="dim">(Engine / Orchestrator)</span>
<span class="dim">┌─────────────────────────────────────────────────────────────┐</span>
<span class="dim">│</span>  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      <span class="dim">│</span>
<span class="dim">│</span>  │   <span class="highlight">PLANNING</span>    │→ │  <span class="highlight">EXECUTION</span>   │→ │  <span class="highlight">EVENT BUS</span>   │      <span class="dim">│</span>
<span class="dim">│</span>  └──────────────┘  └──────────────┘  └──────────────┘      <span class="dim">│</span>
<span class="dim">│</span>  State: PLANNING → EXECUTING → EVALUATING                   <span class="dim">│</span>
<span class="dim">│</span>  Persistence: Save after every step (Postgres)              <span class="dim">│</span>
<span class="dim">└─────────────────────────────────────────────────────────────┘</span>
                              <span class="dim">↓</span>
<span class="layer-label">LAYER 3: THE MUSCLE</span> <span class="dim">(Execution Adapters)</span>
<span class="dim">┌─────────────────────────────────────────────────────────────────────────┐</span>
<span class="dim">│</span>  ┌────────────────┐  ┌────────────────┐  ┌──────────────┐  ┌──────────┐<span class="dim">│</span>
<span class="dim">│</span>  │ <span class="highlight">NativeAdapter</span>  │  │ <span class="highlight">NativeEngine</span>   │  │  <span class="highlight">CrewAI</span>      │  │<span class="highlight">VertexAI</span>  │<span class="dim">│</span>
<span class="dim">│</span>  │ Responses API  │  │ Deterministic  │  │  Adapter     │  │(Future)  │<span class="dim">│</span>
<span class="dim">│</span>  │ GPT-5 (AI)     │  │ (No LLM)       │  │              │  │          │<span class="dim">│</span>
<span class="dim">│</span>  └────────────────┘  └────────────────┘  └──────────────┘  └──────────┘<span class="dim">│</span>
<span class="dim">│</span>                                                                       <span class="dim">│</span>
<span class="dim">│</span>  <span class="dim">Auto-select: actors with LLM → NativeAdapter, without → NativeEngine</span> <span class="dim">│</span>
<span class="dim">└─────────────────────────────────────────────────────────────────────────┘</span></div>
    </div>

    <div class="section">
        <h2 class="section-title">Execution Adapters in Detail</h2>
        <p class="text-muted mb-lg text-sm" style="max-width:700px;line-height:1.7">
            The <strong style="color:var(--text)">EngineFactory</strong> auto-selects the right adapter based on actor configuration.
            Override with <code>engine_type="crewai"</code> to force a specific backend.
        </p>
        <div class="card-grid">
            <div class="card">
                <div class="card-header">
                    <div class="card-icon accent">&#9672;</div>
                    <span class="card-title">NativeAdapter</span>
                </div>
                <p class="card-desc">
                    Uses OpenAI <strong>Responses API</strong> (<code>client.responses.create</code>)
                    with function calling. The LLM decides which tools to call based on goal and context.
                    Supports GPT-5 family: gpt-5-nano, gpt-5-mini, gpt-5.2.
                </p>
                <p class="text-xs text-dim" style="margin-top:var(--space-sm)">
                    Auto-selected when: actors have <code>llm_config</code> set<br>
                    Dependency: <code>openai &ge; 1.66</code>
                </p>
            </div>
            <div class="card">
                <div class="card-header">
                    <div class="card-icon green">&#9654;</div>
                    <span class="card-title">NativeEngine</span>
                </div>
                <p class="card-desc">
                    Deterministic execution without LLM. Generates sequential plans
                    from actor tools and executes them directly. Supports parallel
                    step groups.
                </p>
                <p class="text-xs text-dim" style="margin-top:var(--space-sm)">
                    Auto-selected when: all actors have <code>llm_config=None</code><br>
                    Dependency: none (built-in)
                </p>
            </div>
            <div class="card">
                <div class="card-header">
                    <div class="card-icon blue">&#9881;</div>
                    <span class="card-title">CrewAI Adapter</span>
                </div>
                <p class="card-desc">
                    Wraps CrewAI for LLM-based planning and agent execution.
                    Supports hierarchical delegation and multi-agent orchestration
                    via CrewAI Process.
                </p>
                <p class="text-xs text-dim" style="margin-top:var(--space-sm)">
                    Force with: <code>engine_type="crewai"</code><br>
                    Dependency: <code>crewai</code>, <code>langchain-openai</code>
                </p>
            </div>
            <div class="card">
                <div class="card-header">
                    <div class="card-icon cyan">&#9733;</div>
                    <span class="card-title">VertexAI Adapter</span>
                </div>
                <p class="card-desc">
                    Google Cloud VertexAI integration for plan generation
                    and step execution. Enables GCP-native deployment without
                    OpenAI dependency.
                </p>
                <p class="text-xs text-dim" style="margin-top:var(--space-sm)">
                    Force with: <code>engine_type="vertexai"</code><br>
                    Dependency: <code>google-cloud-aiplatform</code>
                </p>
            </div>
        </div>
    </div>

    <div class="section">
        <h2 class="section-title">Actor Anatomy</h2>
        <div class="card" style="max-width:700px">
            <p class="card-desc mb-lg">
                Every actor in JAF is a self-contained business logic unit with four components:
            </p>
            <table class="info-table">
                <tr><th>Component</th><th>Purpose</th><th>Example</th></tr>
                <tr>
                    <td><strong style="color:var(--accent)">Goal</strong></td>
                    <td>What the actor does</td>
                    <td>"Detect churn risk in customer data"</td>
                </tr>
                <tr>
                    <td><strong style="color:var(--blue)">LLM</strong></td>
                    <td>Optional brain for reasoning</td>
                    <td>gpt-5-nano / gpt-5-mini (or None for deterministic)</td>
                </tr>
                <tr>
                    <td><strong style="color:var(--green)">Tools</strong></td>
                    <td>Deterministic functions</td>
                    <td>lookup_customer(), analyze_health()</td>
                </tr>
                <tr>
                    <td><strong style="color:var(--orange)">Utilities</strong></td>
                    <td>Framework-provided</td>
                    <td>Logger, DB, EventBus</td>
                </tr>
            </table>
        </div>
    </div>

    <div class="section">
        <h2 class="section-title">Data as First-Class Citizen</h2>
        <div class="card" style="max-width:700px">
            <p class="card-desc mb-lg" style="line-height:1.8">
                Agents don't generate generic text — they make decisions <strong style="color:var(--text)">grounded in real business data</strong>.
                The goal, context, and tool results all carry concrete data that the LLM uses to reason and act.
            </p>
            <div class="diagram"><span class="highlight">Goal</span> + <span class="highlight">Data Context</span>
    <span class="dim">↓</span>
<span class="layer-label">LLM</span> <span class="dim">(analyzes context, picks a tool)</span>
    <span class="dim">↓</span>
<span class="highlight">Tool Call</span> → <span class="highlight">Data Source</span> <span class="dim">(CRM, ERP, DB, API)</span>
    <span class="dim">↓</span>
<span class="highlight">Real Data</span> <span class="dim">(customer records, revenue metrics, etc.)</span>
    <span class="dim">↓</span>
<span class="layer-label">LLM</span> <span class="dim">(reasons over actual data → next tool or decision)</span>
    <span class="dim">↓</span>
<span class="highlight">Actionable Decision</span> <span class="dim">(specific to your business, not generic)</span></div>
            <p class="card-desc" style="line-height:1.8;margin-top:var(--space-md)">
                <strong style="color:var(--accent)">Example:</strong>
                "Customer C-1042 has NPS 32 (dropped from 71), 4 open support tickets, and is in the DACH region
                where revenue declined 22%. Recommend: executive escalation + dedicated CSM + pricing review."
                <br><br>
                Every data point comes from a tool call to a real data source — the LLM orchestrates
                <em>which</em> data to fetch and <em>how</em> to combine it into a decision.
            </p>
        </div>
    </div>

    <div class="section">
        <h2 class="section-title">Process State Machine</h2>
        <div class="diagram"><span class="highlight">CREATED</span> → <span class="highlight">PLANNING</span> → <span class="highlight">EXECUTING</span> → <span class="highlight">EVALUATING</span> → <span class="highlight">COMPLETED</span>
                                 <span class="dim">↑              ↓</span>
                                 <span class="dim">└──── retry ───┘</span>
                                                    <span class="dim">↓</span>
                                               <span style="color:var(--red)">FAILED</span>

<span class="dim">Every transition is persisted to Postgres.</span>
<span class="dim">Process can resume from any state after a crash.</span></div>
    </div>

    <div class="section">
        <h2 class="section-title">Event Flow</h2>
        <div class="card" style="max-width:700px">
            <p class="card-desc" style="line-height:1.8">
                The engine emits <strong style="color:var(--text)">AgentAction</strong> events at every step.
                Subscribers receive events in real-time:
            </p>
            <table class="info-table">
                <tr><th>Event Type</th><th>When</th><th>Data</th></tr>
                <tr><td><span style="color:var(--accent)">thinking</span></td><td>LLM is analyzing</td><td>Iteration count</td></tr>
                <tr><td><span style="color:var(--blue)">tool_called</span></td><td>LLM invokes a tool</td><td>Actor, tool name, arguments</td></tr>
                <tr><td><span style="color:var(--green)">tool_result</span></td><td>Tool returns data</td><td>Result preview, execution time</td></tr>
                <tr><td><span style="color:var(--green)">completed</span></td><td>Agent finished</td><td>Final result, total stats</td></tr>
                <tr><td><span style="color:var(--red)">error</span></td><td>Something failed</td><td>Error message</td></tr>
            </table>
        </div>
    </div>
    `;
}


// ── Page: Build Agents ──────────────────────────────

function renderBuild() {
    return `
    <div class="page-header">
        <h1>Build Agents</h1>
        <p class="subtitle">
            From zero to running agent in under 30 lines of code.
            Define an actor, add tools, choose a mode, and run.
        </p>
    </div>

    <div class="section">
        <h2 class="section-title">Step-by-Step Guide</h2>
        <div class="steps">
            <div class="step">
                <div class="step-number">1</div>
                <div class="step-content" style="flex:1">
                    <h3>Define Your Actor</h3>
                    <p class="text-muted mb-lg">
                        An actor is a class with a name, description, goal, and optional LLM config.
                        Use the <code>@actor</code> decorator for concise syntax.
                    </p>
                    <div class="code-block">
                        <div class="code-label">Python</div>
                        <pre>${hl(`from jaf import Actor, Tool, LLMConfig
from jaf.core.actor import actor

@actor(
    name="CustomerAgent",
    description="Analyzes customer health and churn risk",
    goal="Detect at-risk customers and recommend actions",
    llm_config=LLMConfig(model="gpt-5-nano"),
)
class CustomerAgent(Actor):
    pass  # Tools added below`)}</pre>
                    </div>
                </div>
            </div>

            <div class="step">
                <div class="step-number">2</div>
                <div class="step-content" style="flex:1">
                    <h3>Add Tools</h3>
                    <p class="text-muted mb-lg">
                        Tools are regular methods decorated with <code>@Tool</code>.
                        They receive data and return results. The LLM decides when to call them.
                    </p>
                    <div class="code-block">
                        <div class="code-label">Python</div>
                        <pre>${hl(`class CustomerAgent(Actor):

    @Tool(description="Look up customer by ID")
    def lookup_customer(self, customer_id: str) -> dict:
        # In production: query your database
        return db.get_customer(customer_id)

    @Tool(description="Analyze health score and risk factors")
    def analyze_health(self, customer_id: str) -> dict:
        customer = db.get_customer(customer_id)
        risks = check_nps(customer) + check_tickets(customer)
        return {"risk_level": calc_risk(risks), "factors": risks}

    @Tool(description="Recommend retention actions")
    def recommend_actions(self, customer_id: str, risk_level: str) -> dict:
        return generate_retention_plan(customer_id, risk_level)`)}</pre>
                    </div>
                </div>
            </div>

            <div class="step">
                <div class="step-number">3</div>
                <div class="step-content" style="flex:1">
                    <h3>Run the Agent</h3>
                    <p class="text-muted mb-lg">
                        Create an instance and run it through the NativeAdapter.
                        The LLM will reason about the goal and call your tools automatically.
                    </p>
                    <div class="code-block">
                        <div class="code-label">Python</div>
                        <pre>${hl(`from jaf.adapters.native_adapter import NativeAdapter

# Create actor instance (tools auto-discovered)
agent = CustomerAgent()

# Create the execution engine
adapter = NativeAdapter(model="gpt-5-nano")

# Run! The LLM decides which tools to call
result = await adapter.run(
    goal="Analyze customer C-1042 for churn risk",
    actors=[agent],
    context={"priority": "high"},
)

print(result["result"])  # Agent's final analysis`)}</pre>
                    </div>
                </div>
            </div>

            <div class="step">
                <div class="step-number">4</div>
                <div class="step-content" style="flex:1">
                    <h3>For Deterministic Workflows (No LLM)</h3>
                    <p class="text-muted mb-lg">
                        Set <code>llm_config=None</code> and the tools run in a pre-defined order.
                        Same framework, same API, zero AI cost.
                    </p>
                    <div class="code-block">
                        <div class="code-label">Python</div>
                        <pre>${hl(`@actor(
    name="ETLActor",
    description="Parse XML and generate Parquet files",
    goal="Transform data without LLM",
    llm_config=None,  # No LLM needed!
)
class ETLActor(Actor):

    @Tool(description="Parse XML metadata")
    def parse_xml(self, path: str) -> dict:
        return xml_parser.parse(path)

    @Tool(description="Write Parquet files")
    def write_parquet(self, data: dict) -> str:
        return parquet_writer.write(data)`)}</pre>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <div class="section">
        <h2 class="section-title">CLI: From Zero to Project in 30 Seconds</h2>
        <div class="card" style="max-width:700px">
            <p class="card-desc mb-lg" style="line-height:1.8">
                JAF includes a CLI tool for scaffolding new projects.
                One command creates the full project structure with actors,
                workflows, tests, and dependency management.
            </p>
            <div class="code-block">
                <div class="code-label">Terminal</div>
                <pre>${hl(`# Install the framework
pip install jaf-framework

# Scaffold a new project
jaf new my-crm-agents

# What you get:
# my-crm-agents/
#   my_actors/
#     __init__.py
#     sample_actor.py      # Actor with @ToolContract
#   workflows/
#     __init__.py
#     sample_workflow.py   # Workflow factory
#   tests/
#     __init__.py
#     test_sample_actor.py # Pytest + NativeEngine test
#   requirements.txt       # jaf-framework
#   README.md
#   .gitignore`)}</pre>
            </div>
            <p class="card-desc" style="margin-top:var(--space-md);line-height:1.8">
                The generated sample actor is fully functional — run the test
                immediately with <code>pytest</code>. Then replace
                <code>SampleActor</code> with your own business logic.
            </p>
            <div class="code-block">
                <div class="code-label">Terminal</div>
                <pre>${hl(`# Check framework version
jaf --version

# Run the generated test
cd my-crm-agents
pip install -r requirements.txt
pytest`)}</pre>
            </div>
        </div>
    </div>

    <div class="section">
        <h2 class="section-title">Key Concepts</h2>
        <div class="card-grid">
            <div class="card">
                <div class="card-header">
                    <div class="card-icon accent">&#64;</div>
                    <span class="card-title">@Tool Decorator</span>
                </div>
                <p class="card-desc">
                    Wraps methods as invocable tools. Auto-generates OpenAI function
                    schemas from type annotations. The LLM sees tool names and descriptions
                    to decide what to call.
                </p>
            </div>
            <div class="card">
                <div class="card-header">
                    <div class="card-icon blue">&#9881;</div>
                    <span class="card-title">NativeAdapter</span>
                </div>
                <p class="card-desc">
                    Uses OpenAI function calling in a loop: send goal &rarr; LLM picks tool
                    &rarr; execute tool &rarr; send result back &rarr; LLM picks next tool
                    or finishes. Real reasoning, not scripted.
                </p>
            </div>
            <div class="card">
                <div class="card-header">
                    <div class="card-icon green">&#9745;</div>
                    <span class="card-title">ActorRegistry</span>
                </div>
                <p class="card-desc">
                    Global registry for actor instances. Actors auto-register on
                    instantiation. Engines look up actors by name to dispatch tool calls.
                </p>
            </div>
        </div>
    </div>
    `;
}


// ── Page: Demos (shell only — logic in demos.js) ────

function renderDemos() {
    return `
    <div class="page-header">
        <h1>Live Demos</h1>
        <p class="subtitle">
            Select a scenario and click Run to see real AI agents reasoning in real-time.
            Events stream live via SSE as the agent decides which tools to call.
        </p>
    </div>

    <div class="demo-layout">
        <div class="demo-sidebar" id="demo-sidebar">
            <div class="text-muted text-sm" style="padding:var(--space-md)">Loading demos...</div>
        </div>
        <div class="demo-output" id="demo-output">
            <div class="demo-output-header">
                <span class="demo-output-title" id="demo-output-title">Select a demo to begin</span>
                <button class="demo-run-btn" id="demo-run-btn" disabled>Run Demo</button>
            </div>
            <div class="demo-events" id="demo-events">
                <div class="demo-placeholder">
                    Select a demo from the left panel, then click Run to see real-time agent events.
                </div>
            </div>
        </div>
    </div>
    `;
}


// ── Processes Page ──────────────────────────────────────

function renderProcesses() {
    return `
    <div class="section">
        <h1 class="section-title">Process Audit Trail</h1>
        <p class="text-muted mb-lg">
            Every process execution is persisted to PostgreSQL. View processes, their plans, and full event timelines below.
            This demonstrates the framework's persistence-first architecture — zero data loss, full traceability.
        </p>

        <div style="display:flex;gap:12px;align-items:center;margin-bottom:20px;flex-wrap:wrap">
            <div style="display:flex;gap:6px">
                <button class="btn btn-sm proc-filter active" data-status="">All</button>
                <button class="btn btn-sm proc-filter" data-status="running">Running</button>
                <button class="btn btn-sm proc-filter" data-status="completed">Completed</button>
                <button class="btn btn-sm proc-filter" data-status="failed">Failed</button>
                <button class="btn btn-sm proc-filter" data-status="pending">Pending</button>
            </div>
            <button class="btn btn-sm" id="proc-refresh" style="margin-left:auto">Refresh</button>
        </div>

        <div id="proc-table-container">
            <div class="text-muted" style="padding:40px;text-align:center">Loading processes...</div>
        </div>
    </div>
    `;
}

let _processesActiveFilter = '';

function initProcessesPage() {
    // Load processes
    loadProcesses();

    // Filter buttons
    document.querySelectorAll('.proc-filter').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.proc-filter').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            _processesActiveFilter = btn.dataset.status;
            loadProcesses();
        });
    });

    // Refresh button
    const refreshBtn = document.getElementById('proc-refresh');
    if (refreshBtn) refreshBtn.addEventListener('click', loadProcesses);
}

async function loadProcesses() {
    const container = document.getElementById('proc-table-container');
    if (!container) return;

    const statusParam = _processesActiveFilter ? `?status=${_processesActiveFilter}` : '';

    try {
        const res = await fetch(`/api/v1/processes${statusParam}`);
        const data = await res.json();

        if (!data.processes || data.processes.length === 0) {
            container.innerHTML = `
                <div class="text-muted" style="padding:40px;text-align:center">
                    No processes found. Run a demo with the Dynamic Orchestrator to see data here.
                </div>`;
            return;
        }

        let html = `
        <table class="proc-table">
            <thead>
                <tr>
                    <th style="width:90px">ID</th>
                    <th style="width:90px">Status</th>
                    <th>Plan</th>
                    <th style="width:60px">Events</th>
                    <th style="width:160px">Created</th>
                    <th style="width:160px">Updated</th>
                </tr>
            </thead>
            <tbody>`;

        for (const p of data.processes) {
            const statusClass = p.status === 'completed' ? 'status-completed'
                : p.status === 'running' ? 'status-running'
                : p.status === 'failed' ? 'status-failed'
                : 'status-pending';

            const created = p.created_at ? new Date(p.created_at).toLocaleString('en-GB', {day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit',second:'2-digit'}) : '-';
            const updated = p.updated_at ? new Date(p.updated_at).toLocaleString('en-GB', {day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit',second:'2-digit'}) : '-';

            html += `
                <tr class="proc-row" data-pid="${p.id}" style="cursor:pointer">
                    <td><code>${p.id.substring(0,8)}</code></td>
                    <td><span class="proc-status ${statusClass}">${p.status}</span></td>
                    <td>${p.plan_steps} steps (${p.plan_status})</td>
                    <td><strong>${p.event_count}</strong></td>
                    <td class="text-muted">${created}</td>
                    <td class="text-muted">${updated}</td>
                </tr>
                <tr class="proc-detail-row" id="detail-${p.id}" style="display:none">
                    <td colspan="6">
                        <div class="proc-detail" id="detail-content-${p.id}">
                            <div class="text-muted">Loading...</div>
                        </div>
                    </td>
                </tr>`;
        }

        html += '</tbody></table>';
        container.innerHTML = html;

        // Click to expand/collapse
        document.querySelectorAll('.proc-row').forEach(row => {
            row.addEventListener('click', () => {
                const pid = row.dataset.pid;
                const detailRow = document.getElementById(`detail-${pid}`);
                if (detailRow.style.display === 'none') {
                    detailRow.style.display = '';
                    loadProcessDetail(pid);
                } else {
                    detailRow.style.display = 'none';
                }
            });
        });

        // If a process_id is in the URL hash, auto-expand it
        const hashParts = location.hash.split('?pid=');
        if (hashParts.length > 1) {
            const targetPid = hashParts[1];
            const detailRow = document.getElementById(`detail-${targetPid}`);
            if (detailRow) {
                detailRow.style.display = '';
                loadProcessDetail(targetPid);
                detailRow.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        }

    } catch (err) {
        container.innerHTML = `
            <div style="padding:40px;text-align:center;color:var(--pink)">
                Failed to load processes: ${err.message}<br>
                <span class="text-muted">Make sure DATABASE_URL is set and PostgreSQL is running.</span>
            </div>`;
    }
}

async function loadProcessDetail(processId) {
    const container = document.getElementById(`detail-content-${processId}`);
    if (!container) return;

    try {
        // Fetch process + events in parallel
        const [procRes, eventsRes] = await Promise.all([
            fetch(`/api/v1/processes/${processId}`),
            fetch(`/api/v1/processes/${processId}/events`),
        ]);
        const proc = await procRes.json();
        const eventsData = await eventsRes.json();

        let html = '';

        // ── Plan Steps ──
        if (proc.plan && proc.plan.steps && proc.plan.steps.length > 0) {
            html += `<div class="proc-section-title">Plan (${proc.plan.status})</div>`;
            html += '<div class="proc-steps">';
            for (const step of proc.plan.steps) {
                const stepStatus = step.status === 'completed' ? 'status-completed'
                    : step.status === 'executing' ? 'status-running'
                    : step.status === 'failed' ? 'status-failed' : 'status-pending';
                html += `
                    <div class="proc-step">
                        <span class="proc-status ${stepStatus}" style="font-size:0.7rem">${step.status}</span>
                        <strong>${step.actor_name}</strong>.${step.tool_name}
                        ${step.parameters?.description ? `<span class="text-muted"> — ${step.parameters.description.substring(0,100)}</span>` : ''}
                    </div>`;
            }
            html += '</div>';
        }

        // ── Event Timeline ──
        if (eventsData.events && eventsData.events.length > 0) {
            html += `<div class="proc-section-title" style="margin-top:16px">Event Timeline (${eventsData.total} events)</div>`;
            html += '<div class="proc-timeline">';
            for (const evt of eventsData.events) {
                const time = evt.created_at ? new Date(evt.created_at).toLocaleTimeString('en-GB', {hour:'2-digit',minute:'2-digit',second:'2-digit'}) : '';
                const isError = evt.status === 'error';
                html += `
                    <div class="proc-timeline-event ${isError ? 'timeline-error' : ''}">
                        <span class="proc-timeline-time">${time}</span>
                        <span class="proc-timeline-agent">${evt.agent_id}</span>
                        <span class="proc-timeline-type">${evt.action_type}</span>
                        <span class="proc-timeline-msg">${evt.message || ''}</span>
                    </div>`;
            }
            html += '</div>';
        } else {
            html += '<div class="text-muted" style="padding:12px">No events recorded for this process.</div>';
        }

        container.innerHTML = html;

    } catch (err) {
        container.innerHTML = `<div style="color:var(--pink);padding:12px">Failed to load: ${err.message}</div>`;
    }
}
