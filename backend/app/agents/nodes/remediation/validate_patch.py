from typing import Any, Dict
from app.agents.remediation.diff_validator import DiffValidator
from app.agents.state.remediation_state import RemediationState


def validate_unified_diff_node(state: RemediationState) -> Dict[str, Any]:
    """Node: Syntactically and operationally validates the proposed unified Git diff."""
    proposed_patch = state.get("proposed_patch")
    if not proposed_patch:
        return {"validation_result": None}

    diff_content = proposed_patch.get("diff_content", "")
    target_files = state.get("target_files", [])

    source_context = state.get("source_context", [])
    source_snapshots = {
        sc["file_path"].replace("\\", "/").lstrip("/"): sc.get("content", "")
        for sc in source_context
        if "file_path" in sc
    }

    validation = DiffValidator.validate(
        diff_content=diff_content,
        authorized_files=target_files,
        source_snapshots=source_snapshots if source_snapshots else None,
    )

    existing_errors = list(state.get("errors", []))
    if not validation.is_valid:
        existing_errors.extend(validation.validation_errors)
        return {
            "validation_result": validation.model_dump(),
            "errors": existing_errors,
            "execution_status": "failed",
        }

    return {
        "validation_result": validation.model_dump(),
    }

