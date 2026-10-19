from datetime import datetime
from typing import Any, Dict, List

from jobpilot.config import settings
from jobpilot.db.repository import repository
from jobpilot.llm.client import llm_client
from jobpilot.logger import logger
from jobpilot.matcher.eligibility import EligibilityChecker
from jobpilot.matcher.scoring import MatchScorer
from jobpilot.models.schemas import (
    ApplicationDraft,
    ApplicationStatus,
    CandidateProfile,
    Job,
    MatchResult,
)
from jobpilot.sources import JobDiscoveryService
from jobpilot.sources.deduplicator import (
    JobDeduplicator,
    extract_experience_requirements,
    extract_skills_from_text,
)
from jobpilot.utils.date_utils import utc_now_iso


def node_load_candidate_profile(state: Dict[str, Any]) -> Dict[str, Any]:
    """Node 1: Loads the candidate profile and active resume."""
    logger.info("Executing node: load_candidate_profile")
    profile = state.get("candidate_profile") or repository.get_candidate_profile()
    active_resume = repository.get_active_resume()
    resume_id = active_resume["id"] if active_resume else None

    return {
        "candidate_profile": profile,
        "active_resume_id": resume_id,
        "errors": state.get("errors", []),
    }


def node_collect_jobs(state: Dict[str, Any]) -> Dict[str, Any]:
    """Node 2: Discovers jobs from configured sources."""
    logger.info("Executing node: collect_jobs")
    # If jobs were already provided in state (e.g. manual trigger), keep them
    existing_jobs = state.get("raw_jobs")
    if existing_jobs:
        return {"raw_jobs": existing_jobs}

    discovery_service = JobDiscoveryService()
    candidate = state.get("candidate_profile") or repository.get_candidate_profile()
    search_criteria = {
        "preferred_roles": candidate.preferred_roles if candidate else [],
        "preferred_locations": candidate.preferred_locations if candidate else [],
        "open_to_remote": candidate.open_to_remote if candidate else True,
    }
    jobs, _ = discovery_service.discover(search_criteria=search_criteria, limit_per_source=20)
    return {"raw_jobs": jobs}


def node_normalize_jobs(state: Dict[str, Any]) -> Dict[str, Any]:
    """Node 3: Cleans and standardizes job records."""
    logger.info("Executing node: normalize_jobs")
    raw_jobs: List[Job] = state.get("raw_jobs", [])
    normalized: List[Job] = []

    for job in raw_jobs:
        if not job.required_skills:
            job.required_skills = extract_skills_from_text(job.description)[:6]
        if job.min_experience_years == 0.0 and job.max_experience_years == 1.0:
            min_e, max_e = extract_experience_requirements(job.description)
            job.min_experience_years = min_e
            job.max_experience_years = max_e
        normalized.append(job)

    return {"normalized_jobs": normalized}


def node_deduplicate_jobs(state: Dict[str, Any]) -> Dict[str, Any]:
    """Node 4: Deduplicates job listings."""
    logger.info("Executing node: deduplicate_jobs")
    normalized: List[Job] = state.get("normalized_jobs", [])
    unique_jobs, dup_count = JobDeduplicator.deduplicate(normalized)
    logger.info(f"Deduplication completed: {len(unique_jobs)} unique listings ({dup_count} duplicates).")
    return {"unique_jobs": unique_jobs}


def node_extract_job_requirements(state: Dict[str, Any]) -> Dict[str, Any]:
    """Node 5: Extracts structured requirements."""
    logger.info("Executing node: extract_job_requirements")
    unique_jobs: List[Job] = state.get("unique_jobs", [])
    return {"unique_jobs": unique_jobs}


def node_check_hard_eligibility(state: Dict[str, Any]) -> Dict[str, Any]:
    """Node 6: Enforces hard eligibility criteria."""
    logger.info("Executing node: check_hard_eligibility")
    candidate: CandidateProfile = state["candidate_profile"]
    unique_jobs: List[Job] = state.get("unique_jobs", [])
    eligible: List[Job] = []

    for job in unique_jobs:
        is_elig, _, _ = EligibilityChecker.check(candidate, job)
        if is_elig:
            eligible.append(job)

    logger.info(f"Eligibility check: {len(eligible)} / {len(unique_jobs)} jobs eligible.")
    return {"eligible_jobs": eligible}


def node_calculate_match_score(state: Dict[str, Any]) -> Dict[str, Any]:
    """Node 7: Calculates multi-factor match score for all jobs."""
    logger.info("Executing node: calculate_match_score")
    candidate: CandidateProfile = state["candidate_profile"]
    unique_jobs: List[Job] = state.get("unique_jobs", [])
    scorer = MatchScorer()

    matches: List[MatchResult] = []
    for job in unique_jobs:
        match_res = scorer.score_job(candidate, job)
        matches.append(match_res)

    return {"ranked_matches": matches}


def node_rank_matches(state: Dict[str, Any]) -> Dict[str, Any]:
    """Node 8: Ranks matches in descending score order."""
    logger.info("Executing node: rank_matches")
    matches: List[MatchResult] = state.get("ranked_matches", [])
    matches.sort(key=lambda m: m.overall_score, reverse=True)
    return {"ranked_matches": matches}


