/**
 * JAF Demo Runner — SSE Client
 *
 * Handles:
 *  - Fetching available demos from /api/v1/demos
 *  - Rendering the demo selector sidebar
 *  - Running demos via POST /api/v1/demos/{id}/run
 *  - Streaming events via EventSource from /api/v1/stream/{process_id}
 *  - Rendering typed event entries in the output panel
 */

let selectedDemoId = null;
let currentEventSource = null;
let isRunning = false;
let demos = [];
let currentDemoMode = null;   // track mode for context-aware result header
let currentDemoId = null;     // track demo id for specialized rendering
let lastAgentId = null;       // track for visual grouping

// ── Initialize ──────────────────────────────────────

async function initDemos() {
    try {
        const resp = await fetch('/api/v1/demos');
        const data = await resp.json();
        demos = data.demos || [];
        renderSidebar();
    } catch (err) {
        document.getElementById('demo-sidebar').innerHTML =
            '<div class="text-muted text-sm" style="padding:var(--space-md)">Failed to load demos. Is the server running?</div>';
    }
}

// ── Sidebar ─────────────────────────────────────────

function renderSidebar() {
    const sidebar = document.getElementById('demo-sidebar');
    if (!sidebar) return;

    sidebar.innerHTML = demos.map(d => `
        <div class="demo-card ${d.id === selectedDemoId ? 'selected' : ''}"
             data-demo-id="${d.id}"
             onclick="selectDemo('${d.id}')">
            <div class="demo-card-name">${d.name}</div>
            <div class="demo-card-desc">${d.description}</div>
            <div class="demo-card-meta">
                <span class="badge ${d.mode}">${d.mode}</span>
                ${d.pattern ? `<span class="tag">${d.pattern}</span>` : ''}
                ${d.engine ? `<span class="tag">${d.engine}</span>` : ''}
                ${d.model ? `<span class="tag">${d.model}</span>` : '<span class="tag">no LLM</span>'}
                ${d.planning_model ? `<span class="tag">planning: ${d.planning_model}</span>` : ''}
            </div>
        </div>
    `).join('');
}

function selectDemo(demoId) {
    if (isRunning) return;

    selectedDemoId = demoId;
    renderSidebar();

    const demo = demos.find(d => d.id === demoId);
    if (!demo) return;

    currentDemoMode = demo.mode;
    currentDemoId = demo.id;

    const title = document.getElementById('demo-output-title');
    const btn = document.getElementById('demo-run-btn');
    const events = document.getElementById('demo-events');

    title.textContent = demo.name;
    btn.disabled = false;
    btn.textContent = 'Run Demo';
    btn.onclick = () => runDemo(demoId);

    events.innerHTML = `
        <div class="demo-placeholder">
            <div style="text-align:center">
                <div style="font-size:1.1rem;margin-bottom:8px;color:var(--text)">${demo.name}</div>
                <div style="max-width:400px;line-height:1.6">${demo.description}</div>
                <div style="margin-top:16px">
                    <span class="badge ${demo.mode}" style="font-size:0.8rem">${demo.mode}</span>
                    ${demo.pattern ? `<span class="tag" style="font-size:0.8rem">${demo.pattern}</span>` : ''}
                    ${demo.engine ? `<span class="tag" style="font-size:0.8rem">${demo.engine}</span>` : ''}
                    ${demo.model ? `<span class="tag" style="font-size:0.8rem">${demo.model}</span>` : ''}
                    ${demo.planning_model ? `<span class="tag" style="font-size:0.8rem">planning: ${demo.planning_model}</span>` : ''}
                </div>
            </div>
        </div>
    `;
}

// ── Run Demo ────────────────────────────────────────

async function runDemo(demoId) {
    if (isRunning) return;
    isRunning = true;
    lastAgentId = null;

    const demo = demos.find(d => d.id === demoId);
    if (demo) {
        currentDemoMode = demo.mode;
        currentDemoId = demo.id;
    }

    const btn = document.getElementById('demo-run-btn');
    const events = document.getElementById('demo-events');

    btn.disabled = true;
    btn.textContent = 'Running...';
    events.innerHTML = '';

    try {
        // Start the demo
        const resp = await fetch(`/api/v1/demos/${demoId}/run`, { method: 'POST' });
        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || 'Failed to start demo');
        }

        const data = await resp.json();
        const processId = data.process_id;

        // Small delay to let the background task start
        await new Promise(r => setTimeout(r, 300));

        // Connect to SSE stream
        connectSSE(processId);

    } catch (err) {
        addEvent('error', { message: `Error: ${err.message}`, agentId: 'client' });
        resetRunButton();
    }
}

