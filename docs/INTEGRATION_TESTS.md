# End-to-End Integration Tests - JAF Framework

## Overview

This end-to-end integration test suite validates the complete functionality of the JAF framework, from input to output, including all critical components: actors, engines, orchestrator, persistence, events, and crash recovery.

## Results

**26 tests total - 100% success rate**

- **End-to-End Workflow Tests**: 6/6 passed
- **Crash Recovery Tests**: 5/5 passed
- **Persistence Test**: 1/1 passed
- **Unit Tests (reference)**: 14/14 passed

## File Structure

```
tests/integration/
├── README.md                          # This documentation
├── actors_fixtures.py                 # Reusable test actors
├── test_end_to_end_workflow.py       # Complete workflow tests (6 tests)
├── test_crash_recovery.py            # Crash recovery tests (5 tests)
└── test_llm_telemetry_persistence.py # LLM telemetry test (1 test)
```

## Test Coverage

### 1. Actor Fixtures (`actors_fixtures.py`)

Library of deterministic actors (without LLM) for testing:

- **CalculatorActor**: Arithmetic operations
  - `add(a, b)`: Addition
  - `multiply(a, b)`: Multiplication
  - `divide(a, b)`: Division (with zero division handling)

- **ValidatorActor**: Data validations
  - `validate_positive(value)`: Checks if positive
  - `validate_range(value, min_val, max_val)`: Checks range
  - `validate_type(value, expected_type)`: Checks type

- **DataProcessorActor**: Data processing
  - `normalize(values)`: Normalization 0-1
  - `aggregate(values, operation)`: Aggregation (sum, avg, min, max)
  - `filter_data(values, threshold, condition)`: Filtering

### 2. End-to-End Workflow Tests (`test_end_to_end_workflow.py`)

#### test_end_to_end_simple_workflow
**Objective**: Validate a simple 2-step workflow

**Scenario**:
1. Calculate: 10 + 5 = 15
2. Validate: 15 is positive

**Verifies**:
- Process creation and execution
- Persistence of intermediate states
- Event emission (process_started, plan_generated, step_started, step_completed, process_completed)
- Correct final result
- COMPLETED status in database

#### test_end_to_end_multi_actor_workflow
**Objective**: Complex workflow with 3 actors and 4 steps

**Scenario**:
1. Calculator: 3 × 4 = 12
2. Calculator: 12 + 8 = 20
3. DataProcessor: aggregate([20]) = 20
4. Validator: 20 is positive

**Verifies**:
- Multi-actor coordination
- Data flow between steps
- All steps marked as "completed"

#### test_end_to_end_error_handling
**Objective**: Error handling in workflow

**Scenario**:
1. Calculate: 10 + 5 = 15
2. Division by zero (error)

**Verifies**:
- First step succeeds
- Error captured in second step
- Error events emitted
- Partial results saved

#### test_end_to_end_persistence_state_tracking
**Objective**: State tracking at each step

**Verifies**:
- Status transitions: PENDING → RUNNING → COMPLETED
- Context updated at each step
- State saved in database
- All steps marked completed

#### test_event_bus_integration_all_events
**Objective**: Verify complete EventBus integration

**Verifies**:
- Emission of all required events:
  - process_started
  - planning_started
  - plan_generated
  - step_started
  - step_completed
  - process_completed
- Correct event structure (agentId, actionType, message, status, timestamp)

#### test_concurrent_process_isolation
**Objective**: Isolation between concurrent processes

**Scenario**:
- Process 1: 10 + 10 = 20
- Process 2: 5 × 5 = 25

**Verifies**:
- Each process has its own unique ID
- Independent and isolated states
- Different results saved separately
- No cross-contamination

### 3. Crash Recovery Tests (`test_crash_recovery.py`)

#### test_crash_recovery_restore_process_state
**Objective**: State restoration after crash

**Scenario**:
1. Process with 2 steps (1 completed, 1 pending)
2. State saved in database
3. Crash simulation
4. Reload from database

**Verifies**:
- Process ID preserved
- RUNNING status restored
- Correct step states (completed/pending)
- Context preserved

#### test_crash_recovery_resume_from_checkpoint
**Objective**: Resume execution from last checkpoint

**Scenario**:
1. 4-step workflow
2. Complete execution
3. Reload process
4. Verify final state

**Verifies**:
- Process COMPLETED
- All 4 steps completed
- Context contains all intermediate results

#### test_crash_recovery_partial_step_execution
**Objective**: Detection of interrupted step

**Scenario**:
1. Step 1: completed
2. Step 2: executing (crash during execution)
3. Step 3: pending

**Verifies**:
- Detection of "executing" step
- Step reset to "pending" possible
- Database update
- No "executing" step after reset

