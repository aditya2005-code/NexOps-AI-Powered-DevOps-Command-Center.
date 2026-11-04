import fnmatch
from pathlib import Path
from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.agents.tools.base import BaseDiagnosticTool

MAX_FILE_SIZE_BYTES = 100_000  # 100 KB
MAX_READ_LINES = 300
MAX_SEARCH_MATCHES = 20
MAX_LIST_FILES = 100

SENSITIVE_PATTERNS = [
    ".env*",
    "*.pem",
    "*.key",
    "*id_rsa*",
    "*.pkcs12",
    "*.p12",
    "*.pfx",
    "credentials*.json",
    "service_account*.json",
    "*secret*",
    "*password*",
    "*.token*",
    ".git/*",
    ".aws/*",
    ".ssh/*",
]

IGNORED_DIRECTORIES = {
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    ".pytest_cache",
    "dist",
    "build",
}


class CodeSearchMatch(BaseModel):
    file_path: str
    line_number: int
    line_content: str

    model_config = ConfigDict(from_attributes=True)


class SourceInspectionInput(BaseModel):
    workspace_path: Optional[str] = Field(
        None, description="Absolute workspace path configured for the project"
    )
    operation: Literal["list_files", "read_file", "search_code"] = Field(
        ..., description="Inspection action to perform"
    )
    relative_path: str = Field(
        default="", description="Relative path within the project workspace"
    )
    query: Optional[str] = Field(
        None, description="Search term or identifier for search_code"
    )
    start_line: int = Field(default=1, ge=1, description="Line number to begin reading from")
    max_lines: int = Field(
        default=MAX_READ_LINES, ge=1, le=MAX_READ_LINES, description="Max lines to read"
    )


