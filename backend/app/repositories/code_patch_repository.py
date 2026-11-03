import uuid
from typing import Optional
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
    def verify_patch_hash(patch: CodePatch, content: str) -> bool:
        """Verify that the given content exactly matches the patch's cryptographic SHA-256 hash."""
        candidate_hash = CodePatch.compute_sha256(content)
        return patch.patch_hash == candidate_hash

