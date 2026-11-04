import logging
import os
import shutil
import tempfile
import time
import uuid
from pathlib import Path
from typing import Optional

from app.agents.application.exceptions import (
    GitWorktreeError,
    InvalidBaseCommitError,
    SecurityViolationError,
)
from app.agents.application.git_executor import SafeGitExecutor
from app.core.config import settings

logger = logging.getLogger("nexops.agents.application.worktree")


class WorktreeManager:
    """Manages the creation, verification, isolation, and cleanup of disposable Git worktrees."""

    @classmethod
    def get_worktree_root(cls) -> Path:
        """Resolve and ensure the dedicated root directory for NexOps worktrees."""
        if settings.NEXOPS_WORKTREE_DIR:
            root = Path(settings.NEXOPS_WORKTREE_DIR).resolve()
        else:
            root = (Path(tempfile.gettempdir()).resolve() / "nexops_worktrees").resolve()

        root.mkdir(parents=True, exist_ok=True)
        return root

    @classmethod
    def create_worktree(
        cls,
        repo_path: Path,
        patch_id: uuid.UUID,
        base_commit: str,
    ) -> Path:
        """Create an isolated, detached Git worktree at a verified base commit.

        Args:
            repo_path: Primary Git repository directory (read-only reference)
            patch_id: Code patch UUID
            base_commit: Exact commit SHA to check out

        Returns:
            Path to the isolated, clean worktree
        """
        # 1. Validate repository
        if not repo_path.exists() or not repo_path.is_dir():
            raise GitWorktreeError(f"Repository path '{repo_path}' does not exist.")

        if not SafeGitExecutor.is_git_repository(repo_path):
            raise GitWorktreeError(f"Directory '{repo_path}' is not a valid Git repository.")

        # 2. Validate base commit
        clean_commit = base_commit.strip()
        if not SafeGitExecutor.verify_commit_exists(repo_path, clean_commit):
            raise InvalidBaseCommitError(
                f"Base commit '{clean_commit}' does not exist in repository '{repo_path}'."
            )

        # 3. Create isolated worktree path under dedicated root
        root = cls.get_worktree_root()
        worktree_name = f"patch_{patch_id}_{uuid.uuid4().hex[:8]}"
        worktree_path = (root / worktree_name).resolve()

        # Strict containment verification
        if not worktree_path.is_relative_to(root):
            raise SecurityViolationError("Worktree path escapes dedicated worktree root.")

        if worktree_path.exists():
            shutil.rmtree(worktree_path, ignore_errors=True)

        logger.info(
            "Creating isolated worktree at '%s' from commit '%s' (repo: '%s')",
            worktree_path,
            clean_commit[:8],
            repo_path,
        )

        # 4. Execute 'git worktree add <path> <commit> --detach'
        code, stdout, stderr = SafeGitExecutor.execute(
            "worktree",
            ["add", str(worktree_path), clean_commit, "--detach"],
            cwd=repo_path,
        )

        if code != 0:
            error_msg = stderr or stdout
            logger.error("Failed to create worktree: %s", error_msg)
            # Attempt cleanup in case partial directory was left
            if worktree_path.exists():
                shutil.rmtree(worktree_path, ignore_errors=True)
            raise GitWorktreeError(f"Failed to create Git worktree: {error_msg}")

        # 5. Verify worktree cleanliness
        if not SafeGitExecutor.is_worktree_clean(worktree_path):
            cls.remove_worktree(repo_path, worktree_path)
            raise GitWorktreeError("Newly created worktree is not clean.")

        return worktree_path

    @classmethod
    def remove_worktree(cls, repo_path: Path, worktree_path: Path) -> bool:
        """Safely remove a Git worktree and prune Git worktree references.

        Args:
            repo_path: Primary Git repository
            worktree_path: Worktree directory to delete

        Returns:
            True if removed successfully, False if errors were encountered
        """
        logger.info("Cleaning up isolated worktree at '%s'", worktree_path)
        success = True

        # 1. Ask git to remove worktree if repo exists
        try:
            if repo_path.exists() and SafeGitExecutor.is_git_repository(repo_path):
                code, _, stderr = SafeGitExecutor.execute(
                    "worktree",
                    ["remove", "--force", str(worktree_path)],
                    cwd=repo_path,
                )
                if code != 0:
                    logger.warning("git worktree remove warning: %s", stderr)
                    success = False

                SafeGitExecutor.execute("worktree", ["prune"], cwd=repo_path)
        except Exception as exc:
            logger.warning("Exception during git worktree remove: %s", str(exc))
            success = False

        # 2. Ensure filesystem directory is cleaned up
        try:
            if worktree_path.exists():
                shutil.rmtree(worktree_path, ignore_errors=True)
        except Exception as exc:
            logger.error("Failed to delete worktree directory from disk: %s", str(exc))
            success = False

        return success

    @classmethod
    def cleanup_stale_worktrees(cls, repo_path: Optional[Path] = None, max_age_seconds: int = 3600) -> int:
        """Prune and clean up worktrees older than max_age_seconds.

        Returns:
            Number of worktrees cleaned up
        """
        root = cls.get_worktree_root()
        cleaned_count = 0
        now = time.time()

        for entry in root.iterdir():
            if entry.is_dir() and entry.name.startswith("patch_"):
                try:
                    mtime = entry.stat().st_mtime
                    if now - mtime > max_age_seconds:
                        logger.info("Pruning stale worktree '%s'", entry)
                        if repo_path and repo_path.exists():
                            cls.remove_worktree(repo_path, entry)
                        else:
                            shutil.rmtree(entry, ignore_errors=True)
                        cleaned_count += 1
                except Exception as exc:
                    logger.warning("Error pruning stale worktree '%s': %s", entry, str(exc))

        if repo_path and repo_path.exists() and SafeGitExecutor.is_git_repository(repo_path):
            try:
                SafeGitExecutor.execute("worktree", ["prune"], cwd=repo_path)
            except Exception:
                pass

        return cleaned_count

