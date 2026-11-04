from typing import Any, Dict
from app.agents.prompts import format_investigation_prompt
from app.agents.state import InvestigationState


def prepare_context_node(state: InvestigationState) -> Dict[str, Any]:
    """Node: Formats bounded incident and timeline metadata into analysis context."""
    events = state.get("incident_events", [])
    events_lines = []
    for ev in events[:20]:  # Cap at 20 events to avoid unbounded prompt growth
        actor = ev.get("actor_identifier") or ev.get("actor_type") or "system"
        ev_type = ev.get("event_type", "event")
        desc = ev.get("description", "")
        created = ev.get("created_at", "")
        events_lines.append(f"[{created}] ({ev_type}) by {actor}: {desc}")

    events_text = "\n".join(events_lines)

    context = format_investigation_prompt(
        incident_title=state.get("incident_title", "Untitled Incident"),
        incident_severity=state.get("incident_severity", "MEDIUM"),
        incident_status=state.get("incident_status", "OPEN"),
        incident_source=state.get("incident_source", "unknown"),
        incident_description=state.get("incident_description") or "",
        project_name=state.get("project_name") or "Unassigned Project",
        project_environment=state.get("project_environment") or "unknown",
        events_text=events_text,
    )

    return {"investigation_context": context}

