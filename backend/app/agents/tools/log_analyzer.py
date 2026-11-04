import re
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.agents.tools.base import BaseDiagnosticTool

MAX_LOG_CHARS = 500_000
MAX_OUTPUT_ENTRIES = 50
MAX_OUTPUT_PATTERNS = 10

ISO_TIMESTAMP_REGEX = re.compile(
    r"\b(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)\b"
)
SYSLOG_TIMESTAMP_REGEX = re.compile(
    r"\b((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\b"
)
LOG_LEVEL_REGEX = re.compile(r"\b(CRITICAL|FATAL|ERROR|SEVERE|WARNING|WARN)\b", re.IGNORECASE)
EXCEPTION_REGEX = re.compile(r"\b([A-Z][A-Za-z0-9_]*(?:Error|Exception|Fault|Failure))\b")
HTTP_STATUS_REGEX = re.compile(r"\b(50[0-9]|40[0-9]|502 Bad Gateway|504 Gateway Timeout|500 Internal Server Error)\b")


class ExtractedLogEntry(BaseModel):
    entry_id: str
    line_number: int
    level: str
    timestamp: Optional[str] = None
    message: str
    exception_type: Optional[str] = None
    stack_trace: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class RepeatedErrorPattern(BaseModel):
    pattern_template: str
    count: int
    sample_message: str
    first_timestamp: Optional[str] = None
    last_timestamp: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class LogAnalysisInput(BaseModel):
    log_text: str = Field(..., description="Raw text of logs to analyze")
    service_name: Optional[str] = Field(None, description="Optional service or component name")
    max_results: int = Field(default=MAX_OUTPUT_ENTRIES, le=MAX_OUTPUT_ENTRIES)


