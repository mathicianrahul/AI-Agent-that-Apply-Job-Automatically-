"""
LinkedIn Easy Apply Agent — Semi-automated LinkedIn job search and application.

Workflow:
1. Opens LinkedIn in a real browser
2. Waits for user to log in (if not already logged in via saved session)
3. Navigates to job search with user's criteria
4. Scans job listings and identifies Easy Apply jobs
5. Opens each job, pre-fills the application form with candidate info
6. Pauses for user confirmation before submitting each application
7. Logs results to the database
"""

import asyncio
import re
import time
from typing import Dict, List, Optional, Tuple

from playwright.async_api import TimeoutError as PlaywrightTimeout

from jobpilot.logger import logger
from jobpilot.browser_agent.config import browser_config
from jobpilot.browser_agent.helpers import BrowserHelper


class LinkedInAgent:
    """Semi-automated LinkedIn Easy Apply agent."""

    LINKEDIN_URL = "https://www.linkedin.com"
    JOBS_URL = "https://www.linkedin.com/jobs"
    LOGIN_URL = "https://www.linkedin.com/login"

    def __init__(self):
        self.helper = BrowserHelper(platform="linkedin")
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
            # Step 1: Check if already logged in or wait for manual login
            await self._ensure_login(page)

            # Search targets: Pune first, then Remote (Worldwide) if enabled
            targets = [
                {"name": f"{browser_config.SEARCH_LOCATION} (India)", "loc": browser_config.SEARCH_LOCATION, "remote": False}
            ]
            if browser_config.INCLUDE_REMOTE:
                targets.append(
                    {"name": "Remote (Worldwide / International)", "loc": "Worldwide", "remote": True}
                )

            for target in targets:
                if not self.helper.can_apply_more():
                    break
                logger.info(f"[LinkedIn] >>> Searching target: {target['name']} <<<")
                await self._search_jobs(page, location=target["loc"], remote=target["remote"])
                await self._scan_and_apply(page)

        except Exception as e:
            logger.error(f"[LinkedIn] Session error: {e}")
            await self.helper.screenshot("error")

        duration = round(time.time() - session_start, 1)
        summary = {
            "platform": "LinkedIn",
            "duration_seconds": duration,
            "applied": len(self.applied_jobs),
            "skipped": len(self.skipped_jobs),
            "failed": len(self.failed_jobs),
            "applied_jobs": self.applied_jobs,
            "skipped_jobs": self.skipped_jobs,
        }
        logger.info(
            f"[LinkedIn] Session complete: {len(self.applied_jobs)} applied, "
            f"{len(self.skipped_jobs)} skipped, {len(self.failed_jobs)} failed "
            f"in {duration}s"
        )
        # Don't close browser — keep it open so user can review
        return summary

    async def stop(self):
        """Close the browser when user is done."""
        await self.helper.close()

    # -- Step 1: Login Management --------------------------------------

    async def _ensure_login(self, page):
        """Check if user is logged in. If not, navigate to login and wait."""
        logger.info("[LinkedIn] Checking login status...")
        self.helper.bring_to_foreground()
        self.helper.update_live_status("Checking LinkedIn login session...")
        await page.goto("https://www.linkedin.com/feed", wait_until="domcontentloaded")
        await self.helper.human_delay(2.0, 4.0)

        # Check if we're on the feed (logged in) or redirected to login
        is_logged_in = await self._check_logged_in(page)

        if is_logged_in:
            logger.info("[LinkedIn] [OK] Already logged in via saved session!")
            self.helper.bring_to_foreground()
            self.helper.update_live_status("Already logged in! Navigating to jobs...")
            await self.helper.screenshot("logged_in")
            return

        # Navigate to login page
        logger.info("[LinkedIn] Not logged in. Opening login page...")
        self.helper.bring_to_foreground()
        self.helper.update_live_status("Not logged in. Waiting for you to log in in Chromium...", {"waiting_for_user": True})
        await self.helper.screenshot("login_page")
        logger.info("[LinkedIn] +======================================================+")
        logger.info("[LinkedIn] |  Please log in to LinkedIn in the browser window.   |")
        logger.info("[LinkedIn] |  The agent will wait and resume automatically.      |")
        logger.info("[LinkedIn] +======================================================+")

        await page.goto(self.LOGIN_URL, wait_until="domcontentloaded")

        # Wait up to 5 minutes for user to log in
        for attempt in range(60):  # 60 x 5s = 5 minutes
            await asyncio.sleep(5)
            is_logged_in = await self._check_logged_in(page)
            if is_logged_in:
                logger.info("[LinkedIn] [OK] Login detected! Resuming agent...")
                return
            if attempt % 6 == 0 and attempt > 0:
                logger.info(f"[LinkedIn] Waiting for login... ({attempt * 5}s elapsed)")

        raise TimeoutError("[LinkedIn] Login timed out after 5 minutes.")

    async def _check_logged_in(self, page) -> bool:
        """Check if the user is currently logged in to LinkedIn."""
        try:
            url = page.url
            # If on login, signup, authwall, or checkpoint -> definitely NOT logged in
            if any(k in url for k in ["/login", "/signup", "/authwall", "/checkpoint", "uas/login"]):
                return False

            # If there's a visible Sign In / Join now button, NOT logged in
            sign_in_btn = await page.query_selector(
                'a[href*="/login"].nav__button-secondary, '
                'a.nav__button-secondary:has-text("Sign in"), '
                'button:has-text("Sign in")'
            )
            if sign_in_btn:
                visible = await sign_in_btn.is_visible()
                if visible:
                    return False

            # /feed and /mynetwork are always authenticated pages
            if "/feed" in url or "/mynetwork" in url or "/in/" in url:
                return True

            # Check for authenticated nav elements
            for sel in [
                '.global-nav__me',
                'nav[aria-label="Primary"]',
                '.global-nav',
                'img.global-nav__me-photo',
                '#ember-global-nav',
            ]:
                el = await page.query_selector(sel)
                if el:
                    return True

            return False
        except Exception:
            return False

    # -- Step 2: Job Search --------------------------------------------

    async def _close_popups(self, page):
        """Close LinkedIn sign-in modals and other popups."""
        popup_selectors = [
            'button[data-test-modal-close-btn]',
            'button[aria-label="Dismiss"]',
            '.modal__dismiss',
            'button.contextual-sign-in-modal__modal-dismiss-btn',
            'button.artdeco-modal__dismiss',
        ]
        for sel in popup_selectors:
            try:
                btn = await page.query_selector(sel)
                if btn and await btn.is_visible():
                    await btn.click()
                    await asyncio.sleep(0.5)
                    logger.debug("[LinkedIn] Closed popup")
            except Exception:
                pass
        # Also try pressing Escape
        try:
            await page.keyboard.press('Escape')
            await asyncio.sleep(0.3)
        except Exception:
            pass

    async def _search_jobs(self, page, location: str = None, remote: bool = False):
        """Navigate to LinkedIn Jobs and perform a search with user's criteria."""
        keywords = browser_config.SEARCH_KEYWORDS.split(",")[0].strip()
        loc = location or browser_config.SEARCH_LOCATION
        mode_label = "Remote" if remote else loc
        logger.info(f"[LinkedIn] Navigating to job search for '{keywords}' in '{mode_label}'...")
        self.helper.update_live_status(f"Navigating to job search for '{keywords}' in '{mode_label}'...")

        # Build LinkedIn job search URL with filters
        # f_AL=true (Easy Apply), f_E=2 (Entry level), f_TPR=r604800 (Past week), f_WT=2 (Remote)
        remote_param = "&f_WT=2" if remote else ""
        search_url = (
            f"https://www.linkedin.com/jobs/search/"
            f"?keywords={keywords.replace(' ', '%20')}"
            f"&location={loc.replace(' ', '%20')}"
            f"&f_AL=true"
            f"&f_E=2"
            f"&f_TPR=r604800"
            f"{remote_param}"
            f"&sortBy=DD"
        )

        await page.goto(search_url, wait_until="domcontentloaded")
        await self.helper.human_delay(3.0, 5.0)

        # Close any sign-in popup that appears
        await self._close_popups(page)
        await self.helper.human_delay(1.0, 2.0)

        await self.helper.screenshot("search_results")
        self.helper.update_live_status(f"Search loaded: '{keywords}' in '{loc}' ({mode_label})")
        logger.info(f"[LinkedIn] Search loaded: '{keywords}' in '{loc}' ({mode_label}) -- Easy Apply + Entry Level")

    # ── Step 3: Scan and Apply ────────────────────────────────────────

    async def _scan_and_apply(self, page):
        """Scan job listings and apply to matching Easy Apply jobs."""
        pages_scanned = 0

        while pages_scanned < browser_config.MAX_PAGES_TO_SCAN and self.helper.can_apply_more():
            pages_scanned += 1
            logger.info(f"[LinkedIn] Scanning page {pages_scanned}...")
            self.helper.update_live_status(f"Scanning search results page {pages_scanned}...")

            # Get job cards on this page
            job_cards = await self._get_job_cards(page)
            logger.info(f"[LinkedIn] Found {len(job_cards)} job cards on page {pages_scanned}")
            self.helper.update_live_status(f"Found {len(job_cards)} job cards on page {pages_scanned}")

            for idx, card in enumerate(job_cards):
                if not self.helper.can_apply_more():
                    logger.info("[LinkedIn] Reached max applications per session. Stopping.")
                    return

                try:
                    # Click on the job card to load details
                    await card.click()
                    await self.helper.human_delay(1.5, 3.0)

                    # Extract job info
                    job_info = await self._extract_job_info(page, card)
                    if not job_info:
                        continue

                    await self.helper.screenshot(f"viewing_job_{idx}")
                    logger.info(
                        f"[LinkedIn] [{idx + 1}/{len(job_cards)}] "
                        f"{job_info.get('title', '?')} at {job_info.get('company', '?')}"
                    )
                    self.helper.update_live_status(
                        f"Inspecting [{idx + 1}/{len(job_cards)}]: {job_info.get('title', '?')} at {job_info.get('company', '?')}",
                        {"job": job_info, "card_index": idx + 1, "total_cards": len(job_cards)}
                    )

                    # Check if Easy Apply button exists
                    easy_apply_btn = await page.query_selector(
                        'button[aria-label*="Easy Apply"], '
                        'button:has-text("Easy Apply"), '
                        'button.jobs-apply-button'
                    )

                    if not easy_apply_btn:
                        logger.info(f"  -> Skipping (no Easy Apply button)")
                        self.skipped_jobs.append({**job_info, "reason": "No Easy Apply"})
                        self.helper.update_live_status(
                            f"Skipping (no Easy Apply): {job_info.get('title', '?')}",
                            {"job": job_info, "reason": "No Easy Apply"}
                        )
                        continue

                    # Click Easy Apply
                    self.helper.update_live_status(
                        f"Opening Easy Apply: {job_info.get('title', '?')}",
                        {"job": job_info}
                    )
                    await easy_apply_btn.click()
                    await self.helper.human_delay(2.0, 3.5)
                    await self.helper.screenshot(f"easy_apply_opened_{idx}")

                    # Fill the application form
                    filled = await self._fill_application_form(page, job_info)

                    if filled:
                        # Take screenshot for user to review
                        await self.helper.screenshot(f"ready_to_submit_{idx}")

                        self.helper.update_live_status(
                            f"Review Required: {job_info.get('title', '?')} at {job_info.get('company', '?')}",
                            {"job": job_info, "waiting_for_user": True, "card_index": idx + 1, "total_cards": len(job_cards)}
                        )

                        logger.info("  +==================================================+")
                        logger.info(f"  | READY TO SUBMIT: {job_info.get('title', '?')[:40]:<40} |")
                        logger.info("  | Review the form in the browser, then:            |")
                        logger.info("  |  • Click 'Submit' to apply                       |")
                        logger.info("  |  • Or close the dialog to skip                   |")
                        logger.info("  +==================================================+")

                        # Wait for user to submit or close the dialog
                        submitted = await self._wait_for_user_action(page, job_info=job_info)

                        if submitted:
                            self.applied_jobs.append(job_info)
                            self.helper.increment_applied()
                            logger.info(f"  [OK] Applied successfully!")
                            self.helper.update_live_status(
                                f"Applied: {job_info.get('title', '?')} at {job_info.get('company', '?')}",
                                {"job": job_info, "applied": True}
                            )
                        else:
                            self.skipped_jobs.append({**job_info, "reason": "User skipped"})
                            logger.info(f"  -> Skipped by user")
                            self.helper.update_live_status(
                                f"Skipped: {job_info.get('title', '?')}",
                                {"job": job_info, "skipped": True}
                            )

                except Exception as e:
                    logger.warning(f"  [X] Error processing job card {idx}: {e}")
                    self.failed_jobs.append({"index": idx, "error": str(e)})
                    # Try to close any open dialog
                    await self._close_apply_dialog(page)

            # Try to go to next page
            has_next = await self._go_to_next_page(page)
            if not has_next:
                logger.info("[LinkedIn] No more pages to scan.")
                break

    async def _get_job_cards(self, page) -> list:
        """Get all job listing cards on the current search results page."""
        # Close any lingering popups first
        await self._close_popups(page)

        # 1. First try traditional selectors (for guest or classic views)
        selectors = [
            ".jobs-search-results__list-item",
            ".job-card-container",
            "li.jobs-search-results-list__list-item",
            ".scaffold-layout__list-item",
            ".jobs-search__results-list li",
            ".base-card",
            "ul.jobs-search__results-list > li",
            ".base-search-card",
            "div.base-search-card",
            "li .base-card",
        ]
        for sel in selectors:
            cards = await page.query_selector_all(sel)
            if cards:
                logger.info(f"[LinkedIn] Found {len(cards)} cards with selector: {sel}")
                return cards[:20]

        # 2. Modern authenticated LinkedIn UI (Dynamic scroll container extraction)
        try:
            js_handle = await page.evaluate_handle('''() => {
                const scrollContainers = Array.from(document.querySelectorAll('div')).filter(d => {
                    const s = window.getComputedStyle(d);
                    return (s.overflowY === 'auto' || s.overflowY === 'scroll') && d.children.length >= 3;
                });
                for (const c of scrollContainers) {
                    if (c.innerText.includes('ago') || c.innerText.includes('Apply') || c.innerText.includes('Easy Apply')) {
                        const validChildren = [];
                        for (const child of c.children) {
                            const txt = child.innerText || '';
                            if ((txt.includes('ago') || txt.includes('Apply')) && txt.length > 20) {
                                validChildren.push(child);
                            }
                        }
                        if (validChildren.length > 0) return validChildren;
                    }
                }
                // Fallback: any div[data-display-contents="true"]
                const ddc = Array.from(document.querySelectorAll('div[data-display-contents="true"]')).filter(el => {
                    const txt = el.innerText || '';
                    return (txt.includes('ago') || txt.includes('Apply')) && txt.length > 20 && txt.length < 500;
                });
                return ddc;
            }''')
            props = await js_handle.get_properties()
            cards = [v.as_element() for k, v in props.items() if v.as_element()]
            if cards:
                logger.info(f"[LinkedIn] Found {len(cards)} cards using modern UI detector")
                return cards[:20]
        except Exception as e:
            logger.debug(f"[LinkedIn] Dynamic card extraction error: {e}")

        return []

    async def _extract_job_info(self, page, card=None) -> Optional[Dict]:
        """Extract job title, company, and location from the job detail pane or card."""
        info = {}
        try:
            # 1. Detail pane title
            for sel in [
                "a[href*='/jobs/view/']",
                ".jobs-unified-top-card__job-title",
                ".job-details-jobs-unified-top-card__job-title",
                "h1",
                "h2",
            ]:
                title_el = await page.query_selector(sel)
                if title_el:
                    txt = (await title_el.text_content() or "").strip()
                    if txt and len(txt) > 3 and not any(txt.lower().startswith(x) for x in ["are these", "get job", "0 notif"]):
                        info["title"] = txt
                        break

            # 2. Company name
            for sel in [
                "a[href*='/company/']",
                ".jobs-unified-top-card__company-name",
                ".job-details-jobs-unified-top-card__company-name",
                "a.ember-view.t-black.t-normal",
            ]:
                co_el = await page.query_selector(sel)
                if co_el:
                    co_text = (await co_el.text_content() or "").strip()
                    if co_text and len(co_text) > 1:
                        info["company"] = co_text
                        break

            # 3. Location
            for sel in [
                ".jobs-unified-top-card__bullet",
                ".job-details-jobs-unified-top-card__bullet",
                ".t-black--light.mt2",
            ]:
                loc_el = await page.query_selector(sel)
                if loc_el:
                    info["location"] = (await loc_el.text_content() or "").strip()
                    break

            # 4. Fallback from card text if card was passed
            if card and (not info.get("title") or not info.get("company")):
                try:
                    card_text = await card.inner_text()
                    lines = [l.strip() for l in card_text.split("\n") if l.strip() and not l.strip().startswith("Selected,")]
                    if lines:
                        if not info.get("title"):
                            info["title"] = lines[0]
                        if len(lines) > 1 and not info.get("company"):
                            info["company"] = lines[1]
                        if len(lines) > 2 and not info.get("location"):
                            info["location"] = lines[2]
                except Exception:
                    pass

            # 5. Fallback from page document title
            if not info.get("title"):
                doc_title = await page.title()
                if "|" in doc_title:
                    parts = doc_title.split("|")
                    info["title"] = parts[0].strip()
                    if len(parts) > 1 and not info.get("company"):
                        info["company"] = parts[1].strip()

            if not info.get("location"):
                info["location"] = browser_config.SEARCH_LOCATION

            info["url"] = page.url
            info["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")

            return info if info.get("title") else None

        except Exception as e:
            logger.debug(f"[LinkedIn] Error extracting job info: {e}")
            return None

    # ── Form Filling ──────────────────────────────────────────────────

    async def _fill_application_form(self, page, job_info: Dict) -> bool:
        """Fill the Easy Apply multi-step form."""
        max_steps = 7  # LinkedIn forms usually have 1-5 steps

        for step in range(max_steps):
            await self.helper.human_delay(1.0, 2.0)

            # Fill common fields on the current step
            await self._fill_current_step(page)
            await self.helper.screenshot(f"form_step_{step}")
            self.helper.update_live_status(
                f"Form step {step + 1} filled for {job_info.get('title', '?')}",
                {"job": job_info}
            )

            # Check if we're on the review/submit step
            submit_btn = await page.query_selector(
                'button[aria-label*="Submit"], '
                'button:has-text("Submit application"), '
                'button:has-text("Review")'
            )
            if submit_btn:
                btn_text = (await submit_btn.text_content()).strip().lower()
                if "review" in btn_text:
                    # Click review to go to final step
                    await submit_btn.click()
                    await self.helper.human_delay(1.5, 2.5)
                    continue
                elif "submit" in btn_text:
                    # We're at the submit step
                    return True

            # Try to go to next step
            next_btn = await page.query_selector(
                'button[aria-label*="Continue"], '
                'button:has-text("Next"), '
                'button:has-text("Continue")'
            )
            if next_btn:
                await next_btn.click()
                await self.helper.human_delay(1.5, 2.5)
            else:
                # No next button found — might be on final step
                return True

        return True

    async def _fill_current_step(self, page):
        """Detect and fill form fields on the current Easy Apply step."""
        try:
            # 1. Fill city / location field if empty
            city_inputs = await page.query_selector_all(
                'input[placeholder*="city" i], input[placeholder*="location" i], input[id*="city" i]'
            )
            for cinp in city_inputs:
                try:
                    val = await cinp.input_value()
                    if not val.strip():
                        await cinp.fill(browser_config.SEARCH_LOCATION)
                        await asyncio.sleep(0.5)
                        await page.keyboard.press("ArrowDown")
                        await asyncio.sleep(0.2)
                        await page.keyboard.press("Enter")
                        logger.info(f"  Filled: Location with '{browser_config.SEARCH_LOCATION}'")
                except Exception:
                    pass

            # 2. Check for Resume upload input
            resume_inputs = await page.query_selector_all('input[type="file"]')
            for rinput in resume_inputs:
                try:
                    if browser_config.resume_file.exists():
                        await rinput.set_input_files(str(browser_config.resume_file))
                        logger.info("  Uploaded: Resume PDF")
                except Exception:
                    pass

            # 3. Check for form inputs / groups
            form_groups = await page.query_selector_all(
                ".jobs-easy-apply-form-section__grouping, "
                ".fb-dash-form-element, "
                ".artdeco-text-input, "
                "div[data-test-form-element]"
            )

            for group in form_groups:
                try:
                    label_el = await group.query_selector("label, .fb-dash-form-element__label, span.t-14")
                    if not label_el:
                        continue

                    label_text = (await label_el.text_content()).strip().lower()

                    # Phone number
                    if any(kw in label_text for kw in ["phone", "mobile", "contact number"]):
                        input_el = await group.query_selector("input")
                        if input_el:
                            current = await input_el.input_value()
                            if not current.strip():
                                await input_el.fill(browser_config.CANDIDATE_PHONE)

                    # Email
                    elif "email" in label_text:
                        input_el = await group.query_selector("input")
                        if input_el:
                            current = await input_el.input_value()
                            if not current.strip():
                                await input_el.fill(browser_config.CANDIDATE_EMAIL)

                    # Name fields
                    elif "first name" in label_text:
                        input_el = await group.query_selector("input")
                        if input_el:
                            current = await input_el.input_value()
                            if not current.strip():
                                await input_el.fill("Rahul")

                    elif "last name" in label_text:
                        input_el = await group.query_selector("input")
                        if input_el:
                            current = await input_el.input_value()
                            if not current.strip():
                                await input_el.fill("Girase")

                    # Experience years
                    elif any(kw in label_text for kw in ["years of experience", "experience", "work experience"]):
                        input_el = await group.query_selector("input")
                        if input_el:
                            current = await input_el.input_value()
                            if not current.strip():
                                await input_el.fill(str(int(browser_config.CANDIDATE_EXPERIENCE_YEARS)))

                    # Notice period
                    elif "notice period" in label_text:
                        input_el = await group.query_selector("input")
                        if input_el:
                            await input_el.fill(browser_config.CANDIDATE_NOTICE_PERIOD)

                    # Yes/No questions
                    elif any(kw in label_text for kw in [
                        "legally authorized", "work authorization", "authorized to work", "right to work"
                    ]):
                        select_el = await group.query_selector("select")
                        if select_el:
                            await select_el.select_option(label="Yes")
                        else:
                            yes_radio = await group.query_selector('input[value="Yes"], label:has-text("Yes")')
                            if yes_radio:
                                await yes_radio.click()

                    elif "visa" in label_text or "sponsorship" in label_text:
                        select_el = await group.query_selector("select")
                        if select_el:
                            await select_el.select_option(label="No")

                    elif "willing to relocate" in label_text:
                        select_el = await group.query_selector("select")
                        if select_el:
                            await select_el.select_option(label="Yes")

                except Exception as e:
                    logger.debug(f"  Form field error: {e}")
                    continue

        except Exception as e:
            logger.debug(f"  _fill_current_step general error: {e}")

    async def _wait_for_user_action(self, page, timeout: int = 120, job_info: Optional[Dict] = None) -> bool:
        """
        Wait for the user to either submit the application or close the dialog.
        If AUTO_SUBMIT is True, automatically clicks Submit.
        Returns True if submitted, False if skipped/closed.
        """
        if browser_config.AUTO_SUBMIT:
            logger.info("  [Auto-Submit] Submitting application automatically...")
            submit_btn = await page.query_selector(
                'button[aria-label*="Submit application"], '
                'button:has-text("Submit application"), '
                'button:has-text("Submit")'
            )
            if submit_btn:
                await self.helper.human_delay(1.5, 2.5)
                await submit_btn.click()
                await self.helper.human_delay(2.0, 3.5)
                return True

        # Ensure browser is restored and front-and-center
        self.helper.bring_to_foreground()

        start = time.time()
        poll_count = 0
        while time.time() - start < timeout:
            poll_count += 1
            elapsed = int(time.time() - start)
            remaining = max(0, timeout - elapsed)

            # Every 4 seconds, keep browser in front, update countdown, and capture frame
            if poll_count % 2 == 0:
                self.helper.bring_to_foreground()
                title = job_info.get("title", "Job") if job_info else "Job"
                self.helper.update_live_status(
                    f"Awaiting review in Chromium: '{title}' ({remaining}s remaining)",
                    {"waiting_for_user": True, "remaining_seconds": remaining}
                )
                try:
                    await self.helper.screenshot("review_countdown")
                except Exception:
                    pass

            await asyncio.sleep(2)

            # Check if submit dialog is still open
            dialog_open = await page.query_selector(
                '.jobs-easy-apply-modal, '
                '.artdeco-modal--layer-default, '
                '[role="dialog"]'
            )

            if not dialog_open:
                # Dialog closed — check if there's a success message
                success = await page.query_selector(
                    '.artdeco-inline-feedback--success, '
                    ':text("Application submitted"), '
                    ':text("applied")'
                )
                return success is not None

            # Check if we moved to a "Application submitted" state
            submitted_el = await page.query_selector(
                ':text("Application submitted"), '
                ':text("Your application was sent"), '
                '.jobs-post-apply-modal'
            )
            if submitted_el:
                return True

        logger.info("[LinkedIn] User action timeout — skipping this job.")
        await self._close_apply_dialog(page)
        return False

    async def _close_apply_dialog(self, page):
        """Close any open Easy Apply dialog."""
        try:
            dismiss = await page.query_selector(
                'button[aria-label="Dismiss"], '
                'button[aria-label="Close"], '
                '.artdeco-modal__dismiss'
            )
            if dismiss:
                await dismiss.click()
                await asyncio.sleep(1)

            # Handle "Discard application?" confirmation
            discard_btn = await page.query_selector(
                'button:has-text("Discard"), button[data-control-name="discard_application_confirm_btn"]'
            )
            if discard_btn:
                await discard_btn.click()
                await asyncio.sleep(0.5)
        except Exception:
            pass

    async def _go_to_next_page(self, page) -> bool:
        """Navigate to the next page of search results."""
        try:
            next_btn = await page.query_selector(
                'button[aria-label="Next"], '
                'li.artdeco-pagination__indicator--number.active + li button'
            )
            if next_btn:
                await next_btn.click()
                await self.helper.human_delay(3.0, 5.0)
                return True
        except Exception:
            pass
        return False


async def run_linkedin_agent() -> Dict:
    """Convenience function to run the LinkedIn agent."""
    agent = LinkedInAgent()
    try:
        return await agent.start()
    except Exception as e:
        logger.error(f"[LinkedIn] Agent failed: {e}")
        return {"platform": "LinkedIn", "error": str(e)}
