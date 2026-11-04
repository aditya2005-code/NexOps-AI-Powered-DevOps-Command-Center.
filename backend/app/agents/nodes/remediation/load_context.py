from typing import Any, Dict
from app.agents.state.remediation_state import RemediationState
from app.core.config import settings


def load_remediation_context_node(state: RemediationState) -> Dict[str, Any]:
    """Node: Resolves project workspace and extracts investigation context."""
    project_identifier = state.get("project_name") or state.get("project_id")
    workspace = settings.get_project_workspace_path(project_identifier)
    workspace_str = str(workspace) if workspace else state.get("project_workspace_path")

    return {
        "project_workspace_path": workspace_str,
        "errors": list(state.get("errors", [])),
    }

