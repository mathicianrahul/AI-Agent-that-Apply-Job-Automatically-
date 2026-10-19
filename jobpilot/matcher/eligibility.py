from typing import List, Tuple
from jobpilot.models.schemas import CandidateProfile, Job


class EligibilityChecker:
    """
    Evaluates hard eligibility criteria for candidate vs job.
    Ensures disqualifying factors (e.g. experience requirement > fresher limit)
    strictly mark the candidate as ineligible.
    """

    @staticmethod
    def check(candidate: CandidateProfile, job: Job) -> Tuple[bool, List[str], float]:
        """
        Returns (is_eligible, reasons, eligibility_score_0_to_100).
        """
        reasons: List[str] = []
        is_eligible = True
        score = 100.0

        # Rule 1: Experience Requirement
        # If job strictly requires more experience than candidate's allowed maximum
        if job.min_experience_years > candidate.max_experience_years:
            is_eligible = False
            reasons.append(
                f"Disqualifying experience requirement: Job requires minimum {job.min_experience_years:g} years; candidate profile limit is {candidate.max_experience_years:g} years."
            )
            score = 0.0

        # Rule 2: Active listing check
        if not job.is_active:
            is_eligible = False
            reasons.append("Job posting is closed or inactive.")
            score = 0.0

        # Rule 3: Internship / Fresher compatibility
        # If employment type is Internship or Full-time suitable for candidate's graduation year
        job_lower = (job.title + " " + job.description).lower()
        grad_year_str = str(candidate.graduation_year) if candidate.graduation_year else "2027"
        if "intern" in job_lower or grad_year_str in job_lower or "fresher" in job_lower or "entry level" in job_lower:
            reasons.append(f"Matches entry-level / internship profile for graduating batch {candidate.graduation_year}.")
            score = min(100.0, score + 10.0)

        # Rule 4: Graduation year check if explicit in job text
        if "graduating in 2024" in job_lower or "2023 batch only" in job_lower:
            if candidate.graduation_year and candidate.graduation_year > 2025:
                is_eligible = False
                reasons.append("Explicitly restricted to earlier graduation batches (pre-2026).")
                score = 0.0

        # Rule 5: Dynamic Location Preference
        # Check against candidate's preferred locations list and remote preference
        job_loc_lower = (job.location or "").lower()
        is_job_remote = (
            job.is_remote
            or getattr(job, "workplace_type", "").lower() == "remote"
            or any(k in job_loc_lower or k in job.title.lower() for k in ["remote", "work from home", "anywhere", "worldwide", "virtual", "telecommute"])
        )

        candidate_locs = [loc.strip().lower() for loc in (candidate.preferred_locations or []) if loc.strip()]
        is_candidate_open_to_remote = candidate.open_to_remote or any("remote" in l for l in candidate_locs)

        # Candidate preferred cities (excluding the word 'remote')
        preferred_cities = [l for l in candidate_locs if "remote" not in l]
        # Match if any preferred city name is present in job location
        matches_preferred_city = any(city in job_loc_lower for city in preferred_cities) if preferred_cities else False

        loc_acceptable = (is_job_remote and is_candidate_open_to_remote) or matches_preferred_city

        if not loc_acceptable:
            is_eligible = False
            indian_regions = [
                "pune", "maharashtra", "bangalore", "bengaluru", "mumbai", "hyderabad", "delhi", "noida",
                "gurgaon", "gurugram", "chennai", "kolkata", "ahmedabad", "jaipur",
                "chandigarh", "indore", "kochi", "coimbatore", "kerala", "karnataka",
                "tamil nadu", "telangana", "gujarat", "india"
            ]
            preferred_disp = " or ".join([loc.title() for loc in candidate.preferred_locations]) if candidate.preferred_locations else "Remote"
            if any(r in job_loc_lower for r in indian_regions):
                reasons.append(f"Location disqualified: Job is in '{job.location}'. In India, candidate only accepts {preferred_disp}.")
            else:
                reasons.append(f"Location disqualified: International on-site role in '{job.location}'. For out of India, candidate accepts Remote only.")
            score = 0.0

        if is_eligible and not reasons:
            reasons.append("Meets candidate baseline eligibility requirements.")

        return is_eligible, reasons, max(0.0, min(100.0, score))
