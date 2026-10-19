from datetime import datetime, timezone
import re
from typing import Dict, List, Set, Tuple

from jobpilot.config import settings
from jobpilot.matcher.eligibility import EligibilityChecker
from jobpilot.models.schemas import CandidateProfile, Job, MatchResult
from jobpilot.utils.date_utils import utc_now_iso


class MatchScorer:
    """
    Computes transparent, deterministic multi-factor scores (0-100)
    for a candidate against a job opportunity.
    """

    def __init__(self, custom_weights: Dict[str, float] | None = None):
        self.weights = custom_weights or {
            "skill": settings.WEIGHT_SKILL_OVERLAP,
            "role": settings.WEIGHT_ROLE_RELEVANCE,
            "eligibility": settings.WEIGHT_ELIGIBILITY,
            "location": settings.WEIGHT_LOCATION,
            "freshness": settings.WEIGHT_FRESHNESS,
        }

    def score_job(self, candidate: CandidateProfile, job: Job) -> MatchResult:
        # 1. Eligibility Check
        is_eligible, eligibility_reasons, elig_score = EligibilityChecker.check(candidate, job)

        # 2. Skill Overlap (0-100)
        candidate_skills_lower = {s.lower(): s for s in candidate.skills}
        job_req_skills = [s.strip() for s in job.required_skills if s.strip()]
        matched_skills: List[str] = []
        missing_skills: List[str] = []

        if job_req_skills:
            for s in job_req_skills:
                if s.lower() in candidate_skills_lower:
                    matched_skills.append(candidate_skills_lower[s.lower()])
                else:
                    missing_skills.append(s)
            skill_score = (len(matched_skills) / len(job_req_skills)) * 100.0
        else:
            # Check full text match against candidate skills
            desc_lower = job.description.lower()
            for s, original_name in candidate_skills_lower.items():
                if re.search(r"(?i)\b" + re.escape(s) + r"\b", desc_lower):
                    matched_skills.append(original_name)
            skill_score = min(100.0, (len(matched_skills) / 4.0) * 100.0) if matched_skills else 20.0

        # 3. Role Relevance (0-100)
        job_title_lower = job.title.lower()
        role_matches = 0
        for preferred in candidate.preferred_roles:
            tokens = [t.lower() for t in preferred.split() if len(t) > 2]
            if any(token in job_title_lower for token in tokens):
                role_matches += 1

        if any(preferred.lower() in job_title_lower for preferred in candidate.preferred_roles):
            role_score = 100.0
        elif role_matches > 0:
            role_score = min(90.0, role_matches * 30.0)
        else:
            # Partial match based on AI/ML keywords in description
            if any(k in job_title_lower for k in ["ai", "ml", "data", "python", "software", "developer", "engineer"]):
                role_score = 60.0
            else:
                role_score = 20.0

        # 4. Location Preference (0-100)
        job_loc_lower = (job.location or "").lower()
        is_job_remote = (
            job.is_remote
            or getattr(job, "workplace_type", "").lower() == "remote"
            or any(k in job_loc_lower or k in job.title.lower() for k in ["remote", "work from home", "anywhere", "worldwide", "virtual", "telecommute"])
        )

        candidate_locs = [loc.strip().lower() for loc in (candidate.preferred_locations or []) if loc.strip()]
        is_candidate_open_to_remote = candidate.open_to_remote or any("remote" in l for l in candidate_locs)
        preferred_cities = [l for l in candidate_locs if "remote" not in l]
        matches_preferred_city = any(city in job_loc_lower for city in preferred_cities) if preferred_cities else False

        if (is_job_remote and is_candidate_open_to_remote) or matches_preferred_city:
            loc_score = 100.0
        else:
            loc_score = 0.0

        # 5. Freshness Score (0-100)
        freshness_score = 80.0
        if job.posted_date:
            try:
                # If date is ISO format or YYYY-MM-DD
                posted_dt = datetime.fromisoformat(job.posted_date.replace("Z", "+00:00"))
                days_old = (datetime.now(timezone.utc) - posted_dt).days
                if days_old <= 3:
                    freshness_score = 100.0
                elif days_old <= 7:
                    freshness_score = 85.0
                elif days_old <= 14:
                    freshness_score = 70.0
                elif days_old <= 30:
                    freshness_score = 50.0
                else:
                    freshness_score = 25.0
            except Exception:
                freshness_score = 75.0

        # Weighted calculation
        total_weight = sum(self.weights.values())
        weighted_sum = (
            skill_score * self.weights["skill"]
            + role_score * self.weights["role"]
            + elig_score * self.weights["eligibility"]
            + loc_score * self.weights["location"]
            + freshness_score * self.weights["freshness"]
        )
        overall_score = round(weighted_sum / total_weight, 1)

        # Disqualifying enforcement: If not eligible, cap overall score below 30
        if not is_eligible:
            overall_score = min(25.0, overall_score)

        explanation = (
            f"Overall score: {overall_score}%. "
            f"Skill match: {len(matched_skills)} matched, {len(missing_skills)} missing. "
            f"Role relevance: {role_score:.0f}%, Location score: {loc_score:.0f}%. "
            + (f"Ineligible: {'; '.join(eligibility_reasons)}" if not is_eligible else "Eligible for application.")
        )

        return MatchResult(
            job_id=job.id,
            overall_score=overall_score,
            skill_score=round(skill_score, 1),
            role_score=round(role_score, 1),
            eligibility_score=round(elig_score, 1),
            location_score=round(loc_score, 1),
            freshness_score=round(freshness_score, 1),
            matched_skills=matched_skills,
            missing_skills=missing_skills,
            is_eligible=is_eligible,
            eligibility_reasons=eligibility_reasons,
            explanation=explanation,
            evaluated_at=utc_now_iso(),
        )
