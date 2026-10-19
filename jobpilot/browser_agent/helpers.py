"""
Base Browser Helper — common utilities for browser automation across all platforms.
Provides human-like delays, smart element interactions, and session management.
"""

import asyncio
import json
import random
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    async_playwright,
    TimeoutError as PlaywrightTimeout,
)

from jobpilot.logger import logger
from jobpilot.browser_agent.config import browser_config


class BrowserHelper:
    """
    Manages Playwright browser lifecycle with human-like interaction patterns.
    Supports persistent login sessions so user only logs in once.
    """

    def __init__(self, platform: str = "generic"):
        self.platform = platform
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self._applied_count = 0

    async def launch(self) -> Page:
        """Launch browser with persistent context for session reuse."""
        self.playwright = await async_playwright().start()

        state_dir = browser_config.browser_state_path / self.platform
        state_dir.mkdir(parents=True, exist_ok=True)

        # Clear any stale lock files from previous runs
        for lock_name in ["lockfile", "SingletonLock"]:
            lock_file = state_dir / lock_name
            if lock_file.exists():
                try:
                    lock_file.unlink(missing_ok=True)
                except Exception:
                    pass

        launch_kwargs = dict(
            user_data_dir=str(state_dir),
            headless=browser_config.BROWSER_HEADLESS,
            slow_mo=browser_config.BROWSER_SLOW_MO,
            viewport=None,
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            ),
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--start-maximized",
            ],
            ignore_default_args=["--enable-automation"],
        )

        try:
            self.context = await self.playwright.chromium.launch_persistent_context(**launch_kwargs)
        except Exception as e:
            if "existing browser session" in str(e).lower():
                logger.warning(f"[{self.platform}] Stale Chromium lock detected. Auto-recovering...")
                if sys.platform == "win32":
                    try:
                        subprocess.run(
                            ["powershell", "-Command", 'Get-Process | Where-Object { $_.Path -like "*ms-playwright*" } | Stop-Process -Force'],
                            capture_output=True,
                            timeout=5
                        )
                    except Exception:
                        pass
                for lock_name in ["lockfile", "SingletonLock"]:
                    try:
                        (state_dir / lock_name).unlink(missing_ok=True)
                    except Exception:
                        pass
                await asyncio.sleep(1)
                self.context = await self.playwright.chromium.launch_persistent_context(**launch_kwargs)
            else:
                raise

        # Get or create the first page
        if self.context.pages:
            self.page = self.context.pages[0]
        else:
            self.page = await self.context.new_page()

        await self.page.bring_to_front()
        self.bring_to_foreground()
        self.page.set_default_timeout(browser_config.BROWSER_TIMEOUT)
        logger.info(f"[{self.platform}] Browser launched with persistent session.")
        return self.page

    def bring_to_foreground(self):
        """Force the browser window to the foreground and unminimize on Windows."""
        if sys.platform != "win32":
            return
        try:
            import ctypes
            from ctypes import wintypes
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32

            matched_hwnds = []

            def enum_proc(hwnd, lParam):
                if user32.IsWindowVisible(hwnd):
                    length = user32.GetWindowTextLengthW(hwnd)
                    if length > 0:
                        buff = ctypes.create_unicode_buffer(length + 1)
                        user32.GetWindowTextW(hwnd, buff, length + 1)
                        title = buff.value.lower()
                        if any(k in title for k in [self.platform.lower(), "chromium", "chrome", "linkedin", "naukri", "indeed"]):
                            matched_hwnds.append(hwnd)
                return True

            WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
            user32.EnumWindows(WNDENUMPROC(enum_proc), 0)

            for hwnd in matched_hwnds:
                user32.ShowWindow(hwnd, 9)  # 9 = SW_RESTORE
                user32.BringWindowToTop(hwnd)
                fore_hwnd = user32.GetForegroundWindow()
                if fore_hwnd != hwnd:
                    fore_thread = user32.GetWindowThreadProcessId(fore_hwnd, None)
                    curr_thread = kernel32.GetCurrentThreadId()
                    user32.AttachThreadInput(fore_thread, curr_thread, True)
                    user32.SetForegroundWindow(hwnd)
                    user32.AttachThreadInput(fore_thread, curr_thread, False)
                else:
                    user32.SetForegroundWindow(hwnd)
        except Exception as e:
            logger.debug(f"[{self.platform}] Could not bring window to foreground: {e}")

    async def close(self):
        """Gracefully close browser and save session state."""
        try:
            if self.context:
                await self.context.close()
            if self.playwright:
                await self.playwright.stop()
            logger.info(f"[{self.platform}] Browser closed. Session saved.")
        except Exception as e:
            logger.warning(f"[{self.platform}] Error closing browser: {e}")

    # ── Human-like Interaction Utilities ──────────────────────────────

    async def human_delay(self, min_s: Optional[float] = None, max_s: Optional[float] = None):
        """Random delay to mimic human behavior."""
        lo = min_s or browser_config.ACTION_DELAY_MIN
        hi = max_s or browser_config.ACTION_DELAY_MAX
        delay = random.uniform(lo, hi)
        await asyncio.sleep(delay)

    async def human_type(self, selector: str, text: str, clear_first: bool = True):
        """Type text with human-like keystroke delays."""
        try:
            el = await self.page.wait_for_selector(selector, state="visible", timeout=10000)
            if clear_first:
                await el.click(click_count=3)
                await self.page.keyboard.press("Backspace")
                await asyncio.sleep(0.3)

            for char in text:
                await el.type(char, delay=random.randint(30, 120))
                if random.random() < 0.05:  # Occasional pause
                    await asyncio.sleep(random.uniform(0.1, 0.4))

        except PlaywrightTimeout:
            logger.warning(f"[{self.platform}] Could not find element: {selector}")
            raise

    async def safe_click(self, selector: str, timeout: int = 10000) -> bool:
        """Click an element safely, return True if successful."""
        try:
            el = await self.page.wait_for_selector(selector, state="visible", timeout=timeout)
            await el.scroll_into_view_if_needed()
            await asyncio.sleep(random.uniform(0.2, 0.6))
            await el.click()
            return True
        except PlaywrightTimeout:
            logger.debug(f"[{self.platform}] Element not found for click: {selector}")
            return False
        except Exception as e:
            logger.debug(f"[{self.platform}] Click failed on {selector}: {e}")
            return False

    async def safe_fill(self, selector: str, value: str, timeout: int = 10000) -> bool:
        """Fill a form field safely."""
        try:
            el = await self.page.wait_for_selector(selector, state="visible", timeout=timeout)
            await el.scroll_into_view_if_needed()
            await el.fill(value)
            return True
        except PlaywrightTimeout:
            return False

    async def safe_select(self, selector: str, value: str, timeout: int = 5000) -> bool:
        """Select a dropdown option safely."""
        try:
            await self.page.select_option(selector, value=value, timeout=timeout)
            return True
        except Exception:
            return False

    async def upload_file(self, selector: str, file_path: str, timeout: int = 10000) -> bool:
        """Upload a file to a file input element."""
        try:
            el = await self.page.wait_for_selector(selector, timeout=timeout)
            await el.set_input_files(file_path)
            logger.info(f"[{self.platform}] Uploaded file: {Path(file_path).name}")
            return True
        except Exception as e:
            logger.warning(f"[{self.platform}] File upload failed: {e}")
            return False

    async def wait_for_navigation(self, timeout: int = 15000):
        """Wait for page navigation to complete."""
        try:
            await self.page.wait_for_load_state("networkidle", timeout=timeout)
        except PlaywrightTimeout:
            await self.page.wait_for_load_state("domcontentloaded", timeout=5000)

    async def scroll_down(self, pixels: int = 500):
        """Scroll down the page by specified pixels."""
        await self.page.evaluate(f"window.scrollBy(0, {pixels})")
        await asyncio.sleep(random.uniform(0.5, 1.0))

    async def get_text(self, selector: str, timeout: int = 5000) -> Optional[str]:
        """Get text content of an element."""
        try:
            el = await self.page.wait_for_selector(selector, timeout=timeout)
            return await el.text_content()
        except PlaywrightTimeout:
            return None

    async def is_visible(self, selector: str, timeout: int = 3000) -> bool:
        """Check if an element is visible on the page."""
        try:
            await self.page.wait_for_selector(selector, state="visible", timeout=timeout)
            return True
        except PlaywrightTimeout:
            return False

    def update_live_status(self, step: Optional[str] = None, details: Optional[Dict] = None):
        """Write current status to live_status.json for real-time UI monitoring."""
        try:
            status_file = browser_config.browser_state_path / "live_status.json"
            data = {}
            if status_file.exists():
                try:
                    with open(status_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                except Exception:
                    pass

            data["platform"] = self.platform
            data["status"] = "running"
            data["applied_count"] = self._applied_count
            data["max_applications"] = browser_config.MAX_APPLICATIONS_PER_SESSION
            data["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
            data["latest_screenshot"] = str(browser_config.browser_state_path / "screenshots" / "latest.png")

            if step is not None:
                data["step"] = step
            if details:
                data.update(details)

            with open(status_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    async def screenshot(self, name: str = "screenshot"):
        """Take a screenshot for debugging and live UI display."""
        ss_dir = browser_config.browser_state_path / "screenshots"
        ss_dir.mkdir(parents=True, exist_ok=True)
        path = ss_dir / f"{self.platform}_{name}_{int(time.time())}.png"
        await self.page.screenshot(path=str(path), full_page=False)

        # Also copy to latest.png for real-time live feed in the dashboard
        latest_path = ss_dir / "latest.png"
        try:
            shutil.copyfile(str(path), str(latest_path))
        except Exception:
            pass

        # Update screenshot metadata without erasing the active step or job details
        self.update_live_status(details={"last_screenshot": name, "screenshot_updated": time.strftime("%H:%M:%S")})
        logger.info(f"[{self.platform}] Screenshot saved: {path.name}")
        return path

    def can_apply_more(self) -> bool:
        """Check if we haven't exceeded the safety cap."""
        return self._applied_count < browser_config.MAX_APPLICATIONS_PER_SESSION

    def increment_applied(self):
        """Increment the applied counter."""
        self._applied_count += 1
        logger.info(
            f"[{self.platform}] Applications this session: "
            f"{self._applied_count}/{browser_config.MAX_APPLICATIONS_PER_SESSION}"
        )