function connectSSE(processId) {
    if (currentEventSource) {
        currentEventSource.close();
    }

    const es = new EventSource(`/api/v1/stream/${processId}`);
    currentEventSource = es;

    const eventTypes = [
        'process_started', 'thinking', 'llm_response',
        'tool_called', 'tool_result', 'tool_error',
        'completed', 'error'
    ];

    eventTypes.forEach(type => {
        es.addEventListener(type, (e) => {
            try {
                const data = JSON.parse(e.data);
                addEvent(type, data);

                // Handle terminal events
                if (type === 'completed') {
                    showResult(data);
                    es.close();
                    resetRunButton();
                } else if (type === 'error') {
                    es.close();
                    resetRunButton();
                }
            } catch (err) {
                console.error('Failed to parse SSE event:', err);
            }
        });
    });

    es.onerror = () => {
        // SSE connection closed (normal after completed/error)
        if (isRunning) {
            resetRunButton();
        }
    };
}

function resetRunButton() {
    isRunning = false;
    lastAgentId = null;
    const btn = document.getElementById('demo-run-btn');
    if (btn) {
        btn.disabled = false;
        btn.textContent = 'Run Again';
    }
    if (currentEventSource) {
        currentEventSource.close();
        currentEventSource = null;
    }
}

// ── Render Events ───────────────────────────────────

const EVENT_LABELS = {
    process_started: 'GOAL',
    thinking: 'THINK',
    llm_response: 'LLM',
    tool_called: 'TOOL',
    tool_result: 'DATA',
    tool_error: 'ERROR',
    completed: 'DONE',
    error: 'ERROR',
};

// Stable color per agent name for left-border grouping
const AGENT_COLORS = {};
const COLOR_PALETTE = [
    'var(--cyan)', 'var(--blue)', 'var(--orange)',
    'var(--pink)', 'var(--green)', 'var(--accent)',
];
let colorIdx = 0;

function agentColor(name) {
    if (!name || name === 'engine' || name === 'client' || name === 'orchestrator' || name === 'Orchestrator' || name === 'CrewAI' || name === 'CrewAI-Manager') return 'var(--text-dim)';
    if (!AGENT_COLORS[name]) {
        AGENT_COLORS[name] = COLOR_PALETTE[colorIdx % COLOR_PALETTE.length];
        colorIdx++;
    }
    return AGENT_COLORS[name];
}

function addEvent(type, data) {
    const container = document.getElementById('demo-events');
    if (!container) return;

    // Remove placeholder
    const placeholder = container.querySelector('.demo-placeholder');
    if (placeholder) placeholder.remove();

    const time = data.timestamp ? formatTime(data.timestamp) : '';
    const agent = data.agentId || '';
    const msg = data.message || '';
    const label = EVENT_LABELS[type] || type.toUpperCase();
    const color = agentColor(agent);

    // Check if same agent as previous event (for visual grouping)
    const sameAgent = agent && agent === lastAgentId;
    lastAgentId = agent;

    const el = document.createElement('div');
    el.className = `event-entry type-${type}${sameAgent ? ' same-agent' : ''}`;
    el.style.borderLeftColor = color;

    // Two-line layout: line 1 = time + badge + agent, line 2 = message
    el.innerHTML = `
        <div class="event-row-top">
            <span class="event-time">${time}</span>
            <span class="event-badge">${label}</span>
            <span class="event-agent" style="color:${color}">${agent}</span>
        </div>
        <div class="event-row-msg">${escapeHtml(msg)}</div>
    `;

    container.appendChild(el);

    // Auto-scroll to bottom
    container.scrollTop = container.scrollHeight;
}