class SourceInspectionOutput(BaseModel):
    operation: str
    status: Literal["success", "unavailable", "permission_denied", "not_found", "error"]
    workspace_configured: bool
    relative_path: Optional[str] = None
    files: List[str] = Field(default_factory=list)
    content: Optional[str] = None
    line_count: int = 0
    matches: List[CodeSearchMatch] = Field(default_factory=list)
    error: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class SourceInspectionTool(BaseDiagnosticTool):
    """Secure, read-only source-code inspection strictly bounded to a configured project workspace."""

    name = "source_inspector"
    description = (
        "Inspects authorized project source code to locate definitions, analyze stack trace lines, "
        "and inspect files within security boundaries."
    )
    input_schema = SourceInspectionInput
    output_schema = SourceInspectionOutput

    def execute(self, **kwargs) -> SourceInspectionOutput:
        workspace_raw = kwargs.get("workspace_path")
        operation = kwargs.get("operation")
        relative_path_raw = kwargs.get("relative_path", "")
        query = kwargs.get("query")
        start_line = kwargs.get("start_line", 1)
        max_lines = min(kwargs.get("max_lines", MAX_READ_LINES), MAX_READ_LINES)

        # 1. Verify workspace configuration
        if not workspace_raw:
            return SourceInspectionOutput(
                operation=operation,
                status="unavailable",
                workspace_configured=False,
                error="Project workspace is not configured or available for inspection.",
            )

        workspace_path = Path(workspace_raw).resolve()
        if not workspace_path.is_dir():
            return SourceInspectionOutput(
                operation=operation,
                status="unavailable",
                workspace_configured=False,
                error=f"Configured workspace directory '{workspace_raw}' does not exist on disk.",
            )

        # 2. Path Traversal & Escape Check
        target_path = (workspace_path / relative_path_raw).resolve()
        try:
            target_path.relative_to(workspace_path)
        except ValueError:
            return SourceInspectionOutput(
                operation=operation,
                status="permission_denied",
                workspace_configured=True,
                error="Access denied: specified path escapes the configured project workspace.",
            )

        # 3. Check for Sensitive Files
        if self._is_sensitive(target_path, workspace_path):
            return SourceInspectionOutput(
                operation=operation,
                status="permission_denied",
                workspace_configured=True,
                error="Access denied: file or directory matches protected sensitive patterns.",
            )

        # 4. Dispatch Operation
        if operation == "list_files":
            return self._list_files(workspace_path, target_path)
        elif operation == "read_file":
            return self._read_file(workspace_path, target_path, start_line, max_lines)
        elif operation == "search_code":
            return self._search_code(workspace_path, target_path, query or "")
        else:
            return SourceInspectionOutput(
                operation=operation,
                status="error",
                workspace_configured=True,
                error=f"Unknown operation: '{operation}'",
            )

    def _is_sensitive(self, target_path: Path, workspace_path: Path) -> bool:
        """Check if target path matches any sensitive file pattern or parent folder."""
        rel_path_str = str(target_path.relative_to(workspace_path)).replace("\\", "/")
        filename = target_path.name.lower()

        for pattern in SENSITIVE_PATTERNS:
            if fnmatch.fnmatch(filename, pattern.lower()) or fnmatch.fnmatch(
                rel_path_str.lower(), pattern.lower()
            ):
                return True
        return False

    def _list_files(self, workspace_path: Path, target_dir: Path) -> SourceInspectionOutput:
        """List non-ignored files within a directory up to 3 levels deep."""
        if not target_dir.is_dir():
            return SourceInspectionOutput(
                operation="list_files",
                status="not_found",
                workspace_configured=True,
                error=f"Directory '{target_dir.name}' not found.",
            )

        collected: List[str] = []
        try:
            for item in sorted(target_dir.rglob("*")):
                # Check for ignored directories
                parts = item.relative_to(workspace_path).parts
                if any(part in IGNORED_DIRECTORIES for part in parts):
                    continue
                if self._is_sensitive(item, workspace_path):
                    continue
                if item.is_file():
                    collected.append(str(item.relative_to(workspace_path)).replace("\\", "/"))
                    if len(collected) >= MAX_LIST_FILES:
                        break

            return SourceInspectionOutput(
                operation="list_files",
                status="success",
                workspace_configured=True,
                relative_path=str(target_dir.relative_to(workspace_path)).replace("\\", "/"),
                files=collected,
                line_count=len(collected),
            )
        except Exception as exc:
            return SourceInspectionOutput(
                operation="list_files",
                status="error",
                workspace_configured=True,
                error=f"Error listing files: {str(exc)}",
            )

    def _read_file(
        self, workspace_path: Path, file_path: Path, start_line: int, max_lines: int
    ) -> SourceInspectionOutput:
        """Read a bounded range of lines from an authorized file."""
        if not file_path.is_file():
            return SourceInspectionOutput(
                operation="read_file",
                status="not_found",
                workspace_configured=True,
                error=f"File '{file_path.name}' does not exist.",
            )

        # Enforce size limits
        size = file_path.stat().st_size
        if size > MAX_FILE_SIZE_BYTES:
            return SourceInspectionOutput(
                operation="read_file",
                status="permission_denied",
                workspace_configured=True,
                error=f"File exceeds maximum size limit of {MAX_FILE_SIZE_BYTES // 1000} KB (actual: {size // 1000} KB).",
            )

        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
            lines = content.splitlines()
            total_lines = len(lines)

            # Slice lines according to start_line and max_lines
            start_idx = max(0, start_line - 1)
            end_idx = min(total_lines, start_idx + max_lines)
            selected_lines = lines[start_idx:end_idx]

            formatted_content = "\n".join(
                f"{i + start_idx + 1:4d} | {line}" for i, line in enumerate(selected_lines)
            )

            return SourceInspectionOutput(
                operation="read_file",
                status="success",
                workspace_configured=True,
                relative_path=str(file_path.relative_to(workspace_path)).replace("\\", "/"),
                content=formatted_content,
                line_count=len(selected_lines),
            )
        except Exception as exc:
            return SourceInspectionOutput(
                operation="read_file",
                status="error",
                workspace_configured=True,
                error=f"Error reading file: {str(exc)}",
            )

    def _search_code(
        self, workspace_path: Path, target_dir: Path, query: str
    ) -> SourceInspectionOutput:
        """Search permitted files for identifier or error reference."""
        if not query or not query.strip():
            return SourceInspectionOutput(
                operation="search_code",
                status="error",
                workspace_configured=True,
                error="Search query must be non-empty.",
            )

        search_root = target_dir if target_dir.is_dir() else target_dir.parent
        matches: List[CodeSearchMatch] = []
        normalized_query = query.strip()

        try:
            for item in sorted(search_root.rglob("*")):
                if len(matches) >= MAX_SEARCH_MATCHES:
                    break
                parts = item.relative_to(workspace_path).parts
                if any(part in IGNORED_DIRECTORIES for part in parts):
                    continue
                if self._is_sensitive(item, workspace_path):
                    continue
                if not item.is_file() or item.stat().st_size > MAX_FILE_SIZE_BYTES:
                    continue

                try:
                    lines = item.read_text(encoding="utf-8", errors="replace").splitlines()
                    for line_num, line in enumerate(lines, start=1):
                        if normalized_query in line:
                            matches.append(
                                CodeSearchMatch(
                                    file_path=str(item.relative_to(workspace_path)).replace("\\", "/"),
                                    line_number=line_num,
                                    line_content=line.strip()[:200],
                                )
                            )
                            if len(matches) >= MAX_SEARCH_MATCHES:
                                break
                except Exception:
                    continue

            return SourceInspectionOutput(
                operation="search_code",
                status="success",
                workspace_configured=True,
                relative_path=str(search_root.relative_to(workspace_path)).replace("\\", "/"),
                matches=matches,
                line_count=len(matches),
            )
        except Exception as exc:
            return SourceInspectionOutput(
                operation="search_code",
                status="error",
                workspace_configured=True,
                error=f"Error searching code: {str(exc)}",
            )

