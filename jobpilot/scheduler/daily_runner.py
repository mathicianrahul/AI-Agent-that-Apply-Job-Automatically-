import threading
import time
from datetime import datetime
from typing import Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from zoneinfo import ZoneInfo

from jobpilot.agent.graph import run_job_agent
from jobpilot.config import settings
from jobpilot.db.repository import repository
from jobpilot.logger import logger
from jobpilot.models.schemas import AutomationRun
from jobpilot.utils.date_utils import utc_now_iso


class DailyAutomationScheduler:
    """Manages APScheduler background automation with safe concurrency and state tracking."""

    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self._is_running_lock = threading.Lock()
        self.is_active = False
        self.job_id = "daily_jobpilot_run"

    def execute_daily_pipeline(self) -> AutomationRun:
        """Executes the end-to-end LangGraph agent run and saves metrics."""
        if not self._is_running_lock.acquire(blocking=False):
            logger.warning("Daily automation is already executing. Skipping concurrent trigger.")
            return repository.get_latest_automation_run() or AutomationRun()

        start_time = time.time()
        start_iso = utc_now_iso()
        logger.info("Starting Daily JobPilot Automation Run...")

        try:
            # Execute LangGraph agent
            result = run_job_agent()
            duration = round(time.time() - start_time, 2)
            summary = result.get("summary", {})

            # Trigger Daily Email Digest Dispatch to candidate (rgirase312@gmail.com)
            if getattr(settings, "ENABLE_EMAIL_DIGEST", True):
                try:
                    from jobpilot.notifications.email_digest import email_digest_service
                    digest_res = email_digest_service.dispatch_digest()
                    logger.info(f"Daily email digest dispatched: {digest_res.get('message')}")
                except Exception as digest_err:
                    logger.error(f"Failed to dispatch daily email digest: {digest_err}")

            auto_run = AutomationRun(
                run_timestamp=start_iso,
                status="completed",
                jobs_collected=summary.get("total_jobs_discovered", 0),
                jobs_deduplicated=summary.get("total_jobs_discovered", 0),
                eligible_jobs=summary.get("eligible_jobs", 0),
                drafts_created=summary.get("drafts_created", 0),
                errors="; ".join(result.get("errors", [])) if result.get("errors") else None,
                duration_seconds=duration,
            )
            repository.record_automation_run(auto_run)
            logger.info(f"Daily automation completed successfully in {duration}s. {auto_run.drafts_created} drafts created.")
            return auto_run

        except Exception as e:
            duration = round(time.time() - start_time, 2)
            logger.error(f"Daily automation encountered an error: {e}", exc_info=True)
            failed_run = AutomationRun(
                run_timestamp=start_iso,
                status="failed",
                jobs_collected=0,
                jobs_deduplicated=0,
                eligible_jobs=0,
                drafts_created=0,
                errors=str(e),
                duration_seconds=duration,
            )
            repository.record_automation_run(failed_run)
            return failed_run

        finally:
            self._is_running_lock.release()

    def start_scheduler(
        self,
        hour: Optional[int] = None,
        minute: Optional[int] = None,
        timezone_str: Optional[str] = None,
    ) -> None:
        """Starts background APScheduler job."""
        h = hour if hour is not None else settings.DAILY_RUN_HOUR
        m = minute if minute is not None else settings.DAILY_RUN_MINUTE
        tz = timezone_str or settings.TIMEZONE

        if self.scheduler.running:
            self.scheduler.remove_all_jobs()
        else:
            self.scheduler.start()

        trigger = CronTrigger(hour=h, minute=m, timezone=ZoneInfo(tz))
        self.scheduler.add_job(
            self.execute_daily_pipeline,
            trigger=trigger,
            id=self.job_id,
            name="JobPilot Daily Agent Automation",
            replace_existing=True,
        )
        self.is_active = True
        logger.info(f"Scheduler active: Runs daily at {h:02d}:{m:02d} ({tz}).")

    def pause_scheduler(self) -> None:
        if self.scheduler.running:
            try:
                self.scheduler.pause_job(self.job_id)
                self.is_active = False
                logger.info("Daily scheduler paused.")
            except Exception as e:
                logger.warning(f"Pause error: {e}")

    def resume_scheduler(self) -> None:
        if self.scheduler.running:
            try:
                self.scheduler.resume_job(self.job_id)
                self.is_active = True
                logger.info("Daily scheduler resumed.")
            except Exception as e:
                logger.warning(f"Resume error: {e}")

    def trigger_run_now(self) -> AutomationRun:
        """Manually trigger an immediate execution."""
        return self.execute_daily_pipeline()


automation_scheduler = DailyAutomationScheduler()
