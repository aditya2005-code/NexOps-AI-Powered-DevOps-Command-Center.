from typing import Optional
from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.graph import END, START, StateGraph

from app.agents.nodes import (
    analyze_evidence_node,
    build_investigation_plan_node,
    collect_evidence_node,
    create_investigate_node,
    prepare_context_node,
    validate_and_format_node,
    validate_hypotheses_node,
)
from app.agents.state import InvestigationState


def create_investigation_graph(llm: Optional[BaseChatModel] = None):
    """Build and compile the multi-step LangGraph incident investigation workflow.

    Flow:
        START
          ↓
        prepare_context (load incident context & resolve workspace)
          ↓
        build_investigation_plan (plan diagnostic actions)
          ↓
        collect_evidence (run log_analyzer and source_inspector tools)
          ↓
        analyze_evidence (correlate patterns, format evidence with IDs)
          ↓
        investigate (generate structured root cause hypotheses via LLM)
          ↓
        validate_hypotheses (verify evidence IDs, calibrate confidence, rank)
          ↓
        validate_and_format (synthesize final report with evidence and diagnostic summary)
          ↓
        END
    """
    workflow = StateGraph(InvestigationState)

    workflow.add_node("prepare_context", prepare_context_node)
    workflow.add_node("build_investigation_plan", build_investigation_plan_node)
    workflow.add_node("collect_evidence", collect_evidence_node)
    workflow.add_node("analyze_evidence", analyze_evidence_node)
    workflow.add_node("investigate", create_investigate_node(llm=llm))
    workflow.add_node("validate_hypotheses", validate_hypotheses_node)
    workflow.add_node("validate_and_format", validate_and_format_node)

    workflow.add_edge(START, "prepare_context")
    workflow.add_edge("prepare_context", "build_investigation_plan")
    workflow.add_edge("build_investigation_plan", "collect_evidence")
    workflow.add_edge("collect_evidence", "analyze_evidence")
    workflow.add_edge("analyze_evidence", "investigate")
    workflow.add_edge("investigate", "validate_hypotheses")
    workflow.add_edge("validate_hypotheses", "validate_and_format")
    workflow.add_edge("validate_and_format", END)

    return workflow.compile()
