from typing import Any, Dict
from app.agents.state import InvestigationState


def build_investigation_plan_node(state: InvestigationState) -> Dict[str, Any]:
    """Node: Formulates a structured diagnostic plan based on incident inputs and resources."""
    events = state.get("incident_events", [])
    desc = state.get("incident_description") or ""
    title = state.get("incident_title") or ""
    has_workspace = bool(state.get("project_workspace_path"))

    # Check if any event or description appears to contain log or error traces
    combined_text = f"{title}\n{desc}\n" + "\n".join(
        ev.get("description", "") for ev in events
    )
    has_log_content = any(
        kw in combined_text.upper()
        for kw in ("ERROR", "EXCEPTION", "TRACEBACK", "FAILED", "CRITICAL", "WARN", "502", "500", "504")
    ) or len(combined_text.strip()) > 30

    plan: Dict[str, Any] = {
        "run_log_analysis": has_log_content,
        "run_source_inspection": has_workspace,
        "workspace_available": has_workspace,
        "planned_actions": [],
    }

    if has_log_content:
        plan["planned_actions"].append("Extract error logs, stack traces, and repeated patterns via log_analyzer")
    else:
        plan["planned_actions"].append("No explicit log indicators detected in incident events")

    if has_workspace:
        plan["planned_actions"].append("Search configured project workspace for identified symbols or stack references")
    else:
        plan["planned_actions"].append("Project workspace inspection unavailable (not configured or unmapped)")

    return {"investigation_plan": plan}

