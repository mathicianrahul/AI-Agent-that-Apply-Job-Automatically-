from typing import Any, Dict
from langgraph.graph import END, START, StateGraph

from jobpilot.agent.nodes import (
    node_calculate_match_score,
    node_check_hard_eligibility,
    node_collect_jobs,
    node_deduplicate_jobs,
    node_extract_job_requirements,
    node_generate_application_draft,
    node_generate_daily_report,
    node_load_candidate_profile,
    node_normalize_jobs,
    node_rank_matches,
    node_save_results,
    node_select_resume,
    node_validate_draft,
)
from jobpilot.agent.state import AgentState
from jobpilot.logger import logger


def build_job_application_graph():
    """Builds and compiles the modular LangGraph state machine for job discovery and application preparation."""
    workflow = StateGraph(AgentState)

    # 1. Add all nodes
    workflow.add_node("load_candidate_profile", node_load_candidate_profile)
    workflow.add_node("collect_jobs", node_collect_jobs)
    workflow.add_node("normalize_jobs", node_normalize_jobs)
    workflow.add_node("deduplicate_jobs", node_deduplicate_jobs)
    workflow.add_node("extract_job_requirements", node_extract_job_requirements)
    workflow.add_node("check_hard_eligibility", node_check_hard_eligibility)
    workflow.add_node("calculate_match_score", node_calculate_match_score)
    workflow.add_node("rank_matches", node_rank_matches)
    workflow.add_node("select_resume", node_select_resume)
    workflow.add_node("generate_application_draft", node_generate_application_draft)
    workflow.add_node("validate_draft", node_validate_draft)
    workflow.add_node("save_results", node_save_results)
    workflow.add_node("generate_daily_report", node_generate_daily_report)

    # 2. Add sequential and conditional edges
    workflow.add_edge(START, "load_candidate_profile")
    workflow.add_edge("load_candidate_profile", "collect_jobs")
    workflow.add_edge("collect_jobs", "normalize_jobs")
    workflow.add_edge("normalize_jobs", "deduplicate_jobs")
    workflow.add_edge("deduplicate_jobs", "extract_job_requirements")
    workflow.add_edge("extract_job_requirements", "check_hard_eligibility")
    workflow.add_edge("check_hard_eligibility", "calculate_match_score")
    workflow.add_edge("calculate_match_score", "rank_matches")
    workflow.add_edge("rank_matches", "select_resume")
    workflow.add_edge("select_resume", "generate_application_draft")
    workflow.add_edge("generate_application_draft", "validate_draft")
    workflow.add_edge("validate_draft", "save_results")
    workflow.add_edge("save_results", "generate_daily_report")
    workflow.add_edge("generate_daily_report", END)

    app = workflow.compile()
    logger.info("LangGraph Job Application agent compiled successfully.")
    return app


# Pre-compiled application instance
job_agent = build_job_application_graph()


def run_job_agent(custom_jobs=None) -> Dict[str, Any]:
    """Helper function to execute the full LangGraph pipeline."""
    initial_state: AgentState = {
        "candidate_profile": None,
        "raw_jobs": custom_jobs or [],
        "normalized_jobs": [],
        "unique_jobs": [],
        "ranked_matches": [],
        "eligible_jobs": [],
        "drafts": [],
        "active_resume_id": None,
        "errors": [],
        "summary": {},
        "status": "started",
    }
    result = job_agent.invoke(initial_state)
    return result
