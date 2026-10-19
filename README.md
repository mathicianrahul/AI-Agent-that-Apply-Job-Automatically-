# 🚀 JobPilot AI — Personal AI Job Application Agent

JobPilot AI is a production-minded, modular Agentic AI system that automates job discovery, intelligent multi-factor matching, personalized application drafting, and recruitment pipeline tracking.

Built specifically for **Rahul Girase** (Final-year BE in Artificial Intelligence and Machine Learning, 2027 graduate, Fresher / Entry-Level), the application enforces a strict **Human-in-the-Loop** model: no job application is ever submitted without explicit candidate verification and approval.

---

## 🌟 Key Architecture & Capabilities

1. **Deterministic Multi-Factor Scoring Engine (0–100%)**:
   - **40% Skill Overlap**: Matches candidate skills (Python, NumPy, Pandas, Scikit-learn, SQL, OpenCV, MediaPipe, YOLO, LangChain, LangGraph, Hugging Face, FastAPI, MySQL, MongoDB) against job requirements.
   - **25% Role Relevance**: Weights target roles (AI/ML Engineer, Data Scientist, Generative AI Engineer, LLM Application Engineer, Computer Vision Engineer, Python Developer).
   - **20% Candidate Eligibility**: Strict hard eligibility rules. Jobs requiring >1.0 year experience or restricted to pre-2026 graduation batches are marked as **Ineligible** and score-capped.
   - **10% Location Preference**: Strict Pune & Remote rule (In India: **Pune only**; Out of India: **Remote only**; on-site roles elsewhere are disqualified).
   - **5% Posting Freshness**: Recency decay favoring recently posted roles.

2. **13-Stage LangGraph Agent Workflow**:
   - `load_candidate_profile` ➔ `collect_jobs` ➔ `normalize_jobs` ➔ `deduplicate_jobs` ➔ `extract_job_requirements` ➔ `check_hard_eligibility` ➔ `calculate_match_score` ➔ `rank_matches` ➔ `select_resume` ➔ `generate_application_draft` ➔ `validate_draft` ➔ `save_results` ➔ `generate_daily_report`.

3. **Live Verified Job Discovery**:
   - **Greenhouse Public Boards API**: Real-time endpoints (`boards-api.greenhouse.io`) for permitted tech companies (e.g. Canonical, Cloudflare, GitLab).
   - **Arbeitnow Public API**: Permitted job-board API for remote & software engineering listings.
   - **Curated Demo Mode**: Realistic test opportunities tailored to Rahul Girase's 2027 batch.
   - **Custom Importer**: Ingest listings via custom career page URLs or raw descriptions.

4. **Hugging Face LLM Integration (OpenAI-Compatible Endpoint)**:
   - Connects to Hugging Face Inference Providers (`https://api-inference.huggingface.co/v1`) using model `meta-llama/Llama-3.2-3B-Instruct` (or user-configured model).
   - Truthful drafting: Never invents qualifications, degrees, or unlisted project metrics.
   - High-fidelity offline fallback when no token is present or when offline.

5. **Human Approval & Lifecycle Tracking**:
   - Mandatory human approval: Drafts await candidate review before any external submission.
   - Actions: **Approve**, **Reject**, **Save for Later**, **Edit Draft**, **Open Original Job URL**, **Record Verified Submission**.
   - Idempotency & duplicate submission prevention via SHA-256 canonical hashing.

6. **Daily Background Automation (APScheduler)**:
   - Configurable daily run (default 9:00 AM Asia/Kolkata).
   - In-app controls: **Run Now**, **Pause Automation**, **Resume Automation**.

7. **Premium SaaS UI/UX Dashboard (Streamlit)**:
   - Dark navy and charcoal interface (`#0B0F19`, `#111827`) with electric-blue & violet accents.
   - 10 distinct navigation views: Overview, Discover Jobs, Matched Jobs, Application Review, Application Tracker, Resume Manager, Candidate Profile, Automation Settings, Integrations, and Activity Logs.

