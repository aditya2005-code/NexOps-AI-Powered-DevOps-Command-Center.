import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.code_patch import CodePatch
from app.schemas.code_patch import CodePatchCreate


class CodePatchRepository:
    """Repository handling persistence and cryptographic hash verification for Code Patches."""

    @staticmethod
    def create(db: Session, patch_in: CodePatchCreate) -> CodePatch:
        computed_hash = CodePatch.compute_sha256(patch_in.patch_content)
        patch = CodePatch(
            incident_id=patch_in.incident_id,
            agent_execution_id=patch_in.agent_execution_id,
            title=patch_in.title,
            description=patch_in.description,
            patch_content=patch_in.patch_content,
            patch_hash=computed_hash,
            base_commit=patch_in.base_commit,
            status="pending_approval",
        )
        db.add(patch)
        db.flush()
        return patch

    @staticmethod
    def get_by_id(db: Session, patch_id: uuid.UUID) -> Optional[CodePatch]:
        statement = select(CodePatch).where(CodePatch.id == patch_id)
        return db.scalar(statement)

    @staticmethod
    def list_by_incident(db: Session, incident_id: uuid.UUID) -> List[CodePatch]:
        statement = (
            select(CodePatch)
            .where(CodePatch.incident_id == incident_id)
            .order_by(CodePatch.created_at.desc())
        )
        return list(db.scalars(statement).all())

    @staticmethod
    def verify_patch_hash(patch: CodePatch, content: Optional[str] = None) -> bool:
        """Verify that the given content (or patch's own content) matches patch_hash."""
        candidate = content if content is not None else patch.patch_content
        if candidate is None or not candidate.strip():
            return False
        try:
            return patch.patch_hash == CodePatch.compute_sha256(candidate)
        except Exception:
            return False


