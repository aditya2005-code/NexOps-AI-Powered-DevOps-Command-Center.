from typing import Any, Dict, List
from app.agents.schemas.remediation import RemediationPlan
from app.agents.state.remediation_state import RemediationState


def construct_remediation_plan_node(state: RemediationState) -> Dict[str, Any]:
    """Node: Synthesizes investigation evidence into a formal, structured remediation plan."""
    eligibility = state.get("eligibility", {})
    if eligibility.get("status") != "eligible":
        return {"remediation_plan": None}

    inv = state.get("investigation_result", {})
    target_files = state.get("target_files", [])

    # Extract primary hypothesis
    raw_hypotheses = inv.get("structured_hypotheses", []) or inv.get("hypotheses", [])
    if raw_hypotheses and isinstance(raw_hypotheses[0], dict):
        selected_hyp = raw_hypotheses[0].get("root_cause_title", "Unspecified Root Cause")
        tech_explanation = raw_hypotheses[0].get("technical_explanation", selected_hyp)
        supporting_ev_ids = raw_hypotheses[0].get("supporting_evidence_ids", [])
        rec_steps = raw_hypotheses[0].get("recommended_verification_steps", [])
    elif raw_hypotheses:
        selected_hyp = str(raw_hypotheses[0])
        tech_explanation = selected_hyp
        supporting_ev_ids = [
            ev.get("evidence_id")
            for ev in inv.get("evidence_items", [])
            if ev.get("evidence_id")
        ][:2]
        rec_steps = inv.get("recommended_diagnostic_steps", [])[:2]
    else:
        selected_hyp = "Software bug identified in investigation"
        tech_explanation = selected_hyp
        supporting_ev_ids = []
        rec_steps = []

    plan = RemediationPlan(
        incident_id=state.get("incident_id", ""),
        investigation_execution_id=state.get("investigation_execution_id"),
        selected_hypothesis=selected_hyp,
        supporting_evidence_ids=supporting_ev_ids,
        proposed_remediation=f"Apply targeted code fix in {', '.join(target_files)} to address {selected_hyp}",
        expected_behavior_change="Eliminate exceptions, restore valid response handling, and prevent service degradation",
        files_affected=target_files,
        technical_rationale=tech_explanation,
        risks=["Regression in dependent callers", "Subtle logic changes under high load"],
        assumptions=["Target files can be compiled/executed cleanly", "Unit tests cover surrounding logic"],
        verification_requirements=rec_steps or ["Execute project test suite", "Verify error rate returns to zero"],
    )

    return {"remediation_plan": plan.model_dump()}

