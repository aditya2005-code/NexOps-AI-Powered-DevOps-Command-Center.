import logging
from typing import Any, Callable, Dict, Optional
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.llm import get_llm
from app.agents.prompts import SYSTEM_PROMPT
from app.agents.schemas.investigation import InvestigationResult
from app.agents.state import InvestigationState

logger = logging.getLogger("nexops.agents.nodes.investigate")


def create_investigate_node(
    llm: Optional[BaseChatModel] = None,
) -> Callable[[InvestigationState], Dict[str, Any]]:
    """Factory creating the investigation execution node with optional model injection."""

    def investigate_node(state: InvestigationState) -> Dict[str, Any]:
        """Invoke the configured LLM with structured output schema."""
        model = llm or get_llm()
        structured_model = model.with_structured_output(InvestigationResult)

        context = state.get("investigation_context", "")
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=context),
        ]

        try:
            logger.info("Executing LLM investigation for incident: %s", state.get("incident_id"))
            result = structured_model.invoke(messages)

            # Handle Pydantic model vs dict result
            if isinstance(result, InvestigationResult):
                output_data = result.model_dump()
            elif isinstance(result, dict):
                output_data = result
            else:
                output_data = InvestigationResult.model_validate(result).model_dump()

            return {
                "investigation_result": output_data,
                "execution_status": "completed",
            }
        except Exception as exc:
            error_msg = f"{type(exc).__name__}: {str(exc)}"
            logger.error("LLM investigation failed: %s", error_msg)
            existing_errors = list(state.get("errors", []))
            existing_errors.append(error_msg)
            return {
                "errors": existing_errors,
                "execution_status": "failed",
            }

    return investigate_node

