import json
import os
import io
import logging

from framework.logging import get_logger, set_logging_context


def _reset_logging_state():
    """
    Reset logger cache and root handlers between tests
    to avoid cross-test contamination.
    """
    from framework import logging as framework_logging

    # Clear logger cache
    framework_logging._LOGGERS.clear()

    # Reset contextvars
    framework_logging._process_id.set(None)
    framework_logging._actor_name.set(None)
    framework_logging._step_id.set(None)

    # Clear root logger handlers
    root = logging.getLogger()
    for handler in list(root.handlers):
        root.removeHandler(handler)


def test_json_format_logging():
    """JSON logs contain required base + context fields."""
    os.environ["LOG_FORMAT"] = "json"
    _reset_logging_state()

    from framework.logging import JSONFormatter

    log_capture = io.StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.setFormatter(JSONFormatter())

    logger = get_logger("test_logger")
    logger.logger.handlers.clear()
    logger.logger.addHandler(handler)

    set_logging_context(
        process_id="proc-123",
        actor_name="TestActor",
        step_id="step-456",
    )

    logger.info("Test message")

    log_output = log_capture.getvalue().strip()
    log_entry = json.loads(log_output)

    assert log_entry["level"] == "INFO"
    assert log_entry["message"] == "Test message"
    assert log_entry["process_id"] == "proc-123"
    assert log_entry["actor_name"] == "TestActor"
    assert log_entry["step_id"] == "step-456"
    assert "timestamp" in log_entry
    assert "logger" in log_entry

    del os.environ["LOG_FORMAT"]


def test_readable_format_logging():
    """Readable format is used when LOG_FORMAT is not json."""
    os.environ.pop("LOG_FORMAT", None)
    _reset_logging_state()

    log_capture = io.StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    )

    logger = get_logger("test_logger")
    logger.logger.handlers.clear()
    logger.logger.addHandler(handler)

    logger.info("Readable log message")

    output = log_capture.getvalue()

    assert "Readable log message" in output
    assert "INFO" in output
    assert "test_logger" in output


def test_context_is_dynamic_and_updates_without_recreating_logger():
    """
    Context changes must be reflected in logs
    without recreating the logger.
    """
    os.environ["LOG_FORMAT"] = "json"
    _reset_logging_state()

    from framework.logging import JSONFormatter

    log_capture = io.StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.setFormatter(JSONFormatter())

    logger = get_logger("test_logger")
    logger.logger.handlers.clear()
    logger.logger.addHandler(handler)

    set_logging_context(process_id="proc-789")
    logger.info("First message")

    set_logging_context(actor_name="ActorA", step_id="step-1")
    logger.info("Second message")

    lines = log_capture.getvalue().strip().splitlines()
    assert len(lines) == 2

    log1 = json.loads(lines[0])
    log2 = json.loads(lines[1])

    assert log1["process_id"] == "proc-789"
    assert log1["actor_name"] is None
    assert log1["step_id"] is None

    assert log2["process_id"] == "proc-789"
    assert log2["actor_name"] == "ActorA"
    assert log2["step_id"] == "step-1"

    del os.environ["LOG_FORMAT"]


def test_multiple_loggers_share_same_context():
    """
    All loggers must observe the same execution context.
    """
    os.environ["LOG_FORMAT"] = "json"
    _reset_logging_state()

    from framework.logging import JSONFormatter

    log_capture = io.StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.setFormatter(JSONFormatter())

    logger_a = get_logger("logger_a")
    logger_b = get_logger("logger_b")

    logger_a.logger.handlers.clear()
    logger_b.logger.handlers.clear()

    logger_a.logger.addHandler(handler)
    logger_b.logger.addHandler(handler)

    set_logging_context(process_id="proc-999", actor_name="SharedActor")

    logger_a.info("From A")
    logger_b.info("From B")

    lines = log_capture.getvalue().strip().splitlines()
    assert len(lines) == 2

    log_a = json.loads(lines[0])
    log_b = json.loads(lines[1])

    assert log_a["process_id"] == "proc-999"
    assert log_b["process_id"] == "proc-999"
    assert log_a["actor_name"] == "SharedActor"
    assert log_b["actor_name"] == "SharedActor"

    del os.environ["LOG_FORMAT"]


def test_probe_orchestrator_like_flow_context_leak():
    """
    Probe test to detect context leak when clearing actor/step context.
    After clearing with set_logging_context(actor_name=None, step_id=None),
    the next log should NOT contain stale actor/step data.
    """
    os.environ["LOG_FORMAT"] = "json"
    _reset_logging_state()

    from framework.logging import JSONFormatter

    buf = io.StringIO()
    handler = logging.StreamHandler(buf)
    handler.setFormatter(JSONFormatter())

    logger = get_logger("orchestrator")
    logger.logger.handlers.clear()
    logger.logger.addHandler(handler)

    # Step 1: Process started
    set_logging_context(process_id="proc-1")
    logger.info("Process started")

    # Step 2: Executing step with actor context
    set_logging_context(actor_name="ActorA", step_id="step-1")
    logger.info("Executing step")

    # Step 3: Clear actor/step context (between steps)
    set_logging_context(actor_name=None, step_id=None)
    logger.info("Evaluation result")

    lines = buf.getvalue().strip().splitlines()
    print("---- LOGS ----")
    for line in lines:
        print(json.loads(line))

    # Parse logs - only last log matters for leak detection
    log3 = json.loads(lines[2])

    # Verify context leak is fixed
    assert (
        log3["actor_name"] is None
    ), f"Context leak: actor_name should be None but got {log3['actor_name']}"
    assert (
        log3["step_id"] is None
    ), f"Context leak: step_id should be None but got {log3['step_id']}"
    assert log3["process_id"] == "proc-1", "process_id should still be set"

    del os.environ["LOG_FORMAT"]
