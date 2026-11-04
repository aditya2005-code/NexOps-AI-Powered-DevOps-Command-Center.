"""Exceptions for Phase 5.4 Human Approval and Controlled Patch Application."""


class PatchApplicationError(Exception):
    """Base exception for all patch application and approval errors."""
    pass


class PatchNotFoundError(PatchApplicationError):
    """Raised when a requested patch is not found."""
    pass


class PatchNotApprovedError(PatchApplicationError):
    """Raised when an operation requires an approved patch, but patch is not approved."""
    pass


class PatchAlreadyApprovedError(PatchApplicationError):
    """Raised when attempting to approve a patch that is already approved."""
    pass


class PatchAlreadyRejectedError(PatchApplicationError):
    """Raised when attempting to approve/apply a patch that is already rejected."""
    pass


class PatchAlreadyAppliedError(PatchApplicationError):
    """Raised when attempting to approve/apply a patch that has already been applied."""
    pass


class PatchConcurrentModificationError(PatchApplicationError):
    """Raised when a patch is modified or being processed concurrently."""
    pass


class PatchIntegrityError(PatchApplicationError):
    """Raised when patch content does not match its expected cryptographic SHA-256 hash."""
    pass


class ApprovalIntegrityError(PatchApplicationError):
    """Raised when approval record hash does not match the current patch hash."""
    pass


class InvalidBaseCommitError(PatchApplicationError):
    """Raised when expected base commit does not exist or does not match repository."""
    pass


class GitExecutionError(PatchApplicationError):
    """Raised when a Git command fails, times out, or returns a non-zero exit code."""
    pass


class GitWorktreeError(PatchApplicationError):
    """Raised when an isolated worktree cannot be created, verified, or cleaned up."""
    pass


class SecurityViolationError(PatchApplicationError):
    """Raised when a forbidden git command, path traversal, or unauthorized file modification is detected."""
    pass


class AuthenticationRequiredError(PatchApplicationError):
    """Raised when an authenticated identity is required but not provided."""
    pass

