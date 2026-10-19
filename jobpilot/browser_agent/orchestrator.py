"""
Browser Job Agent Orchestrator — Unified launcher for all platform agents.

Usage:
  python -m jobpilot.browser_agent.orchestrator --platform linkedin
  python -m jobpilot.browser_agent.orchestrator --platform naukri
  python -m jobpilot.browser_agent.orchestrator --platform indeed
  python -m jobpilot.browser_agent.orchestrator --platform all
"""

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Dict, List

from jobpilot.logger import logger
from jobpilot.browser_agent.config import browser_config


class BrowserJobAgent:
    """
    Orchestrates browser-based job application agents across multiple platforms.
    Runs each platform sequentially (to avoid suspicious concurrent sessions).
    """

    def __init__(self, platforms: List[str] = None):
        self.platforms = [p.lower() for p in (platforms or ["linkedin", "naukri"])]
        self.results: Dict[str, Dict] = {}

    async def run(self) -> Dict:
        """Run the browser agent for all selected platforms."""
        logger.info("+==========================================================+")
        logger.info("|          JobPilot AI — Browser Application Agent         |")
        logger.info("|                                                          |")
        logger.info(f"|  Candidate: {browser_config.CANDIDATE_NAME:<44} |")
        logger.info(f"|  Email:     {browser_config.CANDIDATE_EMAIL:<44} |")
        logger.info(f"|  Search:    {browser_config.SEARCH_KEYWORDS.split(',')[0].strip()[:44]:<44} |")
        logger.info(f"|  Location:  {browser_config.SEARCH_LOCATION:<44} |")
        logger.info(f"|  Platforms: {', '.join(self.platforms):<44} |")
        logger.info("|                                                          |")
        logger.info("|  Mode: SEMI-AUTOMATED                                    |")
        logger.info("|  -> Agent finds jobs & pre-fills forms                    |")
        logger.info("|  -> YOU review & click Submit for each application        |")
        logger.info("+==========================================================+")

        # Verify resume exists
        if not browser_config.resume_file.exists():
            logger.error(f"Resume not found at: {browser_config.resume_file}")
            logger.error("Please place your resume PDF in data/resumes/ directory.")
            return {"error": "Resume not found"}

        logger.info(f"Resume: {browser_config.resume_file.name} [OK]")

        # Reset / initialize live status for real-time dashboard tracking
        status_file = browser_config.browser_state_path / "live_status.json"
        try:
            with open(status_file, "w", encoding="utf-8") as f:
                json.dump({
                    "platform": self.platforms[0].upper() if self.platforms else "AGENT",
                    "step": f"Agent launched for {', '.join(p.upper() for p in self.platforms)} — Starting browser...",
                    "status": "running",
                    "applied_count": 0,
                    "max_applications": browser_config.MAX_APPLICATIONS_PER_SESSION,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                }, f, indent=2)
        except Exception:
            pass

        total_start = time.time()

        for platform in self.platforms:
            logger.info(f"\n{'='*60}")
            logger.info(f"  Starting: {platform.upper()} Agent")
            logger.info(f"{'='*60}")

            try:
                if platform == "linkedin":
                    from jobpilot.browser_agent.linkedin_agent import run_linkedin_agent
                    result = await run_linkedin_agent()

                elif platform == "naukri":
                    from jobpilot.browser_agent.naukri_agent import run_naukri_agent
                    result = await run_naukri_agent()

                elif platform == "indeed":
                    from jobpilot.browser_agent.indeed_agent import run_indeed_agent
                    result = await run_indeed_agent()

                else:
                    logger.warning(f"Unknown platform: {platform}")
                    result = {"platform": platform, "error": "Unknown platform"}

                self.results[platform] = result

            except Exception as e:
                logger.error(f"[{platform}] Agent crashed: {e}")
                self.results[platform] = {"platform": platform, "error": str(e)}

        total_duration = round(time.time() - total_start, 1)

        # Print summary
        self._print_summary(total_duration)

        # Save session log
        self._save_session_log(total_duration)

        # Mark completed in live status
        try:
            total_applied = sum(r.get("applied", 0) for r in self.results.values() if isinstance(r, dict))
            total_skipped = sum(r.get("skipped", 0) for r in self.results.values() if isinstance(r, dict))
            with open(status_file, "w", encoding="utf-8") as f:
                json.dump({
                    "platform": ", ".join(p.upper() for p in self.platforms),
                    "step": f"Session completed ({total_applied} applied, {total_skipped} skipped)",
                    "status": "completed",
                    "applied_count": total_applied,
                    "max_applications": browser_config.MAX_APPLICATIONS_PER_SESSION,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "latest_screenshot": str(browser_config.browser_state_path / "screenshots" / "latest.png"),
                }, f, indent=2)
        except Exception:
            pass

        return self.results

    def _print_summary(self, total_duration: float):
        """Print a summary of all platform results."""
        logger.info(f"\n{'='*60}")
        logger.info("  SESSION SUMMARY")
        logger.info(f"{'='*60}")

        total_applied = 0
        total_skipped = 0

        for platform, result in self.results.items():
            applied = result.get("applied", 0)
            skipped = result.get("skipped", 0)
            failed = result.get("failed", 0)
            error = result.get("error")
            total_applied += applied
            total_skipped += skipped

            if error:
                logger.info(f"  {platform.upper():12} | ERROR: {error}")
            else:
                logger.info(
                    f"  {platform.upper():12} | Applied: {applied:3} | "
                    f"Skipped: {skipped:3} | Failed: {failed:3} | "
                    f"Duration: {result.get('duration_seconds', 0):.0f}s"
                )

        logger.info(f"{'-'*60}")
        logger.info(f"  TOTAL        | Applied: {total_applied:3} | Skipped: {total_skipped:3}")
        logger.info(f"  Total Time:  {total_duration:.0f}s")
        logger.info(f"{'='*60}")

    def _save_session_log(self, total_duration: float):
        """Save session results as a JSON log."""
        log_dir = Path(browser_config.BROWSER_STATE_DIR).parent / "browser_sessions"
        log_dir.mkdir(parents=True, exist_ok=True)

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"session_{timestamp}.json"

        log_data = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "candidate": browser_config.CANDIDATE_NAME,
            "platforms": self.platforms,
            "search_keywords": browser_config.SEARCH_KEYWORDS,
            "search_location": browser_config.SEARCH_LOCATION,
            "total_duration_seconds": total_duration,
            "results": self.results,
        }

        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(log_data, f, indent=2, default=str)

        logger.info(f"Session log saved: {log_file}")


