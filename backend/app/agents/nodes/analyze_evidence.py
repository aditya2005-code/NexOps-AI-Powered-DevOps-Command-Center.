from typing import Any, Dict, List
from app.agents.state import InvestigationState


def analyze_evidence_node(state: InvestigationState) -> Dict[str, Any]:
    """Node: Correlates collected evidence items and prepares prompt context with explicit evidence IDs."""
    evidence_list = state.get("collected_evidence", [])
    existing_context = state.get("investigation_context", "")

    # Group evidence by classification
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for ev in evidence_list:
        cls_name = ev.get("classification", "other")
        grouped.setdefault(cls_name, []).append(ev)

    evidence_lines: List[str] = [
        "--- CORRELATED EVIDENCE ITEMS (USE THESE IDS AS SUPPORTING EVIDENCE) ---"
    ]

    for ev in evidence_list:
        ev_id = ev.get("evidence_id")
        src = ev.get("source")
        cls_ = ev.get("classification")
        rel = ev.get("reliability")
        desc = ev.get("description", "").replace("\n", " ")[:200]
        ref = ev.get("source_reference") or "unknown"
        ts = f" at {ev.get('timestamp')}" if ev.get("timestamp") else ""
        evidence_lines.append(
            f"- [{ev_id}] ({src}/{cls_}, {rel}{ts}) Ref: {ref} -> {desc}"
        )

    evidence_block = "\n".join(evidence_lines)

    enhanced_context = f"{existing_context}\n\n{evidence_block}\n\n" + (
        "CRITICAL: When generating hypotheses, you MUST reference the specific evidence IDs "
        "(e.g. EV-001, EV-002) in supporting_evidence_ids that prove your hypothesis."
    )

    analysis_summary = {
        "total_evidence_items": len(evidence_list),
        "classifications": {k: len(v) for k, v in grouped.items()},
        "has_verified_evidence": any(ev.get("reliability") == "verified" for ev in evidence_list),
    }

    return {
        "evidence_analysis": analysis_summary,
        "investigation_context": enhanced_context,
    }

