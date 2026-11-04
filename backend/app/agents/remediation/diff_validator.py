import os
import re
from typing import Dict, List, Optional, Set
from app.agents.schemas.remediation import PatchValidationResult

HUNK_HEADER_REGEX = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
FILE_HEADER_OLD = re.compile(r"^--- (?:a/)?([^\s\t]+)")
FILE_HEADER_NEW = re.compile(r"^\+\+\+ (?:b/)?([^\s\t]+)")
BINARY_DIFF_REGEX = re.compile(r"GIT binary patch|Binary files .* differ", re.IGNORECASE)
DRIVE_LETTER_REGEX = re.compile(r"^[a-zA-Z]:", re.IGNORECASE)

MAX_PATCH_LINES = 500
MAX_PATCH_FILES = 5

ALLOWED_EXTENSIONS = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".go",
    ".java",
    ".rs",
    ".json",
    ".yaml",
    ".yml",
    ".sql",
    ".toml",
    ".md",
    ".txt",
    ".html",
    ".css",
}

DISALLOWED_EXTENSIONS = {
    ".exe",
    ".bat",
    ".cmd",
    ".sh",
    ".ps1",
    ".dll",
    ".so",
    ".bin",
    ".env",
    ".pem",
    ".key",
    ".token",
    ".crt",
}