---

## 🛠️ Technology Stack

| Layer | Technology |
|---|---|
| **Language** | Python 3.11 - 3.14 compatible |
| **Agent Orchestration** | LangGraph (`StateGraph`) |
| **LLM Provider** | Hugging Face Inference Providers (OpenAI-compatible chat completions) |
| **Dashboard UI** | Streamlit |
| **Database** | SQLite with WAL mode, foreign keys, and indexes |
| **Scheduler** | APScheduler with native timezone support |
| **Resume Parser** | PyMuPDF (`fitz`) and `python-docx` |
| **Data Models** | Pydantic v2 & Pydantic-Settings |
| **Testing** | pytest (22 passing unit & integration tests) |

---

## 🚀 Quick Start Guide (For Any User)

### Option A: 1-Click Launch (Easiest)
- **Windows**: Double-click `run.bat` (or run `.\run.bat` in PowerShell / CMD).
- **macOS / Linux**: Run `chmod +x run.sh && ./run.sh`.

This script automatically creates a Python virtual environment, installs dependencies, sets up `.env`, and launches the dashboard.

---

### Option B: Manual Setup

#### 1. Clone & Set Up Environment
```bash
git clone <repo-url>
cd "Agent for the Job Apply"
python -m venv venv

# Windows:
.\venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
```

#### 2. Configure Environment Variables (Optional)
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Key settings in `.env`:
- `HF_TOKEN`: *(Optional)* Your free Hugging Face API token for AI cover letter drafting (if empty, rule-based fallback works automatically).
- `DIGEST_RECIPIENT_EMAIL`: Your personal email to receive daily job alerts.
- `DEMO_MODE=true`: Set to `false` when ready to scan live Greenhouse, Lever, and Arbeitnow public job boards.

#### 3. Launch Dashboard
```bash
python -m streamlit run app.py
```
Open **`http://localhost:8501`** in your browser.

---

### 👤 First-Time Personalization in Dashboard
1. **Resume Manager**: Upload your resume (PDF or DOCX). The parser will automatically extract your technical skills and past projects.
2. **Candidate Profile**: Enter your name, target roles, preferred locations (e.g. Pune, Bangalore, Remote), graduation year, and experience limits.
3. **Run Discovery**: Click **⚡ Run Agent Discovery** to match, score, and draft applications customized for your profile!

---

## 🌐 Multi-Platform Job Discovery Architecture & Compliance Matrix

JobPilot AI implements a strict, compliance-first modular source architecture. Automated web scraping that bypasses CAPTCHAs, triggers anti-bot checkpoints, or violates Terms of Service is explicitly avoided. All 10 supported platforms are integrated via officially supported methods:

| Platform | Integration Method | Compliance Status | Setup / Auth Path |
|---|---|---|---|
| **Greenhouse** | Public Boards API (`boards-api.greenhouse.io`) | 🟢 Connected & Live | Public API, no key required |
| **Lever** | Public Postings API (`api.lever.co/v0/postings`) | 🟢 Connected & Live | Public ATS API, no key required |
| **Arbeitnow** | Public Job Board API (`arbeitnow.com/api`) | 🟢 Connected & Live | Public API, permitted usage |
| **Naukri.com** | Candidate URL Ingestion & CSV Import | 🔒 ToS Restricted | Cloudflare/CAPTCHA protected; Ingest via Direct URL or CSV |
| **LinkedIn Jobs** | Candidate URL Ingestion & CSV Alerts | 🔒 ToS Restricted | Scraping prohibited (Sec 8.2); OAuth 2.0 Partner API supported |
| **Indeed India** | Employer XML/RSS Feed & Candidate URL | 🔒 ToS Restricted | Sunset publisher API; XML Feed (`INDEED_FEED_URL`) supported |
| **Internshala** | Candidate URL / Internship Ingestion | 🔒 ToS Restricted | Student portal; Manual URL / 2027 Fresher parser supported |
| **Wellfound** | Candidate URL / Startup CSV Import | 🔒 API Sunset | Cloudflare protected; Manual URL & JSON/CSV import supported |
| **Cutshort** | Candidate URL & Ingestion | 🔒 Closed ATS | Recruiter matchmaking network; Manual URL parser supported |
| **Foundit** | Candidate URL & Ingestion | 🔒 Enterprise Only | Enterprise contract required; Manual URL & CSV supported |
| **Multi-Platform CSV** | Universal CSV/TSV Auto-Mapping Importer | 🟢 Connected & Live | Auto-detects columns for title, company, location, URL, description |

