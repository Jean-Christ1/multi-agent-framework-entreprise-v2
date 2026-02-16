# JAF Sprint Plan by Streams (4 Weeks)

## Work Stream Assignments

### Stream A: Actor SDK
**Team:** Dev #3 (Lead) + Junior #1 (RO)
**Focus:** Actor abstraction, registry, agent migrations

### Stream B: Engine Core
**Team:** Dev #1 (Lead) + Supervisor
**Focus:** Engine interface, adapters, execution logic
**⚠️ CRITICAL PATH**

### Stream C: Persistence & Events
**Team:** Dev #4 (Lead) + Junior #2 (RO)
**Focus:** Database, state management, SSE, observability

### Stream D: Outcomes & DX
**Team:** Dev #2 (Lead) + Supervisor
**Focus:** Flow implementations, CLI, Auto-API, testing

---

## Week 1: Foundation (39 Story Points)

### Stream A Tasks (13 pts):
- **JAF-6** (5 pts): Actor Base Class
  - Create `framework/actor/base_actor.py`
  - Implement hybrid mode (with/without LLM)
  - Unit tests
- **JAF-10** (8 pts): Start Provisioning Migration
  - Refactor `ProvisionningAgent` to inherit Actor
  - Configure tools in `configure()` method
  - Initial testing

**Week 1 Deliverable:** Actor base class working, Provisioning 50% migrated

---

### Stream B Tasks (13 pts):
- **JAF-5** (5 pts): Engine Interface **CRITICAL**
  - Create `framework/engine/engine_abstraction.py`
  - Define: `generate_plan()`, `execute_step()`, `evaluate_progress()`
  - Pydantic models for Plan, PlanStep, StepResult
- **JAF-9** (8 pts): Start CrewAI Adapter
  - Create `framework/engine/crewai_adapter.py`
  - Implement `execute_step()` wrapping CrewAI
  - Initial integration tests

**Week 1 Deliverable:** Engine interface complete, CrewAI adapter 70% done

---

### Stream C Tasks (10 pts):
- **JAF-7** (5 pts): Database Schema
  - Migration `001_processes.sql`
  - Tables: `processes`, `events`
  - Deploy to dev DB
- **JAF-8** (5 pts): Process Repository
  - Create `framework/persistence/process_repo.py`
  - Methods: `create()`, `get()`, `update_status()`, `log_event()`
  - Async with connection pooling

**Week 1 Deliverable:** DB schema deployed, repository working

---

