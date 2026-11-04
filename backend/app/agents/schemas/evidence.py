from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class EvidenceSource(str, Enum):
    LOG = "log"
    STACK_TRACE = "stack_trace"
    SOURCE_CODE = "source_code"
    INCIDENT_DESCRIPTION = "incident_description"
    INCIDENT_EVENT = "incident_event"
    TELEMETRY = "telemetry"
    DIAGNOSTIC_TOOL = "diagnostic_tool"


class EvidenceClassification(str, Enum):
    ERROR_LOG = "error_log"
    STACK_TRACE = "stack_trace"
    CODE_DEFECT = "code_defect"
    CONFIGURATION_ANOMALY = "configuration_anomaly"
    OBSERVED_SYMPTOM = "observed_symptom"
    METRIC_ANOMALY = "metric_anomaly"


class EvidenceReliability(str, Enum):
    VERIFIED = "verified"
    PROBABLE = "probable"
    INCONCLUSIVE = "inconclusive"


class EvidenceItem(BaseModel):
    """Structured evidence element correlating an observed technical fact to its origin."""
    evidence_id: str = Field(..., description="Unique evidence identifier, e.g. EV-001")
    source: EvidenceSource = Field(..., description="Category of technical origin")
    description: str = Field(..., description="Specific, observable technical fact or pattern")
    timestamp: Optional[str] = Field(None, description="ISO-8601 or event timestamp if available")
    source_reference: Optional[str] = Field(
        None, description="File path, event identifier, or log line range"
    )
    classification: EvidenceClassification = Field(..., description="Classification category")
    reliability: EvidenceReliability = Field(
        default=EvidenceReliability.PROBABLE,
        description="Validation status based on corroborating data",
    )

    model_config = ConfigDict(from_attributes=True)


class RootCauseHypothesis(BaseModel):
    """Ranked technical explanation linked explicitly to supporting evidence items."""
    hypothesis_id: str = Field(..., description="Hypothesis identifier, e.g. HYP-001")
    root_cause_title: str = Field(..., description="Concise title of the suspected failure mechanism")
    technical_explanation: str = Field(..., description="In-depth causal explanation of the defect or outage")
    supporting_evidence_ids: List[str] = Field(
        default_factory=list,
        description="List of EvidenceItem IDs directly substantiating this hypothesis",
    )
    contradicting_evidence_ids: List[str] = Field(
        default_factory=list,
        description="List of EvidenceItem IDs that weaken or contradict this hypothesis",
    )
    confidence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Grounded confidence score calculated from evidence quantity and reliability",
    )
    recommended_verification_steps: List[str] = Field(
        default_factory=list,
        description="Targeted diagnostic actions to prove or disprove this hypothesis",
    )

    model_config = ConfigDict(from_attributes=True)

