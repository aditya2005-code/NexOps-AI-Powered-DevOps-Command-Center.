"""Phase 5.4: Human Approval & Controlled Patch Application."""

from app.agents.application.approval_service import ApprovalService
from app.agents.application.exceptions import (
    ApprovalIntegrityError,
    AuthenticationRequiredError,
    GitExecutionError,
    GitWorktreeError,
    InvalidBaseCommitError,
    PatchAlreadyAppliedError,
    PatchAlreadyApprovedError,
    PatchAlreadyRejectedError,
    PatchApplicationError,
    PatchConcurrentModificationError,
    PatchIntegrityError,
    PatchNotApprovedError,
    PatchNotFoundError,
    SecurityViolationError,
)
from app.agents.application.git_executor import SafeGitExecutor
from app.agents.application.patch_application_service import PatchApplicationService
from app.agents.application.worktree_manager import WorktreeManager

__all__ = [
    "ApprovalService",
    "PatchApplicationService",
    "WorktreeManager",
    "SafeGitExecutor",
    "PatchApplicationError",
    "PatchNotFoundError",
    "PatchNotApprovedError",
    "PatchAlreadyApprovedError",
    "PatchAlreadyRejectedError",
    "PatchAlreadyAppliedError",
    "PatchConcurrentModificationError",
    "PatchIntegrityError",
    "ApprovalIntegrityError",
    "InvalidBaseCommitError",
    "GitExecutionError",
    "GitWorktreeError",
    "SecurityViolationError",
    "AuthenticationRequiredError",
]