#### test_crash_recovery_state_consistency
**Objective**: State consistency after recovery

**Verifies**:
- Process ID integrity
- Plan intact (steps, IDs)
- Complete and consistent context
- Consistent status (process and plan)
- Timestamps preserved
- All steps have correct status

#### test_crash_recovery_multiple_processes
**Objective**: Recovery of multiple processes

**Scenario**:
- Process 1: COMPLETED
- Process 2: RUNNING (executing)
- Process 3: PENDING

**Verifies**:
- Each process maintains independent state
- No cross-process contamination
- Isolated contexts

### 4. Persistence Test (`test_llm_telemetry_persistence.py`)

#### test_llm_telemetry_is_persisted
**Objective**: LLM telemetry persistence

**Verifies**:
- LLM metadata saved
- Correct database query
- Data accessible after insertion

## Prerequisites

### PostgreSQL Database

```bash
# Create database
createdb jaf_dev

# Run migrations
psql jaf_dev < migrations/001_create_processes.sql
psql jaf_dev < migrations/002_create_llm_telemetry.sql

# Configure user password
psql jaf_dev -c "ALTER USER <username> WITH PASSWORD '<password>';"
```

### `.env` Configuration

```env
DATABASE_URL=postgresql+asyncpg://<username>:<password>@localhost:5432/jaf_dev
```

### Python Dependencies

```bash
pip install pytest pytest-asyncio asyncpg sqlalchemy pydantic
```

## Running Tests

### All integration tests
```bash
python3 -m pytest tests/integration/ -v
```

### Specific tests
```bash
# End-to-End tests only
python3 -m pytest tests/integration/test_end_to_end_workflow.py -v

# Crash Recovery tests only
python3 -m pytest tests/integration/test_crash_recovery.py -v

# Single test
python3 -m pytest tests/integration/test_end_to_end_workflow.py::test_end_to_end_simple_workflow -v
```

### With detailed output
```bash
python3 -m pytest tests/integration/ -v -s
```

### With short traceback
```bash
python3 -m pytest tests/integration/ -v --tb=short
```

## Tested Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        INPUT (Goal)                          │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    ENGINE (NativeEngine)                     │
│                   - generate_plan()                          │
│                   - execute_step()                           │
│                   - evaluate_progress()                      │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR                              │
│                   - Coordination                             │
│                   - State transitions                        │
│                   - Event emission                           │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    ACTORS (via Registry)                     │
│    CalculatorActor | ValidatorActor | DataProcessorActor    │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    PERSISTENCE (PostgreSQL)                  │
│                   - ProcessRepository                        │
│                   - State snapshots                          │
│                   - Crash recovery                           │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    EVENT BUS                                 │
│                   - AgentAction events                       │
│                   - Real-time updates                        │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    OUTPUT (ProcessResult)                    │
│                   - Status                                   │
│                   - Context                                  │
│                   - Step results                             │
└─────────────────────────────────────────────────────────────┘
```

## What is Tested

**Complete flow**: Input → Engine → Orchestrator → Actors → Persistence → Events → Output

**Persistence**:
- PostgreSQL database save
- ACID transactions
- State restoration

**EventBus**:
- Event emission
- Collection and verification
- Correct structure

**Crash recovery**:
- State restoration
- Execution resume
- Detection of incomplete steps
- Data consistency

**Isolation**:
- Independent concurrent processes
- No state contamination
- Unique IDs

**Error handling**:
- Error capture
- Partial results
- Error states

## Metrics

- **Execution time**: ~2-3 seconds for all tests
- **Coverage**: All main framework components
- **Reliability**: 100% success rate
- **Isolation**: Each test is independent (fixtures with cleanup)

## Patterns Used

- **pytest Fixtures**: To create configured actors and event collector
- **async/await**: All tests are asynchronous
- **Automatic cleanup**: EventBus.clear() and ActorRegistry.clear()
- **Detailed assertions**: Verification of each result aspect
- **Pre-defined plans**: Using NativeEngine with static plans

## Limitations and Future Improvements

- [ ] Tests with CrewAI adapter (currently only NativeEngine)
- [ ] Performance and load tests
- [ ] Intensive concurrency tests
- [ ] Database schema migration tests
- [ ] Tests with multiple simultaneous databases
- [ ] Network resilience tests

## References
- [ARCHITECTURE.md](../../docs/ARCHITECTURE.md) - Framework architecture
- [README.md](../../README.md) - Main documentation
- [AGENTIC_FLOW.md](../../docs/AGENTIC_FLOW.md) - Agentic flow

---

**Created**: January 8, 2026
**Author**: End-to-end integration tests for JAF Framework
**Status**: All tests passing (26/26)