def main():
    """CLI entry point for the browser job agent."""
    parser = argparse.ArgumentParser(
        description="JobPilot AI — Browser-based Job Application Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m jobpilot.browser_agent.orchestrator --platform linkedin
  python -m jobpilot.browser_agent.orchestrator --platform naukri
  python -m jobpilot.browser_agent.orchestrator --platform indeed
  python -m jobpilot.browser_agent.orchestrator --platform linkedin naukri
  python -m jobpilot.browser_agent.orchestrator --platform all
        """,
    )
    parser.add_argument(
        "--platform", "-p",
        nargs="+",
        choices=["linkedin", "naukri", "indeed", "all"],
        default=["linkedin"],
        help="Platform(s) to run the agent on (default: linkedin)",
    )
    parser.add_argument(
        "--keywords", "-k",
        type=str,
        help="Override search keywords",
    )
    parser.add_argument(
        "--location", "-l",
        type=str,
        help="Override search location",
    )
    parser.add_argument(
        "--max-apply", "-m",
        type=int,
        help="Max applications per session (default: 25)",
    )
    parser.add_argument(
        "--remote", "-r",
        action="store_true",
        default=False,
        help="Also search and apply to Remote jobs outside India",
    )
    parser.add_argument(
        "--auto-submit",
        action="store_true",
        default=False,
        help="Automatically click Submit without pausing for manual review",
    )

    args = parser.parse_args()

    # Apply overrides
    if args.keywords:
        browser_config.SEARCH_KEYWORDS = args.keywords
    if args.location:
        browser_config.SEARCH_LOCATION = args.location
    if args.max_apply:
        browser_config.MAX_APPLICATIONS_PER_SESSION = args.max_apply
    if args.remote:
        browser_config.INCLUDE_REMOTE = True
    if args.auto_submit:
        browser_config.AUTO_SUBMIT = True

    platforms = args.platform
    if "all" in platforms:
        platforms = ["linkedin", "naukri", "indeed"]

    agent = BrowserJobAgent(platforms=platforms)
    asyncio.run(agent.run())


if __name__ == "__main__":
    main()
