import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.agents.application.exceptions import (
    AuthenticationRequiredError,
    PatchAlreadyAppliedError,
    PatchAlreadyApprovedError,
    PatchAlreadyRejectedError,
    PatchConcurrentModificationError,
    PatchIntegrityError,
    PatchNotApprovedError,
    PatchNotFoundError,
)
from app.core.config import settings
from app.models.approval import Approval, ApprovalDecision
from app.models.code_patch import CodePatch
from app.models.incident import Incident, IncidentStatus
from app.repositories import ApprovalRepository, AuditLogRepository, CodePatchRepository, IncidentRepository
from app.schemas.approval import ApprovalCreate, ApprovalResponse
from app.schemas.audit_log import AuditLogCreate

logger = logging.getLogger("nexops.agents.application.approval")


class ApprovalService:
    """Service handling human approval and rejection workflows bound cryptographically to patch content hashes."""

    @classmethod
    def resolve_actor_identifier(cls, authenticated_user: Optional[str] = None) -> str:
        """Resolve the reviewer actor identifier enforcing production auth boundaries.

        Limitation Note:
            NexOps currently operates without a fully configured user auth provider (OAuth2/JWT).
            In development/testing environments, when unauthenticated, a clearly labeled
            development actor (`dev_reviewer_unverified`) is used.
            In production environments, an authenticated identity is strictly required.
        """
        if authenticated_user and authenticated_user.strip():
            return authenticated_user.strip()

        # Check environment mode
        is_dev = (settings.ENVIRONMENT or "").lower() in ["development", "dev", "test", "testing"]
        if is_dev and settings.DEV_APPROVAL_ENABLED:
            return settings.DEV_APPROVAL_ACTOR

        raise AuthenticationRequiredError(
            "Authenticated human identity is strictly required for patch approval decisions in production."
        )

    @classmethod
    def get_latest_approval(cls, db: Session, patch_id: uuid.UUID) -> Optional[ApprovalResponse]:
        """Retrieve the most recent approval decision for a patch."""
        approvals = ApprovalRepository.get_by_patch(db, patch_id)
        if not approvals:
            return None
        return ApprovalResponse.model_validate(approvals[0])

    @classmethod
    def get_approval_history(cls, db: Session, patch_id: uuid.UUID) -> List[ApprovalResponse]:
        """Retrieve the complete chronological approval history for a patch."""
        # Verify patch exists
        patch = CodePatchRepository.get_by_id(db, patch_id)
        if patch is None:
            raise PatchNotFoundError(f"Code patch with ID '{patch_id}' was not found.")

        approvals = ApprovalRepository.get_by_patch(db, patch_id)
        return [ApprovalResponse.model_validate(a) for a in approvals]

    @classmethod
    def approve_patch(
        cls,
        db: Session,
        patch_id: uuid.UUID,
        comment: Optional[str] = None,
        authenticated_user: Optional[str] = None,
    ) -> ApprovalResponse:
        """Approve a pending code patch after rigorous cryptographic integrity validation.

        Args:
            db: Database session
            patch_id: Code patch UUID
            comment: Optional human reviewer comment
            authenticated_user: Authenticated reviewer identity (if available)

        Returns:
            ApprovalResponse
        """
        # 1. Resolve reviewer identity
        actor = cls.resolve_actor_identifier(authenticated_user)

        # 2. Load patch
        patch = CodePatchRepository.get_by_id(db, patch_id)
        if patch is None:
            raise PatchNotFoundError(f"Code patch with ID '{patch_id}' was not found.")

        # 3. Verify patch is awaiting approval
        if patch.status == "approved":
            raise PatchAlreadyApprovedError(f"Patch '{patch_id}' has already been approved.")
        if patch.status == "rejected":
            raise PatchAlreadyRejectedError(f"Patch '{patch_id}' has already been rejected and cannot be approved.")
        if patch.status in ["applying", "applied"]:
            raise PatchAlreadyAppliedError(f"Patch '{patch_id}' is already in '{patch.status}' state.")
        if patch.status != "pending_approval":
            raise PatchNotApprovedError(f"Patch '{patch_id}' is in unexpected status '{patch.status}'.")

        # 4. Cryptographic integrity check: recompute SHA-256
        if not patch.patch_content or not patch.patch_content.strip():
            raise PatchIntegrityError(f"Patch '{patch_id}' has empty patch content.")

        computed_hash = CodePatch.compute_sha256(patch.patch_content)
        if computed_hash != patch.patch_hash:
            logger.error(
                "Cryptographic hash mismatch for patch '%s': stored '%s' != computed '%s'",
                patch_id,
                patch.patch_hash,
                computed_hash,
            )
            raise PatchIntegrityError(
                f"Patch integrity check failed: patch content has been altered. Expected {patch.patch_hash}, computed {computed_hash}."
            )

        # 5. Atomic state update using conditional query to prevent concurrent approvals
        now = datetime.now(timezone.utc)
        result = db.execute(
            update(CodePatch)
            .where(CodePatch.id == patch_id, CodePatch.status == "pending_approval")
            .values(status="approved", updated_at=now)
        )
        if result.rowcount == 0:
            raise PatchConcurrentModificationError(
                f"Patch '{patch_id}' status was modified concurrently or is no longer awaiting approval."
            )

        # 6. Create Approval record bound to exact patch and hash
        approval = ApprovalRepository.create(
            db,
            ApprovalCreate(
                patch_id=patch.id,
                patch_hash=computed_hash,
                decision=ApprovalDecision.APPROVED,
                reviewer_identifier=actor,
                comment=comment,
            ),
        )

        # 7. Append audit log
        AuditLogRepository.append(
            db,
            AuditLogCreate(
                action="approval_granted",
                actor_type="user" if authenticated_user else "development_actor",
                actor_identifier=actor,
                resource_type="code_patch",
                resource_id=patch.id,
                details={
                    "incident_id": str(patch.incident_id),
                    "patch_id": str(patch.id),
                    "patch_hash": computed_hash,
                    "approval_id": str(approval.id),
                    "comment": comment,
                    "verified_sha256": True,
                },
            ),
        )

        db.commit()
        db.refresh(approval)
        logger.info("Patch '%s' successfully approved by '%s' with hash '%s'", patch_id, actor, computed_hash[:8])
        return ApprovalResponse.model_validate(approval)

    @classmethod
    def reject_patch(
        cls,
        db: Session,
        patch_id: uuid.UUID,
        reason: Optional[str] = None,
        authenticated_user: Optional[str] = None,
    ) -> ApprovalResponse:
        """Reject a pending code patch.

        Args:
            db: Database session
            patch_id: Code patch UUID
            reason: Optional rejection reason
            authenticated_user: Authenticated reviewer identity (if available)

        Returns:
            ApprovalResponse
        """
        actor = cls.resolve_actor_identifier(authenticated_user)

        patch = CodePatchRepository.get_by_id(db, patch_id)
        if patch is None:
            raise PatchNotFoundError(f"Code patch with ID '{patch_id}' was not found.")

        if patch.status == "rejected":
            raise PatchAlreadyRejectedError(f"Patch '{patch_id}' has already been rejected.")
        if patch.status == "approved":
            raise PatchAlreadyApprovedError(f"Patch '{patch_id}' has already been approved and cannot be rejected.")
        if patch.status in ["applying", "applied"]:
            raise PatchAlreadyAppliedError(f"Patch '{patch_id}' is already in '{patch.status}' state.")
        if patch.status != "pending_approval":
            raise PatchNotApprovedError(f"Patch '{patch_id}' is in unexpected status '{patch.status}'.")

        # Cryptographic check
        computed_hash = CodePatch.compute_sha256(patch.patch_content)
        if computed_hash != patch.patch_hash:
            raise PatchIntegrityError(
                f"Patch integrity check failed: patch content has been altered. Expected {patch.patch_hash}, computed {computed_hash}."
            )

        now = datetime.now(timezone.utc)
        result = db.execute(
            update(CodePatch)
            .where(CodePatch.id == patch_id, CodePatch.status == "pending_approval")
            .values(status="rejected", updated_at=now)
        )
        if result.rowcount == 0:
            raise PatchConcurrentModificationError(
                f"Patch '{patch_id}' status was modified concurrently or is no longer awaiting approval."
            )

        approval = ApprovalRepository.create(
            db,
            ApprovalCreate(
                patch_id=patch.id,
                patch_hash=computed_hash,
                decision=ApprovalDecision.REJECTED,
                reviewer_identifier=actor,
                comment=reason,
            ),
        )

        AuditLogRepository.append(
            db,
            AuditLogCreate(
                action="approval_rejected",
                actor_type="user" if authenticated_user else "development_actor",
                actor_identifier=actor,
                resource_type="code_patch",
                resource_id=patch.id,
                details={
                    "incident_id": str(patch.incident_id),
                    "patch_id": str(patch.id),
                    "patch_hash": computed_hash,
                    "approval_id": str(approval.id),
                    "reason": reason,
                    "verified_sha256": True,
                },
            ),
        )

        db.commit()
        db.refresh(approval)
        logger.info("Patch '%s' rejected by '%s'", patch_id, actor)
        return ApprovalResponse.model_validate(approval)