### Stream D Tasks (3 pts):
- **Planning Week**: Requirements gathering, architecture review
- **JAF-11** (3 pts): Basic Event Bus (Dev #4 can help)
  - Console logging version
  - Event schema: `{agentId, actionType, message, status}`

**Week 1 Deliverable:** Event bus logging to console

---

### **WEEK 1 MILESTONE DEMO (Friday EOD)**
**Integration Demo:**
1. Show Engine interface + Actor base class
2. Run ProvisionningActor via CrewAI adapter
3. Process state saves to DB mid-execution
4. Events log to console
5. Kill process → restart → resumes from DB

---

## Week 2: Execution Modes (42 Story Points)

### Stream A Tasks (13 pts):
- **JAF-10** (complete): Finish Provisioning Migration
  - All workflows working via new Engine
  - Regression tests pass
- **JAF-17** (start): Begin Piramid/Habilitation/Geai migrations
  - 30% progress (complete Week 3)

**Week 2 Deliverable:** Provisioning fully migrated, 3 agents started

---

### Stream B Tasks (16 pts):
- **JAF-9** (complete): Finish CrewAI Adapter
  - Full Plan-Execute-Evaluate loop
  - Error handling, timeouts
  - Integration with persistence
- **JAF-15** (13 pts): Start Native Engine
  - OpenAI function calling integration
  - Tool parsing and execution
  - 50% complete (finish Week 3)
- **JAF-16** (3 pts): Engine Factory
  - Auto-select CrewAI vs Native
  - Configuration via env vars

**Week 2 Deliverable:** CrewAI adapter complete, Native engine 50%, Factory working

---

### Stream C Tasks (5 pts):
- **JAF-14** (5 pts): SSE Endpoint
  - `GET /api/processes/{id}/stream`
  - FastAPI SSE integration
  - Frontend test (mock client)

**Week 2 Deliverable:** Events stream to frontend in real-time

---

### Stream D Tasks (8 pts):
- **JAF-12** (8 pts): Agentic Flow
  - Single orchestrator + flattened tools
  - Cost optimization (cheap LLM)
  - Example workflow

**Week 2 Deliverable:** Agentic flow working with cost analysis

---

### **WEEK 2 MILESTONE DEMO (Friday EOD)**
**Integration Demo:**
1. **Agentic Flow**: Onboarding with 1 actor (cost: $0.05)
2. **Multi-Agent Flow**: Onboarding with 3 actors (cost: $0.12) - partial demo
3. Real-time SSE streaming to frontend
4. CrewAI vs Native engine comparison (latency)

---

## Week 3: Migration & DX (37 Story Points)

### Stream A Tasks (16 pts):
- **JAF-17** (complete): Finish 3 agent migrations
  - Piramid, Habilitation, Geai fully migrated
  - All regression tests pass
- **JAF-18** (3 pts): Migrate Annuaire
  - Simplest agent (directory service)
  - Junior #1 lead

**Week 3 Deliverable:** All 5 agents migrated to Actor pattern

---

### Stream B Tasks (13 pts):
- **JAF-15** (complete): Finish Native Engine
  - Full feature parity with CrewAI adapter
  - Performance benchmarks (5x faster target)
- **Support**: Help other streams with integrations

**Week 3 Deliverable:** Native engine production-ready

---

### Stream C Tasks (13 pts):
- **JAF-22** (8 pts): Start Observability
  - Prometheus metrics instrumentation
  - Grafana dashboard JSON (50% complete)
- **JAF-23** (5 pts): Docker Compose
  - Dev environment: Postgres, Redis, API, Frontend, Mocks
  - Hot reload, seeded data

**Week 3 Deliverable:** Docker Compose working, Grafana 50%

---

### Stream D Tasks (21 pts):
- **JAF-13** (13 pts): Finish Multi-Agent Flow
  - Hierarchical delegation working
  - Complex workflow examples
- **JAF-19** (8 pts): CLI Tool
  - `jems new actor` scaffolding
  - Jinja2 templates
  - Demo video

**Week 3 Deliverable:** Multi-agent flow complete, CLI working

---

### **WEEK 3 MILESTONE DEMO (Friday EOD)**
**Integration Demo:**
1. All 5 agents running via new framework
2. Live demo: `jems new actor --name ComplianceOfficer`
3. Show auto-generated files
4. Docker Compose one-command setup
5. Partial Grafana dashboard

---

## Week 4: Production & Client Demo (31 Story Points)

### Stream A Tasks (3 pts):
- **Polish & Testing**: Final regression tests, bug fixes
- **Documentation**: Actor migration guide

**Week 4 Deliverable:** Framework stable, all tests green

---

### Stream B Tasks (8 pts):
- **JAF-25** (8 pts): E2E Integration Tests
  - Agentic flow test
  - Multi-agent flow test
  - Crash recovery test
  - CI/CD integration

**Week 4 Deliverable:** Full test suite passing

---

### Stream C Tasks (15 pts):
- **JAF-22** (complete): Finish Grafana Dashboard
  - All metrics: success rate, latency, cost, active processes
  - Alerts configured
- **JAF-24** (5 pts): Production Dockerfile
  - Multi-stage build, <200MB
  - Health check, non-root user
- **JAF-23** (polish): Production-ready Docker Compose

**Week 4 Deliverable:** Full observability, production deployment ready

---

### Stream D Tasks (16 pts):
- **JAF-20** (8 pts): Auto-API Generation
  - Scan Actors, generate endpoints
  - Swagger docs
- **JAF-21** (5 pts): Mock LLM
  - Fixtures for all 5 agents
  - CI/CD integration (zero cost tests)
- **JAF-26** (5 pts): Client Demo Prep
  - 30-minute script
  - Demo environment setup
  - Dry run

**Week 4 Deliverable:** Auto-API working, Mock LLM in CI, Demo ready

---

### **WEEK 4 MILESTONE: CLIENT PRESENTATION (Friday)**

**30-Minute Demo Script:**

#### Part 1: The Problem (5 min)
- Show current monolithic orchestrator
- Explain: vendor lock-in, slow development, hard to scale

#### Part 2: The Solution - JAF Architecture (5 min)
- Whiteboard walkthrough: Engine → Actor → Process
- Show code: Actor base class, Engine interface

#### Part 3: The 3 Outcomes (12 min)

**Outcome 1: Agentic Flow (3 min)**
- Run: Employee onboarding with 1 orchestrator + tools
- Show: Cost $0.05, Latency 2s, SSE events
- Use case: "High-volume, simple tasks"

**Outcome 2: Multi-Agent Flow (6 min)**
- Run: Same onboarding, orchestrator delegates to 3 actors
- Show: Cost $0.12, Latency 5s, better reasoning
- Show: Grafana dashboard (metrics, costs)
- Use case: "Complex workflows requiring expertise"

**Outcome 3: Traditional Automation (3 min - if implemented)**
- Run: Hardcoded provisioning flow (no LLM)
- Show: Cost $0.00, Latency 0.5s
- Use case: "Deterministic, compliance-critical"

#### Part 4: Developer Experience (5 min)
- Live: `jems new actor --name InvoiceProcessor`
- Show: Auto-generated code, Auto-API endpoint
- Show: Docker Compose one-command setup
- Show: CI/CD running tests with Mock LLM

#### Part 5: Q&A (3 min)

---

## Stream Coordination Points

### Daily Standups (15 min)
- **Stream A**: Actor migrations status
- **Stream B**: Engine/adapter progress (blocks others)
- **Stream C**: DB/events readiness
- **Stream D**: Outcome implementations

### Weekly Sync (Friday before demo, 1 hour)
- Integration testing across streams
- Demo rehearsal
- Next week planning

### Blockers & Dependencies:
- **Week 1**: Stream B (Engine) blocks all others → Priority #1
- **Week 1-2**: Stream A (Actor) blocks migrations
- **Week 2**: Stream C (SSE) needed for frontend demo
- **Week 3**: All streams converge for multi-agent flow
- **Week 4**: Stream D (Demo prep) coordinates all

---

## Story Point Velocity Tracking

| Week | Stream A | Stream B | Stream C | Stream D | Total | Capacity |
|------|----------|----------|----------|----------|-------|----------|
| 1    | 13       | 13       | 10       | 3        | 39    | 40       |
| 2    | 13       | 16       | 5        | 8        | 42    | 40       |
| 3    | 16       | 13       | 13       | 21       | 63*   | 40       |
| 4    | 3        | 8        | 15       | 16       | 42    | 40       |
| **Total** | **45** | **50** | **43** | **48** | **186** | **160** |

*Week 3 over capacity - some work from Week 2 spillover expected

**Capacity:** 4 devs × 10 pts/week = 40 pts/week
**Total Capacity:** 160 pts over 4 weeks
**Total Backlog:** 186 pts (116% loaded - realistic for sprints)

---

## Risk Mitigation

### High-Risk Items:
1. **JAF-5** (Engine Interface) - If wrong, everything breaks
   - Mitigation: Supervisor + Dev #1, architecture review Week 1
2. **JAF-13** (Multi-Agent Flow) - Complex, 13 pts
   - Mitigation: Start early Week 2, Supervisor support
3. **Week 3 Overload** - 63 pts vs 40 capacity
   - Mitigation: Start JAF-15 (Native Engine) in Week 2

### Medium-Risk Items:
- **JAF-10** (Provisioning Migration) - First migration, sets pattern
- **JAF-9** (CrewAI Adapter) - Must maintain backward compat
- **JAF-14** (SSE) - Critical for frontend demo

### Contingency Plans:
- **If Week 1 slips:** Defer JAF-15 (Native Engine) to Week 3
- **If migrations slow:** Focus on Provisioning + 1 other (defer remaining)
- **If Traditional Automation (Outcome 3) not ready:** Demo just 2 outcomes

---

**End of Sprint Plan**
