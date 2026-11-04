import uuid
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.models.incident import IncidentSeverity, IncidentStatus
from app.repositories import IncidentRepository
from app.schemas.common import BaseResponse
from app.schemas.incident import IncidentEventResponse, IncidentResponse
from app.agents.runtime import IncidentInvestigationExecutor, IncidentRemediationExecutor
from app.agents.schemas.investigation import IncidentInvestigationResponse
from app.agents.schemas.remediation import RemediationResponse
from app.agents.llm.exceptions import LLMConfigurationError
from app.repositories import CodePatchRepository
from app.schemas.code_patch import CodePatchResponse

router = APIRouter()


@router.get(
    "/incidents",
    response_model=BaseResponse[List[IncidentResponse]],
    summary="List Incidents",
    description="Retrieve paginated list of monitored incidents with optional status and severity filtering.",
)
def list_incidents(
    skip: int = Query(0, ge=0, description="Offset for pagination"),
    limit: int = Query(50, ge=1, le=100, description="Page size limit"),
    status: Optional[IncidentStatus] = Query(None, description="Filter by incident status"),
    severity: Optional[IncidentSeverity] = Query(None, description="Filter by incident severity"),
    project_id: Optional[uuid.UUID] = Query(None, description="Filter by project identifier"),
    db: Session = Depends(get_db),
) -> BaseResponse[List[IncidentResponse]]:
    """Query and return incidents ordered by detection timestamp descending."""
    incidents = IncidentRepository.list(
        db,
        skip=skip,
        limit=limit,
        status=status,
        severity=severity,
        project_id=project_id,
    )
    return BaseResponse(
        success=True,
        message="Incidents retrieved successfully",
        data=[IncidentResponse.model_validate(inc) for inc in incidents],
    )


@router.get(
    "/incidents/stats/summary",
    response_model=BaseResponse[Dict[str, int]],
    summary="Incident Metrics Summary",
    description="Returns aggregate counts of incidents grouped by lifecycle status.",
)
def get_incident_stats(
    db: Session = Depends(get_db),
) -> BaseResponse[Dict[str, int]]:
    """Return count statistics across all incident states."""
    total = IncidentRepository.count(db)
    open_count = IncidentRepository.count(db, status=IncidentStatus.OPEN)
    investigating = IncidentRepository.count(db, status=IncidentStatus.INVESTIGATING)
    awaiting_approval = IncidentRepository.count(db, status=IncidentStatus.AWAITING_APPROVAL)
    resolved = IncidentRepository.count(db, status=IncidentStatus.RESOLVED)

    return BaseResponse(
        success=True,
        message="Incident statistics retrieved successfully",
        data={
            "total": total,
            "open": open_count,
            "investigating": investigating,
            "awaiting_approval": awaiting_approval,
            "resolved": resolved,
        },
    )


@router.get(
    "/incidents/{incident_id}",
    response_model=BaseResponse[IncidentResponse],
    summary="Get Incident Detail",
    description="Retrieve a single incident by its unique identifier.",
)
def get_incident(
    incident_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> BaseResponse[IncidentResponse]:
    """Retrieve detailed incident record."""
    incident = IncidentRepository.get_by_id(db, incident_id)
    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident with ID '{incident_id}' not found",
        )
    return BaseResponse(
        success=True,
        message="Incident retrieved successfully",
        data=IncidentResponse.model_validate(incident),
    )


@router.get(
    "/incidents/{incident_id}/events",
    response_model=BaseResponse[List[IncidentEventResponse]],
    summary="List Incident Events",
    description="Retrieve chronological event log and message history for an incident.",
)
def list_incident_events(
    incident_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> BaseResponse[List[IncidentEventResponse]]:
    """Retrieve all event timeline items for an incident."""
    incident = IncidentRepository.get_by_id(db, incident_id)
    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident with ID '{incident_id}' not found",
        )
    events = IncidentRepository.list_events_by_incident(db, incident_id)
    return BaseResponse(
        success=True,
        message="Incident events retrieved successfully",
        data=[IncidentEventResponse.model_validate(ev) for ev in events],
    )


@router.post(
    "/incidents/{incident_id}/investigate",
    response_model=BaseResponse[IncidentInvestigationResponse],
    summary="Trigger Incident AI Investigation",
    description="Executes the LangGraph incident investigation workflow using the configured LLM provider.",
)
def trigger_incident_investigation(
    incident_id: uuid.UUID,
    provider: Optional[str] = Query(None, description="Optional LLM provider override ('gemini' or 'groq')"),
    model: Optional[str] = Query(None, description="Optional LLM model override"),
    db: Session = Depends(get_db),
) -> BaseResponse[IncidentInvestigationResponse]:
    """Execute AI investigation against an existing incident."""
    incident = IncidentRepository.get_by_id(db, incident_id)
    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident with ID '{incident_id}' not found",
        )

    try:
        investigation_response = IncidentInvestigationExecutor.execute(
            db=db,
            incident_id=incident_id,
            provider=provider,
            model=model,
        )
        return BaseResponse(
            success=True,
            message="Incident investigation completed successfully",
            data=investigation_response,
        )
    except LLMConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Investigation workflow failed: {str(exc)}",
        )


@router.post(
    "/incidents/{incident_id}/remediate",
    response_model=BaseResponse[RemediationResponse],
    summary="Trigger AI Remediation & Patch Generation",
    description="Evaluates remediation eligibility and generates a unified code patch.",
)
def trigger_incident_remediation(
    incident_id: uuid.UUID,
    provider: Optional[str] = Query(None, description="Optional LLM provider override ('gemini' or 'groq')"),
    model: Optional[str] = Query(None, description="Optional LLM model override"),
    db: Session = Depends(get_db),
) -> BaseResponse[RemediationResponse]:
    """Execute AI remediation planning and patch generation for an incident."""
    incident = IncidentRepository.get_by_id(db, incident_id)
    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident with ID '{incident_id}' not found",
        )

    try:
        remediation_response = IncidentRemediationExecutor.execute(
            db=db,
            incident_id=incident_id,
            provider=provider,
            model=model,
        )
        return BaseResponse(
            success=True,
            message="Incident remediation evaluation completed",
            data=remediation_response,
        )
    except LLMConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Remediation workflow failed: {str(exc)}",
        )


@router.get(
    "/incidents/{incident_id}/patches",
    response_model=BaseResponse[List[CodePatchResponse]],
    summary="List Incident Code Patches",
    description="Retrieve all proposed code patches generated for an incident.",
)
def list_incident_patches(
    incident_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> BaseResponse[List[CodePatchResponse]]:
    """List code patches for an incident ordered by creation timestamp descending."""
    incident = IncidentRepository.get_by_id(db, incident_id)
    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident with ID '{incident_id}' not found",
        )

    patches = CodePatchRepository.list_by_incident(db, incident_id)
    patch_responses = []
    for p in patches:
        resp = CodePatchResponse.model_validate(p)
        resp.is_hash_valid = CodePatchRepository.verify_patch_hash(p)
        patch_responses.append(resp)

    return BaseResponse(
        success=True,
        message="Incident code patches retrieved successfully",
        data=patch_responses,
    )