class LogAnalysisOutput(BaseModel):
    total_lines: int
    error_count: int
    critical_count: int
    warning_count: int
    extracted_entries: List[ExtractedLogEntry]
    repeated_patterns: List[RepeatedErrorPattern]
    likely_exceptions: List[str]
    frequency_spike_detected: bool
    spike_details: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class LogAnalysisTool(BaseDiagnosticTool):
    """Deterministic, bounded log analyzer for extracting errors, stack traces, and patterns."""

    name = "log_analyzer"
    description = (
        "Analyzes supplied log text to extract ERROR and CRITICAL entries, stack traces, "
        "repeated patterns, and detect frequency spikes without executing code."
    )
    input_schema = LogAnalysisInput
    output_schema = LogAnalysisOutput

    def execute(self, **kwargs) -> LogAnalysisOutput:
        raw_text = kwargs.get("log_text", "")
        max_results = min(kwargs.get("max_results", MAX_OUTPUT_ENTRIES), MAX_OUTPUT_ENTRIES)
        warnings: List[str] = []

        if not raw_text or not raw_text.strip():
            return LogAnalysisOutput(
                total_lines=0,
                error_count=0,
                critical_count=0,
                warning_count=0,
                extracted_entries=[],
                repeated_patterns=[],
                likely_exceptions=[],
                frequency_spike_detected=False,
                warnings=["No log text provided to analyze."],
            )

        if len(raw_text) > MAX_LOG_CHARS:
            warnings.append(
                f"Log text truncated from {len(raw_text)} chars to {MAX_LOG_CHARS} chars."
            )
            raw_text = raw_text[:MAX_LOG_CHARS]

        lines = raw_text.splitlines()
        total_lines = len(lines)

        extracted_entries: List[ExtractedLogEntry] = []
        timestamps: List[datetime] = []
        pattern_map: dict[str, list[ExtractedLogEntry]] = {}
        likely_exceptions_set: set[str] = set()

        error_count = 0
        critical_count = 0
        warning_count = 0

        current_entry: Optional[ExtractedLogEntry] = None
        current_trace_lines: list[str] = []

        for idx, line in enumerate(lines, start=1):
            stripped = line.strip()
            if not stripped:
                continue

            # Check if this line is a continuation of a stack trace
            is_trace_line = (
                line.startswith(" ")
                or line.startswith("\t")
                or "Traceback (" in line
                or "at " in line
                or 'File "' in line
                or "Caused by:" in line
            )

            if is_trace_line and current_entry is not None:
                current_trace_lines.append(stripped)
                continue

            # If we were accumulating a stack trace, finalize it
            if current_entry and current_trace_lines:
                current_entry.stack_trace = "\n".join(current_trace_lines[:30])
                current_trace_lines = []
                current_entry = None

            # Detect log level
            level_match = LOG_LEVEL_REGEX.search(stripped)
            level = level_match.group(1).upper() if level_match else None

            # Detect timestamp
            ts_str = None
            ts_dt = None
            iso_match = ISO_TIMESTAMP_REGEX.search(stripped)
            if iso_match:
                ts_str = iso_match.group(1)
                try:
                    ts_dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                except Exception:
                    pass
            else:
                syslog_match = SYSLOG_TIMESTAMP_REGEX.search(stripped)
                if syslog_match:
                    ts_str = syslog_match.group(1)

            if ts_dt:
                timestamps.append(ts_dt)

            if level in ("CRITICAL", "FATAL"):
                critical_count += 1
            elif level in ("ERROR", "SEVERE"):
                error_count += 1
            elif level in ("WARNING", "WARN"):
                warning_count += 1

            # Detect exception or HTTP status
            exc_match = EXCEPTION_REGEX.search(stripped)
            http_match = HTTP_STATUS_REGEX.search(stripped)
            exc_type = None
            if exc_match:
                exc_type = exc_match.group(1)
                likely_exceptions_set.add(exc_type)
            elif http_match:
                exc_type = f"HTTP_{http_match.group(1)}"
                likely_exceptions_set.add(exc_type)

            # Record entry if it is ERROR, CRITICAL, or contains an exception
            if level in ("CRITICAL", "FATAL", "ERROR", "SEVERE") or exc_type:
                entry = ExtractedLogEntry(
                    entry_id=f"LOG-{len(extracted_entries) + 1:03d}",
                    line_number=idx,
                    level=level or "ERROR",
                    timestamp=ts_str,
                    message=stripped[:300],
                    exception_type=exc_type,
                )
                current_entry = entry
                current_trace_lines = []

                if len(extracted_entries) < max_results:
                    extracted_entries.append(entry)

                # Cluster into patterns by normalizing dynamic identifiers
                normalized = self._normalize_message(stripped)
                pattern_map.setdefault(normalized, []).append(entry)

        # Flush trailing stack trace
        if current_entry and current_trace_lines:
            current_entry.stack_trace = "\n".join(current_trace_lines[:30])

        # Form repeated patterns list
        sorted_patterns = sorted(pattern_map.items(), key=lambda item: len(item[1]), reverse=True)
        repeated_patterns: List[RepeatedErrorPattern] = []
        for template, entries in sorted_patterns[:MAX_OUTPUT_PATTERNS]:
            repeated_patterns.append(
                RepeatedErrorPattern(
                    pattern_template=template[:200],
                    count=len(entries),
                    sample_message=entries[0].message,
                    first_timestamp=entries[0].timestamp,
                    last_timestamp=entries[-1].timestamp,
                )
            )

        # Detect frequency spikes if >= 4 timestamps found
        spike_detected, spike_details = self._detect_spike(timestamps)

        return LogAnalysisOutput(
            total_lines=total_lines,
            error_count=error_count,
            critical_count=critical_count,
            warning_count=warning_count,
            extracted_entries=extracted_entries,
            repeated_patterns=repeated_patterns,
            likely_exceptions=sorted(list(likely_exceptions_set)),
            frequency_spike_detected=spike_detected,
            spike_details=spike_details,
            warnings=warnings,
        )

    def _normalize_message(self, message: str) -> str:
        """Strip dynamic parts (UUIDs, IPs, numbers, dates) for pattern clustering."""
        msg = ISO_TIMESTAMP_REGEX.sub("<TIMESTAMP>", message)
        msg = re.sub(r"\b[0-9a-fA-F-]{36}\b", "<UUID>", msg)
        msg = re.sub(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(?::\d+)?\b", "<IP>", msg)
        msg = re.sub(r"\b0x[0-9a-fA-F]+\b", "<HEX>", msg)
        msg = re.sub(r"\b\d+\b", "<NUM>", msg)
        return msg.strip()

    def _detect_spike(self, timestamps: List[datetime]) -> tuple[bool, Optional[str]]:
        """Detect sudden frequency increase in error timestamps."""
        if len(timestamps) < 4:
            return False, None
        try:
            sorted_ts = sorted(timestamps)
            total_duration = (sorted_ts[-1] - sorted_ts[0]).total_seconds()
            if total_duration <= 0:
                return True, f"All {len(timestamps)} errors occurred in the exact same second."
            # Compare first half error rate with second half error rate
            midpoint = sorted_ts[0] + (sorted_ts[-1] - sorted_ts[0]) / 2
            first_half = sum(1 for t in sorted_ts if t <= midpoint)
            second_half = sum(1 for t in sorted_ts if t > midpoint)
            if second_half >= 3 * max(first_half, 1):
                return True, (
                    f"Error frequency increased significantly: {second_half} in 2nd half vs "
                    f"{first_half} in 1st half."
                )
        except Exception:
            pass
        return False, None

