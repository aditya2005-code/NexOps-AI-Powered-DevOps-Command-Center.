import uuid
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.models.incident import IncidentSeverity, IncidentStatus
from app.repositories import IncidentRepository
from app.schemas.common import BaseResponse
from app.schemas.incident import IncidentEventResponse, IncidentResponse

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