class DiffValidator:
    """Validates unified Git diff syntax, hunk line counts, file path boundaries, and source context."""

    @classmethod
    def validate(
        cls,
        diff_content: str,
        authorized_files: Optional[List[str]] = None,
        source_snapshots: Optional[Dict[str, str]] = None,
        max_lines: int = MAX_PATCH_LINES,
        max_files: int = MAX_PATCH_FILES,
    ) -> PatchValidationResult:
        errors: List[str] = []

        if not diff_content or not diff_content.strip():
            return PatchValidationResult(
                is_valid=False,
                syntax_valid=False,
                authorized_files_only=False,
                lines_added=0,
                lines_removed=0,
                validation_errors=["Patch content is empty or contains only whitespace."],
            )

        if BINARY_DIFF_REGEX.search(diff_content):
            return PatchValidationResult(
                is_valid=False,
                syntax_valid=False,
                authorized_files_only=False,
                lines_added=0,
                lines_removed=0,
                validation_errors=["Binary patches are strictly forbidden."],
            )

        lines = diff_content.splitlines()
        lines_added = 0
        lines_removed = 0
        touched_files: Set[str] = set()

        seen_file_headers: Set[str] = set()
        has_file_header = False
        current_file: Optional[str] = None

        # Tracking for hunk line counts
        current_hunk_old_expected = 0
        current_hunk_new_expected = 0
        current_hunk_old_actual = 0
        current_hunk_new_actual = 0
        current_hunk_header_line = 0
        in_hunk = False

        # Accumulator for old lines in current hunk to verify against source context
        current_hunk_old_lines: List[str] = []

        def finalize_hunk():
            nonlocal in_hunk, current_hunk_old_actual, current_hunk_new_actual, current_hunk_old_lines
            if in_hunk:
                if (current_hunk_old_actual != current_hunk_old_expected) or (
                    current_hunk_new_actual != current_hunk_new_expected
                ):
                    errors.append(
                        f"Line {current_hunk_header_line}: Hunk line count mismatch: "
                        f"header specifies -{current_hunk_old_expected},+{current_hunk_new_expected}, "
                        f"but hunk contains -{current_hunk_old_actual},+{current_hunk_new_actual} lines."
                    )

                # Verify original source context against authorized snapshot if provided
                if source_snapshots and current_file:
                    norm_curr = current_file.replace("\\", "/").lstrip("/")
                    snapshot_text = source_snapshots.get(norm_curr)
                    if snapshot_text is not None and current_hunk_old_lines:
                        # Extract non-empty old context lines (stripping leading spaces/minuses)
                        clean_old_lines = [
                            l for l in current_hunk_old_lines if l.strip()
                        ]
                        if clean_old_lines:
                            # Verify that at least the core old context lines exist in snapshot
                            missing_lines = [
                                l for l in clean_old_lines if l not in snapshot_text
                            ]
                            if missing_lines:
                                errors.append(
                                    f"Line {current_hunk_header_line}: Source context mismatch in '{current_file}': "
                                    f"original hunk lines do not match authorized source snapshot: {missing_lines[0][:60]!r}"
                                )

                in_hunk = False
                current_hunk_old_actual = 0
                current_hunk_new_actual = 0
                current_hunk_old_lines = []

        for idx, line in enumerate(lines, start=1):
            # Check old file header: --- a/file
            old_match = FILE_HEADER_OLD.match(line)
            if old_match:
                finalize_hunk()
                old_file_raw = old_match.group(1).replace("\\", "/")
                if old_file_raw == "/dev/null":
                    errors.append(
                        f"Line {idx}: File creation (--- /dev/null) is not permitted. Only modifications to existing files are allowed."
                    )
                continue

            # Check new file header: +++ b/file
            new_match = FILE_HEADER_NEW.match(line)
            if new_match:
                finalize_hunk()
                new_file_raw = new_match.group(1).replace("\\", "/")
                if new_file_raw == "/dev/null":
                    errors.append(
                        f"Line {idx}: File deletion (+++ /dev/null) is strictly prohibited in remediation patches."
                    )
                    continue

                if new_file_raw in seen_file_headers:
                    errors.append(
                        f"Line {idx}: Duplicate file header for '{new_file_raw}' detected in diff."
                    )
                seen_file_headers.add(new_file_raw)

                current_file = new_file_raw
                touched_files.add(new_file_raw)
                has_file_header = True
                continue

            # Check hunk header
            hunk_match = HUNK_HEADER_REGEX.match(line)
            if hunk_match:
                finalize_hunk()
                if not has_file_header:
                    errors.append(
                        f"Line {idx}: Hunk header found before unified diff file headers (--- / +++)."
                    )

                in_hunk = True
                current_hunk_header_line = idx

                # Parse expected line counts (default to 1 if count is omitted in @@ -x +y @@)
                current_hunk_old_expected = (
                    int(hunk_match.group(2)) if hunk_match.group(2) is not None else 1
                )
                current_hunk_new_expected = (
                    int(hunk_match.group(4)) if hunk_match.group(4) is not None else 1
                )
                current_hunk_old_actual = 0
                current_hunk_new_actual = 0
                current_hunk_old_lines = []
                continue

            # Within a hunk, line must start with ' ', '+', '-', or '\'
            if in_hunk:
                if not line:
                    # An empty line in diff counts as a context line with empty content
                    current_hunk_old_actual += 1
                    current_hunk_new_actual += 1
                    continue

                prefix = line[0]
                content = line[1:]
                if prefix == "+":
                    lines_added += 1
                    current_hunk_new_actual += 1
                elif prefix == "-":
                    lines_removed += 1
                    current_hunk_old_actual += 1
                    current_hunk_old_lines.append(content)
                elif prefix == " ":
                    current_hunk_old_actual += 1
                    current_hunk_new_actual += 1
                    current_hunk_old_lines.append(content)
                elif prefix == "\\":
                    # "\ No newline at end of file"
                    pass
                else:
                    errors.append(
                        f"Line {idx}: Invalid diff line prefix '{prefix}'. Hunk lines must start with '+', '-', or ' '."
                    )
            elif not has_file_header:
                # Leading metadata like "diff --git" or "index" is acceptable
                if not (
                    line.startswith("diff --git")
                    or line.startswith("index ")
                    or line.startswith("#")
                ):
                    pass

        # Finalize trailing hunk
        finalize_hunk()

        if not has_file_header:
            errors.append("Unified diff missing file headers (--- a/file and +++ b/file).")

        if not touched_files:
            errors.append("Diff does not modify any valid target files.")

        if len(touched_files) > max_files:
            errors.append(
                f"Patch modifies {len(touched_files)} files, which exceeds the limit of {max_files}."
            )

        total_lines_changed = lines_added + lines_removed
        if total_lines_changed > max_lines:
            errors.append(
                f"Patch modifies {total_lines_changed} lines ({lines_added}+ / {lines_removed}-), exceeding limit of {max_lines}."
            )

        # Path traversal, drive letters, and unauthorized files check
        authorized_files_only = True
        normalized_auth = (
            {f.replace("\\", "/").lstrip("/") for f in authorized_files}
            if authorized_files is not None
            else None
        )

        for tf in touched_files:
            norm_path = tf.replace("\\", "/")

            # Reject drive letters (C:\, D:/, etc.)
            if DRIVE_LETTER_REGEX.match(norm_path) or ":" in norm_path:
                errors.append(
                    f"Security error: Diff contains drive-letter or absolute path '{tf}'."
                )
                authorized_files_only = False

            # Reject absolute paths (starting with / or \)
            if tf.startswith("/") or tf.startswith("\\") or norm_path.startswith("/"):
                errors.append(
                    f"Security error: Diff contains absolute path '{tf}'."
                )
                authorized_files_only = False

            # Reject path traversal (..)
            if ".." in tf or "/../" in norm_path or norm_path.startswith("../"):
                errors.append(
                    f"Security error: Diff attempts invalid path traversal on '{tf}'."
                )
                authorized_files_only = False

            # Check file extensions
            _, ext = os.path.splitext(norm_path)
            ext_lower = ext.lower()
            if ext_lower in DISALLOWED_EXTENSIONS:
                errors.append(
                    f"Security error: Disallowed file extension '{ext}' in target file '{tf}'."
                )
                authorized_files_only = False
            elif ext_lower and ext_lower not in ALLOWED_EXTENSIONS:
                errors.append(
                    f"Security error: Unexpected file extension '{ext}' in target file '{tf}'."
                )
                authorized_files_only = False

            # Check authorization if list is provided
            if normalized_auth is not None and norm_path.lstrip("/") not in normalized_auth:
                errors.append(
                    f"Unauthorized file modification: '{tf}' was not authorized for remediation."
                )
                authorized_files_only = False

        syntax_valid = (
            len(errors) == 0 and has_file_header and (lines_added + lines_removed > 0)
        )
        is_valid = syntax_valid and authorized_files_only

        return PatchValidationResult(
            is_valid=is_valid,
            syntax_valid=syntax_valid,
            authorized_files_only=authorized_files_only,
            lines_added=lines_added,
            lines_removed=lines_removed,
            validation_errors=errors,
        )
