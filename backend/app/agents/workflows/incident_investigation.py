from typing import Optional
from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.graph import END, START, StateGraph

from app.agents.nodes import (
    create_investigate_node,
    prepare_context_node,
    validate_and_format_node,
)
from app.agents.state import InvestigationState


def create_investigation_graph(llm: Optional[BaseChatModel] = None):
    """Build and compile the LangGraph incident investigation workflow.

    Flow:
        START -> prepare_context -> investigate -> validate_and_format -> END
    """
    workflow = StateGraph(InvestigationState)

    workflow.add_node("prepare_context", prepare_context_node)
    workflow.add_node("investigate", create_investigate_node(llm=llm))
    workflow.add_node("validate_and_format", validate_and_format_node)

    workflow.add_edge(START, "prepare_context")
    workflow.add_edge("prepare_context", "investigate")
    workflow.add_edge("investigate", "validate_and_format")
    workflow.add_edge("validate_and_format", END)

    return workflow.compile()

