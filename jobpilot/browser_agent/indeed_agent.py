"""
Indeed Apply Agent — Semi-automated job search and application on Indeed India.

Workflow:
1. Opens Indeed India in a real browser
2. Searches for jobs matching user's criteria (Pune, AI/ML, Fresher)
3. For each matching job: opens it, identifies apply mechanism
4. If Indeed Apply: pre-fills the form, uploads resume, pauses for user
5. If external site: opens it for user to complete manually
"""

import asyncio
import time
from typing import Dict, List, Optional

from playwright.async_api import TimeoutError as PlaywrightTimeout

from jobpilot.logger import logger
from jobpilot.browser_agent.config import browser_config
from jobpilot.browser_agent.helpers import BrowserHelper


class IndeedAgent:
    """Semi-automated Indeed India job application agent."""

    INDEED_URL = "https://in.indeed.com"

    def __init__(self):
        self.helper = BrowserHelper(platform="indeed")
        self.applied_jobs: List[Dict] = []
        self.skipped_jobs: List[Dict] = []
        self.failed_jobs: List[Dict] = []

    async def start(self) -> Dict:
        """Main entry point."""
        page = await self.helper.launch()
        session_start = time.time()

        try:
            # Indeed doesn't always require login for search
            await page.goto(self.INDEED_URL, wait_until="domcontentloaded")
            await self.helper.human_delay(2.0, 4.0)

            # Check if there's a login prompt and handle it
            login_prompt = await page.query_selector('a:has-text("Sign in"), a[href*="login"]')
            if login_prompt:
                logger.info("[Indeed] Sign-in available. Checking if needed for applications...")

            targets = [browser_config.SEARCH_LOCATION]
            if browser_config.INCLUDE_REMOTE:
                targets.append("Remote")

            for loc in targets:
                if not self.helper.can_apply_more():
                    break
                logger.info(f"[Indeed] >>> Searching location: {loc} <<<")
                await self._search_jobs(page, location=loc)
                await self._scan_and_apply(page)

        except Exception as e:
            logger.error(f"[Indeed] Session error: {e}")
            await self.helper.screenshot("error")

        duration = round(time.time() - session_start, 1)
        summary = {
            "platform": "Indeed India",
            "duration_seconds": duration,
            "applied": len(self.applied_jobs),
            "skipped": len(self.skipped_jobs),
            "failed": len(self.failed_jobs),
            "applied_jobs": self.applied_jobs,
            "skipped_jobs": self.skipped_jobs,
        }
        logger.info(
            f"[Indeed] Session complete: {len(self.applied_jobs)} applied, "
            f"{len(self.skipped_jobs)} skipped, {len(self.failed_jobs)} failed "
            f"in {duration}s"
        )
        return summary

    async def stop(self):
        """Close the browser."""
        await self.helper.close()

    # -- Job Search ----------------------------------------------------

    async def _search_jobs(self, page, location: str = None):
        """Search for jobs on Indeed India."""
        keywords = browser_config.SEARCH_KEYWORDS.split(",")[0].strip()
        loc = location or browser_config.SEARCH_LOCATION
        freshness = browser_config.SEARCH_FRESHNESS

        self.helper.bring_to_foreground()
        self.helper.update_live_status(f"Searching Indeed for '{keywords}' in '{loc}'...")

        search_url = (
            f"https://in.indeed.com/jobs"
            f"?q={keywords.replace(' ', '+')}"
            f"&l={loc.replace(' ', '+')}"
            f"&fromage={freshness}"  # Last N days
            f"&sort=date"
        )

        await page.goto(search_url, wait_until="domcontentloaded")
        await self.helper.human_delay(3.0, 5.0)
        await self.helper.screenshot("search_results")
        logger.info(f"[Indeed] Search loaded: '{keywords}' in '{loc}', last {freshness} days")

    # -- Scan and Apply ------------------------------------------------

    async def _scan_and_apply(self, page):
        """Scan job listings and process applications."""
        pages_scanned = 0

        while pages_scanned < browser_config.MAX_PAGES_TO_SCAN and self.helper.can_apply_more():
            pages_scanned += 1
            logger.info(f"[Indeed] Scanning page {pages_scanned}...")

            # Get job cards
            job_cards = await self._get_job_cards(page)
            self.helper.update_live_status(f"Scanning Indeed page {pages_scanned} (Found {len(job_cards)} jobs)...")
            logger.info(f"[Indeed] Found {len(job_cards)} job listings on page {pages_scanned}")

            for idx, card in enumerate(job_cards):
                if not self.helper.can_apply_more():
                    logger.info("[Indeed] Reached max applications cap. Stopping.")
                    return

                try:
                    job_info = await self._extract_job_from_card(card)
                    if not job_info:
                        continue

                    logger.info(
                        f"[Indeed] [{idx + 1}/{len(job_cards)}] "
                        f"{job_info.get('title', '?')} at {job_info.get('company', '?')}"
                    )

                    # Click on job card to load details
                    await card.click()
                    await self.helper.human_delay(2.0, 3.5)

                    # Look for Apply button in the job detail pane
                    apply_btn = await page.query_selector(
                        '#indeedApplyButton, '
                        'button:has-text("Apply now"), '
                        'a:has-text("Apply now"), '
                        'button[id*="apply"], '
                        '.jobsearch-IndeedApplyButton-newDesign'
                    )

                    if not apply_btn:
                        logger.info(f"  -> No direct apply button found")
                        self.skipped_jobs.append({**job_info, "reason": "No apply button"})
                        continue

                    apply_text = (await apply_btn.text_content()).strip().lower()
                    apply_href = await apply_btn.get_attribute("href") or ""

                    # Check if it's Indeed Apply or external
                    is_indeed_apply = "indeedapply" in (await apply_btn.get_attribute("class") or "").lower()

                    if is_indeed_apply or "apply now" in apply_text:
                        # Open in new tab for application
                        job_page = await self.helper.context.new_page()

                        # Get the actual job URL
                        job_link = await card.query_selector("a[href*='/viewjob'], a[data-jk], h2 a")
                        if job_link:
                            job_href = await job_link.get_attribute("href")
                            if job_href and not job_href.startswith("http"):
                                job_href = f"https://in.indeed.com{job_href}"
                            if job_href:
                                await job_page.goto(job_href, wait_until="domcontentloaded")
                                await self.helper.human_delay(2.0, 4.0)

                        # Click apply on the job page
                        job_apply_btn = await job_page.query_selector(
                            '#indeedApplyButton, '
                            'button:has-text("Apply now"), '
                            'a:has-text("Apply now")'
                        )

                        if job_apply_btn:
                            await job_apply_btn.click()
                            await self.helper.human_delay(2.0, 4.0)

                            # Handle login if required
                            login_check = await job_page.query_selector(
                                '#login-email-input, '
                                'input[name="__email"], '
                                ':text("Sign in to apply")'
                            )
                            if login_check:
                                logger.info("  +===============================================+")
                                logger.info("  | Indeed requires sign-in to apply.             |")
                                logger.info("  | Please sign in in the browser window.         |")
                                logger.info("  +===============================================+")

                                # Wait for user to sign in (up to 3 minutes)
                                for _ in range(36):
                                    await asyncio.sleep(5)
                                    login_check = await job_page.query_selector(
                                        '#login-email-input, input[name="__email"]'
                                    )
                                    if not login_check:
                                        break

                            # Fill application form fields
                            await self._fill_indeed_form(job_page, job_info)

                            await self.helper.screenshot(f"indeed_ready_{idx}")

                            logger.info("  +==================================================+")
                            logger.info(f"  | READY: {job_info.get('title', '?')[:46]:<46} |")
                            logger.info("  | Review & click 'Submit' or close tab to skip.   |")
                            logger.info("  +==================================================+")

                            submitted = await self._wait_for_submit(job_page)
                            if submitted:
                                self.applied_jobs.append({**job_info, "channel": "indeed_direct"})
                                self.helper.increment_applied()
                                logger.info(f"  [OK] Applied!")
                            else:
                                self.skipped_jobs.append({**job_info, "reason": "User skipped"})

                        try:
                            if not job_page.is_closed():
                                await job_page.close()
                        except Exception:
                            pass

                    else:
                        # External application
                        logger.info(f"  -> External site apply — opening...")
                        self.skipped_jobs.append({**job_info, "reason": "External apply"})

                except Exception as e:
                    logger.warning(f"  [X] Error on job {idx}: {e}")
                    self.failed_jobs.append({"index": idx, "error": str(e)})

            # Next page
            has_next = await self._go_to_next_page(page)
            if not has_next:
                break

    async def _get_job_cards(self, page) -> list:
        """Get job listing cards from Indeed search results."""
        selectors = [
            ".job_seen_beacon",
            ".jobsearch-ResultsList > li",
            "div.cardOutline",
            ".tapItem",
        ]
        for sel in selectors:
            cards = await page.query_selector_all(sel)
            if cards:
                return cards[:15]
        return []

    async def _extract_job_from_card(self, card) -> Optional[Dict]:
        """Extract job info from an Indeed search result card."""
        info = {}
        try:
            # Title
            for sel in ["h2.jobTitle a span", "h2.jobTitle span", ".jcs-JobTitle span", "a[data-jk] span"]:
                el = await card.query_selector(sel)
                if el:
                    info["title"] = (await el.text_content()).strip()
                    break

            # Company
            for sel in [".companyName", "span[data-testid='company-name']", ".company"]:
                el = await card.query_selector(sel)
                if el:
                    info["company"] = (await el.text_content()).strip()
                    break

            # Location
            for sel in [".companyLocation", "div[data-testid='text-location']", ".location"]:
                el = await card.query_selector(sel)
                if el:
                    info["location"] = (await el.text_content()).strip()
                    break

            info["source"] = "Indeed India"
            info["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")

            return info if info.get("title") else None
        except Exception:
            return None

    async def _fill_indeed_form(self, page, job_info: Dict):
        """Fill Indeed application form fields."""
        inputs = await page.query_selector_all("input, textarea, select")
        for el in inputs:
            try:
                el_type = await el.get_attribute("type") or ""
                name = (await el.get_attribute("name") or "").lower()
                label_id = await el.get_attribute("id") or ""
                aria = (await el.get_attribute("aria-label") or "").lower()
                placeholder = (await el.get_attribute("placeholder") or "").lower()
                combined = f"{name} {label_id} {aria} {placeholder}"

                current_value = await el.input_value() if el_type not in ("file", "checkbox", "radio") else ""
                if current_value and current_value.strip():
                    continue

                if el_type == "file":
                    if browser_config.resume_file.exists():
                        await el.set_input_files(str(browser_config.resume_file))
                        logger.info("  Uploaded: Resume")
                elif any(kw in combined for kw in ["name", "full_name", "fullname"]):
                    await el.fill(browser_config.CANDIDATE_NAME)
                elif any(kw in combined for kw in ["email", "e-mail"]):
                    await el.fill(browser_config.CANDIDATE_EMAIL)
                elif any(kw in combined for kw in ["phone", "mobile", "contact"]):
                    await el.fill(browser_config.CANDIDATE_PHONE)
                elif any(kw in combined for kw in ["city", "location"]):
                    await el.fill(browser_config.CANDIDATE_CURRENT_LOCATION)

            except Exception:
                continue

    async def _wait_for_submit(self, page, timeout: int = 120) -> bool:
        """Wait for user to submit or close."""
        if browser_config.AUTO_SUBMIT:
            logger.info("  [Auto-Submit] Auto-submitting application...")
            for sel in [
                'button:has-text("Submit your application")',
                'button:has-text("Submit application")',
                'button:has-text("Submit")',
                'button[type="submit"]',
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
            try:
                if page.is_closed():
                    return False
            except Exception:
                return False

            for sel in [
                ':text("Application submitted")',
                ':text("You have applied")',
                ':text("Your application has been submitted")',
            ]:
                try:
                    el = await page.query_selector(sel)
                    if el:
                        return True
                except Exception:
                    pass
        return False

    async def _go_to_next_page(self, page) -> bool:
        """Navigate to next page of Indeed results."""
        try:
            next_link = await page.query_selector(
                'a[data-testid="pagination-page-next"], '
                'a[aria-label="Next Page"], '
                'a:has-text("Next")'
            )
            if next_link:
                await next_link.click()
                await self.helper.human_delay(3.0, 5.0)
                return True
        except Exception:
            pass
        return False


async def run_indeed_agent() -> Dict:
    """Convenience function to run the Indeed agent."""
    agent = IndeedAgent()
    try:
        return await agent.start()
    except Exception as e:
        logger.error(f"[Indeed] Agent failed: {e}")
        return {"platform": "Indeed India", "error": str(e)}
