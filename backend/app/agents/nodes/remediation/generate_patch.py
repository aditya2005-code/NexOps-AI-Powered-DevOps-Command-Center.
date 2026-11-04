import logging
from typing import Any, Callable, Dict, Optional
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.llm import get_llm
from app.agents.prompts.remediation import REMEDIATION_SYSTEM_PROMPT
from app.agents.schemas.remediation import ProposedPatch
from app.agents.state.remediation_state import RemediationState

logger = logging.getLogger("nexops.agents.nodes.remediation.generate_patch")


def create_generate_patch_node(
    llm: Optional[BaseChatModel] = None,
) -> Callable[[RemediationState], Dict[str, Any]]:
    """Factory creating the patch generation node with structured Pydantic output."""

    def generate_patch_node(state: RemediationState) -> Dict[str, Any]:
        eligibility = state.get("eligibility", {})
        if eligibility.get("status") != "eligible":
            return {"proposed_patch": None}

        # If source context was empty, cannot generate grounded patch
        source_context = state.get("source_context", [])
        if not source_context:
            err = "Source context for authorized files could not be retrieved from workspace."
            existing_errors = list(state.get("errors", []))
            existing_errors.append(err)
            return {
                "proposed_patch": None,
                "errors": existing_errors,
                "execution_status": "failed",
            }

        model = llm or get_llm()
        structured_model = model.with_structured_output(ProposedPatch)

        context = state.get("remediation_context", "")
        messages = [
            SystemMessage(content=REMEDIATION_SYSTEM_PROMPT),
            HumanMessage(content=context),
        ]

        try:
            logger.info("Generating code patch for incident %s", state.get("incident_id"))
            result = structured_model.invoke(messages)

            if isinstance(result, ProposedPatch):
                patch_data = result.model_dump()
            elif isinstance(result, dict):
                patch_data = result
            else:
                patch_data = ProposedPatch.model_validate(result).model_dump()

            return {
                "proposed_patch": patch_data,
                "execution_status": "completed",
            }
        except Exception as exc:
            err_msg = f"{type(exc).__name__}: {str(exc)}"
            logger.error("Patch generation failed: %s", err_msg)
            existing_errors = list(state.get("errors", []))
            existing_errors.append(err_msg)
            return {
                "proposed_patch": None,
                "errors": existing_errors,
                "execution_status": "failed",
            }

    return generate_patch_node

