import json
import os
from pathlib import Path
import streamlit as st
import pandas as pd

from jobpilot.agent.graph import run_job_agent
from jobpilot.config import BASE_DIR, settings
from jobpilot.db.repository import repository
from jobpilot.llm.client import llm_client
from jobpilot.logger import logger
from jobpilot.models.schemas import (
    ApplicationDraft,
    ApplicationStatus,
    CandidateProfile,
    Job,
)
from jobpilot.resume.parser import resume_parser
from jobpilot.scheduler.daily_runner import automation_scheduler
from jobpilot.sources import JobDiscoveryService, MultiPlatformCSVImporter
from jobpilot.sources.custom_importer import CustomJobImporter
from jobpilot.notifications.email_digest import email_digest_service
from jobpilot.tracker.service import tracker_service
from jobpilot.ui.theme import CUSTOM_CSS, render_header


# Configure Page
st.set_page_config(
    page_title="JobPilot AI — Personal AI Job Application Agent",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Inject Dark Theme CSS
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def main():
    # Sidebar Navigation
    with st.sidebar:
        st.markdown(
            """
            <div style="padding: 12px 0 20px 0; border-bottom: 1px solid #1F2937; margin-bottom: 16px;">
                <div style="font-size: 1.35rem; font-weight: 700; color: #FFFFFF; letter-spacing: -0.02em;">
                    🚀 JobPilot <span style="color: #60A5FA;">AI</span>
                </div>
                <div style="font-size: 0.8rem; color: #9CA3AF; margin-top: 4px;">
                    Personal AI Job Application Agent
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        nav_choice = st.radio(
            "Navigation",
            options=[
                "Overview",
                "Discover Jobs",
                "Matched Jobs",
                "Application Review",
                "Application Tracker",
                "🤖 Browser Agent",
                "Resume Manager",
                "Candidate Profile",
                "Automation Settings",
                "Integrations",
                "Activity Logs",
            ],
            label_visibility="collapsed",
        )

        st.markdown("<div style='margin-top: 30px;'></div>", unsafe_allow_html=True)
        # Quick Profile Summary
        candidate = repository.get_candidate_profile()
        st.markdown(
            f"""
            <div style="background: #161F30; border: 1px solid #1F2937; border-radius: 8px; padding: 12px;">
                <div style="font-size: 0.75rem; color: #9CA3AF; text-transform: uppercase; font-weight: 600;">Candidate</div>
                <div style="font-size: 0.95rem; font-weight: 600; color: #FFFFFF; margin-top: 2px;">{candidate.name}</div>
                <div style="font-size: 0.8rem; color: #60A5FA; margin-top: 2px;">Graduating {candidate.graduation_year}</div>
                <div style="font-size: 0.75rem; color: #9CA3AF; margin-top: 4px;">{candidate.experience_level}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Trigger Automation Button in Sidebar
        st.markdown("<div style='margin-top: 16px;'></div>", unsafe_allow_html=True)
        if st.button("⚡ Run Agent Discovery", use_container_width=True, type="primary"):
            with st.spinner("Executing LangGraph agent pipeline..."):
                run_res = automation_scheduler.trigger_run_now()
                st.success(f"Agent finished! {run_res.drafts_created} drafts created.")
                st.rerun()

    # Route Views
    if nav_choice == "Overview":
        render_overview(candidate)
    elif nav_choice == "Discover Jobs":
        render_discover_jobs()
    elif nav_choice == "Matched Jobs":
        render_matched_jobs()
    elif nav_choice == "Application Review":
        render_application_review()
    elif nav_choice == "Application Tracker":
        render_application_tracker()
    elif nav_choice == "🤖 Browser Agent":
        render_browser_agent()
    elif nav_choice == "Resume Manager":
        render_resume_manager()
    elif nav_choice == "Candidate Profile":
        render_candidate_profile()
    elif nav_choice == "Automation Settings":
        render_automation_settings()
    elif nav_choice == "Integrations":
        render_integrations()
    elif nav_choice == "Activity Logs":
        render_activity_logs()


# ==========================================
# 1. OVERVIEW PAGE
# ==========================================
def render_overview(candidate: CandidateProfile):
    st.markdown(
        render_header("Executive Overview", "Real-time metrics, pipeline health, and agent status from SQLite."),
        unsafe_allow_html=True,
    )

    metrics = repository.get_dashboard_metrics()
    latest_run = repository.get_latest_automation_run()

    # Active Browser Agent Banner
    bs_status_file = BASE_DIR / "data" / "browser_state" / "live_status.json"
    if bs_status_file.exists():
        try:
            with open(bs_status_file, "r", encoding="utf-8") as f:
                bs_data = json.load(f)
            if bs_data.get("status") == "running":
                st.info(
                    f"🔴 **Live Browser Agent Active ({bs_data.get('platform', 'Browser').upper()}):** "
                    f"{bs_data.get('step', 'Working...')} — Navigate to **🤖 Browser Agent** in the sidebar to view the live screen and actions!"
                )
        except Exception:
            pass

    # Top KPI Cards
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(
            f"""
            <div class="jobpilot-metric-card">
                <div class="metric-title">Total Jobs Discovered</div>
                <div class="metric-value">{metrics['total_jobs']}</div>
                <div class="metric-sub">Deduplicated in database</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            f"""
            <div class="jobpilot-metric-card">
                <div class="metric-title">Eligible Roles</div>
                <div class="metric-value">{metrics['eligible_jobs']}</div>
                <div class="metric-sub">Meets 2027 / Fresher limits</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            f"""
            <div class="jobpilot-metric-card">
                <div class="metric-title">High Match (≥70%)</div>
                <div class="metric-value">{metrics['high_match_jobs']}</div>
                <div class="metric-sub">Personalized drafts ready</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col4:
        st.markdown(
            f"""
            <div class="jobpilot-metric-card">
                <div class="metric-title">Awaiting Approval</div>
                <div class="metric-value">{metrics['pending_review']}</div>
                <div class="metric-sub">Pending Human Review</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)

    # Secondary Metrics Row
    col_a, col_b, col_c = st.columns([1, 1, 1])
    with col_a:
        st.markdown(
            f"""
            <div class="jobpilot-card">
                <div class="metric-title">Submitted Applications</div>
                <div class="metric-value" style="color: #34D399;">{metrics['submitted']}</div>
                <div style="font-size: 0.85rem; color: #9CA3AF; margin-top: 6px;">Verified external submissions</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col_b:
        st.markdown(
            f"""
            <div class="jobpilot-card">
                <div class="metric-title">Interviews & Assessments</div>
                <div class="metric-value" style="color: #60A5FA;">{metrics['interviews_assessments']}</div>
                <div style="font-size: 0.85rem; color: #9CA3AF; margin-top: 6px;">Active recruitment stages</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col_c:
        last_run_text = latest_run.run_timestamp[:16].replace("T", " ") if latest_run else "No run yet"
        st.markdown(
            f"""
            <div class="jobpilot-card">
                <div class="metric-title">Latest Automation Run</div>
                <div style="font-size: 1.25rem; font-weight: 700; color: #FFFFFF; margin-top: 4px;">{last_run_text}</div>
                <div style="font-size: 0.85rem; color: #9CA3AF; margin-top: 6px;">Status: <span style="color: #34D399;">{latest_run.status if latest_run else 'idle'}</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Charts / Pipeline Breakdown
    st.markdown("<div style='margin-top: 24px;'></div>", unsafe_allow_html=True)
    c1, c2 = st.columns([3, 2])

    with c1:
        st.subheader("Application Pipeline Breakdown")
        pipeline_data = metrics.get("pipeline_counts", {})
        if pipeline_data:
            df_pipe = pd.DataFrame(list(pipeline_data.items()), columns=["Stage", "Count"])
            st.bar_chart(df_pipe.set_index("Stage"))
        else:
            st.info("Pipeline records will appear here as jobs are discovered and reviewed.")

    with c2:
        st.subheader("Match Score Distribution")
        dist_data = metrics.get("score_distribution", {})
        if dist_data:
            df_dist = pd.DataFrame(list(dist_data.items()), columns=["Score Band", "Jobs"])
            st.dataframe(df_dist, hide_index=True, use_container_width=True)
        else:
            st.info("Score distribution will populate after running matching.")

    # Recent Discovered Jobs Preview
    st.markdown("<div style='margin-top: 24px;'></div>", unsafe_allow_html=True)
    st.subheader("Recent Discovered Jobs")
    recent_jobs = repository.list_jobs(limit=5)
    if recent_jobs:
        for j in recent_jobs:
            badge = '<span class="pill-demo">Demo</span>' if j.is_demo else '<span class="pill-live">Live</span>'
            remote_badge = '<span class="pill-skill">Remote</span>' if j.is_remote else '<span class="pill-skill">On-site</span>'
            st.markdown(
                f"""
                <div class="jobpilot-card">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <div>
                            <div style="font-size: 1.1rem; font-weight: 600; color: #FFFFFF;">
                                {j.title} {badge}
                            </div>
                            <div style="color: #9CA3AF; font-size: 0.9rem; margin-top: 2px;">
                                🏢 <b>{j.company}</b> &nbsp;|&nbsp; 📍 {j.location} &nbsp;|&nbsp; {remote_badge}
                            </div>
                        </div>
                        <div style="color: #60A5FA; font-weight: 600; font-size: 0.9rem;">
                            {j.salary_range or 'Competitive'}
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.info("No jobs discovered yet. Click 'Run Agent Discovery' in the sidebar to populate listings.")


# ==========================================
# 2. DISCOVER JOBS PAGE
# ==========================================
def render_discover_jobs():
    st.markdown(
        render_header("Discover Jobs", "Search, filter, and import listings across multi-platform feeds with verified compliance."),
        unsafe_allow_html=True,
    )

    discovery_service = JobDiscoveryService()

    # 1. Platform Connection Diagnostics Banner
    with st.expander("🌐 Multi-Platform Connection Status & Diagnostics", expanded=False):
        statuses = discovery_service.get_platform_statuses()
        status_rows = []
        for s in statuses:
            badge_icon = "🟢 Connected" if s.connection_status == "Connected" else ("🔒 Restricted" if "Restricted" in s.connection_status else "🟡 Action Needed")
            status_rows.append({
                "Platform": s.name,
                "Status": badge_icon,
                "Integration Method": s.permitted_method,
                "Auth Requirements": s.auth_requirements,
                "Last Sync": s.last_successful_fetch[:16].replace("T", " ") if s.last_successful_fetch else "Pending",
                "Jobs Discovered": s.jobs_retrieved,
                "Notes / Restrictions": s.errors_or_warnings or "Operational",
            })
        df_status = pd.DataFrame(status_rows)
        st.dataframe(df_status, hide_index=True, use_container_width=True)
        st.caption("🔒 Platforms marked Restricted adhere to Terms of Service and anti-bot boundaries; ingest via Manual URL, JD, or CSV.")

    t1, t2, t3 = st.tabs(["Browse Listings", "Single URL / JD Ingestion", "Bulk CSV / Spreadsheet Import"])

    with t1:
        # Search & Filter Controls
        f1, f2, f3, f4 = st.columns([3, 2, 1, 1])
        with f1:
            search_query = st.text_input("🔍 Search job title, company, or skills", placeholder="e.g. Machine Learning, Python, Pune")
        with f2:
            source_filter = st.selectbox(
                "Filter Platform",
                options=[
                    "All Sources",
                    "Naukri",
                    "LinkedIn",
                    "Indeed",
                    "Internshala",
                    "Wellfound",
                    "Cutshort",
                    "Foundit",
                    "Company Careers",
                    "Manual Imports",
                    "Demo Mode",
                ],
            )
        with f3:
            remote_only = st.checkbox("Remote Only", value=False)
        with f4:
            workplace_filter = st.selectbox("Workplace", ["All", "Remote", "Hybrid", "On-site"])

        # Map display source to db query
        selected_source = None
        if source_filter == "Company Careers":
            # Will filter in Python or query
            selected_source = None
        elif source_filter == "Manual Imports":
            selected_source = None
        elif source_filter != "All Sources":
            selected_source = source_filter

        jobs = repository.list_jobs(
            keyword=search_query if search_query.strip() else None,
            source=selected_source,
            is_remote=True if remote_only else None,
            limit=100,
        )

        # Apply secondary python filters if necessary
        if source_filter == "Company Careers":
            jobs = [j for j in jobs if any(k in j.source_name.lower() for k in ["greenhouse", "lever", "arbeitnow", "company"])]
        elif source_filter == "Manual Imports":
            jobs = [j for j in jobs if any(k in j.source_name.lower() for k in ["manual", "imported", "csv", "user"])]

        if workplace_filter != "All":
            jobs = [j for j in jobs if j.workplace_type.lower() == workplace_filter.lower()]

        st.caption(f"Showing **{len(jobs)}** active job listings.")

        if not jobs:
            st.warning("No jobs match your search criteria. Try adjusting filters or click 'Run Agent Discovery'.")

        for job in jobs:
            with st.container():
                source_badge = '<span class="pill-demo">Demo</span>' if job.is_demo else f'<span class="pill-live">{job.source_name}</span>'
                workplace_pill = f'<span class="pill-skill">{job.workplace_type}</span>'
                skills_html = "".join([f'<span class="pill-skill">{s}</span>' for s in job.required_skills[:6]])

                st.markdown(
                    f"""
                    <div class="jobpilot-card">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                            <div>
                                <h3 style="margin: 0; font-size: 1.15rem; color: #FFFFFF;">
                                    {job.title} {source_badge}
                                </h3>
                                <div style="color: #9CA3AF; font-size: 0.9rem; margin-top: 4px;">
                                    <b>{job.company}</b> &nbsp;•&nbsp; 📍 {job.location} &nbsp;•&nbsp; {workplace_pill} &nbsp;•&nbsp; Posted: {job.posted_date or 'Recent'}
                                </div>
                                <div style="margin-top: 8px;">
                                    {skills_html}
                                </div>
                            </div>
                            <div style="text-align: right;">
                                <div style="color: #34D399; font-weight: 600; font-size: 0.95rem;">{job.salary_range or 'Competitive'}</div>
                                <div style="color: #6B7280; font-size: 0.8rem; margin-top: 4px;">Exp: {job.min_experience_years:g}-{job.max_experience_years:g} yrs</div>
                            </div>
                        </div>
                        <div style="margin-top: 12px; font-size: 0.88rem; color: #D1D5DB; line-height: 1.5;">
                            {job.description[:280]}...
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                # Application links row (Primary + All Alternates)
                col_btn_primary, col_btn_alts = st.columns([1, 3])
                with col_btn_primary:
                    if job.url and job.url.startswith("http"):
                        st.link_button(f"🔗 Apply on {job.source_name}", job.url, use_container_width=True)

                with col_btn_alts:
                    # Render alternate source buttons if present
                    if job.alternate_source_urls:
                        alt_links = [
                            (s_name, s_url)
                            for s_name, s_url in job.alternate_source_urls.items()
                            if s_url != job.url and s_url.startswith("http")
                        ]
                        if alt_links:
                            c_sub_cols = st.columns(len(alt_links))
                            for idx, (alt_name, alt_url) in enumerate(alt_links):
                                with c_sub_cols[idx]:
                                    st.link_button(f"🌐 Also on {alt_name}", alt_url, use_container_width=True)

    with t2:
        st.subheader("Ingest Single Job URL or Pasted Description")
        st.write("Found an opening on Naukri, LinkedIn, Indeed, Internshala, Wellfound, or a company site? Ingest it here.")

        with st.form("manual_job_form"):
            col_m1, col_m2 = st.columns(2)
            with col_m1:
                m_title = st.text_input("Job Title*", placeholder="e.g. Junior AI/ML Engineer")
                m_company = st.text_input("Company Name*", placeholder="e.g. Tata Consultancy Services / Google")
                m_source = st.selectbox(
                    "Source Platform*",
                    ["Naukri", "LinkedIn", "Indeed", "Internshala", "Wellfound", "Cutshort", "Foundit", "Company Career Website", "Other"],
                )
            with col_m2:
                m_loc = st.text_input("Location*", value="Pune / Remote")
                m_remote = st.checkbox("Remote Opportunity", value=True)
                m_url = st.text_input("Application URL", placeholder="https://www.naukri.com/job-listings-... or https://linkedin.com/jobs/view/...")
                m_salary = st.text_input("Salary / Stipend", placeholder="e.g. ₹6,50,000 PA")

            m_desc = st.text_area("Job Description*", height=180, placeholder="Paste the job description or internship requirements here...")

            submitted = st.form_submit_button("Ingest, Normalize & Analyze Job", type="primary")
            if submitted:
                if not m_title.strip() or not m_company.strip() or not m_desc.strip():
                    st.error("Title, Company, and Description are required.")
                else:
                    new_job = CustomJobImporter.create_from_manual_input(
                        title=m_title,
                        company=m_company,
                        description=m_desc,
                        location=m_loc,
                        is_remote=m_remote,
                        url=m_url,
                        salary_range=m_salary,
                        source_name=m_source,
                    )
                    repository.upsert_job(new_job)

                    # Immediately score
                    candidate = repository.get_candidate_profile()
                    from jobpilot.matcher.scoring import MatchScorer
                    scorer = MatchScorer()
                    match_res = scorer.score_job(candidate, new_job)
                    repository.upsert_match_result(match_res)

                    st.success(f"✓ Job successfully ingested from {m_source}! Match Score: {match_res.overall_score:.0f}%")
                    st.rerun()

    with t3:
        st.subheader("Bulk CSV / Spreadsheet Importer")
        st.write(
            "Import exported listings from Naukri, LinkedIn, Indeed, Internshala, or any spreadsheet. "
            "Columns for title, company, location, URL, and description are auto-detected."
        )

        default_csv_platform = st.selectbox(
            "Default Source Label",
            ["Naukri", "LinkedIn", "Indeed", "Internshala", "Wellfound", "Cutshort", "Foundit", "Spreadsheet Import"],
        )

        csv_file = st.file_uploader("Upload CSV or TSV File", type=["csv", "tsv", "txt"])

        if csv_file:
            content_str = csv_file.read().decode("utf-8", errors="replace")
            parsed_jobs, failed_rows, warnings = MultiPlatformCSVImporter.import_from_csv(
                content_str,
                default_source=default_csv_platform,
            )

            st.write(f"Parsed **{len(parsed_jobs)}** valid job listings ({failed_rows} skipped / incomplete rows).")

            if warnings:
                for w in warnings:
                    st.warning(w)

            if parsed_jobs:
                preview_data = [
                    {
                        "Title": pj.title,
                        "Company": pj.company,
                        "Location": pj.location,
                        "Remote": pj.is_remote,
                        "Skills": ", ".join(pj.required_skills[:4]),
                        "URL": pj.url[:40] + "..." if len(pj.url) > 40 else pj.url,
                    }
                    for pj in parsed_jobs[:8]
                ]
                st.dataframe(pd.DataFrame(preview_data), use_container_width=True)

                if st.button("🚀 Import, Deduplicate & Score All Listings", type="primary"):
                    with st.spinner("Saving listings and computing candidate match scores..."):
                        candidate = repository.get_candidate_profile()
                        from jobpilot.matcher.scoring import MatchScorer
                        scorer = MatchScorer()

                        saved_count = 0
                        for job in parsed_jobs:
                            repository.upsert_job(job)
                            match = scorer.score_job(candidate, job)
                            repository.upsert_match_result(match)
                            saved_count += 1

                        st.success(f"Successfully imported and scored {saved_count} job listings!")
                        st.rerun()


# ==========================================
# 3. MATCHED JOBS PAGE
# ==========================================
def render_matched_jobs():
    st.markdown(
        render_header("AI Matched Jobs", "Transparent multi-factor scores, skill overlap, and hard eligibility evaluations."),
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns([2, 1])
    with c1:
        min_threshold = st.slider("Minimum Match Score (%)", min_value=0, max_value=100, value=50, step=5)
    with c2:
        only_eligible = st.checkbox("Only Show Eligible Roles", value=True)

    matched_pairs = repository.list_matched_jobs(min_score=float(min_threshold), only_eligible=only_eligible, limit=50)

    if not matched_pairs:
        st.info("No matched jobs found meeting this threshold. Try lowering the threshold or run discovery.")
        return

    st.write(f"Displaying **{len(matched_pairs)}** ranked jobs.")

    for job, match in matched_pairs:
        with st.container():
            score_color = "#34D399" if match.overall_score >= 70 else ("#FBBF24" if match.overall_score >= 50 else "#F87171")
            elig_badge = '<span class="pill-eligible">✓ Eligible</span>' if match.is_eligible else '<span class="pill-ineligible">✕ Ineligible</span>'

            matched_skills_html = "".join([f'<span class="pill-skill">✓ {s}</span>' for s in match.matched_skills]) or '<span style="color:#6B7280; font-size:0.8rem;">None detected</span>'
            missing_skills_html = "".join([f'<span class="pill-missing">✕ {s}</span>' for s in match.missing_skills]) or '<span style="color:#6B7280; font-size:0.8rem;">None</span>'

            st.markdown(
                f"""
                <div class="jobpilot-card">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <div style="flex: 1;">
                            <div style="display: flex; align-items: center; gap: 8px;">
                                <h3 style="margin: 0; font-size: 1.2rem; color: #FFFFFF;">{job.title}</h3>
                                {elig_badge}
                            </div>
                            <div style="color: #9CA3AF; font-size: 0.9rem; margin-top: 4px;">
                                🏢 <b>{job.company}</b> &nbsp;•&nbsp; 📍 {job.location} &nbsp;•&nbsp; Exp: {job.min_experience_years:g}-{job.max_experience_years:g} yrs
                            </div>
                        </div>
                        <div style="text-align: right; min-width: 100px;">
                            <div style="font-size: 1.75rem; font-weight: 700; color: {score_color};">{match.overall_score:.0f}%</div>
                            <div style="font-size: 0.75rem; color: #9CA3AF; text-transform: uppercase;">Match Score</div>
                        </div>
                    </div>

                    <!-- Breakdown Bar -->
                    <div style="display: flex; gap: 16px; margin-top: 14px; padding: 10px 14px; background: #0B0F19; border-radius: 6px; font-size: 0.8rem; color: #9CA3AF;">
                        <div>Skills: <b style="color: #FFFFFF;">{match.skill_score:.0f}%</b></div>
                        <div>Role Fit: <b style="color: #FFFFFF;">{match.role_score:.0f}%</b></div>
                        <div>Eligibility: <b style="color: #FFFFFF;">{match.eligibility_score:.0f}%</b></div>
                        <div>Location: <b style="color: #FFFFFF;">{match.location_score:.0f}%</b></div>
                        <div>Freshness: <b style="color: #FFFFFF;">{match.freshness_score:.0f}%</b></div>
                    </div>

                    <div style="margin-top: 12px;">
                        <div style="font-size: 0.8rem; color: #9CA3AF; font-weight: 600; margin-bottom: 4px;">MATCHED SKILLS:</div>
                        <div>{matched_skills_html}</div>
                    </div>

                    <div style="margin-top: 8px;">
                        <div style="font-size: 0.8rem; color: #9CA3AF; font-weight: 600; margin-bottom: 4px;">MISSING SKILLS:</div>
                        <div>{missing_skills_html}</div>
                    </div>

                    <div style="margin-top: 12px; font-size: 0.85rem; color: #D1D5DB; background: #161F30; padding: 8px 12px; border-radius: 6px;">
                        💡 <i>{match.explanation}</i>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )


# ==========================================
# 4. APPLICATION REVIEW PAGE
# ==========================================
def render_application_review():
    st.markdown(
        render_header("Application Review", "Human-in-the-loop review. Inspect drafts, edit answers, and approve before submission."),
        unsafe_allow_html=True,
    )

    # Query applications pending review
    pending_items = repository.list_applications_by_status(ApplicationStatus.PENDING_REVIEW)

    if not pending_items:
        st.success("🎉 You're all caught up! No applications currently awaiting review.")
        st.info("Run discovery from the sidebar to find high-match roles and generate new drafts.")
        return

    st.write(f"You have **{len(pending_items)}** application package(s) awaiting your decision.")

    for job, app, match, draft in pending_items:
        with st.expander(f"📋 {job.title} at {job.company} — Match: {match.overall_score if match else 'N/A'}%", expanded=True):
            st.markdown(
                f"""
                <div style="background: #161F30; padding: 12px 16px; border-radius: 8px; margin-bottom: 16px;">
                    <div style="display: flex; justify-content: space-between;">
                        <div>
                            <span style="font-size: 1.1rem; font-weight: 600; color: #FFFFFF;">{job.title}</span> &nbsp;
                            <span style="color: #9CA3AF;">at {job.company}</span>
                        </div>
                        <div style="color: #34D399; font-weight: 600;">{job.salary_range or 'Competitive'}</div>
                    </div>
                    <div style="font-size: 0.85rem; color: #9CA3AF; margin-top: 4px;">
                        📍 {job.location} &nbsp;•&nbsp; Source: {job.source_name} &nbsp;•&nbsp; Exp: {job.min_experience_years:g}-{job.max_experience_years:g} yrs
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Details Tabs
            tab_draft, tab_desc, tab_qa = st.tabs(["Cover Letter Draft", "Job Description", "Tailored Q&A Answers"])

            with tab_desc:
                st.write(job.description)
                if job.url and job.url.startswith("http"):
                    st.link_button("🌐 Open Original Job Posting", job.url)

            with tab_draft:
                current_cl = draft.cover_letter if draft else "No draft generated yet."
                edited_cl = st.text_area("Cover Letter (Editable)", value=current_cl, height=240, key=f"cl_{job.id}")

            with tab_qa:
                answers = draft.answers if draft else {}
                edited_answers = {}
                for q, a in answers.items():
                    edited_answers[q] = st.text_area(f"Q: {q}", value=a, height=90, key=f"qa_{job.id}_{q[:15]}")

            # Save draft edits button
            if st.button("💾 Save Draft Changes", key=f"save_draft_{job.id}"):
                tracker_service.update_draft_content(job.id, edited_cl, edited_answers)
                st.success("Draft edits saved!")
                st.rerun()

            st.markdown("<hr style='border-color: #1F2937;'>", unsafe_allow_html=True)

            # Decision Action Buttons
            col_a1, col_a2, col_a3, col_a4 = st.columns([2, 2, 2, 3])

            with col_a1:
                if st.button("✅ Approve", key=f"appr_{job.id}", type="primary", use_container_width=True):
                    tracker_service.approve_application(job.id)
                    st.success("Application approved! Moved to Tracker.")
                    st.rerun()

            with col_a2:
                if st.button("❌ Reject", key=f"rej_{job.id}", use_container_width=True):
                    tracker_service.reject_application(job.id, reason="User rejected draft.")
                    st.warning("Job rejected.")
                    st.rerun()

            with col_a3:
                if st.button("⏳ Save for Later", key=f"later_{job.id}", use_container_width=True):
                    tracker_service.save_for_later(job.id)
                    st.info("Saved for later.")

            with col_a4:
                # Submission Confirmation Flow
                with st.popover("🚀 Record Submission"):
                    st.write("**Verify Submission Details**")
                    st.caption("Human confirmation required. Never submit without explicit user consent.")
                    sub_channel = st.selectbox("Submission Channel", ["Company Career Site", "LinkedIn", "Email", "Other"], key=f"chan_{job.id}")
                    conf_id = st.text_input("Confirmation ID / Ref No.", key=f"conf_{job.id}", placeholder="e.g. APP-94821")
                    confirm_check = st.checkbox("I confirm that this application was completed.", key=f"chk_{job.id}")

                    if st.button("Confirm Submission", key=f"btn_sub_{job.id}", type="primary"):
                        if not confirm_check:
                            st.error("Please tick the confirmation checkbox.")
                        else:
                            tracker_service.record_manual_submission(job.id, channel=sub_channel, confirmation_id=conf_id)
                            st.success("Submission successfully recorded in Tracker!")
                            st.rerun()


# ==========================================
# 5. APPLICATION TRACKER PAGE
# ==========================================
def render_application_tracker():
    st.markdown(
        render_header("Application Tracker", "Track status across the complete recruitment lifecycle from draft to offer."),
        unsafe_allow_html=True,
    )

    status_filter = st.selectbox(
        "Filter by Status",
        options=["All Statuses"] + [s.value for s in ApplicationStatus],
    )

    filter_val = None if status_filter == "All Statuses" else ApplicationStatus(status_filter)
    applications = repository.list_applications_by_status(filter_val)

    st.write(f"Displaying **{len(applications)}** tracked application(s).")

    for job, app, match, draft in applications:
        with st.container():
            st.markdown(
                f"""
                <div class="jobpilot-card">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <div>
                            <div style="font-size: 1.15rem; font-weight: 600; color: #FFFFFF;">
                                {job.title}
                            </div>
                            <div style="color: #9CA3AF; font-size: 0.9rem; margin-top: 2px;">
                                🏢 <b>{job.company}</b> &nbsp;•&nbsp; 📍 {job.location} &nbsp;•&nbsp; Updated: {app.updated_at[:10]}
                            </div>
                        </div>
                        <div style="text-align: right;">
                            <span style="background: rgba(59, 130, 246, 0.2); color: #60A5FA; padding: 4px 12px; border-radius: 6px; font-weight: 600; font-size: 0.85rem;">
                                {app.status.value}
                            </span>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Stage updater inside expander
            with st.expander(f"Manage Status for {job.title} at {job.company}"):
                c1, c2, c3 = st.columns([2, 3, 1])
                with c1:
                    new_st = st.selectbox(
                        "Update Pipeline Stage",
                        options=[s.value for s in ApplicationStatus],
                        index=[s.value for s in ApplicationStatus].index(app.status.value),
                        key=f"status_sel_{job.id}",
                    )
                with c2:
                    st_notes = st.text_input("Stage Notes / Feedback", value=app.submission_notes or "", key=f"notes_in_{job.id}")
                with c3:
                    st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
                    if st.button("Update", key=f"update_btn_{job.id}"):
                        tracker_service.update_pipeline_stage(job.id, ApplicationStatus(new_st), notes=st_notes)
                        st.success("Status updated!")
                        st.rerun()


# ==========================================
# 6. RESUME MANAGER PAGE
# ==========================================
def render_resume_manager():
    st.markdown(
        render_header("Resume Manager", "Upload, parse, and review resume text, extracted skills, and projects."),
        unsafe_allow_html=True,
    )

    active_resume = repository.get_active_resume()

    t1, t2 = st.tabs(["Active Resume", "Upload New Resume"])

    with t1:
        if active_resume:
            st.markdown(
                f"""
                <div class="jobpilot-card">
                    <h3 style="margin: 0; font-size: 1.15rem; color: #FFFFFF;">
                        📄 {active_resume['filename']} <span style="font-size: 0.8rem; color: #34D399;">(Active)</span>
                    </h3>
                    <div style="color: #9CA3AF; font-size: 0.85rem; margin-top: 4px;">
                        Version: {active_resume['version_tag']} &nbsp;•&nbsp; Uploaded: {active_resume['uploaded_at'][:10]}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.subheader("Identified Skills in Resume")
            skills_html = "".join([f'<span class="pill-skill">{s}</span>' for s in active_resume["parsed_skills"]])
            st.markdown(skills_html or "No skills parsed.", unsafe_allow_html=True)

            st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
            st.subheader("Extracted Projects & Achievements")
            for proj in active_resume["parsed_projects"]:
                st.markdown(f"- {proj}")

            with st.expander("View Extracted Raw Text"):
                st.text_area("Resume Text", value=active_resume["extracted_text"], height=300, disabled=True)
        else:
            st.info("No resume uploaded yet. Default candidate profile is currently active. Upload a PDF/DOCX to customize.")

    with t2:
        st.subheader("Upload PDF or DOCX Resume")
        st.write("Upload candidate resume to extract skills, verify facts, and attach to drafted applications.")

        uploaded_file = st.file_uploader("Choose a file", type=["pdf", "docx"])
        version_label = st.text_input("Version Tag", value="v1.0 (2027 Campus)")

        if uploaded_file and st.button("Parse and Save Resume", type="primary"):
            with st.spinner("Parsing resume text and extracting technical skills..."):
                file_bytes = uploaded_file.read()
                saved_path = resume_parser.save_uploaded_file(file_bytes, uploaded_file.name)
                parsed_data = resume_parser.parse_file(saved_path)

                resume_id = repository.save_resume(
                    filename=parsed_data["filename"],
                    file_path=parsed_data["file_path"],
                    extracted_text=parsed_data["extracted_text"],
                    skills=parsed_data["parsed_skills"],
                    projects=parsed_data["parsed_projects"],
                    version_tag=version_label,
                )

                st.success(f"Resume parsed and saved successfully! ID: {resume_id}")
                st.write(f"Detected **{len(parsed_data['parsed_skills'])}** skills and **{len(parsed_data['parsed_projects'])}** projects.")
                if parsed_data["recommendations"]:
                    st.info("💡 Recommendations: " + " ".join(parsed_data["recommendations"]))
                st.rerun()


# ==========================================
# 7. CANDIDATE PROFILE PAGE
# ==========================================
def render_candidate_profile():
    st.markdown(
        render_header("Candidate Profile", "Configure candidate education, skills, projects, and target preferences."),
        unsafe_allow_html=True,
    )

    profile = repository.get_candidate_profile()

    with st.form("candidate_profile_form"):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("Full Name*", value=profile.name)
            email = st.text_input("Email*", value=profile.email or "")
            phone = st.text_input("Phone Number*", value=profile.phone or "")
            education = st.text_input("Education*", value=profile.education)
            grad_year = st.number_input("Graduation Year*", value=profile.graduation_year, min_value=2024, max_value=2030)

        with c2:
            exp_level = st.text_input("Experience Level*", value=profile.experience_level)
            max_exp = st.number_input("Max Experience Limit (Years)*", value=profile.max_experience_years, min_value=0.0, max_value=5.0, step=0.5)
            remote_pref = st.checkbox("Open to Remote Positions", value=profile.open_to_remote)
            locations_str = st.text_input("Preferred Locations (comma separated)*", value=", ".join(profile.preferred_locations))

        roles_str = st.text_area(
            "Preferred Roles (comma separated)*",
            value=", ".join(profile.preferred_roles),
            height=70,
        )

        skills_str = st.text_area(
            "Verified Skills (comma separated)*",
            value=", ".join(profile.skills),
            height=90,
        )

        st.subheader("Key Academic & AI Projects")
        projects_json_str = st.text_area(
            "Projects (JSON format)*",
            value=json.dumps(profile.projects, indent=2),
            height=200,
        )

        save_btn = st.form_submit_button("Save Profile Settings", type="primary")
        if save_btn:
            try:
                parsed_projects = json.loads(projects_json_str)
                updated_profile = CandidateProfile(
                    name=name.strip(),
                    email=email.strip(),
                    phone=phone.strip(),
                    education=education.strip(),
                    graduation_year=int(grad_year),
                    experience_level=exp_level.strip(),
                    max_experience_years=float(max_exp),
                    preferred_roles=[r.strip() for r in roles_str.split(",") if r.strip()],
                    skills=[s.strip() for s in skills_str.split(",") if s.strip()],
                    projects=parsed_projects,
                    preferred_locations=[l.strip() for l in locations_str.split(",") if l.strip()],
                    open_to_remote=remote_pref,
                )
                repository.save_candidate_profile(updated_profile)
                st.success("Candidate profile updated successfully!")
                st.rerun()
            except json.JSONDecodeError:
                st.error("Invalid JSON format in Projects field.")


# ==========================================
# 8. AUTOMATION SETTINGS PAGE
# ==========================================
def render_automation_settings():
    st.markdown(
        render_header("Automation Settings", "Configure daily execution schedules, scoring weights, and automation triggers."),
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(2)

    with c1:
        st.subheader("Daily Scheduler (APScheduler)")
        st.write("Configures daily automated discovery and match drafting.")

        sched_status = "Active 🟢" if automation_scheduler.is_active else "Paused / Idle ⏸️"
        st.info(f"Scheduler Status: **{sched_status}**")

        hour = st.number_input("Daily Run Hour (24h)", min_value=0, max_value=23, value=settings.DAILY_RUN_HOUR)
        minute = st.number_input("Daily Run Minute", min_value=0, max_value=59, value=settings.DAILY_RUN_MINUTE)
        timezone = st.text_input("Timezone", value=settings.TIMEZONE)

        col_b1, col_b2, col_b3 = st.columns(3)
        with col_b1:
            if st.button("Start / Apply", type="primary", use_container_width=True):
                automation_scheduler.start_scheduler(hour=int(hour), minute=int(minute), timezone_str=timezone)
                st.success(f"Scheduler active at {hour:02d}:{minute:02d} ({timezone})")
                st.rerun()
        with col_b2:
            if st.button("Pause", use_container_width=True):
                automation_scheduler.pause_scheduler()
                st.warning("Scheduler paused.")
                st.rerun()
        with col_b3:
            if st.button("Resume", use_container_width=True):
                automation_scheduler.resume_scheduler()
                st.success("Scheduler resumed.")
                st.rerun()

        st.caption("Note: Local background scheduling requires the application process to remain active.")

        st.markdown("<div style='margin-top: 14px;'></div>", unsafe_allow_html=True)
        st.write(f"📧 **Daily Digest Recipient:** `{settings.DIGEST_RECIPIENT_EMAIL}`")
        if st.button("📨 Dispatch Daily Digest Now", key="quick_digest_btn"):
            with st.spinner("Generating and dispatching digest..."):
                res = email_digest_service.dispatch_digest()
                st.success(f"Digest ready! {res['message']}")
                st.rerun()

    with c2:
        st.subheader("Match Weight Configurations")
        st.write("Tune scoring factor importance. Total weight sum = 100%.")

        w_skill = st.slider("Skill Overlap Weight (%)", 10, 60, int(settings.WEIGHT_SKILL_OVERLAP))
        w_role = st.slider("Role Relevance Weight (%)", 10, 40, int(settings.WEIGHT_ROLE_RELEVANCE))
        w_elig = st.slider("Eligibility Weight (%)", 10, 40, int(settings.WEIGHT_ELIGIBILITY))
        w_loc = st.slider("Location Weight (%)", 0, 20, int(settings.WEIGHT_LOCATION))
        w_fresh = st.slider("Freshness Weight (%)", 0, 15, int(settings.WEIGHT_FRESHNESS))

        min_draft_score = st.slider("Minimum Match Score to Generate Draft (%)", 50, 90, int(settings.MIN_MATCH_SCORE_TO_DRAFT))

        if st.button("Save Weight Settings"):
            settings.WEIGHT_SKILL_OVERLAP = float(w_skill)
            settings.WEIGHT_ROLE_RELEVANCE = float(w_role)
            settings.WEIGHT_ELIGIBILITY = float(w_elig)
            settings.WEIGHT_LOCATION = float(w_loc)
            settings.WEIGHT_FRESHNESS = float(w_fresh)
            settings.MIN_MATCH_SCORE_TO_DRAFT = float(min_draft_score)
            st.success("Scoring weights saved in memory!")


# ==========================================
# 9. INTEGRATIONS PAGE
# ==========================================
def render_integrations():
    st.markdown(
        render_header("Integrations & Platforms", "Manage external LLM endpoints, multi-platform career sources, and email digest delivery."),
        unsafe_allow_html=True,
    )

    t_llm, t_platforms, t_email = st.tabs(["Hugging Face LLM", "Job Platforms & Auth", "Daily Email Digest"])

    with t_llm:
        st.subheader("Hugging Face Inference Providers (OpenAI-compatible Endpoint)")
        st.write(
            "JobPilot AI connects to Hugging Face chat-completions endpoint for LLM requirements extraction, "
            "cover letter drafting, and truthful Q&A generation."
        )

        with st.form("hf_config_form"):
            hf_token = st.text_input("Hugging Face API Token (HF_TOKEN)", value=settings.HF_TOKEN or "", type="password", placeholder="hf_...")
            hf_model = st.text_input("Model Identifier", value=settings.HF_MODEL)
            hf_base_url = st.text_input("Base URL", value=settings.HF_BASE_URL)

            saved = st.form_submit_button("Save & Test Connection", type="primary")
            if saved:
                settings.HF_TOKEN = hf_token.strip() if hf_token.strip() else None
                settings.HF_MODEL = hf_model.strip()
                settings.HF_BASE_URL = hf_base_url.strip()

                test_client = llm_client.__class__(token=settings.HF_TOKEN, model=settings.HF_MODEL, base_url=settings.HF_BASE_URL)
                status = test_client.validate_connection()

                if status["success"]:
                    st.success(f"✓ {status['message']}")
                else:
                    st.warning(f"⚠️ {status['message']}")

    with t_platforms:
        st.subheader("Multi-Platform Status & Credential Configurations")
        st.write("Configure optional authorized credentials or inspect technical access requirements across all supported platforms.")

        with st.form("platform_credentials_form"):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("#### Direct Platforms & Job Boards")
                naukri_key = st.text_input("Naukri Recruiter API Key", value=settings.NAUKRI_API_KEY or "", type="password", placeholder="Enter key if enterprise recruiter")
                linkedin_token = st.text_input("LinkedIn Partner OAuth Token", value=settings.LINKEDIN_ACCESS_TOKEN or "", type="password", placeholder="Bearer token with r_jobs scope")
                indeed_feed = st.text_input("Indeed Authorized XML Feed URL", value=settings.INDEED_FEED_URL or "", placeholder="https://feed.indeed.com/xml/...")
            with col2:
                st.markdown("#### Company Careers & Public ATS Feeds")
                gh_boards = st.text_input("Greenhouse Board Identifiers (comma-separated)", value=settings.GREENHOUSE_BOARDS)
                lever_slugs = st.text_input("Lever Company Identifiers (comma-separated)", value=settings.LEVER_COMPANIES)

            if st.form_submit_button("Save Platform Configurations", type="primary"):
                settings.NAUKRI_API_KEY = naukri_key.strip() if naukri_key.strip() else None
                settings.LINKEDIN_ACCESS_TOKEN = linkedin_token.strip() if linkedin_token.strip() else None
                settings.INDEED_FEED_URL = indeed_feed.strip() if indeed_feed.strip() else None
                settings.GREENHOUSE_BOARDS = gh_boards.strip()
                settings.LEVER_COMPANIES = lever_slugs.strip()
                st.success("Platform settings saved!")
                st.rerun()

        # Detailed compliance cards
        st.markdown("<hr style='border-color: #1F2937;'>", unsafe_allow_html=True)
        st.subheader("Platform Access Methods & Restrictions Summary")
        matrix_data = [
            {"Platform": "Naukri.com", "Access Status": "Restricted by ToS", "Authorized Method": "Manual URL / Pasted JD / CSV Bulk Import", "Rate Limit / Anti-Bot": "Protected by Cloudflare & CAPTCHA. Web scraping prohibited by ToS Sec 6.2"},
            {"Platform": "LinkedIn Jobs", "Access Status": "Requires Partner OAuth", "Authorized Method": "Candidate URL / CSV Import / Partner API", "Rate Limit / Anti-Bot": "OAuth 2.0 with 'r_jobs' scope. Scraping prohibited by User Agreement Sec 8.2"},
            {"Platform": "Indeed India", "Access Status": "Requires Feed / Partner Key", "Authorized Method": "Authorized Employer XML Feed / Candidate URL", "Rate Limit / Anti-Bot": "Publisher API discontinued; Cloudflare/Datadome protected. XML feeds supported"},
            {"Platform": "Internshala", "Access Status": "Restricted (No Public API)", "Authorized Method": "Manual Internship URL / Pasted JD / CSV", "Rate Limit / Anti-Bot": "Student portal auth only. Dedicated 2027 Fresher & Internship parsing"},
            {"Platform": "Wellfound (AngelList)", "Access Status": "Restricted (API Sunset)", "Authorized Method": "Candidate URL / Startup CSV Import", "Rate Limit / Anti-Bot": "Cloudflare protected. Direct URL / JSON import supported"},
            {"Platform": "Cutshort", "Access Status": "Restricted (Closed ATS)", "Authorized Method": "Candidate URL / CSV Ingestion", "Rate Limit / Anti-Bot": "Candidate account only. URL & text ingestion fully supported"},
            {"Platform": "Foundit (Monster)", "Access Status": "Restricted (Enterprise Only)", "Authorized Method": "Candidate URL / CSV Ingestion", "Rate Limit / Anti-Bot": "Paid enterprise employer contract required for API"},
            {"Platform": "Greenhouse Public API", "Access Status": "🟢 Connected & Live", "Authorized Method": "Official REST API (boards-api.greenhouse.io)", "Rate Limit / Anti-Bot": "Open public board feeds. No authentication required"},
            {"Platform": "Lever Company Careers", "Access Status": "🟢 Connected & Live", "Authorized Method": "Official REST API (api.lever.co/v0/postings)", "Rate Limit / Anti-Bot": "Open public postings endpoint. No authentication required"},
            {"Platform": "Arbeitnow Public API", "Access Status": "🟢 Connected & Live", "Authorized Method": "Official REST API (arbeitnow.com/api/job-board-api)", "Rate Limit / Anti-Bot": "Open job board API. Permitted public usage"},
        ]
        st.dataframe(pd.DataFrame(matrix_data), hide_index=True, use_container_width=True)

    with t_email:
        st.subheader("Daily Email Digest Configuration")
        st.write(
            "JobPilot AI generates an automated email digest summarizing newly discovered jobs, "
            "source platforms, match scores, direct links, and pending application drafts."
        )

        with st.form("email_digest_form"):
            digest_email = st.text_input("Digest Recipient Email*", value=settings.DIGEST_RECIPIENT_EMAIL)
            enable_digest = st.checkbox("Enable Daily Digest Dispatch", value=settings.ENABLE_EMAIL_DIGEST)
            st.markdown("#### Optional Outgoing SMTP Credentials")
            st.caption("If blank or offline, digests are securely rendered and preserved in `data/email_digests/`.")
            col_s1, col_s2 = st.columns(2)
            with col_s1:
                smtp_host = st.text_input("SMTP Server Host", value=settings.SMTP_HOST or "", placeholder="e.g. smtp.gmail.com")
                smtp_port = st.number_input("SMTP Server Port", value=settings.SMTP_PORT, min_value=1, max_value=65535)
                smtp_from = st.text_input("From Address", value=settings.SMTP_FROM)
            with col_s2:
                smtp_user = st.text_input("SMTP Username / Email", value=settings.SMTP_USER or "")
                smtp_pass = st.text_input("SMTP Password / App Password", value=settings.SMTP_PASSWORD or "", type="password")
                smtp_tls = st.checkbox("Use STARTTLS Encryption", value=settings.SMTP_USE_TLS)

            if st.form_submit_button("Save Email Settings", type="primary"):
                settings.DIGEST_RECIPIENT_EMAIL = digest_email.strip()
                settings.ENABLE_EMAIL_DIGEST = enable_digest
                settings.SMTP_HOST = smtp_host.strip() if smtp_host.strip() else None
                settings.SMTP_PORT = int(smtp_port)
                settings.SMTP_FROM = smtp_from.strip()
                settings.SMTP_USER = smtp_user.strip() if smtp_user.strip() else None
                settings.SMTP_PASSWORD = smtp_pass.strip() if smtp_pass.strip() else None
                settings.SMTP_USE_TLS = smtp_tls
                st.success("Email configuration saved!")
                st.rerun()

        st.markdown("<hr style='border-color: #1F2937;'>", unsafe_allow_html=True)
        col_test1, col_test2 = st.columns([1, 1])
        with col_test1:
            if st.button("🚀 Generate & Dispatch Test Email Digest Now", use_container_width=True):
                with st.spinner("Generating and dispatching email digest..."):
                    res = email_digest_service.dispatch_digest()
                    st.success(f"Digest generated for {res['recipient']}! {res['message']}")
                    st.rerun()

        with col_test2:
            latest_html = email_digest_service.get_latest_digest_html()
            if latest_html:
                with st.popover("👁️ Preview Latest Generated Email Digest"):
                    st.components.v1.html(latest_html, height=500, scrolling=True)
            else:
                st.info("Click 'Generate & Dispatch Test Email Digest' to produce the first digest.")


# ==========================================
# 10. ACTIVITY LOGS PAGE
# ==========================================
def render_activity_logs():
    st.markdown(
        render_header("Activity & Audit Logs", "Tamper-evident trail of pipeline runs, draft modifications, and approvals."),
        unsafe_allow_html=True,
    )

    logs = repository.list_audit_logs(limit=100)
    if not logs:
        st.info("No audit events recorded yet.")
        return

    df_logs = pd.DataFrame(logs)
    st.dataframe(df_logs, use_container_width=True, hide_index=True)


# ==========================================
# 11. BROWSER AGENT PAGE
# ==========================================
def render_browser_agent():
    st.markdown(
        render_header(
            "🤖 Browser Application Agent",
            "Semi-automated job search & application agent. Opens a real browser, finds matching jobs on LinkedIn / Naukri / Indeed, pre-fills your application, and lets you review before submitting."
        ),
        unsafe_allow_html=True,
    )

    from jobpilot.browser_agent.config import browser_config

    # ── Platform Launch ──
    st.subheader("🚀 Launch Agent")
    st.markdown(
        "> **How it works:** The agent opens a real Chromium browser → your login stays securely saved → "
        "it searches Pune and Remote jobs, pre-fills your application forms with your resume & contact info, "
        "and either submits automatically or pauses for your review in the browser."
    )

    col_opt1, col_opt2 = st.columns(2)
    with col_opt1:
        include_remote = st.checkbox(
            "🌍 Include Remote Jobs Worldwide",
            value=browser_config.INCLUDE_REMOTE,
            help="Also search for Worldwide / International remote positions",
        )
    with col_opt2:
        auto_submit = st.checkbox(
            "⚡ Auto-Submit Applications",
            value=browser_config.AUTO_SUBMIT,
            help="If checked, automatically clicks Submit without pausing for manual review",
        )

    col_ln, col_nk, col_in, col_all = st.columns(4)
    with col_ln:
        launch_linkedin = st.button("🔗 LinkedIn Easy Apply", use_container_width=True, type="primary")
    with col_nk:
        launch_naukri = st.button("💼 Naukri.com", use_container_width=True, type="primary")
    with col_in:
        launch_indeed = st.button("🔍 Indeed India", use_container_width=True)
    with col_all:
        launch_all = st.button("🌐 All Platforms", use_container_width=True)

    if any([launch_linkedin, launch_naukri, launch_indeed, launch_all]):
        import subprocess, sys
        platforms = []
        if launch_linkedin:
            platforms = ["linkedin"]
        elif launch_naukri:
            platforms = ["naukri"]
        elif launch_indeed:
            platforms = ["indeed"]
        elif launch_all:
            platforms = ["linkedin", "naukri", "indeed"]

        browser_config.INCLUDE_REMOTE = include_remote
        browser_config.AUTO_SUBMIT = auto_submit

        cmd_args = [sys.executable, "-m", "jobpilot.browser_agent.orchestrator", "--platform", *platforms]
        if include_remote:
            cmd_args.append("--remote")
        if auto_submit:
            cmd_args.append("--auto-submit")

        cmd_display = " ".join(cmd_args)
        st.info(
            f"🚀 Launching **{', '.join(p.title() for p in platforms)}** agent...\n\n"
            f"• Location: **{browser_config.SEARCH_LOCATION}**" + (" + **Remote Worldwide**" if include_remote else "") + "\n"
            f"• Auto-Submit: **{'Enabled' if auto_submit else 'Disabled (Pauses for your confirmation)'}**\n\n"
            f"The Chromium browser window is now active on your desktop. Watch the live screen stream below!"
        )

        try:
            if sys.platform == "win32":
                platform_str = " ".join(platforms)
                remote_flag = " --remote" if include_remote else ""
                auto_submit_flag = " --auto-submit" if auto_submit else ""
                win_cmd = f'start "JobPilot Agent" cmd /k "{sys.executable}" -m jobpilot.browser_agent.orchestrator --platform {platform_str}{remote_flag}{auto_submit_flag}'
                proc = subprocess.Popen(win_cmd, cwd=str(BASE_DIR), shell=True)
                st.success(f"✅ Launched! Terminal and Chromium browser windows are active.")
            else:
                proc = subprocess.Popen(cmd_args, cwd=str(BASE_DIR))
                st.success(f"✅ Process started (PID: {proc.pid})! Chromium browser window is active.")
        except Exception as e:
            st.warning(f"Could not open separate terminal window automatically: {e}. You can run `{cmd_display}` in your terminal.")

    st.markdown("---")

    # ── Live Agent Activity Monitor ──
    st.subheader("🔴 Live Agent Activity Monitor")
    st.markdown("Monitor what the agent is doing in real-time, including live screenshots and form filling status.")

    col_mon1, col_mon2, col_mon3 = st.columns([2, 1, 1])
    with col_mon2:
        auto_refresh = st.checkbox("⚡ Auto-refresh (2s)", value=True, help="Automatically refreshes the live screen and activity")
    with col_mon3:
        refresh_btn = st.button("🔄 Refresh Now", use_container_width=True)

    # Use client-side smooth auto-refresh
    if auto_refresh:
        try:
            from streamlit_autorefresh import st_autorefresh
            st_autorefresh(interval=2000, limit=None, key="browser_agent_live_monitor")
        except Exception:
            pass

    status_file = Path(browser_config.BROWSER_STATE_DIR) / "live_status.json"
    latest_img = Path(browser_config.BROWSER_STATE_DIR) / "screenshots" / "latest.png"

    # Action button to bring Chromium window to foreground on desktop
    with col_mon1:
        if st.button("🖥️ Bring Chromium Window to Foreground", use_container_width=True, help="Pop the Chromium browser window to the front of your desktop"):
            try:
                from jobpilot.browser_agent.helpers import BrowserHelper
                h = BrowserHelper("linkedin")
                h.bring_to_foreground()
                st.toast("Brought Chromium window to the foreground!")
            except Exception as e:
                st.warning(f"Could not bring window to front: {e}")

    if status_file.exists():
        try:
            with open(status_file, "r", encoding="utf-8") as f:
                live_data = json.load(f)

            cur_step = live_data.get("step", "Idle")
            cur_plat = live_data.get("platform", "generic").upper()
            cur_status = live_data.get("status", "running")
            applied_c = live_data.get("applied_count", 0)
            max_c = live_data.get("max_applications", 25)
            last_ts = live_data.get("timestamp", "")
            job_details = live_data.get("job")
            waiting_user = live_data.get("waiting_for_user", False)
            rem_sec = live_data.get("remaining_seconds")

            # Metric cards
            m_col1, m_col2, m_col3, m_col4 = st.columns(4)
            with m_col1:
                st.metric("Platform", cur_plat)
            with m_col2:
                st.metric("Applications", f"{applied_c} / {max_c}")
            with m_col3:
                card_idx = live_data.get("card_index")
                total_cards = live_data.get("total_cards")
                if card_idx and total_cards:
                    st.metric("Job Progress", f"{card_idx} of {total_cards}")
                else:
                    st.metric("Status", "Active" if not waiting_user else "Needs Review")
            with m_col4:
                st.metric("Last Action", last_ts.split()[-1] if last_ts else "Just now")

            if waiting_user:
                rem_text = f" ({rem_sec}s remaining)" if rem_sec is not None else ""
                st.warning(
                    f"⚠️ **Action Required in Chromium Browser Window{rem_text}:** Review the pre-filled application for "
                    f"**{job_details.get('title', 'this job') if job_details else 'this job'}**, "
                    f"then click **Submit** in the Chromium window (or close to skip). "
                    f"Click **🖥️ Bring Chromium Window to Foreground** above if the browser is hidden."
                )

            st.info(f"📍 **Current Activity:** {cur_step}")

            # Job details card if active
            if job_details:
                with st.expander("💼 Current Job Details", expanded=True):
                    st.markdown(f"**Job Title:** {job_details.get('title', 'N/A')}")
                    st.markdown(f"**Company:** {job_details.get('company', 'N/A')}")
                    st.markdown(f"**Location:** {job_details.get('location', 'N/A')}")
                    if job_details.get("url"):
                        st.markdown(f"[🔗 View Job Listing on {cur_plat}]({job_details.get('url')})")

            # Display Live Screenshot without browser caching
            if latest_img.exists():
                try:
                    with open(latest_img, "rb") as img_f:
                        img_bytes = img_f.read()
                    st.markdown("#### 📸 Live Browser View")
                    st.image(img_bytes, caption=f"Live Browser Screen — {last_ts}", use_container_width=True)
                except Exception:
                    pass

        except Exception as e:
            st.caption(f"Waiting for live status update: {e}")
    else:
        st.info("Agent is currently idle. Click one of the launch buttons above to start!")

    st.markdown("---")

    # ── Status Cards & Configuration ──
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        resume_ok = browser_config.resume_file.exists()
        st.metric("Resume", "✓ Ready" if resume_ok else "✗ Missing")
    with col2:
        st.metric("Location", browser_config.SEARCH_LOCATION)
    with col3:
        st.metric("Max Apply / Session", browser_config.MAX_APPLICATIONS_PER_SESSION)
    with col4:
        st.metric("Mode", "Semi-Auto")

    with st.expander("⚙️ Advanced Agent Configuration", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            cfg_keywords = st.text_input(
                "Search Keywords",
                value=browser_config.SEARCH_KEYWORDS,
                help="Comma-separated keywords for job search",
            )
            cfg_location = st.text_input(
                "Search Location",
                value=browser_config.SEARCH_LOCATION,
            )
            cfg_max_apply = st.slider(
                "Max Applications Per Session",
                min_value=1, max_value=50,
                value=browser_config.MAX_APPLICATIONS_PER_SESSION,
            )
        with c2:
            cfg_name = st.text_input("Candidate Name", value=browser_config.CANDIDATE_NAME)
            cfg_email = st.text_input("Candidate Email", value=browser_config.CANDIDATE_EMAIL)
            cfg_phone = st.text_input("Candidate Phone", value=browser_config.CANDIDATE_PHONE)
            cfg_resume = st.text_input("Resume PDF Path", value=str(browser_config.resume_file))

        if st.button("💾 Save Configuration Changes"):
            browser_config.SEARCH_KEYWORDS = cfg_keywords
            browser_config.SEARCH_LOCATION = cfg_location
            browser_config.MAX_APPLICATIONS_PER_SESSION = cfg_max_apply
            browser_config.CANDIDATE_NAME = cfg_name
            browser_config.CANDIDATE_EMAIL = cfg_email
            browser_config.CANDIDATE_PHONE = cfg_phone
            browser_config.RESUME_PATH = cfg_resume
            st.success("Configuration updated successfully!")

    st.markdown("---")

    # ── Session History ──
    st.subheader("📋 Past Agent Sessions")
    sessions_dir = Path(browser_config.BROWSER_STATE_DIR).parent / "browser_sessions"
    if sessions_dir.exists():
        session_files = sorted(sessions_dir.glob("session_*.json"), reverse=True)
        if session_files:
            for sf in session_files[:10]:
                try:
                    with open(sf, "r") as f:
                        data = json.load(f)
                    with st.expander(
                        f"📅 {data.get('timestamp', sf.stem)} — "
                        f"{', '.join(data.get('platforms', []))}"
                    ):
                        for plat, result in data.get("results", {}).items():
                            applied = result.get("applied", 0)
                            skipped = result.get("skipped", 0)
                            st.markdown(
                                f"**{plat.upper()}**: {applied} applied, {skipped} skipped "
                                f"({result.get('duration_seconds', 0):.0f}s)"
                            )
                            if result.get("applied_jobs"):
                                for job in result["applied_jobs"]:
                                    st.markdown(
                                        f"  ✓ {job.get('title', '?')} at {job.get('company', '?')}"
                                    )
                except Exception:
                    pass
        else:
            st.info("No agent sessions recorded yet. Launch an agent to get started!")
    else:
        st.info("No agent sessions recorded yet. Launch an agent to get started!")


if __name__ == "__main__":
    main()
