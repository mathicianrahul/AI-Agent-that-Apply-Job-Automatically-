from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import html
import os
from pathlib import Path
import smtplib
from typing import Any, Dict, List, Optional

from jobpilot.config import BASE_DIR, settings
from jobpilot.db.repository import repository
from jobpilot.logger import logger
from jobpilot.models.schemas import ApplicationStatus, Job, MatchResult, PlatformSourceStatus
from jobpilot.utils.date_utils import utc_now_iso


class EmailDigestService:
    """
    Constructs and dispatches the daily job discovery email digest.
    Recipient default: rgirase312@gmail.com
    Contains:
    - Newly discovered jobs & their source platform
    - Company, title, and posting date
    - Match score & transparent reasons
    - Original application URLs & all alternate platform links
    - Pending application drafts awaiting candidate review
    - Source status & platform failure/restriction notices
    """

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or (BASE_DIR / "data" / "email_digests")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_digest_data(self) -> Dict[str, Any]:
        """Collects latest jobs, matches, drafts, and source alerts from repository."""
        # 1. Fetch top discovered jobs
        jobs = repository.list_jobs(limit=15)

        # 2. Match scores for these jobs
        job_cards = []
        for j in jobs:
            match = repository.get_match_result(j.id)
            score = match.overall_score if match else 0.0
            reasons = match.eligibility_reasons if match else []
            job_cards.append({
                "job": j,
                "match": match,
                "score": score,
                "reasons": reasons,
            })

        # Sort descending by score
        job_cards.sort(key=lambda x: x["score"], reverse=True)

        # 3. Pending drafts
        pending_apps = repository.list_applications_by_status(ApplicationStatus.PENDING_REVIEW)

        # 4. Platform statuses & failures
        from jobpilot.sources import JobDiscoveryService
        discovery = JobDiscoveryService()
        platform_statuses = discovery.get_platform_statuses()
        failures = [p for p in platform_statuses if p.connection_status in ["Error", "Restricted / Manual Only"]]

        return {
            "timestamp": utc_now_iso(),
            "jobs_data": job_cards[:10],
            "pending_drafts_count": len(pending_apps),
            "pending_drafts": pending_apps[:5],
            "platform_failures": failures,
            "all_platforms": platform_statuses,
        }

    def render_html_digest(self, data: Dict[str, Any]) -> str:
        """Renders a responsive, modern HTML email digest."""
        jobs_html = ""
        for item in data["jobs_data"]:
            j: Job = item["job"]
            score = item["score"]
            score_color = "#10B981" if score >= 70 else ("#F59E0B" if score >= 50 else "#EF4444")

            # Alternate source links
            links = []
            if j.url:
                links.append(f'<a href="{html.escape(j.url)}" style="color:#3B82F6;text-decoration:none;font-weight:600;" target="_blank">Apply on {html.escape(j.source_name)}</a>')
            for alt_name, alt_url in j.alternate_source_urls.items():
                if alt_url != j.url:
                    links.append(f'<a href="{html.escape(alt_url)}" style="color:#9CA3AF;text-decoration:none;font-size:12px;" target="_blank">via {html.escape(alt_name)}</a>')
            links_str = " &nbsp;|&nbsp; ".join(links)

            reasons_html = ""
            if item["reasons"]:
                reasons_html = f"<div style='font-size:12px;color:#6B7280;margin-top:4px;'>Eligibility: {', '.join(html.escape(r) for r in item['reasons'])}</div>"

            skills_str = ", ".join(j.required_skills[:6]) if j.required_skills else "Python, ML"

            jobs_html += f"""
            <div style="background:#1E293B;border-radius:8px;padding:16px;margin-bottom:12px;border:1px solid #334155;">
                <table width="100%" cellpadding="0" cellspacing="0" border="0">
                    <tr>
                        <td>
                            <div style="font-size:16px;font-weight:700;color:#F8FAFC;">{html.escape(j.title)}</div>
                            <div style="font-size:13px;color:#94A3B8;margin-top:3px;">
                                🏢 <b>{html.escape(j.company)}</b> &nbsp;•&nbsp; 📍 {html.escape(j.location)} ({html.escape(j.workplace_type)}) &nbsp;•&nbsp; 📅 {html.escape(str(j.posted_date or 'Recent'))}
                            </div>
                            <div style="font-size:12px;color:#CBD5E1;margin-top:6px;">
                                <b>Key Skills:</b> {html.escape(skills_str)}
                            </div>
                            {reasons_html}
                            <div style="margin-top:10px;">{links_str}</div>
                        </td>
                        <td align="right" valign="top" style="width:80px;">
                            <div style="background:{score_color}22;border:1px solid {score_color};color:{score_color};font-weight:800;font-size:18px;border-radius:6px;padding:6px 10px;text-align:center;">
                                {score:.0f}%
                                <div style="font-size:10px;font-weight:600;text-transform:uppercase;color:#94A3B8;">Match</div>
                            </div>
                        </td>
                    </tr>
                </table>
            </div>
            """

        if not jobs_html:
            jobs_html = "<p style='color:#94A3B8;'>No new jobs discovered today.</p>"

        # Failures HTML
        failures_html = ""
        for f in data["platform_failures"]:
            failures_html += f"""
            <li style="margin-bottom:6px;color:#FCA5A5;">
                <b>{html.escape(f.name)}:</b> {html.escape(f.errors_or_warnings or 'Notice')} (Method: {html.escape(f.permitted_method)})
            </li>
            """

        date_str = data["timestamp"][:10]
        recipient = settings.DIGEST_RECIPIENT_EMAIL

        html_template = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>JobPilot AI Daily Digest</title>
        </head>
        <body style="margin:0;padding:20px;background:#0F172A;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:#F8FAFC;">
            <div style="max-width:680px;margin:0 auto;background:#0B0F19;border-radius:12px;padding:24px;border:1px solid #1E293B;">
                <!-- Header -->
                <div style="border-bottom:1px solid #1E293B;padding-bottom:16px;margin-bottom:20px;">
                    <table width="100%">
                        <tr>
                            <td>
                                <div style="font-size:22px;font-weight:800;color:#FFFFFF;letter-spacing:-0.5px;">
                                    🚀 JobPilot <span style="color:#60A5FA;">AI</span> Daily Digest
                                </div>
                                <div style="font-size:13px;color:#94A3B8;margin-top:4px;">
                                    Prepared for Rahul Girase ({html.escape(recipient)}) • Batch of 2027
                                </div>
                            </td>
                            <td align="right">
                                <div style="font-size:12px;background:#1E293B;color:#60A5FA;padding:6px 12px;border-radius:20px;font-weight:600;display:inline-block;">
                                    {html.escape(date_str)}
                                </div>
                            </td>
                        </tr>
                    </table>
                </div>

                <!-- Stats summary -->
                <div style="display:flex;gap:12px;margin-bottom:24px;">
                    <table width="100%" cellpadding="6" cellspacing="0" style="background:#161F30;border-radius:8px;padding:12px;border:1px solid #1E293B;">
                        <tr>
                            <td align="center" style="border-right:1px solid #334155;">
                                <div style="font-size:20px;font-weight:700;color:#60A5FA;">{len(data['jobs_data'])}</div>
                                <div style="font-size:11px;color:#94A3B8;text-transform:uppercase;">Discovered Today</div>
                            </td>
                            <td align="center" style="border-right:1px solid #334155;">
                                <div style="font-size:20px;font-weight:700;color:#10B981;">{data['pending_drafts_count']}</div>
                                <div style="font-size:11px;color:#94A3B8;text-transform:uppercase;">Pending Drafts</div>
                            </td>
                            <td align="center">
                                <div style="font-size:20px;font-weight:700;color:#F59E0B;">{len(data['platform_failures'])}</div>
                                <div style="font-size:11px;color:#94A3B8;text-transform:uppercase;">Source Notices</div>
                            </td>
                        </tr>
                    </table>
                </div>

                <!-- Job Listings -->
                <div style="margin-bottom:24px;">
                    <div style="font-size:15px;font-weight:700;color:#F1F5F9;margin-bottom:12px;text-transform:uppercase;letter-spacing:0.5px;">
                        Top Matching Opportunities
                    </div>
                    {jobs_html}
                </div>

                <!-- Platform Notices -->
                <div style="background:#1E1B2E;border:1px solid #4C1D95;border-radius:8px;padding:16px;margin-bottom:20px;">
                    <div style="font-size:13px;font-weight:700;color:#C4B5FD;margin-bottom:8px;">
                        🛡️ Multi-Platform Source Status & Compliance Notes
                    </div>
                    <ul style="margin:0;padding-left:20px;font-size:12px;color:#CBD5E1;">
                        {failures_html or "<li style='color:#34D399;'>All primary source adapters operating as configured.</li>"}
                    </ul>
                </div>

                <!-- Footer -->
                <div style="border-top:1px solid #1E293B;padding-top:16px;text-align:center;font-size:12px;color:#64748B;">
                    JobPilot AI • Personal AI Job Application Agent • Human Approval Enforced
                </div>
            </div>
        </body>
        </html>
        """
        return html_template

    def render_text_digest(self, data: Dict[str, Any]) -> str:
        """Renders a clean plain-text digest fallback."""
        lines = [
            f"=== JOBPILOT AI DAILY DIGEST ({data['timestamp'][:10]}) ===",
            f"Prepared for: Rahul Girase ({settings.DIGEST_RECIPIENT_EMAIL})",
            f"Pending Application Drafts: {data['pending_drafts_count']}",
            "",
            "TOP MATCHING OPPORTUNITIES:",
        ]
        for item in data["jobs_data"]:
            j: Job = item["job"]
            score = item["score"]
            lines.append(f"- {j.title} at {j.company} (Score: {score:.0f}%)")
            lines.append(f"  Location: {j.location} | Source: {j.source_name}")
            lines.append(f"  Link: {j.url}")
            for alt_name, alt_url in j.alternate_source_urls.items():
                if alt_url != j.url:
                    lines.append(f"  Alternate ({alt_name}): {alt_url}")
            lines.append("")

        lines.append("PLATFORM COMPLIANCE & STATUS NOTICES:")
        for f in data["platform_failures"]:
            lines.append(f"- {f.name}: {f.errors_or_warnings} [{f.permitted_method}]")

        lines.append("\nNote: Human approval is required prior to all external application submissions.")
        return "\n".join(lines)

    def dispatch_digest(self) -> Dict[str, Any]:
        """
        Gathers data, generates HTML & text digests, saves to disk,
        and sends via SMTP if credentials are configured.
        """
        data = self.generate_digest_data()
        html_content = self.render_html_digest(data)
        text_content = self.render_text_digest(data)
        recipient = settings.DIGEST_RECIPIENT_EMAIL
        subject = f"🚀 JobPilot AI Daily Digest ({data['timestamp'][:10]}) — {len(data['jobs_data'])} New Opportunities"

        # 1. Always save digest locally to ensure persistence and UI inspection
        date_tag = data["timestamp"][:10].replace("-", "")
        digest_file = self.output_dir / f"digest_{date_tag}.html"
        latest_file = self.output_dir / "latest_digest.html"

        digest_file.write_text(html_content, encoding="utf-8")
        latest_file.write_text(html_content, encoding="utf-8")
        logger.info(f"Saved daily email digest to {digest_file}")

        # 2. Record notification in database
        repository.record_notification(
            title=f"Daily Digest Generated ({date_tag})",
            message=f"Prepared digest for {recipient} with {len(data['jobs_data'])} jobs and {data['pending_drafts_count']} drafts.",
            category="digest",
        )

        # 3. Attempt SMTP delivery if configured
        smtp_success = False
        smtp_msg = ""

        if settings.SMTP_HOST and settings.SMTP_USER and settings.SMTP_PASSWORD:
            try:
                logger.info(f"Attempting to send email digest to {recipient} via {settings.SMTP_HOST}...")
                msg = MIMEMultipart("alternative")
                msg["Subject"] = subject
                msg["From"] = settings.SMTP_FROM
                msg["To"] = recipient

                msg.attach(MIMEText(text_content, "plain"))
                msg.attach(MIMEText(html_content, "html"))

                if settings.SMTP_USE_TLS:
                    server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15)
                    server.starttls()
                clean_pw = (settings.SMTP_PASSWORD or "").replace(" ", "")
                server.login(settings.SMTP_USER, clean_pw)
                server.sendmail(settings.SMTP_FROM, [recipient], msg.as_string())
                server.quit()

                smtp_success = True
                smtp_msg = f"Dispatched successfully to {recipient} via SMTP"
                logger.info(smtp_msg)

            except Exception as e:
                smtp_msg = f"SMTP dispatch failed: {str(e)}. Digest preserved locally."
                logger.warning(smtp_msg)
        else:
            smtp_msg = f"SMTP credentials not configured. Digest saved locally at {digest_file}."
            logger.info(smtp_msg)

        # Log audit trail
        repository.log_audit(
            action="daily_email_digest_dispatched",
            entity_type="email_digest",
            entity_id=date_tag,
            details={
                "recipient": recipient,
                "jobs_count": len(data["jobs_data"]),
                "smtp_sent": smtp_success,
                "status_message": smtp_msg,
                "file_path": str(digest_file),
            },
        )

        return {
            "success": True,
            "recipient": recipient,
            "jobs_count": len(data["jobs_data"]),
            "smtp_sent": smtp_success,
            "message": smtp_msg,
            "file_path": str(digest_file),
            "html_content": html_content,
        }

    def get_latest_digest_html(self) -> Optional[str]:
        latest_file = self.output_dir / "latest_digest.html"
        if latest_file.exists():
            return latest_file.read_text(encoding="utf-8")
        return None


email_digest_service = EmailDigestService()
