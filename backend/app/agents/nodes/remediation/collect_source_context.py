from typing import Any, Dict, List
from app.agents.prompts.remediation import format_remediation_prompt
from app.agents.state.remediation_state import RemediationState
from app.agents.tools import tool_registry


def collect_source_context_node(state: RemediationState) -> Dict[str, Any]:
    """Node: Reads authorized source code files using SourceInspectionTool and formats LLM context."""
    eligibility = state.get("eligibility", {})
    if eligibility.get("status") != "eligible":
        return {"source_context": [], "remediation_context": ""}

    workspace_path = state.get("project_workspace_path")
    target_files = state.get("target_files", [])
    plan = state.get("remediation_plan") or {}

    collected_sources: List[Dict[str, Any]] = []
    source_context_blocks: List[str] = []

    for rel_path in target_files:
        read_res = tool_registry.execute(
            "source_inspector",
            operation="read_file",
            workspace_path=workspace_path,
            relative_path=rel_path,
            start_line=1,
            max_lines=150,
        )
        if read_res.success and read_res.data and read_res.data.get("status") == "success":
            content = read_res.data.get("content", "")
            collected_sources.append({
                "file_path": rel_path,
                "content": content,
                "line_count": read_res.data.get("line_count", 0),
            })
            source_context_blocks.append(f"=== File: {rel_path} ===\n{content}\n")
        else:
            err_msg = read_res.error or (read_res.data.get("error") if read_res.data else "Read failed")
            source_context_blocks.append(f"=== File: {rel_path} === [UNAVAILABLE: {err_msg}]\n")

    # Format evidence summary
    inv = state.get("investigation_result", {})
    evidence_lines: List[str] = []
    for ev in inv.get("evidence_items", []):
        evidence_lines.append(
            f"[{ev.get('evidence_id')}] ({ev.get('source')}/{ev.get('classification')}): {ev.get('description')}"
        )
    evidence_text = "\n".join(evidence_lines)

    # Format full prompt context
    prompt = format_remediation_prompt(
        incident_title=state.get("incident_title", "Untitled Incident"),
        root_cause_hypothesis=plan.get("selected_hypothesis", "Identified bug"),
        technical_rationale=plan.get("technical_rationale", ""),
        evidence_text=evidence_text,
        source_context_text="\n".join(source_context_blocks),
        target_files=target_files,
    )

    return {
        "source_context": collected_sources,
        "remediation_context": prompt,
    }

