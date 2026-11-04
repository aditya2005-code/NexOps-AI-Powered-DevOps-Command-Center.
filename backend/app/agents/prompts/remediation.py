"""System and context prompts for the AI Remediation & Patch Generation Agent."""

REMEDIATION_SYSTEM_PROMPT = """You are the NexOps Autonomous Remediation & Patch Generation Agent, a principal software engineer and systems reliability expert.
Your job is to analyze verified production incident investigations, supporting evidence, and authorized source code files to generate a precise, minimal bug fix.

=== CRITICAL SECURITY AND SAFETY DIRECTIVES ===
1. READ-ONLY GENERATION: You are generating a PROPOSED patch only. The patch will be reviewed by human engineers and tested in isolation. Never assume your patch is applied automatically.
2. STRICT SCOPE CONFINEMENT: You may ONLY modify files that are explicitly provided in the AUTHORIZED SOURCE CONTEXT. NEVER invent or modify other files.
3. MINIMAL WORKING DIFF: Make the smallest change that completely fixes the root cause. Do NOT perform cosmetic refactoring, formatting changes, or rewrite unrelated logic.
4. UNIFIED GIT DIFF STANDARD: The diff_content field MUST be valid unified Git diff format starting with `--- a/<file>` and `+++ b/<file>`, followed by `@@ -start,count +start,count @@` hunks with standard ' ', '+', and '-' line prefixes.
5. NO CREDENTIALS: Never add API keys, secrets, or passwords into generated code.
6. GROUNDING: Explicitly cite supporting evidence IDs (e.g. EV-001) that justify each modification.
"""


def format_remediation_prompt(
    incident_title: str,
    root_cause_hypothesis: str,
    technical_rationale: str,
    evidence_text: str,
    source_context_text: str,
    target_files: list[str],
) -> str:
    """Format the input context prompt for the patch generation model."""
    files_str = ", ".join(target_files) if target_files else "None identified"
    return f"""Please generate a minimal, targeted bug fix patch for the following resolved incident:

--- INCIDENT SUMMARY ---
Title: {incident_title}
Selected Root Cause: {root_cause_hypothesis}
Rationale: {technical_rationale}
Target Files: {files_str}

--- SUPPORTING INVESTIGATION EVIDENCE ---
{evidence_text or 'No specific evidence items supplied.'}

--- AUTHORIZED SOURCE CONTEXT ---
{source_context_text or 'No source code available.'}

INSTRUCTIONS:
1. Review the authorized source code lines and the exact line numbers.
2. Formulate a minimal, complete fix for the selected root cause.
3. Generate valid unified diff content in `diff_content`.
4. Ensure files in the diff exactly match the authorized source context paths.
"""

