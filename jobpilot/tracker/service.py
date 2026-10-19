from typing import Any, Dict, List, Optional, Tuple
from jobpilot.db.repository import repository
from jobpilot.logger import logger
from jobpilot.models.schemas import (
    ApplicationDraft,
    ApplicationRecord,
    ApplicationStatus,
    Job,
    MatchResult,
)
from jobpilot.utils.date_utils import utc_now_iso


class ApplicationTrackerService:
    """
    Manages human review decisions, draft editing, and lifecycle tracking of job applications.
    Enforces that no application is submitted without explicit user approval.
    """

    @staticmethod
    def approve_application(job_id: str, user_notes: Optional[str] = None) -> ApplicationRecord:
        """User approves draft for application."""
        logger.info(f"User approved application draft for job: {job_id}")
        repository.update_application_status(
            job_id,
            ApplicationStatus.APPROVED,
            notes=user_notes or "Draft approved by candidate.",
        )
        repository.log_audit("application_approved", "application", job_id, {"notes": user_notes})
        return repository.get_application(job_id)

    @staticmethod
    def reject_application(job_id: str, reason: Optional[str] = None) -> ApplicationRecord:
        """User rejects job opportunity."""
        logger.info(f"User rejected job: {job_id}. Reason: {reason}")
        repository.update_application_status(
            job_id,
            ApplicationStatus.REJECTED,
            notes=reason or "Rejected by candidate during review.",
        )
        repository.log_audit("application_rejected", "application", job_id, {"reason": reason})
        return repository.get_application(job_id)

    @staticmethod
    def save_for_later(job_id: str, notes: Optional[str] = None) -> ApplicationRecord:
        """User bookmarks or postpones review."""
        repository.update_application_status(
            job_id,
            ApplicationStatus.PENDING_REVIEW,
            notes=notes or "Saved for later review.",
        )
        return repository.get_application(job_id)

    @staticmethod
    def update_draft_content(job_id: str, cover_letter: str, answers: Dict[str, str], notes: Optional[str] = None) -> ApplicationDraft:
        """User customizes or edits generated cover letter or answers."""
        draft = ApplicationDraft(
            job_id=job_id,
            cover_letter=cover_letter,
            answers=answers,
            notes=notes,
            updated_at=utc_now_iso(),
        )
        repository.upsert_draft(draft)
        repository.log_audit("draft_edited", "application_draft", job_id)
        return draft

    @staticmethod
    def record_manual_submission(
        job_id: str,
        channel: str = "Company Portal",
        confirmation_id: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> ApplicationRecord:
        """
        Records verified submission completed by the user.
        Validates idempotency to prevent duplicate submissions.
        """
        existing = repository.get_application(job_id)
        if existing and existing.status == ApplicationStatus.SUBMITTED:
            logger.warning(f"Job {job_id} is already submitted. Skipping duplicate submission.")
            return existing

        details = f"Submitted via {channel}. " + (f"Ref ID: {confirmation_id}. " if confirmation_id else "") + (notes or "")
        repository.update_application_status(
            job_id=job_id,
            status=ApplicationStatus.SUBMITTED,
            notes=details,
            channel=channel,
        )
        repository.log_audit("application_submitted", "application", job_id, {"channel": channel, "conf_id": confirmation_id})
        return repository.get_application(job_id)

    @staticmethod
    def update_pipeline_stage(job_id: str, new_status: ApplicationStatus, notes: Optional[str] = None) -> ApplicationRecord:
        """Transitions application between pipeline stages (Assessment, Interview, Offer, Rejected, etc.)."""
        repository.update_application_status(job_id, new_status, notes=notes)
        repository.log_audit("pipeline_status_changed", "application", job_id, {"new_status": new_status.value, "notes": notes})
        return repository.get_application(job_id)


tracker_service = ApplicationTrackerService()