function showResult(data) {
    const container = document.getElementById('demo-events');
    if (!container) return;

    const resultText = data.data?.result || data.message || 'No result';
    const isDynamic = currentDemoId === 'dynamic_orchestrator';
    const d = data.data || {};
    const processId = d.process_id || data.process_id || '';

    // Context-aware header
    let headerText;
    if (isDynamic) {
        headerText = 'Dynamic Orchestrator Result';
    } else if (currentDemoMode === 'traditional') {
        headerText = 'Workflow Result';
    } else if (currentDemoMode === 'crewai') {
        headerText = 'CrewAI Result';
    } else {
        headerText = 'Agent Final Response';
    }

    // Build the collapsible audit trail panel
    let auditPanel = '';
    const panelId = 'audit-panel-' + Date.now();

    // Step-by-step execution summary (for dynamic orchestrator or any multi-step demo)
    let stepsHtml = '';
    if (d.step_results && d.step_results.length > 0) {
        stepsHtml = '<div style="margin-top:8px"><strong style="font-size:0.78rem;color:var(--text-dim)">STEP EXECUTION</strong></div>';
        for (const sr of d.step_results) {
            const isDynamicStep = sr.step > (d.total_steps - (d.steps_added || 0));
            stepsHtml += `
                <div style="display:flex;gap:8px;align-items:center;padding:3px 0;font-size:0.82rem">
                    <span style="color:var(--text-dim);min-width:50px">Step ${sr.step}</span>
                    <span style="color:var(--cyan)">${sr.agent || '-'}</span>
                    <span class="text-muted">${(sr.description || '').substring(0,60)}</span>
                    ${sr.tool_calls ? `<span style="color:var(--orange);font-size:0.75rem">${sr.tool_calls} tool calls</span>` : ''}
                    ${isDynamicStep ? '<span style="background:var(--accent);color:var(--bg);padding:1px 6px;border-radius:3px;font-size:0.7rem;font-weight:600">DYNAMIC</span>' : ''}
                </div>`;
        }
    }

    // Build the persistence summary rows
    let persistenceRows = '';
    if (processId) {
        persistenceRows += `
            <div class="audit-trail-row">
                <span class="audit-trail-label">Process ID</span>
                <code class="audit-trail-value">${processId.substring(0,8)}...</code>
            </div>`;
    }
    if (d.total_steps !== undefined) {
        persistenceRows += `
            <div class="audit-trail-row">
                <span class="audit-trail-label">Steps Executed</span>
                <span class="audit-trail-value">${d.total_steps}</span>
            </div>`;
    }
    if (d.steps_added) {
        persistenceRows += `
            <div class="audit-trail-row">
                <span class="audit-trail-label">Steps Added Dynamically</span>
                <span class="audit-trail-value" style="color:var(--accent)">${d.steps_added}</span>
            </div>`;
    }
    if (d.events_persisted !== undefined) {
        persistenceRows += `
            <div class="audit-trail-row">
                <span class="audit-trail-label">Events in PostgreSQL</span>
                <span class="audit-trail-value">${d.events_persisted}</span>
            </div>`;
    }
    if (d.total_iterations !== undefined) {
        persistenceRows += `
            <div class="audit-trail-row">
                <span class="audit-trail-label">LLM Iterations</span>
                <span class="audit-trail-value">${d.total_iterations}</span>
            </div>`;
    }
    if (d.total_tool_calls !== undefined) {
        persistenceRows += `
            <div class="audit-trail-row">
                <span class="audit-trail-label">Tool Calls</span>
                <span class="audit-trail-value">${d.total_tool_calls}</span>
            </div>`;
    }

    // View in Processes link (only for dynamic orchestrator with PostgreSQL persistence)
    let viewLink = '';
    if (isDynamic && processId) {
        viewLink = `<a class="audit-trail-link" href="#processes?pid=${processId}">View in Processes Page</a>`;
    }

    if (persistenceRows || stepsHtml) {
        auditPanel = `
            <div class="audit-trail-panel">
                <div class="audit-trail-header" onclick="document.getElementById('${panelId}').classList.toggle('expanded');this.querySelector('.audit-trail-toggle').textContent=document.getElementById('${panelId}').classList.contains('expanded')?'collapse':'expand'">
                    <span>Workflow Execution &amp; Audit Trail</span>
                    <span class="audit-trail-toggle">expand</span>
                </div>
                <div class="audit-trail-body" id="${panelId}">
                    ${persistenceRows}
                    ${stepsHtml}
                    ${viewLink}
                </div>
            </div>`;
    }

    const el = document.createElement('div');
    el.className = 'demo-result';
    el.innerHTML = `
        <div class="demo-result-header">${headerText}</div>
        ${escapeHtml(resultText)}
        ${auditPanel}
    `;

    container.appendChild(el);
    container.scrollTop = container.scrollHeight;
}

// ── Utilities ───────────────────────────────────────

function formatTime(isoString) {
    try {
        const d = new Date(isoString);
        return d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    } catch {
        return '';
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
