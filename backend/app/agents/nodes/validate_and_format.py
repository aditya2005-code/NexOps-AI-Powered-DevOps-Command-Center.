import logging
from typing import Any, Dict
from app.agents.schemas.investigation import InvestigationResult
from app.agents.state import InvestigationState

logger = logging.getLogger("nexops.agents.nodes.validate")


def validate_and_format_node(state: InvestigationState) -> Dict[str, Any]:
    """Node: Validates structured output and formats final output state."""
    raw_result = state.get("investigation_result")
    errors = list(state.get("errors", []))

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
        )
        return {
            "investigation_result": fallback.model_dump(),
            "execution_status": "failed",
            "errors": errors or [fallback_msg],
        }

    try:
        validated = InvestigationResult.model_validate(raw_result)
        return {
            "investigation_result": validated.model_dump(),
            "execution_status": "completed",
        }
    except Exception as exc:
        err = f"Validation failed for LLM output: {str(exc)}"
        logger.warning(err)
        errors.append(err)
        return {
            "errors": errors,
            "execution_status": "failed",
        }

