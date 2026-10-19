import pytest
from jobpilot.matcher.eligibility import EligibilityChecker
from jobpilot.matcher.scoring import MatchScorer
from jobpilot.models.schemas import CandidateProfile, Job


@pytest.fixture
def candidate():
    return CandidateProfile(
        name="Rahul Girase",
        education="Final-year BE in Artificial Intelligence and Machine Learning",
        graduation_year=2027,
        experience_level="Fresher / entry-level",
        max_experience_years=1.0,
        preferred_roles=["AI/ML Engineer"],
        skills=["Python", "SQL"],
        preferred_locations=["Pune", "Remote"],
        open_to_remote=True,
    )


def test_pune_onsite_job_is_eligible(candidate):
    job = Job(
        id="pune_1",
        title="AI/ML Engineer",
        company="Tech Pune",
        location="Pune, Maharashtra",
        is_remote=False,
        workplace_type="On-site",
        description="Python & ML in Pune office.",
        url="https://example.com/pune",
        source_name="Demo",
    )
    is_elig, reasons, score = EligibilityChecker.check(candidate, job)
    assert is_elig is True

    scorer = MatchScorer()
    res = scorer.score_job(candidate, job)
    assert res.location_score == 100.0
    assert res.is_eligible is True


def test_international_remote_job_is_eligible(candidate):
    job = Job(
        id="intl_remote_1",
        title="Generative AI Engineer",
        company="Global Labs US",
        location="Worldwide (Remote)",
        is_remote=True,
        workplace_type="Remote",
        description="Remote role open globally. Python, LLM.",
        url="https://example.com/remote",
        source_name="Demo",
    )
    is_elig, reasons, score = EligibilityChecker.check(candidate, job)
    assert is_elig is True

    scorer = MatchScorer()
    res = scorer.score_job(candidate, job)
    assert res.location_score == 100.0
    assert res.is_eligible is True


def test_domestic_non_pune_onsite_job_is_disqualified(candidate):
    job = Job(
        id="bangalore_1",
        title="AI/ML Engineer",
        company="Alpha Bangalore",
        location="Bangalore, Karnataka",
        is_remote=False,
        workplace_type="On-site",
        description="On-site in Bangalore.",
        url="https://example.com/blr",
        source_name="Demo",
    )
    is_elig, reasons, score = EligibilityChecker.check(candidate, job)
    assert is_elig is False
    assert any("candidate only accepts Pune or Remote" in r for r in reasons)

    scorer = MatchScorer()
    res = scorer.score_job(candidate, job)
    assert res.is_eligible is False
    assert res.location_score == 0.0
    assert res.overall_score <= 25.0


def test_international_onsite_job_is_disqualified(candidate):
    job = Job(
        id="london_1",
        title="AI/ML Engineer",
        company="EuroTech",
        location="London, United Kingdom",
        is_remote=False,
        workplace_type="On-site",
        description="On-site in Central London.",
        url="https://example.com/london",
        source_name="Demo",
    )
    is_elig, reasons, score = EligibilityChecker.check(candidate, job)
    assert is_elig is False
    assert any("For out of India, candidate accepts Remote only" in r for r in reasons)

    scorer = MatchScorer()
    res = scorer.score_job(candidate, job)
    assert res.is_eligible is False
    assert res.location_score == 0.0
    assert res.overall_score <= 25.0


def test_dynamic_candidate_profile_custom_location():
    # User preferring Bangalore & Hyderabad, graduating in 2026
    custom_user = CandidateProfile(
        name="Priya Sharma",
        graduation_year=2026,
        experience_level="Fresher",
        max_experience_years=1.0,
        preferred_roles=["Data Scientist"],
        skills=["Python", "Pandas"],
        preferred_locations=["Bangalore", "Hyderabad"],
        open_to_remote=False,
    )
    blr_job = Job(
        id="blr_custom_1",
        title="Data Scientist",
        company="Data Corp",
        location="Bangalore, Karnataka",
        is_remote=False,
        workplace_type="On-site",
        description="Data scientist role in Bangalore.",
        url="https://example.com/blr-data",
        source_name="Demo",
    )
    is_elig, reasons, score = EligibilityChecker.check(custom_user, blr_job)
    assert is_elig is True
    scorer = MatchScorer()
    res = scorer.score_job(custom_user, blr_job)
    assert res.location_score == 100.0
    assert res.is_eligible is True

    # Pune job should be disqualified for this custom user since she only accepts Bangalore/Hyderabad
    pune_job = Job(
        id="pune_custom_1",
        title="Data Scientist",
        company="Pune Labs",
        location="Pune, Maharashtra",
        is_remote=False,
        workplace_type="On-site",
        description="On-site in Pune.",
        url="https://example.com/pune-data",
        source_name="Demo",
    )
    is_pune_elig, pune_reasons, _ = EligibilityChecker.check(custom_user, pune_job)
    assert is_pune_elig is False
    assert any("Bangalore" in r for r in pune_reasons)

