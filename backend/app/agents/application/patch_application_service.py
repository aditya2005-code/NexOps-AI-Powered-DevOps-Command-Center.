import logging
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.agents.application.exceptions import (
    ApprovalIntegrityError,
    GitExecutionError,
    GitWorktreeError,
    InvalidBaseCommitError,
    PatchAlreadyAppliedError,
    PatchAlreadyRejectedError,
    PatchApplicationError,
    PatchConcurrentModificationError,
    PatchIntegrityError,
    PatchNotApprovedError,
    PatchNotFoundError,
    SecurityViolationError,
)
from app.agents.application.git_executor import SafeGitExecutor
from app.agents.application.worktree_manager import WorktreeManager
from app.agents.remediation.diff_validator import DiffValidator
from app.core.config import settings
from app.models.approval import Approval, ApprovalDecision
from app.models.code_patch import CodePatch
from app.models.incident import Incident
from app.models.project import Project
from app.repositories import (
    ApprovalRepository,
    AuditLogRepository,
    CodePatchRepository,
    IncidentRepository,
    ProjectRepository,
)
from app.schemas.audit_log import AuditLogCreate
from app.schemas.code_patch import PatchApplicationStatusResponse

logger = logging.getLogger("nexops.agents.application.service")


class PatchApplicationService:
    """Orchestrates isolated, controlled Git patch application with strict hash binding and short DB transactions."""

    @classmethod
    def apply_patch(
        cls,
        db: Session,
        patch_id: uuid.UUID,
        authenticated_user: Optional[str] = None,
    ) -> PatchApplicationStatusResponse:
        """Apply an approved code patch inside an isolated Git worktree.

        Args:
            db: Database session
            patch_id: Code patch UUID
            authenticated_user: Optional authenticated actor identifier

        Returns:
            PatchApplicationStatusResponse
        """
        actor = authenticated_user or "system"

        # ---------------------------------------------------------
        # PHASE 1: Pre-application Verification & Lock (Short Txn)
        # ---------------------------------------------------------
        patch = CodePatchRepository.get_by_id(db, patch_id)
        if patch is None:
            raise PatchNotFoundError(f"Code patch with ID '{patch_id}' was not found.")

        # Check existing status
        if patch.status == "applying":
            raise PatchConcurrentModificationError(
                f"Patch '{patch_id}' application is already in progress by another worker."
            )
        if patch.status == "applied":
            raise PatchAlreadyAppliedError(f"Patch '{patch_id}' has already been successfully applied.")
        if patch.status == "rejected":
            raise PatchAlreadyRejectedError(f"Patch '{patch_id}' has been rejected and cannot be applied.")
        if patch.status != "approved":
            raise PatchNotApprovedError(
                f"Patch '{patch_id}' cannot be applied because its status is '{patch.status}', not 'approved'."
            )

        # Retrieve and verify approval record
        approvals = ApprovalRepository.get_by_patch(db, patch_id)
        if not approvals or approvals[0].decision != ApprovalDecision.APPROVED:
            raise PatchNotApprovedError(f"Patch '{patch_id}' has no valid APPROVED human approval record.")
        latest_approval = approvals[0]

        # Cryptographic verification: Recompute SHA-256 of persisted patch
        if not patch.patch_content or not patch.patch_content.strip():
            raise PatchIntegrityError(f"Patch '{patch_id}' has empty patch content.")

        current_hash = CodePatch.compute_sha256(patch.patch_content)
        if current_hash != patch.patch_hash:
            raise PatchIntegrityError(
                f"Cryptographic hash mismatch: patch content does not match stored hash '{patch.patch_hash}'."
            )

        # Cryptographic binding: Verify approval authorizes the exact current bytes
        if latest_approval.patch_hash != current_hash:
            raise ApprovalIntegrityError(
                f"Approval hash mismatch: approval was granted for hash '{latest_approval.patch_hash}', "
                f"but patch content hash is '{current_hash}'. Refusing to apply modified patch."
            )

        # Resolve project and repo path
        incident = IncidentRepository.get_by_id(db, patch.incident_id)
        project: Optional[Project] = None
        if incident and incident.project_id:
            project = ProjectRepository.get_by_id(db, incident.project_id)

        project_identifier = project.name if project else (str(incident.project_id) if incident else None)
        repo_path = settings.get_project_workspace_path(project_identifier)

        # Atomic state transition from 'approved' -> 'applying'
        now = datetime.now(timezone.utc)
        result = db.execute(
            update(CodePatch)
            .where(CodePatch.id == patch_id, CodePatch.status == "approved")
            .values(status="applying", updated_at=now)
        )
        if result.rowcount == 0:
            raise PatchConcurrentModificationError(
                f"Concurrent state change: patch '{patch_id}' is no longer in 'approved' status."
            )

        AuditLogRepository.append(
            db,
            AuditLogCreate(
                action="patch_application_started",
                actor_type="user" if authenticated_user else "system",
                actor_identifier=actor,
                resource_type="code_patch",
                resource_id=patch.id,
                details={
                    "incident_id": str(patch.incident_id),
                    "patch_hash": current_hash,
                    "approval_id": str(latest_approval.id),
                    "base_commit": patch.base_commit,
                },
            ),
        )
        db.commit()

        # Capture snapshot variables needed for Phase 2 outside the DB transaction
        patch_content = patch.patch_content
        expected_base_commit = patch.base_commit
        incident_id = patch.incident_id
        approval_id = latest_approval.id

        # ---------------------------------------------------------
        # PHASE 2: Isolated Git Worktree Execution (No DB Lock)
        # ---------------------------------------------------------
        worktree_path: Optional[Path] = None
        application_error: Optional[str] = None
        modified_files: List[str] = []
        lines_added = 0
        lines_removed = 0
        effective_base_commit = expected_base_commit

        try:
            # 1. Verify Git executable availability
            if not SafeGitExecutor.is_git_available():
                raise GitExecutionError("Git executable is not available on host system.")

            # 2. Verify repository path
            if not repo_path or not repo_path.exists() or not repo_path.is_dir():
                raise GitWorktreeError(
                    f"Project repository directory '{repo_path}' is not configured or does not exist."
                )

            if not SafeGitExecutor.is_git_repository(repo_path):
                raise GitWorktreeError(f"Target repository '{repo_path}' is not a valid Git repository.")

            # 3. Resolve and verify base commit
            if not effective_base_commit:
                effective_base_commit = SafeGitExecutor.get_head_commit(repo_path)

            if not SafeGitExecutor.verify_commit_exists(repo_path, effective_base_commit):
                raise InvalidBaseCommitError(
                    f"Base commit '{effective_base_commit}' does not exist in repository '{repo_path}'."
                )

            # 4. Create isolated Git worktree
            worktree_path = WorktreeManager.create_worktree(
                repo_path=repo_path,
                patch_id=patch_id,
                base_commit=effective_base_commit,
            )

            # 5. Pre-application check (git apply --check)
            can_apply, check_err = SafeGitExecutor.apply_check(worktree_path, patch_content)
            if not can_apply:
                raise PatchApplicationError(
                    f"Pre-flight patch verification failed (git apply --check): {check_err}"
                )

            # 6. Apply patch into isolated worktree
            applied, apply_err = SafeGitExecutor.apply_patch(worktree_path, patch_content)
            if not applied:
                raise PatchApplicationError(f"Patch application failed: {apply_err}")

            # 7. Inspect resulting diff
            modified_files = SafeGitExecutor.get_modified_files(worktree_path)
            lines_added, lines_removed = SafeGitExecutor.get_diff_stats(worktree_path)

            # 8. Verify touched files match authorized diff files
            val_res = DiffValidator.validate(patch_content)
            authorized_patch_files = set(val_res.files_touched)
            for mod_file in modified_files:
                norm_mod = mod_file.replace("\\", "/").lstrip("/")
                if norm_mod not in authorized_patch_files:
                    raise SecurityViolationError(
                        f"Patch modified unauthorized file '{mod_file}' not declared in patch diff."
                    )

            logger.info(
                "Patch '%s' applied cleanly in worktree '%s'. Files: %s (+%s/-%s)",
                patch_id,
                worktree_path,
                modified_files,
                lines_added,
                lines_removed,
            )

        except Exception as exc:
            application_error = str(exc)
            logger.error("Error during patch '%s' application: %s", patch_id, application_error)
        finally:
            # 9. Clean up isolated worktree
            if worktree_path and repo_path:
                cleanup_ok = WorktreeManager.remove_worktree(repo_path, worktree_path)
                if not cleanup_ok:
                    logger.warning("Worktree cleanup encountered warnings for '%s'", worktree_path)

        # ---------------------------------------------------------
        # PHASE 3: Final State Persistence & Audit (Short Txn)
        # ---------------------------------------------------------
        final_now = datetime.now(timezone.utc)
        final_status = "applied" if application_error is None else "failed"

        db.execute(
            update(CodePatch)
            .where(CodePatch.id == patch_id)
            .values(
                status=final_status,
                base_commit=effective_base_commit,
                updated_at=final_now,
            )
        )

        audit_action = "patch_application_succeeded" if final_status == "applied" else "patch_application_failed"
        audit_details: Dict[str, Any] = {
            "incident_id": str(incident_id),
            "patch_id": str(patch_id),
            "patch_hash": current_hash,
            "approval_id": str(approval_id),
            "base_commit": effective_base_commit,
            "modified_files": modified_files,
            "lines_added": lines_added,
            "lines_removed": lines_removed,
        }
        if application_error:
            audit_details["error"] = SafeGitExecutor.sanitize_output(application_error)

        AuditLogRepository.append(
            db,
            AuditLogCreate(
                action=audit_action,
                actor_type="user" if authenticated_user else "system",
                actor_identifier=actor,
                resource_type="code_patch",
                resource_id=patch_id,
                details=audit_details,
            ),
        )
        db.commit()

        # If execution failed, raise appropriate exception to API caller
        if application_error:
            raise PatchApplicationError(f"Controlled patch application failed: {application_error}")

        # Return comprehensive status response
        refreshed_patch = CodePatchRepository.get_by_id(db, patch_id)
        return PatchApplicationStatusResponse(
            patch_id=patch_id,
            incident_id=incident_id,
            status="applied",
            base_commit=effective_base_commit,
            applied_at=final_now,
            applied_by=actor,
            modified_files=modified_files,
            lines_added=lines_added,
            lines_removed=lines_removed,
            execution_details={
                "worktree_isolated": True,
                "verified_hash": current_hash,
                "preflight_check": "passed",
            },
            is_hash_valid=True,
            created_at=refreshed_patch.created_at if refreshed_patch else final_now,
            updated_at=final_now,
        )

    @classmethod
    def get_application_status(cls, db: Session, patch_id: uuid.UUID) -> PatchApplicationStatusResponse:
        """Retrieve the current application status and sanitized execution details for a patch."""
        patch = CodePatchRepository.get_by_id(db, patch_id)
        if patch is None:
            raise PatchNotFoundError(f"Code patch with ID '{patch_id}' was not found.")

        # Re-verify hash integrity
        is_hash_valid = CodePatchRepository.verify_patch_hash(patch)

        # Retrieve relevant audit logs for application details
        logs = AuditLogRepository.get_by_resource(db, resource_type="code_patch", resource_id=patch_id)
        applied_at: Optional[datetime] = None
        applied_by: Optional[str] = None
        modified_files: List[str] = []
        lines_added: Optional[int] = None
        lines_removed: Optional[int] = None
        error_summary: Optional[str] = None
        execution_details: Dict[str, Any] = {}

        for log in logs:
            if log.action in ["patch_application_succeeded", "patch_application_failed"]:
                applied_at = log.created_at
                applied_by = log.actor_identifier
                details = log.details or {}
                modified_files = details.get("modified_files", [])
                lines_added = details.get("lines_added")
                lines_removed = details.get("lines_removed")
                error_summary = details.get("error")
                execution_details = {
                    "audit_action": log.action,
                    "base_commit": details.get("base_commit"),
                    "patch_hash": details.get("patch_hash"),
                }
                break

        return PatchApplicationStatusResponse(
            patch_id=patch.id,
            incident_id=patch.incident_id,
            status=patch.status,
            base_commit=patch.base_commit,
            applied_at=applied_at,
            applied_by=applied_by,
            modified_files=modified_files,
            lines_added=lines_added,
            lines_removed=lines_removed,
            execution_details=execution_details,
            error_summary=error_summary,
            is_hash_valid=is_hash_valid,
            created_at=patch.created_at,
            updated_at=patch.updated_at,
        )

    @classmethod
    def recover_stale_applying_patches(cls, db: Session, max_age_seconds: int = 600) -> int:
        """Recover patches left stuck in 'applying' status due to unexpected server interruption."""
        now = datetime.now(timezone.utc)
        stmt = select(CodePatch).where(CodePatch.status == "applying")
        applying_patches = list(db.scalars(stmt).all())
        recovered_count = 0

        for patch in applying_patches:
            patch_updated = patch.updated_at
            if patch_updated.tzinfo is None:
                patch_updated = patch_updated.replace(tzinfo=timezone.utc)
            diff_seconds = (now - patch_updated).total_seconds()
            if diff_seconds >= max_age_seconds:
                logger.warning(
                    "Recovering abandoned patch '%s' stuck in 'applying' for %.1fs",
                    patch.id,
                    diff_seconds,
                )
                patch.status = "failed"
                patch.updated_at = now
                AuditLogRepository.append(
                    db,
                    AuditLogCreate(
                        action="patch_application_failed",
                        actor_type="system",
                        actor_identifier="stale_patch_recovery",
                        resource_type="code_patch",
                        resource_id=patch.id,
                        details={
                            "incident_id": str(patch.incident_id),
                            "error": f"Patch application timed out or was interrupted after {int(diff_seconds)}s.",
                        },
                    ),
                )
                recovered_count += 1

        if recovered_count > 0:
            db.commit()
            WorktreeManager.cleanup_stale_worktrees(max_age_seconds=max_age_seconds)

        return recovered_count
