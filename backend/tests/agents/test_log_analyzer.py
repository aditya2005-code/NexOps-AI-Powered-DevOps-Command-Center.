from app.agents.tools.log_analyzer import LogAnalysisTool


def test_log_analyzer_empty_input():
    tool = LogAnalysisTool()
    output = tool.execute(log_text="")
    assert output.total_lines == 0
    assert output.error_count == 0
    assert "No log text provided" in output.warnings[0]


def test_log_analyzer_extracts_error_and_critical():
    tool = LogAnalysisTool()
    sample_logs = """
2026-11-04T10:15:00Z [INFO] Service startup initiated
2026-11-04T10:15:02Z [ERROR] ConnectionRefusedError: Failed to connect to Redis on 10.0.0.5:6379
2026-11-04T10:15:05Z [WARNING] Retrying Redis connection (attempt 1/3)
2026-11-04T10:15:10Z [CRITICAL] FatalException: Redis cluster quorum lost. Service halting.
"""
    output = tool.execute(log_text=sample_logs)

    assert output.total_lines == 5
    assert output.error_count == 1
    assert output.critical_count == 1
    assert output.warning_count == 1
    assert len(output.extracted_entries) == 2

    # Verify extracted entry details
    redis_err = output.extracted_entries[0]
    assert redis_err.level == "ERROR"
    assert redis_err.timestamp == "2026-11-04T10:15:02Z"
    assert "ConnectionRefusedError" in redis_err.message
    assert redis_err.exception_type == "ConnectionRefusedError"

    fatal_err = output.extracted_entries[1]
    assert fatal_err.level == "CRITICAL"
    assert fatal_err.timestamp == "2026-11-04T10:15:10Z"
    assert fatal_err.exception_type == "FatalException"

    assert "ConnectionRefusedError" in output.likely_exceptions
    assert "FatalException" in output.likely_exceptions


def test_log_analyzer_repeated_pattern_grouping():
    tool = LogAnalysisTool()
    repeated_logs = """
2026-11-04T11:00:01Z [ERROR] Timeout connecting to upstream server 192.168.1.10 for request req-a1b2c3d4-e5f6-7890-abcd-1234567890ef
2026-11-04T11:00:02Z [ERROR] Timeout connecting to upstream server 192.168.1.11 for request req-11223344-5566-7788-99aa-bbccddeeff00
2026-11-04T11:00:03Z [ERROR] Timeout connecting to upstream server 192.168.1.12 for request req-99887766-5544-3322-1100-ffeeddccbbaa
"""
    output = tool.execute(log_text=repeated_logs)

    assert output.error_count == 3
    assert len(output.repeated_patterns) == 1

    pattern = output.repeated_patterns[0]
    assert pattern.count == 3
    assert "<IP>" in pattern.pattern_template
    assert "<UUID>" in pattern.pattern_template
    assert pattern.first_timestamp == "2026-11-04T11:00:01Z"
    assert pattern.last_timestamp == "2026-11-04T11:00:03Z"


def test_log_analyzer_stack_trace_capture():
    tool = LogAnalysisTool()
    trace_log = """
2026-11-04T12:00:00Z [ERROR] Unhandled exception occurred:
Traceback (most recent call last):
  File "backend/app/api/checkout.py", line 42, in process_payment
    response = gateway.charge(amount)
  File "backend/app/gateway.py", line 15, in charge
    raise ConnectionResetError("Connection closed by peer")
ConnectionResetError: Connection closed by peer
"""
    output = tool.execute(log_text=trace_log)
    assert len(output.extracted_entries) >= 1
    entry = output.extracted_entries[0]
    assert entry.stack_trace is not None
    assert "process_payment" in entry.stack_trace
    assert "ConnectionResetError" in entry.stack_trace


def test_log_analyzer_oversized_input_truncation():
    tool = LogAnalysisTool()
    huge_log = "2026-11-04T12:00:00Z [ERROR] Repeated error message\n" * 15_000
    assert len(huge_log) > 500_000

    output = tool.execute(log_text=huge_log)
    assert any("Log text truncated" in w for w in output.warnings)
    assert output.error_count > 0


def test_log_analyzer_frequency_spike_detection():
    tool = LogAnalysisTool()
    # 1 error in first 20 minutes, 5 errors in last 2 minutes
    burst_logs = """
2026-11-04T10:00:00Z [ERROR] Database query timeout
2026-11-04T10:18:00Z [ERROR] Database query timeout
2026-11-04T10:19:00Z [ERROR] Database query timeout
2026-11-04T10:19:30Z [ERROR] Database query timeout
2026-11-04T10:20:00Z [ERROR] Database query timeout
"""
    output = tool.execute(log_text=burst_logs)
    assert output.frequency_spike_detected is True
    assert output.spike_details is not None

