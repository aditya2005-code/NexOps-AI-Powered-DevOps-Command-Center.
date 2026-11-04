import logging
from typing import Any, Dict, List
from app.agents.schemas.investigation import InvestigationResult
from app.agents.schemas.evidence import EvidenceItem, RootCauseHypothesis
from app.agents.state import InvestigationState

logger = logging.getLogger("nexops.agents.nodes.validate")


def validate_and_format_node(state: InvestigationState) -> Dict[str, Any]:
    """Node: Synthesizes structured evidence, hypotheses, and diagnostic summaries into final result."""
    raw_result = state.get("investigation_result") or {}
    errors = list(state.get("errors", []))
    collected_ev = state.get("collected_evidence", [])
    ranked_hypotheses = state.get("hypotheses", [])
    validation_res = state.get("validation_results", {})
    tool_runs = state.get("tool_execution_results", [])

    is_insufficient = validation_res.get("insufficient_evidence", False)

    # Convert collected evidence to EvidenceItem models
    evidence_models: List[EvidenceItem] = []
    for ev in collected_ev:
        try:
            evidence_models.append(EvidenceItem.model_validate(ev))
        except Exception:
            pass

    # Convert ranked hypotheses to RootCauseHypothesis models
    hypothesis_models: List[RootCauseHypothesis] = []
    for hyp in ranked_hypotheses:
        try:
            hypothesis_models.append(RootCauseHypothesis.model_validate(hyp))
        except Exception:
            pass

    # Overall confidence is highest hypothesis confidence or default
    overall_confidence = (
        hypothesis_models[0].confidence_score
        if hypothesis_models
        else float(raw_result.get("confidence_score", 0.0))
    )

    # Diagnostic execution summary
    diagnostic_summary = {
        "tools_executed": [tr.get("tool_name") for tr in tool_runs],
        "tool_runs_count": len(tool_runs),
        "evidence_count": len(evidence_models),
        "hypotheses_count": len(hypothesis_models),
        "workspace_path": state.get("project_workspace_path"),
    }

    if state.get("execution_status") == "failed" or not raw_result:
        fallback_msg = errors[-1] if errors else "Investigation could not be completed."
        fallback = InvestigationResult(
            incident_summary=f"Automated investigation failed for incident {state.get('incident_id', 'unknown')}.",
            observed_facts=[state.get("incident_title", "Unknown incident")],
            hypotheses=["Unable to generate root cause hypotheses due to execution failure."],
            supporting_evidence=[],
            confidence_score=0.0,
            recommended_diagnostic_steps=["Inspect LLM logs and backend connectivity."],
            recommended_next_actions=["Perform manual triage on the incident."],
            missing_information=[fallback_msg],
            evidence_items=evidence_models,
            structured_hypotheses=hypothesis_models,
            insufficient_evidence=True,
            diagnostic_summary=diagnostic_summary,
        )
        return {
            "investigation_result": fallback.model_dump(),
            "execution_status": "failed",
            "errors": errors or [fallback_msg],
        }

    try:
        # Build backwards-compatible strings for hypotheses and supporting evidence
        hyp_strings = [
            f"{h.root_cause_title}: {h.technical_explanation}"
            if h.technical_explanation and h.technical_explanation != h.root_cause_title
            else h.root_cause_title
            for h in hypothesis_models
        ] or raw_result.get("hypotheses", [])

        sup_strings = [
            f"[{ev.evidence_id}] {ev.description}"
            for ev in evidence_models[:5]
        ] or raw_result.get("supporting_evidence", [])

        # If evidence was insufficient, explicitly record that
        missing_info = list(raw_result.get("missing_information", []))
        if is_insufficient and "Sufficient diagnostic logs or stack traces to verify root cause" not in missing_info:
            missing_info.append("Sufficient diagnostic logs or stack traces to verify root cause")

        summary = raw_result.get("incident_summary") or f"Investigation of {state.get('incident_title')}"
        if is_insufficient:
            summary += " (Notice: Technical evidence is currently insufficient to determine a verified root cause)."

        validated = InvestigationResult(
            incident_summary=summary,
            observed_facts=raw_result.get("observed_facts", [state.get("incident_title", "Incident")]),
            hypotheses=hyp_strings,
            supporting_evidence=sup_strings,
            confidence_score=overall_confidence,
            recommended_diagnostic_steps=raw_result.get("recommended_diagnostic_steps", []),
            recommended_next_actions=raw_result.get("recommended_next_actions", []),
            missing_information=missing_info,
            evidence_items=evidence_models,
            structured_hypotheses=hypothesis_models,
            insufficient_evidence=is_insufficient,
            diagnostic_summary=diagnostic_summary,
        )

        return {
            "investigation_result": validated.model_dump(),
            "execution_status": "completed",
        }
    except Exception as exc:
        err = f"Validation failed for investigation result: {str(exc)}"
        logger.warning(err)
        errors.append(err)
        return {
            "errors": errors,
            "execution_status": "failed",
        }
