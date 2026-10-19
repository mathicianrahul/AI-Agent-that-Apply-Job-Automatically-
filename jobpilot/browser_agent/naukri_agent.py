"""
Naukri.com Apply Agent — Semi-automated job search and application on Naukri.

Workflow:
1. Opens Naukri.com in a real browser
2. Waits for user to log in manually (if not already logged in)
3. Searches for jobs matching user's criteria (Pune, AI/ML, Fresher)
4. For each matching job: opens it, pre-fills the apply form, uploads resume
5. Pauses for user confirmation before submitting each application
6. Logs results for tracking
"""

import asyncio
import time
from typing import Dict, List, Optional

from playwright.async_api import TimeoutError as PlaywrightTimeout

from jobpilot.logger import logger
from jobpilot.browser_agent.config import browser_config
from jobpilot.browser_agent.helpers import BrowserHelper


class NaukriAgent:
    """Semi-automated Naukri.com job application agent."""

    NAUKRI_URL = "https://www.naukri.com"
    LOGIN_URL = "https://www.naukri.com/nlogin/login"
    SEARCH_BASE = "https://www.naukri.com"

    def __init__(self):
        self.helper = BrowserHelper(platform="naukri")
        self.applied_jobs: List[Dict] = []
        self.skipped_jobs: List[Dict] = []
        self.failed_jobs: List[Dict] = []

    async def start(self) -> Dict:
        """
        Main entry point: launches browser, ensures login, searches jobs, and applies.
        Returns a summary dict of the session.
        """
        page = await self.helper.launch()
        session_start = time.time()

        try:
            # Step 1: Check login
            await self._ensure_login(page)

            # Search targets: Pune first, then Remote (Work from home) if enabled
            targets = [
                {"name": f"{browser_config.SEARCH_LOCATION} (India)", "loc": browser_config.SEARCH_LOCATION, "remote": False}
            ]
            if browser_config.INCLUDE_REMOTE:
                targets.append(
                    {"name": "Remote / Work From Home", "loc": browser_config.SEARCH_LOCATION, "remote": True}
                )

            for target in targets:
                if not self.helper.can_apply_more():
                    break
                logger.info(f"[Naukri] >>> Searching target: {target['name']} <<<")
                await self._search_jobs(page, location=target["loc"], remote=target["remote"])
                await self._scan_and_apply(page)

        except Exception as e:
            logger.error(f"[Naukri] Session error: {e}")
            await self.helper.screenshot("error")

        duration = round(time.time() - session_start, 1)
        summary = {
            "platform": "Naukri.com",
            "duration_seconds": duration,
            "applied": len(self.applied_jobs),
            "skipped": len(self.skipped_jobs),
            "failed": len(self.failed_jobs),
            "applied_jobs": self.applied_jobs,
            "skipped_jobs": self.skipped_jobs,
        }
        logger.info(
            f"[Naukri] Session complete: {len(self.applied_jobs)} applied, "
            f"{len(self.skipped_jobs)} skipped, {len(self.failed_jobs)} failed "
            f"in {duration}s"
        )
        return summary

    async def stop(self):
        """Close the browser when user is done."""
        await self.helper.close()

    # -- Step 1: Login Management --------------------------------------

    async def _ensure_login(self, page):
        """Check if user is logged in. If not, navigate to login and wait."""
        logger.info("[Naukri] Checking login status...")
        self.helper.bring_to_foreground()
        self.helper.update_live_status("Checking Naukri login session...")
        await page.goto(self.NAUKRI_URL, wait_until="domcontentloaded")
        await self.helper.human_delay(2.0, 4.0)

        is_logged_in = await self._check_logged_in(page)

        if is_logged_in:
            logger.info("[Naukri] [OK] Already logged in via saved session!")
            self.helper.bring_to_foreground()
            self.helper.update_live_status("Already logged in to Naukri! Navigating to jobs...")
            await self.helper.screenshot("naukri_logged_in")
            return

        logger.info("[Naukri] Not logged in. Opening login page...")
        self.helper.bring_to_foreground()
        self.helper.update_live_status("Not logged in to Naukri. Waiting for login in Chromium...", {"waiting_for_user": True})
        logger.info("[Naukri] +======================================================+")
        logger.info("[Naukri] |  Please log in to Naukri.com in the browser window. |")
        logger.info("[Naukri] |  The agent will wait and resume automatically.      |")
        logger.info("[Naukri] +======================================================+")

        await page.goto(self.LOGIN_URL, wait_until="domcontentloaded")

        # Wait up to 5 minutes for user to log in
        for attempt in range(60):
            await asyncio.sleep(5)
            is_logged_in = await self._check_logged_in(page)
            if is_logged_in:
                logger.info("[Naukri] [OK] Login detected! Resuming agent...")
                return
            if attempt % 6 == 0 and attempt > 0:
                logger.info(f"[Naukri] Waiting for login... ({attempt * 5}s elapsed)")

        raise TimeoutError("[Naukri] Login timed out after 5 minutes.")

    async def _check_logged_in(self, page) -> bool:
        """Check if the user is currently logged in to Naukri."""
        try:
            url = page.url
            # If we're on a dashboard/mnjuser page, we're logged in
            if "/mnjuser" in url or "/dashboard" in url:
                return True

            # Check for profile/user elements
            for sel in [
                ".nI-gNb-drawer__icon",  # User avatar in nav
                'a[href*="mnjuser"]',
                ".nI-gNb-sb__cnt",
                '#login_Layer[style*="display: none"]',
                ".view-profile",
            ]:
                el = await page.query_selector(sel)
                if el:
                    return True

            # Check for "Logout" text
            logout = await page.query_selector('a:has-text("Logout"), a:has-text("Sign Out")')
            if logout:
                return True

            return False
        except Exception:
            return False

    # -- Step 2: Job Search --------------------------------------------

    async def _search_jobs(self, page, location: str = None, remote: bool = False):
        """Search for jobs matching user's criteria on Naukri."""
        keywords = browser_config.SEARCH_KEYWORDS.split(",")[0].strip()
        loc = location or browser_config.SEARCH_LOCATION
        experience = browser_config.SEARCH_EXPERIENCE  # e.g., "0-1"
        kw_slug = keywords.lower().replace(" ", "-").replace("/", "-")

        if remote:
            logger.info(f"[Naukri] Setting up Work-From-Home / Remote job search for '{keywords}'...")
            search_url = (
                f"https://www.naukri.com/work-from-home-{kw_slug}-jobs"
                f"?k={keywords.replace(' ', '+')}"
                f"&wfhType=0"
                f"&experience={experience.split('-')[0]}"
                f"&nignbevent_src=jobsearchDeskGNB"
            )
        else:
            logger.info(f"[Naukri] Setting up job search for '{keywords}' in '{loc}'...")
            search_url = (
                f"https://www.naukri.com/{kw_slug}-jobs-in-{loc.lower()}"
                f"?k={keywords.replace(' ', '+')}"
                f"&l={loc}"
                f"&experience={experience.split('-')[0]}"
                f"&nignbevent_src=jobsearchDeskGNB"
            )

        await page.goto(search_url, wait_until="domcontentloaded")
        await self.helper.human_delay(3.0, 5.0)

        # Try to close any popup/overlay
        await self._close_popups(page)

        await self.helper.screenshot("search_results")
        mode = "Remote / WFH" if remote else loc
        logger.info(f"[Naukri] Search loaded: '{keywords}' ({mode}), Exp: {experience} years")

    async def _close_popups(self, page):
        """Close common Naukri popups and overlays."""
        popup_selectors = [
            'button:has-text("Close")',
            ".chatbot_closeButton",
            "#cross-icon",
            'button[title="Close"]',
            ".modal-close",
        ]
        for sel in popup_selectors:
            try:
                btn = await page.query_selector(sel)
                if btn:
                    await btn.click()
                    await asyncio.sleep(0.5)
            except Exception:
                pass

    # -- Step 3: Scan and Apply ----------------------------------------

    async def _scan_and_apply(self, page):
        """Scan job listings and apply to matching jobs."""
        pages_scanned = 0

        while pages_scanned < browser_config.MAX_PAGES_TO_SCAN and self.helper.can_apply_more():
            pages_scanned += 1
            logger.info(f"[Naukri] Scanning page {pages_scanned}...")

            # Get job cards
            job_cards = await self._get_job_cards(page)
            logger.info(f"[Naukri] Found {len(job_cards)} job listings on page {pages_scanned}")

            for idx, card in enumerate(job_cards):
                if not self.helper.can_apply_more():
                    logger.info("[Naukri] Reached max applications per session. Stopping.")
                    return

                try:
                    job_info = await self._extract_job_from_card(card)
                    if not job_info:
                        continue

                    logger.info(
                        f"[Naukri] [{idx + 1}/{len(job_cards)}] "
                        f"{job_info.get('title', '?')} at {job_info.get('company', '?')}"
                    )

                    # Get the job link and open in same tab
                    link = await card.query_selector("a.title, a.cust-job-card-title, a[class*='title']")
                    if not link:
                        link = await card.query_selector("a")

                    if not link:
                        continue

                    href = await link.get_attribute("href")
                    if not href:
                        continue

                    if not href.startswith("http"):
                        href = f"https://www.naukri.com{href}"

                    # Open job page in new tab
                    job_page = await self.helper.context.new_page()
                    await job_page.goto(href, wait_until="domcontentloaded")
                    await self.helper.human_delay(2.0, 4.0)
                    await self._close_popups(job_page)

                    # Look for Apply button
                    apply_btn = await job_page.query_selector(
                        'button:has-text("Apply"), '
                        'button:has-text("Apply on company site"), '
                        '#apply-button, '
                        '.apply-button, '
                        'button[id*="apply"]'
                    )

                    if not apply_btn:
                        logger.info(f"  -> Skipping (no Apply button found)")
                        self.skipped_jobs.append({**job_info, "reason": "No Apply button"})
                        await job_page.close()
                        continue

                    # Check if already applied
                    already_applied = await job_page.query_selector(
                        ':text("Already Applied"), '
                        ':text("You have already applied"), '
                        '.already-applied'
                    )
                    if already_applied:
                        logger.info(f"  -> Already applied to this job")
                        self.skipped_jobs.append({**job_info, "reason": "Already applied"})
                        await job_page.close()
                        continue

                    apply_text = (await apply_btn.text_content()).strip().lower()

                    if "company site" in apply_text:
                        # External application — just open it
                        logger.info(f"  -> Opens company site (external apply)")
                        await apply_btn.click()
                        await self.helper.human_delay(3.0, 5.0)

                        logger.info("  +==================================================+")
                        logger.info(f"  | EXTERNAL APPLY: {job_info.get('title', '?')[:40]:<40} |")
                        logger.info("  | Complete the application on the company website. |")
                        logger.info("  | Close the tab when done or to skip.              |")
                        logger.info("  +==================================================+")

                        # Wait for user to handle external application
                        await self._wait_for_tab_close(job_page)
                        self.applied_jobs.append({**job_info, "channel": "external"})
                        self.helper.increment_applied()

                    else:
                        # Direct Naukri apply
                        await apply_btn.click()
                        await self.helper.human_delay(2.0, 3.5)

                        # Fill application form
                        await self._fill_naukri_form(job_page, job_info)

                        await self.helper.screenshot(f"naukri_ready_{idx}")

                        logger.info("  +==================================================+")
                        logger.info(f"  | READY TO SUBMIT: {job_info.get('title', '?')[:40]:<40} |")
                        logger.info("  | Review the form in the browser, then:            |")
                        logger.info("  |  • Click 'Submit' / 'Apply' to apply             |")
                        logger.info("  |  • Or close the tab to skip                      |")
                        logger.info("  +==================================================+")

                        submitted = await self._wait_for_naukri_submit(job_page)
                        if submitted:
                            self.applied_jobs.append({**job_info, "channel": "naukri_direct"})
                            self.helper.increment_applied()
                            logger.info(f"  [OK] Applied successfully!")
                        else:
                            self.skipped_jobs.append({**job_info, "reason": "User skipped"})
                            logger.info(f"  -> Skipped by user")

                    # Close the job page tab
                    try:
                        if not job_page.is_closed():
                            await job_page.close()
                    except Exception:
                        pass

                except Exception as e:
                    logger.warning(f"  [X] Error processing job {idx}: {e}")
                    self.failed_jobs.append({"index": idx, "error": str(e)})

            # Next page
            has_next = await self._go_to_next_page(page)
            if not has_next:
                logger.info("[Naukri] No more pages to scan.")
                break

    async def _get_job_cards(self, page) -> list:
        """Get job listing cards from search results."""
        selectors = [
            "article.jobTuple, .cust-job-tuple",
            ".srp-jobtuple-wrapper",
            ".jobTupleHeader",
            "div[data-job-id]",
            ".list .jobTuple",
        ]
        for sel in selectors:
            cards = await page.query_selector_all(sel)
            if cards:
                return cards[:20]  # Limit to 20 per page
        return []

    async def _extract_job_from_card(self, card) -> Optional[Dict]:
        """Extract job info from a Naukri search result card."""
        info = {}
        try:
            # Title
            for sel in ["a.title", ".cust-job-card-title", "a[class*='title']", ".row1 a"]:
                el = await card.query_selector(sel)
                if el:
                    info["title"] = (await el.text_content()).strip()
                    break

            # Company
            for sel in [".comp-name", ".companyInfo a", ".subTitle a", "a.comp-name"]:
                el = await card.query_selector(sel)
                if el:
                    info["company"] = (await el.text_content()).strip()
                    break

            # Location
            for sel in [".loc", ".locWdth", ".location", "span[class*='loc']"]:
                el = await card.query_selector(sel)
                if el:
                    info["location"] = (await el.text_content()).strip()
                    break

            # Experience
            for sel in [".exp", ".experience", "span[class*='exp']"]:
                el = await card.query_selector(sel)
                if el:
                    info["experience"] = (await el.text_content()).strip()
                    break

            info["source"] = "Naukri.com"
            info["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")

            return info if info.get("title") else None
        except Exception:
            return None

    async def _fill_naukri_form(self, page, job_info: Dict):
        """Fill the Naukri application form fields."""
        # Try to fill common form fields
        field_map = {
            "name": browser_config.CANDIDATE_NAME,
            "email": browser_config.CANDIDATE_EMAIL,
            "mobile": browser_config.CANDIDATE_PHONE.replace("+91 ", ""),
            "phone": browser_config.CANDIDATE_PHONE.replace("+91 ", ""),
            "experience": str(int(browser_config.CANDIDATE_EXPERIENCE_YEARS)),
            "current_ctc": browser_config.CANDIDATE_CURRENT_CTC,
            "expected_ctc": browser_config.CANDIDATE_EXPECTED_CTC,
            "notice_period": browser_config.CANDIDATE_NOTICE_PERIOD,
            "location": browser_config.CANDIDATE_CURRENT_LOCATION,
        }

        # Try filling inputs by placeholder, aria-label, or name attribute
        inputs = await page.query_selector_all("input[type='text'], input[type='email'], input[type='tel'], input[type='number']")
        for input_el in inputs:
            try:
                placeholder = (await input_el.get_attribute("placeholder") or "").lower()
                name = (await input_el.get_attribute("name") or "").lower()
                aria = (await input_el.get_attribute("aria-label") or "").lower()
                combined = f"{placeholder} {name} {aria}"

                current_value = await input_el.input_value()
                if current_value.strip():
                    continue  # Don't overwrite existing values

                for key, value in field_map.items():
                    if key in combined:
                        await input_el.fill(value)
                        logger.debug(f"  Filled: {key} = {value}")
                        break

            except Exception:
                continue

        # Try to upload resume
        file_inputs = await page.query_selector_all('input[type="file"]')
        for fi in file_inputs:
            try:
                if browser_config.resume_file.exists():
                    await fi.set_input_files(str(browser_config.resume_file))
                    logger.info("  Uploaded: Resume PDF")
                    break
            except Exception:
                continue

    async def _wait_for_naukri_submit(self, page, timeout: int = 120) -> bool:
        """Wait for user to submit or close the application."""
        if browser_config.AUTO_SUBMIT:
            logger.info("  [Auto-Submit] Submitting application automatically...")
            for sel in [
                'button:has-text("Submit"), button:has-text("Apply"), .apply-button'
            ]:
                try:
                    btn = await page.query_selector(sel)
                    if btn:
                        await self.helper.human_delay(1.5, 2.5)
                        await btn.click()
                        await self.helper.human_delay(2.0, 3.5)
                        return True
                except Exception:
                    pass

        start = time.time()
        while time.time() - start < timeout:
            await asyncio.sleep(2)

            # Check if page is closed
            try:
                if page.is_closed():
                    return False
            except Exception:
                return False

            # Check for success indicators
            success_selectors = [
                ':text("Application Submitted")',
                ':text("applied successfully")',
                ':text("You have successfully applied")',
                ".apply-success",
            ]
            for sel in success_selectors:
                try:
                    el = await page.query_selector(sel)
                    if el:
                        return True
                except Exception:
                    pass

        return False

    async def _wait_for_tab_close(self, page, timeout: int = 180):
        """Wait for user to close the external application tab."""
        start = time.time()
        while time.time() - start < timeout:
            await asyncio.sleep(3)
            try:
                if page.is_closed():
                    return
            except Exception:
                return

    async def _go_to_next_page(self, page) -> bool:
        """Navigate to the next page of Naukri search results."""
        try:
            next_btn = await page.query_selector(
                'a:has-text("Next"), '
                'a.fright.fs14.btn-secondary, '
                '.pagination a.fright'
            )
            if next_btn:
                await next_btn.click()
                await self.helper.human_delay(3.0, 5.0)
                await self._close_popups(page)
                return True
        except Exception:
            pass
        return False


async def run_naukri_agent() -> Dict:
    """Convenience function to run the Naukri agent."""
    agent = NaukriAgent()
    try:
        return await agent.start()
    except Exception as e:
        logger.error(f"[Naukri] Agent failed: {e}")
        return {"platform": "Naukri.com", "error": str(e)}
