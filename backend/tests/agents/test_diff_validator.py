from app.agents.remediation.diff_validator import DiffValidator

SAMPLE_VALID_DIFF = """--- a/backend/app/gateway.py
+++ b/backend/app/gateway.py
@@ -10,5 +10,8 @@
 def forward_request(url, timeout=30):
     try:
         return requests.get(url, timeout=timeout)
+    except requests.exceptions.Timeout:
+        logger.warning("Gateway timeout occurred")
+        return None
     except Exception as exc:
         raise exc
"""


def test_diff_validator_valid_diff():
    res = DiffValidator.validate(
        diff_content=SAMPLE_VALID_DIFF,
        authorized_files=["backend/app/gateway.py"],
    )
    assert res.is_valid is True
    assert res.syntax_valid is True
    assert res.authorized_files_only is True
    assert res.lines_added == 3
    assert res.lines_removed == 0
    assert len(res.validation_errors) == 0


def test_diff_validator_empty_content():
    res = DiffValidator.validate(diff_content="")
    assert res.is_valid is False
    assert "empty" in res.validation_errors[0]


def test_diff_validator_binary_diff_rejected():
    binary_diff = "GIT binary patch\nliteral 1234\n..."
    res = DiffValidator.validate(diff_content=binary_diff)
    assert res.is_valid is False
    assert "Binary patches are strictly forbidden" in res.validation_errors[0]


def test_diff_validator_missing_headers():
    malformed = """@@ -1,3 +1,3 @@
 def test():
+    pass
-    fail()
"""
    res = DiffValidator.validate(diff_content=malformed)
    assert res.is_valid is False
    assert any("missing file headers" in err for err in res.validation_errors)


def test_diff_validator_unauthorized_file_rejected():
    res = DiffValidator.validate(
        diff_content=SAMPLE_VALID_DIFF,
        authorized_files=["backend/app/unrelated.py"],
    )
    assert res.is_valid is False
    assert res.authorized_files_only is False
    assert any("was not authorized" in err for err in res.validation_errors)


def test_diff_validator_path_traversal_rejected():
    traversal_diff = """--- a/../../etc/passwd
+++ b/../../etc/passwd
@@ -1,1 +1,1 @@
-root:x:0:0
+root:x:0:0:hacked
"""
    res = DiffValidator.validate(diff_content=traversal_diff)
    assert res.is_valid is False
    assert any("path traversal" in err for err in res.validation_errors)


def test_diff_validator_line_count_limit():
    large_diff_lines = [
        "--- a/file.py",
        "+++ b/file.py",
        "@@ -1,1 +1,600 @@",
    ] + ["+extra line" for _ in range(600)]
    large_diff = "\n".join(large_diff_lines)

    res = DiffValidator.validate(diff_content=large_diff, max_lines=500)
    assert res.is_valid is False
    assert any("exceeding limit of 500" in err for err in res.validation_errors)


def test_diff_validator_malformed_hunk_counts():
    """Verify mismatch between hunk header -x,+y counts and actual lines is caught."""
    # Header says -3,+3 but hunk contains 4 old lines and 3 new lines
    bad_hunk_diff = """--- a/service.py
+++ b/service.py
@@ -10,3 +10,3 @@
 line 1
 line 2
-line 3
-extra deleted line
+line 3 replacement
"""
    res = DiffValidator.validate(
        diff_content=bad_hunk_diff,
        authorized_files=["service.py"],
    )
    assert res.is_valid is False
    assert any("Hunk line count mismatch" in err for err in res.validation_errors)


def test_diff_validator_altered_source_context():
    """Verify diff where original hunk lines do not match actual source snapshot is rejected."""
    hallucinated_diff = """--- a/service.py
+++ b/service.py
@@ -1,2 +1,2 @@
-def completely_hallucinated_function():
+def real_function():
     return True
"""
    real_snapshot = {
        "service.py": "def actual_existing_function():\n    return False\n"
    }

    res = DiffValidator.validate(
        diff_content=hallucinated_diff,
        authorized_files=["service.py"],
        source_snapshots=real_snapshot,
    )
    assert res.is_valid is False
    assert any("Source context mismatch" in err for err in res.validation_errors)


def test_diff_validator_duplicate_file_headers():
    """Verify duplicate file declarations for the same file are detected."""
    duplicate_diff = """--- a/service.py
+++ b/service.py
@@ -1,2 +1,2 @@
-x = 1
+x = 2
--- a/service.py
+++ b/service.py
@@ -10,2 +10,2 @@
-y = 1
+y = 2
"""
    res = DiffValidator.validate(
        diff_content=duplicate_diff,
        authorized_files=["service.py"],
    )
    assert res.is_valid is False
    assert any("Duplicate file header" in err for err in res.validation_errors)


def test_diff_validator_windows_path_traversal_and_drive_letters():
    """Verify Windows drive letters and Windows backslash traversals are rejected."""
    # Drive letter
    drive_diff = """--- a/C:/Windows/System32/drivers/etc/hosts
+++ b/C:/Windows/System32/drivers/etc/hosts
@@ -1,1 +1,1 @@
-127.0.0.1 localhost
+0.0.0.0 localhost
"""
    res_drive = DiffValidator.validate(diff_content=drive_diff)
    assert res_drive.is_valid is False
    assert any("drive-letter" in err for err in res_drive.validation_errors)

    # Backslash traversal
    backslash_diff = """--- a/..\\..\\secret.txt
+++ b/..\\..\\secret.txt
@@ -1,1 +1,1 @@
-old
+new
"""
    res_bs = DiffValidator.validate(diff_content=backslash_diff)
    assert res_bs.is_valid is False
    assert any("path traversal" in err for err in res_bs.validation_errors)


def test_diff_validator_file_creation_and_deletion_rejected():
    """Verify file creation and deletion are rejected by policy."""
    # Deletion
    del_diff = """--- a/important.py
+++ /dev/null
@@ -1,2 +0,0 @@
-def delete_me():
-    pass
"""
    res_del = DiffValidator.validate(diff_content=del_diff)
    assert res_del.is_valid is False
    assert any("File deletion (+++ /dev/null) is strictly prohibited" in err for err in res_del.validation_errors)

    # Creation
    create_diff = """--- /dev/null
+++ b/new_file.py
@@ -0,0 +1,2 @@
+def brand_new():
+    pass
"""
    res_create = DiffValidator.validate(diff_content=create_diff)
    assert res_create.is_valid is False
    assert any("File creation (--- /dev/null) is not permitted" in err for err in res_create.validation_errors)


def test_diff_validator_disallowed_file_extensions():
    """Verify unexpected/executable/sensitive file extensions are rejected."""
    for bad_file in ["malicious.exe", "script.sh", "config.env", "cert.pem", "agent.ps1"]:
        diff = f"""--- a/{bad_file}
+++ b/{bad_file}
@@ -1,1 +1,1 @@
-x
+y
"""
        res = DiffValidator.validate(diff_content=diff)
        assert res.is_valid is False
        assert any("Disallowed file extension" in err for err in res.validation_errors)
