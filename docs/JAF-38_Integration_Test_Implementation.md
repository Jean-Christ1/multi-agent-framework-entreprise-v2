# JAF-38: Integration Test Implementation

## Overview
This document outlines the implementation details for JAF-38, which focuses on creating and validating integration tests for the JEMS Multi-Agent Framework. The goal of these tests is to ensure that the framework's components interact seamlessly and perform as expected in various scenarios.

## Objectives
- Validate the interaction between agents and orchestrators.
- Ensure the framework handles multi-agent workflows correctly.
- Test crash recovery and state persistence mechanisms.
- Verify event emission and coordination between components.

## Implementation Details

### Key Features Tested
1. **Agentic Flow Validation**
   - Ensures that individual agents can achieve their goals with the orchestrator.
   - Validates proper integration with NativeEngine for deterministic testing.
   - Tests HTTP mocking to eliminate external dependencies.

2. **Multi-Agent Coordination**
   - Tests the ability of multiple agent types to coexist (Actor-based and legacy agents).
   - Demonstrates framework support for non-migrated agents.
   - Validates ActorRegistry functionality.

3. **Crash Recovery and State Persistence**
   - Validates PostgreSQL state persistence across application restarts.
   - Tests process state restoration with proper session context managers.
   - Ensures data integrity and cleanup after tests.

4. **Event Emission**
   - Verifies that events are emitted correctly throughout workflow lifecycle.
   - Ensures EventBus integration and real-time monitoring capability.
   - Validates event structure (agentId, actionType, message, status, timestamp).

### Test Results
- All integration tests pass successfully.
- Execution time: approximately 1.33 seconds.
- Test suite includes proper resource cleanup and HTTP mocking.

## Results
5 smoke tests total - 100% success rate

- **Agentic Flow Test**: 1/1 passed
- **Multi-Agent Coordination Test**: 1/1 passed
- **State Persistence Test**: 1/1 passed
- **Event Emission Test**: 1/1 passed
- **Framework Smoke Test**: 1/1 passed

## File Structure
```
tests/integration/
├── test_end_to_end.py                # Comprehensive smoke tests (5 tests)
├── test_llm_telemetry_persistence.py # Tests for telemetry persistence
```

## Test Coverage

### 1. Agentic Flow Test (`test_agentic_flow_provisioning_with_crewai`)
- **Objective**: Validate complete workflow with orchestrator and actor
- **Scenario**:
  - Goal: Provision laptop for employee C123456
  - Actor: ProvisionningAgent with NativeEngine
  - HTTP calls mocked for deterministic testing
- **Verifies**:
  - Actor migration and registration working
  - Orchestrator integration functional
  - Process completes with COMPLETED status (not RUNNING, as NativeEngine is deterministic)
  - Plan generation with steps
  - Event emission (process_started and others)
  - Process cleanup after test

### 2. Multi-Agent Coordination Test (`test_multi_agent_onboarding_workflow`)
- **Objective**: Demonstrate multi-agent framework capability
- **Scenario**:
  - Multiple agent types coexisting:
    - GeaiAgent (legacy, not migrated to Actor)
    - PiramidAgent (legacy, not migrated to Actor)
    - ProvisionningActor (migrated to Actor base class)
  - Manual coordination workflow
- **Verifies**:
  - All agent types can be instantiated
  - Actor-based agents registered in ActorRegistry
  - Non-migrated agents accessible for future migration
  - Framework supports mixed agent architectures

### 3. State Persistence Test (`test_crash_recovery_state_persistence`)
- **Objective**: Validate PostgreSQL state persistence and restoration
- **Scenario**:
  - Create process with partial execution (2 completed steps, 2 pending)
  - Save state to database using async context managers
  - Simulate crash (clear memory)
  - Restore process from database
- **Verifies**:
  - Process ID preservation
  - Status restoration (RUNNING)
  - Step states correctly restored (completed vs pending)
  - Context preservation across crash
  - Proper session cleanup with context managers
  - Process cleanup after test
- **Note**: This test validates state persistence only. Workflow resumption with orchestrator.resume() is not yet implemented.

### 4. Event Emission Test (`test_event_bus_integration_complete_workflow`)
- **Objective**: Verify EventBus integration and event lifecycle
- **Scenario**:
  - Execute complete workflow
  - Collect all emitted events
  - Validate event structure
- **Verifies**:
  - Events emitted at all lifecycle points
  - Required events present (process_started, etc.)
  - Event structure correctness:
    - agentId field present
    - actionType field present
    - timestamp field present
    - message field present
  - Real-time monitoring capability
  - Process cleanup after test