### Multi-Platform Link Preservation:
When the same vacancy is listed across multiple platforms (e.g., both LinkedIn and Naukri), `JobDeduplicator` unifies the record into a single canonical entry while preserving **all source URLs** in `alternate_source_urls`. The candidate can choose their preferred application route.

---

## 📧 Automated Daily Email Digest

JobPilot AI automates a daily discovery run at **9:00 AM Asia/Kolkata**.
- **Digest Recipient:** `rgirase312@gmail.com`
- **Digest Contents:** Newly discovered jobs, source platform badges, company and title, match scores with eligibility reasons, original application links (with all alternate source links), pending application drafts awaiting review, and platform notices.
- **Delivery:** Dispatches via configured SMTP or renders responsive HTML digests saved locally in `data/email_digests/`.
- **UI Inspection:** Preview live generated digests directly from the **Integrations** or **Automation Settings** tab.

---

## 🧪 Running the Automated Test Suite

All 31 unit, integration, and security tests can be executed with:

```bash
python -m pytest tests/ -v
```

### Test Coverage Highlights:
- `tests/test_multi_platform_discovery.py`: Common `JobSource` interface validation, all 10 platform adapters, `MultiPlatformCSVImporter` auto-column mapping, `JobDeduplicator` link preservation across multi-source duplicates, and `EmailDigestService` generation for `rgirase312@gmail.com`.
- `tests/test_phase1_foundation.py`: Candidate profile seeding, job upserting, deduplication, and application lifecycle metrics.
- `tests/test_phase2_discovery.py`: URL canonicalization, deterministic ID hashing, skill extraction, experience parsing, and live Greenhouse source adapters.
- `tests/test_phase3_matching.py`: Hard eligibility rules, senior role disqualification, multi-factor scoring calculation, and truthful cover letter fallbacks.
- `tests/test_phase4_agent_and_tracker.py`: Resume DOCX parsing, LangGraph 13-stage pipeline execution, and submission idempotency.
- `tests/test_phase5_scheduler_and_integrity.py`: Graduation batch eligibility filtering, status preservation on rediscovery, draft editing, and APScheduler lifecycle.

---

## 🔒 Security & Privacy Practices

- **Zero Credential Leaking**: Logs use a redacting formatter to mask tokens, passwords, and API keys.
- **Strict Human Approval**: Applications are never auto-submitted.
- **Local SQLite Storage**: Candidate profiles and resumes are stored privately in `data/` and excluded by `.gitignore`.
- **Truthful Prompting**: Prompt boundaries prevent LLMs from fabricating candidate metrics or unverified work experience.

---

## ☁️ Continuous Cloud Deployment

To run JobPilot AI continuously in the cloud (e.g. AWS EC2, GCP Compute Engine, DigitalOcean, or Render):
1. Deploy the repository and set `.env` with production settings (`DEMO_MODE=false`).
2. Run the scheduler as a background systemd service:
   ```ini
   [Unit]
   Description=JobPilot AI Background Scheduler
   After=network.target

   [Service]
   Type=simple
   User=appuser
   WorkingDirectory=/opt/jobpilot
   ExecStart=/usr/bin/python3 -c "from jobpilot.scheduler.daily_runner import automation_scheduler; import time; automation_scheduler.start_scheduler(); time.sleep(999999999)"
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```
3. Expose Streamlit on port 8501 behind an Nginx reverse proxy with HTTPS/SSL.
