import pytest
from jobpilot.llm.client import HuggingFaceLLMClient
from jobpilot.matcher.eligibility import EligibilityChecker
from jobpilot.matcher.scoring import MatchScorer
from jobpilot.models.schemas import CandidateProfile, Job


@pytest.fixture
def sample_candidate():
    return CandidateProfile(
        name="Rahul Girase",
        education="Final-year BE in Artificial Intelligence and Machine Learning",
        graduation_year=2027,
        experience_level="Fresher / entry-level",
        max_experience_years=1.0,
        preferred_roles=["AI/ML Engineer", "Data Scientist", "Python Developer"],
        skills=["Python", "Scikit-learn", "Pandas", "SQL", "LangChain", "FastAPI"],
        preferred_locations=["Pune", "Remote"],
    )


def test_eligibility_checker_fresher_job(sample_candidate):
    job = Job(
        id="job_elig_1",
        title="Junior ML Engineer",
        company="Alpha AI",
        location="Pune",
        min_experience_years=0.0,
        max_experience_years=1.0,
        description="Ideal for freshers and 2027 graduates with Python knowledge.",
        url="https://example.com/job1",
        source_name="Demo",
    )
    is_elig, reasons, score = EligibilityChecker.check(sample_candidate, job)
    assert is_elig is True
    assert score >= 80.0


def test_eligibility_checker_disqualifying_senior_job(sample_candidate):
    job = Job(
        id="job_senior_1",
        title="Senior AI Architect",
        company="BigCloud",
        location="Pune",
        min_experience_years=6.0,  # Greater than candidate max_experience_years (1.0)
        max_experience_years=10.0,
        description="Requires 6+ years of production experience.",
        url="https://example.com/job2",
        source_name="Demo",
    )
    is_elig, reasons, score = EligibilityChecker.check(sample_candidate, job)
    assert is_elig is False
    assert any("Disqualifying experience requirement" in r for r in reasons)
    assert score == 0.0


def test_match_scorer_calculation(sample_candidate):
    scorer = MatchScorer()

    # High match job
    job_high = Job(
        id="job_high_match",
        title="AI/ML Engineer Fresher",
        company="CognitiveLab",
        location="Pune",
        required_skills=["Python", "Scikit-learn", "SQL"],
        description="Looking for entry level AI/ML Engineer in Pune with Python and Scikit-learn.",
        url="https://example.com/job_high",
        source_name="Demo",
    )
    match_high = scorer.score_job(sample_candidate, job_high)
    assert match_high.is_eligible is True
    assert match_high.overall_score >= 70.0
    assert "Python" in match_high.matched_skills
    assert "Scikit-learn" in match_high.matched_skills

    # Senior job must have score capped
    job_senior = Job(
        id="job_senior_disqualified",
        title="Lead Staff AI Engineer",
        company="MegaCorp",
        location="Bangalore",
        min_experience_years=5.0,
        required_skills=["Python", "SQL"],
        description="5+ years experience required.",
        url="https://example.com/job_senior",
        source_name="Demo",
    )
    match_senior = scorer.score_job(sample_candidate, job_senior)
    assert match_senior.is_eligible is False
    assert match_senior.overall_score <= 25.0  # Capped for ineligible jobs!


def test_truthful_cover_letter_fallback(sample_candidate):
    client = HuggingFaceLLMClient(token="")
    assert client.is_configured() is False

    job = Job(
        id="job_test_cl",
        title="Junior Python Developer",
        company="DataFlow",
        location="Pune",
        description="Python backend developer for data APIs.",
        url="https://example.com/cl",
        source_name="Demo",
    )

    cover_letter = client.generate_cover_letter(sample_candidate, job)
    assert "Rahul Girase" in cover_letter
    assert "DataFlow" in cover_letter
    assert "Junior Python Developer" in cover_letter
    assert "2027" in cover_letter

    answers = client.generate_answers(sample_candidate, job)
    assert len(answers) >= 3
    assert "2027" in answers["What is your availability to start?"]
