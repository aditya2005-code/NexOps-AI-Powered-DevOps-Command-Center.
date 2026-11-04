from typing import Any, Dict
from app.agents.remediation.risk_evaluator import PatchRiskEvaluator
from app.agents.schemas.remediation import PatchValidationResult, ProposedPatch
from app.agents.state.remediation_state import RemediationState


def evaluate_patch_risk_node(state: RemediationState) -> Dict[str, Any]:
    """Node: Computes operational stability and regression risk for the validated patch."""
    proposed_patch = state.get("proposed_patch")
    val_data = state.get("validation_result")

    if not proposed_patch or not val_data:
        return {"risk_assessment": None}

    try:
        patch_obj = ProposedPatch.model_validate(proposed_patch)
        val_obj = PatchValidationResult.model_validate(val_data)
        assessment = PatchRiskEvaluator.evaluate(patch_obj, val_obj)
        return {"risk_assessment": assessment.model_dump()}
    except Exception as exc:
        return {
            "risk_assessment": None,
            "errors": list(state.get("errors", [])) + [f"Risk evaluation error: {str(exc)}"],
        }

