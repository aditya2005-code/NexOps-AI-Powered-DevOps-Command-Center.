import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.approval import Approval
from app.models.code_patch import CodePatch
from app.schemas.approval import ApprovalCreate


class ApprovalRepository:
    """Repository handling human-in-the-loop approvals cryptographically linked to patch hashes."""

    @staticmethod
    def create(db: Session, approval_in: ApprovalCreate) -> Approval:
        approval = Approval(
            patch_id=approval_in.patch_id,
            patch_hash=approval_in.patch_hash,
            decision=approval_in.decision,
            reviewer_identifier=approval_in.reviewer_identifier,
            comment=approval_in.comment,
        )
        db.add(approval)
        db.flush()
        return approval

    @staticmethod
    def get_by_patch(db: Session, patch_id: uuid.UUID) -> List[Approval]:
        statement = (
            select(Approval)
            .where(Approval.patch_id == patch_id)
            .order_by(Approval.decided_at.desc())
        )
        return list(db.scalars(statement).all())

    @staticmethod
    def validate_approval_hash(approval: Approval, current_patch: CodePatch) -> bool:
        """Validate that the approval's authorized hash matches the current patch content hash."""
        return approval.patch_hash == current_patch.patch_hash

