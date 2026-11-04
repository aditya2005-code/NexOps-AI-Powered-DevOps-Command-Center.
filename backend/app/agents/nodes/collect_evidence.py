import re
from typing import Any, Dict, List
from app.agents.schemas.evidence import (
    EvidenceClassification,
    EvidenceItem,
    EvidenceReliability,
    EvidenceSource,
)
from app.agents.state import InvestigationState
from app.agents.tools import tool_registry


def collect_evidence_node(state: InvestigationState) -> Dict[str, Any]:
    """Node: Runs authorized diagnostic tools to gather structured, verifiable evidence."""
    events = state.get("incident_events", [])
    title = state.get("incident_title") or ""
    desc = state.get("incident_description") or ""
    workspace_path = state.get("project_workspace_path")
    plan = state.get("investigation_plan", {})

    collected_evidence: List[Dict[str, Any]] = []
    tool_runs: List[Dict[str, Any]] = []
    evidence_counter = 1

    # 1. Register incident description as an observed symptom evidence item if provided
    if desc.strip():
        ev_id = f"EV-{evidence_counter:03d}"
        evidence_counter += 1
        item = EvidenceItem(
            evidence_id=ev_id,
            source=EvidenceSource.INCIDENT_DESCRIPTION,
            description=f"Incident report for '{title}': {desc[:300]}",
            source_reference="incident_intake",
            classification=EvidenceClassification.OBSERVED_SYMPTOM,
            reliability=EvidenceReliability.VERIFIED,
        )
        collected_evidence.append(item.model_dump())

    # 2. Register incident timeline events as evidence items
    for ev in events[:5]:
        ev_desc = ev.get("description", "").strip()
        if ev_desc:
            ev_id = f"EV-{evidence_counter:03d}"
            evidence_counter += 1
            actor = ev.get("actor_identifier") or ev.get("actor_type") or "user"
            item = EvidenceItem(
                evidence_id=ev_id,
                source=EvidenceSource.INCIDENT_EVENT,
                description=f"Timeline event by {actor}: {ev_desc[:300]}",
                timestamp=ev.get("created_at"),
                source_reference=f"event:{ev.get('event_type', 'message')}",
                classification=EvidenceClassification.OBSERVED_SYMPTOM,
                reliability=EvidenceReliability.VERIFIED,
            )
            collected_evidence.append(item.model_dump())

    # 3. Gather all text for log analysis
    event_texts = [f"Event {ev.get('event_type')}: {ev.get('description', '')}" for ev in events]
    combined_log_text = f"Incident Title: {title}\nDescription: {desc}\n" + "\n".join(event_texts)

    # 4. Run Log Analysis Tool if planned
    if plan.get("run_log_analysis", True):
        log_res = tool_registry.execute(
            "log_analyzer",
            log_text=combined_log_text,
            service_name=state.get("project_name"),
        )
        tool_runs.append(log_res.model_dump())

        if log_res.success and log_res.data:
            data = log_res.data
            # Convert extracted entries into evidence items
            for entry in data.get("extracted_entries", []):
                ev_id = f"EV-{evidence_counter:03d}"
                evidence_counter += 1

                source = (
                    EvidenceSource.STACK_TRACE
                    if entry.get("stack_trace")
                    else EvidenceSource.LOG
                )
                classification = (
                    EvidenceClassification.STACK_TRACE
                    if entry.get("stack_trace")
                    else EvidenceClassification.ERROR_LOG
                )

                description = f"[{entry.get('level')}] {entry.get('message')}"
                if entry.get("stack_trace"):
                    description += f"\nStack trace:\n{entry.get('stack_trace')}"

                item = EvidenceItem(
                    evidence_id=ev_id,
                    source=source,
                    description=description[:500],
                    timestamp=entry.get("timestamp"),
                    source_reference=f"log:line_{entry.get('line_number')}",
                    classification=classification,
                    reliability=EvidenceReliability.VERIFIED,
                )
                collected_evidence.append(item.model_dump())

            # Convert repeated patterns into evidence items
            for pattern in data.get("repeated_patterns", []):
                if pattern.get("count", 0) > 1:
                    ev_id = f"EV-{evidence_counter:03d}"
                    evidence_counter += 1
                    item = EvidenceItem(
                        evidence_id=ev_id,
                        source=EvidenceSource.LOG,
                        description=(
                            f"Repeated error pattern occurred {pattern.get('count')} times: "
                            f"{pattern.get('sample_message')}"
                        ),
                        timestamp=pattern.get("first_timestamp"),
                        source_reference="log_pattern_cluster",
                        classification=EvidenceClassification.ERROR_LOG,
                        reliability=EvidenceReliability.VERIFIED,
                    )
                    collected_evidence.append(item.model_dump())

            # Check frequency spike
            if data.get("frequency_spike_detected"):
                ev_id = f"EV-{evidence_counter:03d}"
                evidence_counter += 1
                item = EvidenceItem(
                    evidence_id=ev_id,
                    source=EvidenceSource.TELEMETRY,
                    description=f"Error frequency spike detected: {data.get('spike_details')}",
                    source_reference="log_analyzer_spike_detection",
                    classification=EvidenceClassification.METRIC_ANOMALY,
                    reliability=EvidenceReliability.VERIFIED,
                )
                collected_evidence.append(item.model_dump())

    # 5. Run Source Code Inspection if workspace is configured
    if workspace_path and plan.get("run_source_inspection", True):
        # Look for search candidates from log exceptions or words in title
        search_terms: List[str] = []
        if tool_runs and tool_runs[0].get("data"):
            search_terms.extend(tool_runs[0]["data"].get("likely_exceptions", []))

        # Also extract file paths mentioned in descriptions or stack traces
        file_matches = re.findall(r'File ["\']([a-zA-Z0-9_/\\.-]+)["\']', combined_log_text)
        for rel_file in file_matches[:2]:
            read_res = tool_registry.execute(
                "source_inspector",
                operation="read_file",
                workspace_path=workspace_path,
                relative_path=rel_file,
                max_lines=50,
            )
            tool_runs.append(read_res.model_dump())
            if read_res.success and read_res.data and read_res.data.get("status") == "success":
                ev_id = f"EV-{evidence_counter:03d}"
                evidence_counter += 1
                item = EvidenceItem(
                    evidence_id=ev_id,
                    source=EvidenceSource.SOURCE_CODE,
                    description=f"Source inspection of {rel_file}:\n{read_res.data.get('content')}",
                    source_reference=rel_file,
                    classification=EvidenceClassification.CODE_DEFECT,
                    reliability=EvidenceReliability.VERIFIED,
                )
                collected_evidence.append(item.model_dump())

        # If we have exceptions, search code for their occurrence
        for term in search_terms[:2]:
            search_res = tool_registry.execute(
                "source_inspector",
                operation="search_code",
                workspace_path=workspace_path,
                query=term,
            )
            tool_runs.append(search_res.model_dump())
            if search_res.success and search_res.data and search_res.data.get("matches"):
                ev_id = f"EV-{evidence_counter:03d}"
                evidence_counter += 1
                matches_str = "; ".join(
                    f"{m['file_path']}:{m['line_number']} -> {m['line_content']}"
                    for m in search_res.data["matches"][:3]
                )
                item = EvidenceItem(
                    evidence_id=ev_id,
                    source=EvidenceSource.SOURCE_CODE,
                    description=f"Code reference search for '{term}': {matches_str}",
                    source_reference=search_res.data["matches"][0]["file_path"],
                    classification=EvidenceClassification.CODE_DEFECT,
                    reliability=EvidenceReliability.PROBABLE,
                )
                collected_evidence.append(item.model_dump())

    # 6. Fallback if no specific evidence was found at all
    if not collected_evidence:
        ev_id = f"EV-{evidence_counter:03d}"
        fallback_item = EvidenceItem(
            evidence_id=ev_id,
            source=EvidenceSource.INCIDENT_DESCRIPTION,
            description=f"Reported incident title: {title}. Description: {desc or 'None'}",
            source_reference="incident_intake",
            classification=EvidenceClassification.OBSERVED_SYMPTOM,
            reliability=EvidenceReliability.INCONCLUSIVE,
        )
        collected_evidence.append(fallback_item.model_dump())

    return {
        "collected_evidence": collected_evidence,
        "tool_execution_results": tool_runs,
    }
