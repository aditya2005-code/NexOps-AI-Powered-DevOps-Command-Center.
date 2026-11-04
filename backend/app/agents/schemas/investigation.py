import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.agents.schemas.evidence import EvidenceItem, RootCauseHypothesis


class InvestigationResult(BaseModel):
    """Structured, grounded investigation output produced by the AI Agent."""
    incident_summary: str = Field(
        ...,
        description="Concise summary of the incident grounded strictly in the provided report",
    )
    observed_facts: List[str] = Field(
        default_factory=list,
        description="Concrete facts, error messages, and telemetry indicators directly observed in the incident data",
    )
    hypotheses: List[str] = Field(
        default_factory=list,
        description="Probable root cause hypotheses deduced by the model, clearly separated from observed facts",
    )
    supporting_evidence: List[str] = Field(
        default_factory=list,
        description="Specific observed facts, timestamps, or errors that substantiate the hypotheses",
    )
    confidence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score between 0.0 and 1.0 reflecting evidence sufficiency (lower when data is sparse)",
    )
    recommended_diagnostic_steps: List[str] = Field(
        default_factory=list,
        description="Read-only diagnostic steps or metric queries an engineer should execute to confirm the root cause",
    )
    recommended_next_actions: List[str] = Field(
        default_factory=list,
        description="Immediate operator triage or remediation recommendations",
    )
    missing_information: List[str] = Field(
        default_factory=list,
        description="Crucial context, logs, traces, or system telemetry that were absent from the report",
    )
    # Phase 5.2 Structured Evidence & Hypotheses
    evidence_items: List[EvidenceItem] = Field(
        default_factory=list,
        description="Correlated technical evidence records with IDs and source references",
    )
    structured_hypotheses: List[RootCauseHypothesis] = Field(
        default_factory=list,
        description="Hypotheses with explicit supporting evidence references and confidence ratings",
    )
    insufficient_evidence: bool = Field(
        default=False,
        description="True if evidence is insufficient to determine a dependable root cause",
    )
    diagnostic_summary: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Metadata on diagnostic tools executed during investigation",
    )

    model_config = ConfigDict(from_attributes=True)


class IncidentInvestigationResponse(BaseModel):
    """API response model for an incident investigation execution."""
    incident_id: uuid.UUID
    execution_id: uuid.UUID
    provider: str
    model: str
    investigation: InvestigationResult
    execution_status: str
    duration_seconds: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

