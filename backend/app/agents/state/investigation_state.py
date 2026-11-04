from typing import Any, Dict, List, Optional, TypedDict


class InvestigationState(TypedDict, total=False):
    """LangGraph state representation for the incident investigation workflow."""

    # Core Identifiers & Incident Details
    incident_id: str
    project_id: Optional[str]
    incident_title: str
    incident_description: Optional[str]
    incident_severity: str
    incident_status: str
    incident_source: str

    # Project Context
    project_name: Optional[str]
    project_environment: Optional[str]

    # Chronological Event Timeline
    incident_events: List[Dict[str, Any]]

    # Formatted prompt context prepared by prepare_context node
    investigation_context: str

    # Structured Output from LLM
    investigation_result: Optional[Dict[str, Any]]

    # Workflow Execution Metadata
    execution_status: str
    errors: List[str]

