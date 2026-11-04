import logging
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple

from app.agents.application.exceptions import (
    GitExecutionError,
    SecurityViolationError,
)
from app.core.config import settings

logger = logging.getLogger("nexops.agents.application.git")

# Strict allowlist of git subcommands permitted for patch application
ALLOWED_GIT_SUBCOMMANDS = {
    "rev-parse",
    "cat-file",
    "worktree",
    "status",
    "apply",
    "diff",
}

# Forbidden subcommands that must be strictly rejected
FORBIDDEN_GIT_SUBCOMMANDS = {
    "push",
    "merge",
    "commit",
    "pull",
    "clone",
    "rebase",
    "reset",
    "checkout",
    "branch",
    "tag",
    "remote",
    "submodule",
    "clean",
}

MAX_OUTPUT_BYTES = 65536  # 64 KB


class SafeGitExecutor:
    """Tightly controlled, non-shell Git subprocess execution wrapper with allowlisting and secret redaction."""

    _git_executable: Optional[str] = None

    @classmethod
    def resolve_git_binary(cls) -> str:
        """Resolve the Git executable path securely or raise an error."""
        if cls._git_executable and os.path.isfile(cls._git_executable):
            return cls._git_executable

        # 1. Check configured setting
        configured = settings.GIT_EXECUTABLE_PATH
        if configured and os.path.isfile(configured):
            cls._git_executable = configured
            return configured

        # 2. Check system PATH
        discovered = shutil.which("git")
        if discovered:
            cls._git_executable = discovered
            return discovered

        raise GitExecutionError(
            "Git executable not found on host system. Git must be installed and accessible."
        )

    @classmethod
    def is_git_available(cls) -> bool:
        """Check if Git binary is resolvable."""
        try:
            cls.resolve_git_binary()
            return True
        except GitExecutionError:
            return False

    @classmethod
    def sanitize_output(cls, raw: str) -> str:
        """Redact potential secrets or credentials from git output."""
        if not raw:
            return ""
        # Redact tokens, passwords, bearer credentials
        sanitized = re.sub(r"://([^:@]+):([^@]+)@", r"://\1:[REDACTED]@", raw)
        sanitized = re.sub(r"(token|secret|password|api[_-]?key)=([^\s&]+)", r"\1=[REDACTED]", sanitized, flags=re.IGNORECASE)
        sanitized = re.sub(r"Bearer\s+[A-Za-z0-9_\-\.]+", "Bearer [REDACTED]", sanitized)
        return sanitized

    @classmethod
    def execute(
        cls,
        subcommand: str,
        args: List[str],
        cwd: Path,
        stdin_content: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> Tuple[int, str, str]:
        """Execute an allowlisted Git subcommand safely using argument arrays and shell=False.

        Args:
            subcommand: Allowed Git subcommand (e.g. 'worktree', 'status', 'apply', 'diff')
            args: Command arguments as a string list (never shell-escaped string)
            cwd: Working directory (must be a validated existing Path)
            stdin_content: Optional content piped to stdin (e.g. unified patch diff)
            timeout: Subprocess timeout in seconds

        Returns:
            Tuple of (returncode, stdout, stderr)
        """
        subcommand_clean = subcommand.strip().lower()
        if subcommand_clean in FORBIDDEN_GIT_SUBCOMMANDS or subcommand_clean not in ALLOWED_GIT_SUBCOMMANDS:
            raise SecurityViolationError(
                f"Forbidden Git subcommand '{subcommand}'. Only allowlisted operational commands are permitted."
            )

        # Ensure cwd exists and is a directory
        if not cwd.exists() or not cwd.is_dir():
            raise GitExecutionError(f"Target working directory '{cwd}' does not exist or is not a directory.")

        git_bin = cls.resolve_git_binary()
        cmd = [git_bin, subcommand_clean] + args

        # Build clean sanitized environment
        safe_env = {
            "PATH": os.environ.get("PATH", ""),
            "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
            "COMSPEC": os.environ.get("COMSPEC", ""),
            "TMP": os.environ.get("TMP", ""),
            "TEMP": os.environ.get("TEMP", ""),
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_CONFIG_NOSYSTEM": "1",
            "LC_ALL": "C",
        }

        effective_timeout = timeout or settings.GIT_SUBPROCESS_TIMEOUT

        stdin_data = stdin_content.encode("utf-8") if stdin_content else None

        try:
            process = subprocess.run(
                cmd,
                cwd=str(cwd.resolve()),
                input=stdin_data,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=False,
                timeout=effective_timeout,
                env=safe_env,
            )
            stdout = cls.sanitize_output(process.stdout[:MAX_OUTPUT_BYTES].decode("utf-8", errors="replace"))
            stderr = cls.sanitize_output(process.stderr[:MAX_OUTPUT_BYTES].decode("utf-8", errors="replace"))
            return process.returncode, stdout, stderr
        except subprocess.TimeoutExpired as exc:
            logger.error("Git command timed out after %s seconds: %s", effective_timeout, subcommand_clean)
            raise GitExecutionError(
                f"Git command '{subcommand_clean}' timed out after {effective_timeout}s."
            ) from exc
        except Exception as exc:
            if isinstance(exc, GitExecutionError) or isinstance(exc, SecurityViolationError):
                raise
            logger.error("Git execution error on %s: %s", subcommand_clean, str(exc))
            raise GitExecutionError(f"Git execution failed on '{subcommand_clean}': {str(exc)}") from exc

    @classmethod
    def is_git_repository(cls, repo_path: Path) -> bool:
        """Verify that the target path is a valid Git repository."""
        code, stdout, _ = cls.execute("rev-parse", ["--is-inside-work-tree"], cwd=repo_path)
        return code == 0 and "true" in stdout.strip().lower()

    @classmethod
    def verify_commit_exists(cls, repo_path: Path, commit_sha: str) -> bool:
        """Verify that a commit SHA exists in the repository."""
        if not commit_sha or not re.match(r"^[0-9a-fA-F]{4,40}$", commit_sha.strip()):
            return False
        code, _, _ = cls.execute("cat-file", ["-e", f"{commit_sha.strip()}^{{commit}}"], cwd=repo_path)
        return code == 0

    @classmethod
    def get_head_commit(cls, repo_path: Path) -> str:
        """Retrieve current HEAD commit SHA."""
        code, stdout, stderr = cls.execute("rev-parse", ["HEAD"], cwd=repo_path)
        if code != 0:
            raise GitExecutionError(f"Failed to resolve HEAD commit: {stderr}")
        return stdout.strip()

    @classmethod
    def is_worktree_clean(cls, path: Path) -> bool:
        """Verify that a worktree has no modified or untracked files."""
        code, stdout, _ = cls.execute("status", ["--porcelain"], cwd=path)
        return code == 0 and len(stdout.strip()) == 0

    @classmethod
    def apply_check(cls, worktree_path: Path, patch_content: str) -> Tuple[bool, str]:
        """Dry-run test patch application using 'git apply --check -' via stdin."""
        code, stdout, stderr = cls.execute(
            "apply",
            ["--check", "-"],
            cwd=worktree_path,
            stdin_content=patch_content,
        )
        if code == 0:
            return True, ""
        error_msg = (stderr or stdout).strip()
        return False, error_msg

    @classmethod
    def apply_patch(cls, worktree_path: Path, patch_content: str) -> Tuple[bool, str]:
        """Apply patch to the worktree using 'git apply --whitespace=nowarn -' via stdin."""
        code, stdout, stderr = cls.execute(
            "apply",
            ["--whitespace=nowarn", "-"],
            cwd=worktree_path,
            stdin_content=patch_content,
        )
        if code == 0:
            return True, ""
        error_msg = (stderr or stdout).strip()
        return False, error_msg

    @classmethod
    def get_modified_files(cls, worktree_path: Path) -> List[str]:
        """Get list of files modified in the worktree."""
        code, stdout, stderr = cls.execute("diff", ["--name-only"], cwd=worktree_path)
        if code != 0:
            raise GitExecutionError(f"Failed to inspect worktree diff: {stderr}")
        lines = [line.strip().replace("\\", "/") for line in stdout.splitlines() if line.strip()]
        return lines

    @classmethod
    def get_diff_stats(cls, worktree_path: Path) -> Tuple[int, int]:
        """Get lines added and lines removed in the worktree diff."""
        code, stdout, _ = cls.execute("diff", ["--numstat"], cwd=worktree_path)
        if code != 0:
            return 0, 0
        added = 0
        removed = 0
        for line in stdout.splitlines():
            parts = line.strip().split("\t")
            if len(parts) >= 2:
                try:
                    added += int(parts[0]) if parts[0] != "-" else 0
                    removed += int(parts[1]) if parts[1] != "-" else 0
                except ValueError:
                    pass
        return added, removed

