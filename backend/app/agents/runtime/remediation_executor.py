import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from langchain_core.language_models.chat_models import BaseChatModel
from sqlalchemy.orm import Session

from app.agents.llm import LLMConfigurationError, LLMProviderFactory
from app.agents.schemas.remediation import (
    PatchRiskAssessment,
    PatchValidationResult,
    ProposedPatch,
    RemediationEligibility,
    RemediationEligibilityStatus,
    RemediationPlan,
    RemediationResponse,
)
from app.agents.state.remediation_state import RemediationState
from app.agents.workflows.remediation import create_remediation_graph
from app.core.config import settings
from app.models.agent_execution import AgentExecutionStatus, AgentType
from app.repositories import (
    AgentExecutionRepository,
    AuditLogRepository,
    CodePatchRepository,
    IncidentRepository,
    ProjectRepository,
)
from app.schemas.agent_execution import AgentExecutionCreate
from app.schemas.audit_log import AuditLogCreate
from app.schemas.code_patch import CodePatchCreate

logger = logging.getLogger("nexops.agents.runtime.remediation")


class IncidentRemediationExecutor:
    """Orchestrates end-to-end incident remediation planning and code patch generation."""

    @classmethod
    def execute(
        cls,
        db: Session,
        incident_id: uuid.UUID,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        llm: Optional[BaseChatModel] = None,
        investigation_result_override: Optional[Dict[str, Any]] = None,
    ) -> RemediationResponse:
        # 1. Verify incident exists
        incident = IncidentRepository.get_by_id(db, incident_id)
        if incident is None:
            raise ValueError(f"Incident with ID '{incident_id}' not found")

        # 2. Resolve project context
        project = None
        if incident.project_id:
            project = ProjectRepository.get_by_id(db, incident.project_id)

        # 3. Resolve investigation result
        inv_data = investigation_result_override
        inv_exec_id = None
        if not inv_data:
            executions = AgentExecutionRepository.list_by_incident(db, incident_id)
            for ex in executions:
                if ex.agent_type == AgentType.INCIDENT_MANAGER and ex.status == AgentExecutionStatus.COMPLETED:
                    inv_data = ex.output_data
                    inv_exec_id = str(ex.id)
                    break

        if not inv_data:
            # Fallback to incident root_cause_summary if available
            if incident.root_cause_summary:
                inv_data = {
                    "incident_summary": incident.title,
                    "hypotheses": [incident.root_cause_summary],
                    "evidence_items": [],
                    "insufficient_evidence": False,
                }
            else:
                inv_data = {
                    "incident_summary": incident.title,
                    "hypotheses": [],
                    "evidence_items": [],
                    "insufficient_evidence": True,
                }

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
            "investigation_execution_id": inv_exec_id,
            "provider": resolved_provider,
            "model": selected_model,
        }
        execution = AgentExecutionRepository.create(
            db,
            AgentExecutionCreate(
                incident_id=incident.id,
                agent_type=AgentType.FIX_AGENT,
                input_data=input_payload,
            ),
        )
        AgentExecutionRepository.update_status(db, execution, AgentExecutionStatus.RUNNING)
        db.commit()
        db.refresh(execution)

        start_time = time.perf_counter()

        # 6. Instantiate LLM
        try:
            active_llm = llm or LLMProviderFactory.create_llm(
                provider=resolved_provider,
                model=selected_model,
            )
        except LLMConfigurationError as cfg_err:
            error_str = f"LLMConfigurationError: {str(cfg_err)}"
            AgentExecutionRepository.update_status(
                db,
                execution=execution,
                status=AgentExecutionStatus.FAILED,
                error_summary=error_str,
            )
            AuditLogRepository.append(
                db,
                AuditLogCreate(
                    action="remediation_planning_failed",
                    actor_type="system",
                    actor_identifier="remediation_agent",
                    resource_type="agent_execution",
                    resource_id=execution.id,
                    details={"incident_id": str(incident.id), "error": error_str},
                ),
            )
            db.commit()
            raise cfg_err

        # 7. Construct initial graph state
        project_ws = settings.get_project_workspace_path(project.name if project else None)
        initial_state: RemediationState = {
            "incident_id": str(incident.id),
            "investigation_execution_id": inv_exec_id,
            "project_id": str(project.id) if project else None,
            "project_name": project.name if project else None,
            "project_workspace_path": str(project_ws) if project_ws else None,
            "incident_title": incident.title,
            "incident_description": incident.description,
            "investigation_result": inv_data,
            "errors": [],
        }

        # 8. Execute LangGraph remediation workflow and manage database transaction
        try:
            graph = create_remediation_graph(llm=active_llm)
            final_state = graph.invoke(initial_state)

            duration = time.perf_counter() - start_time

            eligibility_data = final_state.get("eligibility", {})
            eligibility = RemediationEligibility.model_validate(eligibility_data)

            plan_data = final_state.get("remediation_plan")
            plan = RemediationPlan.model_validate(plan_data) if plan_data else None

            patch_data = final_state.get("proposed_patch")
            patch = ProposedPatch.model_validate(patch_data) if patch_data else None

            val_data = final_state.get("validation_result")
            validation = PatchValidationResult.model_validate(val_data) if val_data else None

            risk_data = final_state.get("risk_assessment")
            risk = PatchRiskAssessment.model_validate(risk_data) if risk_data else None

            # Determine success condition
            if eligibility.status == RemediationEligibilityStatus.ELIGIBLE:
                is_success = (
                    final_state.get("execution_status") == "completed"
                    and patch is not None
                    and validation is not None
                    and validation.is_valid is True
                    and len(final_state.get("errors", [])) == 0
                )
            else:
                is_success = len(final_state.get("errors", [])) == 0

            persisted_patch_id = None
            persisted_patch_hash = None

            # 9. Persist CodePatch if valid
            if patch and validation and validation.is_valid:
                created_patch = CodePatchRepository.create(
                    db,
                    CodePatchCreate(
                        incident_id=incident.id,
                        agent_execution_id=execution.id,
                        title=patch.title,
                        description=patch.problem_description,
                        patch_content=patch.diff_content,
                    ),
                )
                persisted_patch_id = created_patch.id
                persisted_patch_hash = created_patch.patch_hash

            # 10. Update AgentExecution & AuditLog
            output_payload = {
                "eligibility": eligibility.model_dump(),
                "remediation_plan": plan.model_dump() if plan else None,
                "proposed_patch": patch.model_dump() if patch else None,
                "validation_result": validation.model_dump() if validation else None,
                "risk_assessment": risk.model_dump() if risk else None,
                "patch_id": str(persisted_patch_id) if persisted_patch_id else None,
                "patch_hash": persisted_patch_hash,
            }

            final_status = (
                AgentExecutionStatus.COMPLETED
                if is_success
                else AgentExecutionStatus.FAILED
            )

            error_summary = (
                "; ".join(final_state.get("errors", []))
                if not is_success
                else None
            )

            AgentExecutionRepository.update_status(
                db,
                execution=execution,
                status=final_status,
                output_data=output_payload,
                error_summary=error_summary,
            )

            AuditLogRepository.append(
                db,
                AuditLogCreate(
                    action="remediation_patch_generated" if persisted_patch_id else "remediation_evaluation_completed",
                    actor_type="agent",
                    actor_identifier="remediation_agent",
                    resource_type="code_patch" if persisted_patch_id else "incident",
                    resource_id=persisted_patch_id or incident.id,
                    details={
                        "execution_id": str(execution.id),
                        "eligibility_status": eligibility.status.value,
                        "patch_id": str(persisted_patch_id) if persisted_patch_id else None,
                        "patch_hash": persisted_patch_hash,
                        "risk_level": risk.risk_level.value if risk else None,
                        "duration_seconds": round(duration, 3),
                    },
                ),
            )

            db.commit()
            db.refresh(execution)
        except Exception as exc:
            db.rollback()
            try:
                AgentExecutionRepository.update_status(
                    db,
                    execution=execution,
                    status=AgentExecutionStatus.FAILED,
                    error_summary=f"{type(exc).__name__}: {str(exc)}",
                )
                db.commit()
            except Exception:
                db.rollback()
            raise exc

        return RemediationResponse(
            incident_id=incident.id,
            execution_id=execution.id,
            patch_id=persisted_patch_id,
            patch_hash=persisted_patch_hash,
            eligibility=eligibility,
            remediation_plan=plan,
            proposed_patch=patch,
            validation=validation,
            risk=risk,
            execution_status=final_status.value,
            duration_seconds=round(duration, 3),
            created_at=datetime.now(timezone.utc),
        )

