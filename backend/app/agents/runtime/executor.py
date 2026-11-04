import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from langchain_core.language_models.chat_models import BaseChatModel
from sqlalchemy.orm import Session

from app.agents.llm import LLMConfigurationError, LLMProviderFactory
from app.agents.schemas.investigation import (
    IncidentInvestigationResponse,
    InvestigationResult,
)
from app.agents.state import InvestigationState
from app.agents.workflows.incident_investigation import create_investigation_graph
from app.core.config import settings
from app.models.agent_execution import AgentExecutionStatus, AgentType
from app.repositories import (
    AgentExecutionRepository,
    AuditLogRepository,
    IncidentRepository,
    ProjectRepository,
)
from app.schemas.agent_execution import AgentExecutionCreate
from app.schemas.audit_log import AuditLogCreate

logger = logging.getLogger("nexops.agents.runtime")


class IncidentInvestigationExecutor:
    """Orchestrates end-to-end incident investigation using LangGraph and persists execution records."""

    @classmethod
    def execute(
        cls,
        db: Session,
        incident_id: uuid.UUID,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        llm: Optional[BaseChatModel] = None,
    ) -> IncidentInvestigationResponse:
        """Run incident investigation workflow and record full lifecycle into PostgreSQL."""
        # 1. Verify incident exists
        incident = IncidentRepository.get_by_id(db, incident_id)
        if incident is None:
            raise ValueError(f"Incident with ID '{incident_id}' not found")

        # 2. Resolve project context
        project = None
        if incident.project_id:
            project = ProjectRepository.get_by_id(db, incident.project_id)

        # 3. Resolve event timeline
        events = IncidentRepository.list_events_by_incident(db, incident_id)
        events_data = [
            {
                "event_type": ev.event_type,
                "actor_type": ev.actor_type,
                "actor_identifier": ev.actor_identifier,
                "description": ev.description,
                "created_at": ev.created_at.isoformat() if ev.created_at else "",
            }
            for ev in events
        ]

        # 4. Resolve provider and model details
        resolved_provider = LLMProviderFactory.get_effective_provider_name(provider)
        selected_model = (
            model
            or settings.LLM_MODEL
            or (settings.GEMINI_MODEL if resolved_provider == "gemini" else settings.GROQ_MODEL)
        )

        # 5. Create initial AgentExecution record
        input_payload = {
            "incident_id": str(incident.id),
            "incident_title": incident.title,
            "project_name": project.name if project else None,
            "provider": resolved_provider,
            "model": selected_model,
        }
        execution = AgentExecutionRepository.create(
            db,
            AgentExecutionCreate(
                incident_id=incident.id,
                agent_type=AgentType.INCIDENT_MANAGER,
                input_data=input_payload,
            ),
        )
        AgentExecutionRepository.update_status(db, execution, AgentExecutionStatus.RUNNING)
        db.commit()
        db.refresh(execution)

        start_time = time.perf_counter()

        # 6. Attempt LLM instantiation if not pre-injected
        try:
            active_llm = llm or LLMProviderFactory.create_llm(
                provider=resolved_provider,
                model=selected_model,
            )
        except LLMConfigurationError as cfg_err:
            duration = time.perf_counter() - start_time
            error_str = f"LLMConfigurationError: {str(cfg_err)}"
            logger.error("Investigation halted due to configuration error: %s", error_str)

            AgentExecutionRepository.update_status(
                db,
                execution=execution,
                status=AgentExecutionStatus.FAILED,
                error_summary=error_str,
            )
            AuditLogRepository.append(
                db,
                AuditLogCreate(
                    action="agent_investigation_failed",
                    actor_type="system",
                    actor_identifier="agent_runtime",
                    resource_type="agent_execution",
                    resource_id=execution.id,
                    details={"incident_id": str(incident.id), "error": error_str},
                ),
            )
            db.commit()
            raise cfg_err

        # 7. Construct initial graph state
        project_ws = settings.get_project_workspace_path(project.name if project else None)
        initial_state: InvestigationState = {
            "incident_id": str(incident.id),
            "project_id": str(incident.project_id) if incident.project_id else None,
            "incident_title": incident.title,
            "incident_description": incident.description,
            "incident_severity": incident.severity.value if hasattr(incident.severity, "value") else str(incident.severity),
            "incident_status": incident.status.value if hasattr(incident.status, "value") else str(incident.status),
            "incident_source": incident.source,
            "project_name": project.name if project else "Unassigned",
            "project_environment": project.environment if project else "unknown",
            "project_workspace_path": str(project_ws) if project_ws else None,
            "incident_events": events_data,
            "errors": [],
        }

        # 8. Execute LangGraph workflow
        graph = create_investigation_graph(llm=active_llm)
        final_state = graph.invoke(initial_state)

        duration = time.perf_counter() - start_time
        raw_result = final_state.get("investigation_result", {})
        investigation_result = InvestigationResult.model_validate(raw_result)
        is_success = final_state.get("execution_status") == "completed"

        # 9. Persist outcomes and audit trail
        if is_success:
            AgentExecutionRepository.update_status(
                db,
                execution=execution,
                status=AgentExecutionStatus.COMPLETED,
                output_data=investigation_result.model_dump(),
            )
            # Update incident's root cause summary if hypotheses were formed
            if investigation_result.structured_hypotheses:
                incident.root_cause_summary = "\n".join(
                    f"{h.root_cause_title}: {h.technical_explanation}"
                    if h.technical_explanation and h.technical_explanation != h.root_cause_title
                    else h.root_cause_title
                    for h in investigation_result.structured_hypotheses
                )
            elif investigation_result.hypotheses:
                incident.root_cause_summary = "\n".join(investigation_result.hypotheses)

            AuditLogRepository.append(
                db,
                AuditLogCreate(
                    action="agent_investigation_completed",
                    actor_type="agent",
                    actor_identifier="incident_investigation_agent",
                    resource_type="incident",
                    resource_id=incident.id,
                    details={
                        "execution_id": str(execution.id),
                        "provider": resolved_provider,
                        "model": selected_model,
                        "confidence": investigation_result.confidence_score,
                        "duration_seconds": round(duration, 3),
                    },
                ),
            )
        else:
            err_summary = "; ".join(final_state.get("errors", ["Investigation failed"]))
            AgentExecutionRepository.update_status(
                db,
                execution=execution,
                status=AgentExecutionStatus.FAILED,
                output_data=investigation_result.model_dump(),
                error_summary=err_summary,
            )
            AuditLogRepository.append(
                db,
                AuditLogCreate(
                    action="agent_investigation_failed",
                    actor_type="agent",
                    actor_identifier="incident_investigation_agent",
                    resource_type="incident",
                    resource_id=incident.id,
                    details={
                        "execution_id": str(execution.id),
                        "provider": resolved_provider,
                        "model": selected_model,
                        "error": err_summary,
                    },
                ),
            )

        db.commit()
        db.refresh(execution)

        return IncidentInvestigationResponse(
            incident_id=incident.id,
            execution_id=execution.id,
            provider=resolved_provider,
            model=selected_model,
            investigation=investigation_result,
            execution_status=execution.status.value if hasattr(execution.status, "value") else str(execution.status),
            duration_seconds=round(duration, 3),
            created_at=datetime.now(timezone.utc),
        )
