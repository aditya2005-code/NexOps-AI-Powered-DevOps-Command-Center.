import pytest
from app.agents.tools.source_inspector import SourceInspectionTool


@pytest.fixture
def temp_workspace(tmp_path):
    """Create an isolated, temporary project workspace for testing."""
    ws = tmp_path / "test_project"
    ws.mkdir()

    # Create safe source files
    src = ws / "src"
    src.mkdir()
    (src / "main.py").write_text(
        "def run():\n    print('Hello World')\n    raise ValueError('Sample error')\n",
        encoding="utf-8",
    )
    (src / "utils.py").write_text("def helper():\n    return 42\n", encoding="utf-8")

    # Create sensitive files
    (ws / ".env").write_text("DATABASE_PASSWORD=supersecret", encoding="utf-8")
    (ws / "server.pem").write_text("-----BEGIN RSA PRIVATE KEY-----", encoding="utf-8")
    (ws / "credentials.json").write_text('{"token": "xyz"}', encoding="utf-8")

    # Create oversized file
    (ws / "huge.log").write_text("A" * 150_000, encoding="utf-8")

    return ws


def test_source_inspector_unconfigured_workspace():
    tool = SourceInspectionTool()
    output = tool.execute(operation="list_files", workspace_path=None)
    assert output.status == "unavailable"
    assert output.workspace_configured is False
    assert "not configured" in output.error


def test_source_inspector_nonexistent_workspace(tmp_path):
    tool = SourceInspectionTool()
    non_existent = str(tmp_path / "does_not_exist")
    output = tool.execute(operation="list_files", workspace_path=non_existent)
    assert output.status == "unavailable"
    assert "does not exist" in output.error


def test_source_inspector_path_traversal_rejection(temp_workspace):
    tool = SourceInspectionTool()
    # Attempt to escape workspace with ../
    output = tool.execute(
        operation="read_file",
        workspace_path=str(temp_workspace),
        relative_path="../../etc/passwd",
    )
    assert output.status == "permission_denied"
    assert "escapes the configured project workspace" in output.error


def test_source_inspector_sensitive_file_rejection(temp_workspace):
    tool = SourceInspectionTool()

    # .env
    out_env = tool.execute(
        operation="read_file",
        workspace_path=str(temp_workspace),
        relative_path=".env",
    )
    assert out_env.status == "permission_denied"
    assert "matches protected sensitive patterns" in out_env.error

    # .pem
    out_pem = tool.execute(
        operation="read_file",
        workspace_path=str(temp_workspace),
        relative_path="server.pem",
    )
    assert out_pem.status == "permission_denied"

    # credentials.json
    out_cred = tool.execute(
        operation="read_file",
        workspace_path=str(temp_workspace),
        relative_path="credentials.json",
    )
    assert out_cred.status == "permission_denied"


def test_source_inspector_file_size_limit(temp_workspace):
    tool = SourceInspectionTool()
    out = tool.execute(
        operation="read_file",
        workspace_path=str(temp_workspace),
        relative_path="huge.log",
    )
    assert out.status == "permission_denied"
    assert "exceeds maximum size limit" in out.error


def test_source_inspector_list_and_read_files(temp_workspace):
    tool = SourceInspectionTool()

    # List files
    list_out = tool.execute(operation="list_files", workspace_path=str(temp_workspace))
    assert list_out.status == "success"
    assert "src/main.py" in list_out.files
    assert "src/utils.py" in list_out.files
    assert ".env" not in list_out.files  # Filtered out
    assert "server.pem" not in list_out.files

    # Read safe file
    read_out = tool.execute(
        operation="read_file",
        workspace_path=str(temp_workspace),
        relative_path="src/main.py",
        start_line=1,
        max_lines=10,
    )
    assert read_out.status == "success"
    assert "def run():" in read_out.content
    assert "ValueError" in read_out.content


def test_source_inspector_search_code(temp_workspace):
    tool = SourceInspectionTool()
    search_out = tool.execute(
        operation="search_code",
        workspace_path=str(temp_workspace),
        query="ValueError",
    )
    assert search_out.status == "success"
    assert len(search_out.matches) == 1
    assert search_out.matches[0].file_path == "src/main.py"
    assert "raise ValueError" in search_out.matches[0].line_content

