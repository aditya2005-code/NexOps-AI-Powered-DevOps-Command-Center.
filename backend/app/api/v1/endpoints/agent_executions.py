import uuid
from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.repositories import AgentExecutionRepository
from app.schemas.agent_execution import AgentExecutionResponse
from app.schemas.common import BaseResponse

router = APIRouter()


def _sanitize_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Remove any sensitive credential keys from payload before exposure."""
    sanitized = dict(payload)
    sensitive_keys = {"api_key", "token", "secret", "password", "key", "authorization"}
    for k in list(sanitized.keys()):
        if any(sk in k.lower() for sk in sensitive_keys):
            sanitized[k] = "*** redacted ***"
    return sanitized


@router.get(
    "/agent-executions/{execution_id}",
    response_model=BaseResponse[AgentExecutionResponse],
    summary="Get Agent Execution Detail",
    description="Retrieve structured agent execution record by unique execution ID.",
)
def get_agent_execution(
    execution_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> BaseResponse[AgentExecutionResponse]:
    """Retrieve execution record including investigation outputs, timing, and status."""
    execution = AgentExecutionRepository.get_by_id(db, execution_id)
    if execution is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent execution with ID '{execution_id}' not found",
        )

    # Sanitize input_data just in case
    execution_dict = {
        "id": execution.id,
        "incident_id": execution.incident_id,
        "agent_type": execution.agent_type,
        "status": execution.status,
        "input_data": _sanitize_payload(execution.input_data or {}),
        "output_data": execution.output_data or {},
        "error_summary": execution.error_summary,
        "started_at": execution.started_at,
        "completed_at": execution.completed_at,
        "created_at": execution.created_at,
    }

    return BaseResponse(
        success=True,
        message="Agent execution retrieved successfully",
        data=AgentExecutionResponse.model_validate(execution_dict),
    )