def node_select_resume(state: Dict[str, Any]) -> Dict[str, Any]:
    """Node 9: Selects appropriate candidate resume."""
    logger.info("Executing node: select_resume")
    resume_id = state.get("active_resume_id")
    return {"active_resume_id": resume_id}


def node_generate_application_draft(state: Dict[str, Any]) -> Dict[str, Any]:
    """Node 10: Generates personalized application drafts for high match jobs."""
    logger.info("Executing node: generate_application_draft")
    candidate: CandidateProfile = state["candidate_profile"]
    matches: List[MatchResult] = state.get("ranked_matches", [])
    unique_jobs: List[Job] = state.get("unique_jobs", [])
    job_map = {j.id: j for j in unique_jobs}
    resume_id = state.get("active_resume_id")

    drafts: List[ApplicationDraft] = []
    min_score = settings.MIN_MATCH_SCORE_TO_DRAFT

    for match in matches:
        if match.is_eligible and match.overall_score >= min_score:
            job = job_map.get(match.job_id)
            if job:
                logger.info(f"Generating draft for high-match job: {job.title} at {job.company} (Score: {match.overall_score}%)")
                cover_letter = llm_client.generate_cover_letter(candidate, job)
                answers = llm_client.generate_answers(candidate, job)
                draft = ApplicationDraft(
                    job_id=job.id,
                    resume_id=resume_id,
                    cover_letter=cover_letter,
                    answers=answers,
                    notes=f"Auto-drafted by JobPilot AI (Match score: {match.overall_score}%)",
                    created_at=utc_now_iso(),
                    updated_at=utc_now_iso(),
                )
                drafts.append(draft)

    return {"drafts": drafts}


def node_validate_draft(state: Dict[str, Any]) -> Dict[str, Any]:
    """Node 11: Validates generated drafts for completeness and integrity."""
    logger.info("Executing node: validate_draft")
    drafts: List[ApplicationDraft] = state.get("drafts", [])
    validated: List[ApplicationDraft] = []

    for d in drafts:
        if len(d.cover_letter.strip()) > 50 and d.answers:
            validated.append(d)
        else:
            logger.warning(f"Draft for job {d.job_id} failed integrity validation.")

    return {"drafts": validated}


def node_save_results(state: Dict[str, Any]) -> Dict[str, Any]:
    """Node 12: Persists jobs, match results, drafts, and applications to database."""
    logger.info("Executing node: save_results")
    unique_jobs: List[Job] = state.get("unique_jobs", [])
    matches: List[MatchResult] = state.get("ranked_matches", [])
    drafts: List[ApplicationDraft] = state.get("drafts", [])
    drafted_job_ids = {d.job_id for d in drafts}

    # 1. Upsert all jobs
    for job in unique_jobs:
        repository.upsert_job(job)

    # 2. Upsert match results
    for match in matches:
        repository.upsert_match_result(match)

    # 3. Save drafts and set status to PENDING_REVIEW
    for draft in drafts:
        repository.upsert_draft(draft)
        # Check current status before changing; do not overwrite submitted/interview status
        existing_app = repository.get_application(draft.job_id)
        if not existing_app or existing_app.status in (ApplicationStatus.DISCOVERED, ApplicationStatus.ELIGIBLE, ApplicationStatus.DRAFTED):
            repository.update_application_status(
                draft.job_id,
                ApplicationStatus.PENDING_REVIEW,
                notes="Application draft ready for human approval.",
            )

    # 4. For eligible jobs that didn't meet draft threshold, update to ELIGIBLE
    for match in matches:
        if match.is_eligible and match.job_id not in drafted_job_ids:
            existing_app = repository.get_application(match.job_id)
            if not existing_app or existing_app.status == ApplicationStatus.DISCOVERED:
                repository.update_application_status(
                    match.job_id,
                    ApplicationStatus.ELIGIBLE,
                    notes=f"Eligible role (Score: {match.overall_score}%).",
                )

    repository.log_audit(
        action="agent_run_completed",
        entity_type="langgraph_pipeline",
        details={
            "jobs_saved": len(unique_jobs),
            "matches_scored": len(matches),
            "drafts_created": len(drafts),
        },
    )

    return {"status": "saved"}


def node_generate_daily_report(state: Dict[str, Any]) -> Dict[str, Any]:
    """Node 13: Compiles execution summary statistics."""
    logger.info("Executing node: generate_daily_report")
    unique_jobs: List[Job] = state.get("unique_jobs", [])
    matches: List[MatchResult] = state.get("ranked_matches", [])
    eligible_jobs: List[Job] = state.get("eligible_jobs", [])
    drafts: List[ApplicationDraft] = state.get("drafts", [])

    summary = {
        "timestamp": utc_now_iso(),
        "total_jobs_discovered": len(unique_jobs),
        "eligible_jobs": len(eligible_jobs),
        "high_matches": len([m for m in matches if m.overall_score >= settings.MIN_MATCH_SCORE_TO_DRAFT]),
        "drafts_created": len(drafts),
        "status": "success",
    }

    return {"summary": summary, "status": "completed"}
