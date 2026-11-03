import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.agent_execution import AgentExecution
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