### 5. Framework Smoke Test (`test_framework_smoke_test_all_components`)
- **Objective**: Comprehensive validation of all framework components
- **Components Tested**:
  1. **Actor System**:
     - ActorRegistry with registered actors
     - ProvisionningActor with tools available
  2. **Event System**:
     - EventBus emission working
     - Event collectors receiving events
  3. **Persistence Layer**:
     - Process creation and storage
     - Process retrieval from database
     - Proper cleanup with delete_process method
     - Session context managers
  4. **Multi-Agent Support**:
     - GeaiAgent instantiation
     - PiramidAgent instantiation
     - Mixed architecture support
- **Verifies**:
  - All components working together
  - Framework release-readiness
  - No resource leaks (connections properly closed)

## Technical Implementation Details

### Fixtures
- **cleanup**: Auto-used fixture to clear ActorRegistry after each test
- **event_collector**: Collects events via EventBus subscription for verification
- **http_mock**: Mocks HTTP requests (requests.Session.post/get) to avoid external dependencies
- **cleanup_processes**: Tracks created process IDs and deletes them after test using async context managers
- **provisioning_actor**: Configured ProvisionningAgent registered in ActorRegistry
- **piramid_actor**: PiramidAgent instance (legacy, not yet migrated)
- **geai_actor**: GeaiAgent instance (legacy, not yet migrated)
- **session_maker**: Async session maker for database operations (returns async_sessionmaker, not ProcessRepository)
- **orchestrator**: Orchestrator with NativeEngine for deterministic testing

### Key Improvements
1. **Session Management**: All database operations use async context managers (`async with session_maker() as session:`)
2. **HTTP Mocking**: All tests with ProvisionningAgent use http_mock fixture with explicit verification to eliminate external dependencies
3. **Resource Cleanup**: cleanup_processes fixture ensures no test data persists in database
4. **Deterministic Assertions**: Tests expect COMPLETED status from NativeEngine (not RUNNING or COMPLETED)
5. **Proper Naming**: Fixture and test names match their actual functionality (e.g., session_maker returns async_sessionmaker)

### ProcessRepository Enhancements
Added `delete_process(process_id)` method for proper test cleanup:
```python
async def delete_process(self, process_id: uuid.UUID) -> bool:
    """Delete a process from the database."""
    query = text("DELETE FROM processes WHERE id = :id")
    result = await self.session.execute(query, {"id": process_id})
    await self.session.commit()
    return result.rowcount > 0
```

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

### .env Configuration
```
DATABASE_URL=postgresql+asyncpg://<username>:<password>@localhost:5432/jaf_dev
```

### Python Dependencies
```bash
pip install pytest pytest-asyncio asyncpg sqlalchemy pydantic
```

## Running Tests

### All integration tests
```bash
python3 -m pytest tests/integration/test_end_to_end.py -v
```

### Individual tests
```bash
# Test 1: Agentic flow
python3 -m pytest tests/integration/test_end_to_end.py::test_agentic_flow_provisioning_with_crewai -v

# Test 2: Multi-agent coordination
python3 -m pytest tests/integration/test_end_to_end.py::test_multi_agent_onboarding_workflow -v

# Test 3: State persistence
python3 -m pytest tests/integration/test_end_to_end.py::test_crash_recovery_state_persistence -v

# Test 4: Event emission
python3 -m pytest tests/integration/test_end_to_end.py::test_event_bus_integration_complete_workflow -v

# Test 5: Smoke test
python3 -m pytest tests/integration/test_end_to_end.py::test_framework_smoke_test_all_components -v
```

### With detailed output
```bash
python3 -m pytest tests/integration/test_end_to_end.py -v --capture=no
```

### With short traceback
```bash
python3 -m pytest tests/integration/test_end_to_end.py -v --tb=short
```

### As standalone demo
```bash
# The test file can be run directly as a demo
python3 tests/integration/test_end_to_end.py
```

## Expected Output
```
===== test session starts =====
platform linux -- Python 3.10.12, pytest-9.0.2, pluggy-1.6.0
collected 5 items

tests/integration/test_end_to_end.py::test_agentic_flow_provisioning_with_crewai PASSED [ 20%]
tests/integration/test_end_to_end.py::test_multi_agent_onboarding_workflow PASSED [ 40%]
tests/integration/test_end_to_end.py::test_crash_recovery_state_persistence PASSED [ 60%]
tests/integration/test_end_to_end.py::test_event_bus_integration_complete_workflow PASSED [ 80%]
tests/integration/test_end_to_end.py::test_framework_smoke_test_all_components PASSED [100%]

===== 5 passed in 1.33s =====
```

## Conclusion
The integration test suite provides comprehensive validation of the JAF framework components:
- Actor system with migration support
- Orchestrator with deterministic execution
- State persistence with proper resource management
- EventBus integration for real-time monitoring
- Multi-agent architecture support

All tests pass successfully with proper cleanup and no resource leaks, demonstrating framework readiness for production use.
