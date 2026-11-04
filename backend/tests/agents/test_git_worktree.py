import subprocess
import tempfile
import uuid
from pathlib import Path
import pytest

from app.agents.application.exceptions import (
    GitExecutionError,
    GitWorktreeError,
    InvalidBaseCommitError,
    SecurityViolationError,
)
from app.agents.application.git_executor import SafeGitExecutor
from app.agents.application.worktree_manager import WorktreeManager


@pytest.fixture
def temp_git_repo():
    """Create a temporary real Git repository with an initial commit for testing."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        repo_path = Path(tmp_dir).resolve()

        # Initialize Git repo
        subprocess.run(["git", "init"], cwd=str(repo_path), check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@nexops.local"],
            cwd=str(repo_path),
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "NexOps Test"],
            cwd=str(repo_path),
            check=True,
            capture_output=True,
        )

        # Create an initial file and commit
        sample_file = repo_path / "app.py"
        sample_file.write_text("def run():\n    return 'initial'\n", encoding="utf-8")

        subprocess.run(["git", "add", "app.py"], cwd=str(repo_path), check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=str(repo_path),
            check=True,
            capture_output=True,
        )

        # Get initial commit SHA
        head_sha = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=str(repo_path),
            text=True,
        ).strip()

        yield repo_path, head_sha


def test_safe_git_executor_is_available():
    """Verify Git binary is resolvable on the host system."""
    assert SafeGitExecutor.is_git_available() is True
    bin_path = SafeGitExecutor.resolve_git_binary()
    assert bin_path is not None


def test_safe_git_executor_forbidden_command_rejected(temp_git_repo):
    """Verify forbidden git commands like push, commit, merge are strictly blocked."""
    repo_path, _ = temp_git_repo

    for forbidden in ["push", "merge", "commit", "rebase", "reset"]:
        with pytest.raises(SecurityViolationError) as exc_info:
            SafeGitExecutor.execute(forbidden, ["origin", "main"], cwd=repo_path)
        assert "Forbidden Git subcommand" in str(exc_info.value)


def test_safe_git_executor_secret_redaction():
    """Verify passwords, tokens, and authorization headers are redacted."""
    raw = "Connecting to https://user:super_secret_password@github.com/repo with token=ghp_123456789 and Bearer my_jwt_token"
    sanitized = SafeGitExecutor.sanitize_output(raw)

    assert "super_secret_password" not in sanitized
    assert "[REDACTED]" in sanitized
    assert "ghp_123456789" not in sanitized
    assert "my_jwt_token" not in sanitized


def test_worktree_creation_and_cleanup(temp_git_repo):
    """Test creating an isolated worktree from a valid base commit, then cleaning it up."""
    repo_path, head_sha = temp_git_repo
    patch_id = uuid.uuid4()

    # 1. Create worktree
    wt_path = WorktreeManager.create_worktree(
        repo_path=repo_path,
        patch_id=patch_id,
        base_commit=head_sha,
    )

    assert wt_path.exists()
    assert wt_path.is_dir()
    # Check that file exists inside worktree
    wt_file = wt_path / "app.py"
    assert wt_file.exists()
    assert "initial" in wt_file.read_text(encoding="utf-8")

    # Verify worktree is clean
    assert SafeGitExecutor.is_worktree_clean(wt_path) is True

    # 2. Cleanup worktree
    cleaned = WorktreeManager.remove_worktree(repo_path, wt_path)
    assert cleaned is True
    assert not wt_path.exists()


def test_worktree_invalid_base_commit_rejected(temp_git_repo):
    """Test worktree creation fails when an invalid base commit is specified."""
    repo_path, _ = temp_git_repo
    patch_id = uuid.uuid4()

    with pytest.raises(InvalidBaseCommitError) as exc_info:
        WorktreeManager.create_worktree(
            repo_path=repo_path,
            patch_id=patch_id,
            base_commit="deadbeefdeadbeefdeadbeefdeadbeefdeadbeef",
        )
    assert "does not exist in repository" in str(exc_info.value)


def test_worktree_nonexistent_repo_rejected():
    """Test worktree creation fails when target repo does not exist."""
    fake_path = Path("/path/that/definitely/does/not/exist")
    with pytest.raises(GitWorktreeError):
        WorktreeManager.create_worktree(
            repo_path=fake_path,
            patch_id=uuid.uuid4(),
            base_commit="abc1234",
        )

