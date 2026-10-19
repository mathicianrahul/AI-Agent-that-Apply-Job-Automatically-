from typing import Any, Dict, List, Optional
from typing_extensions import TypedDict

from jobpilot.models.schemas import (
    ApplicationDraft,
    CandidateProfile,
    Job,
    MatchResult,
)


class AgentState(TypedDict):
    """Typed state passed across LangGraph nodes."""

    candidate_profile: Optional[CandidateProfile]
    raw_jobs: List[Job]
    normalized_jobs: List[Job]
    unique_jobs: List[Job]
    ranked_matches: List[MatchResult]
    eligible_jobs: List[Job]
    drafts: List[ApplicationDraft]
    active_resume_id: Optional[int]
    errors: List[str]
    summary: Dict[str, Any]
    status: str
