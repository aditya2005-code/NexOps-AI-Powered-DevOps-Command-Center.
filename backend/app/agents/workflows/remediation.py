from typing import Literal, Optional
from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.graph import END, START, StateGraph

from app.agents.nodes.remediation import (
    collect_source_context_node,
    construct_remediation_plan_node,
    create_generate_patch_node,
    evaluate_patch_risk_node,
    evaluate_remediation_eligibility_node,
    load_remediation_context_node,
    validate_unified_diff_node,
)
from app.agents.state.remediation_state import RemediationState


def should_proceed_with_remediation(state: RemediationState) -> Literal["proceed", "end"]:
    """Conditional edge checking whether incident investigation is eligible for code patch."""
    eligibility = state.get("eligibility", {})
    if eligibility.get("status") == "eligible":
        return "proceed"
    return "end"


def should_validate_patch(state: RemediationState) -> Literal["validate", "end"]:
    """Conditional edge checking whether patch was successfully generated before validation."""
    if state.get("proposed_patch") is not None:
        return "validate"
    return "end"


def create_remediation_graph(llm: Optional[BaseChatModel] = None):
    """Build and compile the multi-step LangGraph remediation and patch generation workflow."""
    workflow = StateGraph(RemediationState)

    workflow.add_node("load_context", load_remediation_context_node)
    workflow.add_node("evaluate_eligibility", evaluate_remediation_eligibility_node)
    workflow.add_node("construct_plan", construct_remediation_plan_node)
    workflow.add_node("collect_source_context", collect_source_context_node)
    workflow.add_node("generate_patch", create_generate_patch_node(llm=llm))
    workflow.add_node("validate_patch", validate_unified_diff_node)
    workflow.add_node("evaluate_risk", evaluate_patch_risk_node)

    # 1. Start -> Load Context -> Evaluate Eligibility
    workflow.add_edge(START, "load_context")
    workflow.add_edge("load_context", "evaluate_eligibility")

    # 2. Eligibility Gate
    workflow.add_conditional_edges(
        "evaluate_eligibility",
        should_proceed_with_remediation,
        {
            "proceed": "construct_plan",
            "end": END,
        },
    )

    # 3. Plan -> Collect Source -> Generate Patch
    workflow.add_edge("construct_plan", "collect_source_context")
    workflow.add_edge("collect_source_context", "generate_patch")

    # 4. Patch Generation Gate
    workflow.add_conditional_edges(
        "generate_patch",
        should_validate_patch,
        {
            "validate": "validate_patch",
            "end": END,
        },
    )

    # 5. Validate -> Evaluate Risk -> End
    workflow.add_edge("validate_patch", "evaluate_risk")
    workflow.add_edge("evaluate_risk", END)

    return workflow.compile()

