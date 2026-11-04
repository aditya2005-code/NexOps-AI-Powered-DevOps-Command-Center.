import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.agent_execution import AgentExecution, AgentExecutionStatus
from app.schemas.agent_execution import AgentExecutionCreate


class AgentExecutionRepository:
    """Repository handling persistence operations for Agent Executions."""

    @staticmethod
    def create(db: Session, execution_in: AgentExecutionCreate) -> AgentExecution:
        execution = AgentExecution(
            incident_id=execution_in.incident_id,
            agent_type=execution_in.agent_type,
            input_data=execution_in.input_data,
        )
        db.add(execution)
        db.flush()
        return execution

    @staticmethod
    def get_by_id(db: Session, execution_id: uuid.UUID) -> Optional[AgentExecution]:
        statement = select(AgentExecution).where(AgentExecution.id == execution_id)
        return db.scalar(statement)

    @staticmethod
    def list_by_incident(db: Session, incident_id: uuid.UUID) -> List[AgentExecution]:
        statement = (
            select(AgentExecution)
            .where(AgentExecution.incident_id == incident_id)
            .order_by(AgentExecution.started_at.desc())
        )
        return list(db.scalars(statement).all())

    @staticmethod
    def update_status(
        db: Session,
        execution: AgentExecution,
        status: AgentExecutionStatus,
        output_data: Optional[Dict[str, Any]] = None,
        error_summary: Optional[str] = None,
    ) -> AgentExecution:
        execution.status = status
        if output_data is not None:
            execution.output_data = output_data
        if error_summary is not None:
            execution.error_summary = error_summary
        if status in (
            AgentExecutionStatus.COMPLETED,
            AgentExecutionStatus.FAILED,
            AgentExecutionStatus.CANCELLED,
        ):
            execution.completed_at = datetime.now(timezone.utc)
        db.flush()
        return execution


