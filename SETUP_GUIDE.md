# 🚀 JobPilot AI — Complete Setup & Quickstart Guide

> **JobPilot AI** is an autonomous, open-source AI agent that continuously discovers job openings across 10+ career platforms (Greenhouse, Lever, Arbeitnow, LinkedIn, Naukri), extracts requirements, matches them strictly against **your** resume and graduation year, and prepares tailored application drafts with a strict **Human-in-the-Loop** verification model.

---

## 📌 System Prerequisites (Takes ~1 min)

Before getting started, make sure you have:

1. **Python 3.11 or higher** installed from [python.org/downloads](https://www.python.org/downloads/).
   > ⚠️ **Crucial on Windows:** Make sure to check the box **"Add Python to PATH"** during installation.
2. **Git** installed from [git-scm.com](https://git-scm.com/) (or you can download the project as a `.zip` file from GitHub).

---

## ⚡ Step 1: Clone or Download the Project

Open your Terminal (macOS/Linux) or PowerShell / Command Prompt (Windows) and run:

```bash
git clone https://github.com/mathicianrahul/AI-Agent-that-Apply-Job-Automatically-.git
cd AI-Agent-that-Apply-Job-Automatically-
```

*(If you downloaded the `.zip` file, simply extract it and open your terminal in that folder).*

---

## 🚀 Step 2: One-Click Launch (The Easiest Way)

We have built automated, 1-click startup scripts that handle all environment creation and dependency installation for you:

### 🪟 Windows Users:
Simply **double-click** the file:
```text
run.bat
```
*(Or run `.\run.bat` in PowerShell / CMD).*

### 🍏 Mac / Linux Users:
Open your terminal inside the folder and run:
```bash
chmod +x run.sh && ./run.sh
```

### ⚙️ What the 1-Click script does automatically:
1. Verifies that Python is installed.
2. Creates an isolated Python virtual environment (`venv`).
3. Installs all required packages from `requirements.txt`.
4. Creates your `.env` configuration file from `.env.example`.
5. Starts the Streamlit dashboard and opens your browser to: **`http://localhost:8501`**.

---

### 💻 Alternative: Manual Setup via Terminal
If you prefer running commands manually:

```bash
# 1. Create and activate virtual environment
python -m venv venv

# Windows:
.\venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create .env
cp .env.example .env

# 4. Start the dashboard
python -m streamlit run app.py
```

---

## 👤 Step 3: Personalize Your Profile in 2 Minutes

Once **`http://localhost:8501`** opens in your browser, configure your settings from the left sidebar:

### 1. Upload Your Resume (`Resume Manager` Tab)
- Go to the **Resume Manager** tab.
- Click **"Upload PDF or DOCX Resume"** and select your resume.
- The built-in parser will automatically extract your technical skills, past projects, and education.

### 2. Configure Your Preferences (`Candidate Profile` Tab)
- Go to the **Candidate Profile** tab.
- Fill in:
  - **Full Name**, **Email**, and **Phone Number**.
  - **Graduation Year** (e.g. `2025`, `2026`, `2027`).
  - **Preferred Locations** (e.g. *Bangalore, Pune, Mumbai, Remote*).
  - **Target Roles** (e.g. *AI/ML Engineer, Data Scientist, Python Developer*).
  - **Max Experience Limit** (e.g. `1.0` year for freshers/entry-level).
- Click **"Save Profile Settings"**.

---

## 🔑 Step 4: Configure Free AI Token & Live Search (Optional)

JobPilot AI runs completely offline using accurate deterministic rule-based fallbacks. However, to enable live AI-generated cover letters and email digests, you can configure your `.env` file:

```ini
# Free Hugging Face API Token for AI Cover Letter Drafting:
HF_TOKEN=hf_your_free_token_here
HF_MODEL=meta-llama/Llama-3.2-3B-Instruct

# Your Personal Email for Daily Job Application Alerts:
DIGEST_RECIPIENT_EMAIL=your_email@gmail.com

# Live Internet Scanning vs Demo Mode:
DEMO_MODE=false   # Set to 'false' to search real live company job boards!
```

> 💡 **Tip:** You can get a 100% free Hugging Face API token in 30 seconds at [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) (no credit card required).

---

## 🎯 Step 5: Run Discovery & Review Application Drafts

1. Click the prominent blue button in the sidebar: **⚡ Run Agent Discovery**.
2. The 13-stage LangGraph workflow will:
   - Query enabled job boards.
   - Disqualify irrelevant or ineligible roles based on experience and location.
   - Calculate a deterministic multi-factor match score (0–100%).
   - Select the best matching resume and draft tailored cover letters.
3. Open the **Application Review** tab:
   - Inspect the AI-drafted cover letter and tailored answers.
   - You can **Edit**, **Approve**, or **Reject** with one click.
4. Click **"Open Original Job URL"** to verify and submit directly on the company's verified application portal.

---

## 🌐 Supported Discovery Channels & Platforms

| Platform | Integration Method | Status & Access |
|---|---|---|
| **Greenhouse** | Public Boards API | 🟢 **Live** (Public endpoint, no API key needed) |
| **Lever** | Postings REST API | 🟢 **Live** (Public endpoint, no API key needed) |
| **Arbeitnow** | Job Board API | 🟢 **Live** (Remote & tech listings) |
| **LinkedIn Jobs** | Direct URL & CSV Alerts | 🔵 **Ready** (Paste direct vacancy URL or upload CSV) |
| **Naukri.com** | Direct URL & CSV Alerts | 🔵 **Ready** (Paste direct vacancy URL or upload CSV) |
| **Custom Career Pages** | Universal Ingestor | 🟢 **Live** (Paste any employer vacancy URL) |

---

## 📊 How the Matching Engine Scores Jobs (0–100%)

The scoring engine evaluates jobs deterministically using 5 weighted pillars:
- **40% Skill Overlap**: Matches keywords and tools from your parsed resume against job requirements.
- **25% Role Relevance**: Weights alignment with your desired job titles.
- **20% Hard Eligibility**: Enforces experience limits and graduation batch compatibility.
- **10% Location Match**: Scores 100% for your selected preferred cities or remote roles.
- **5% Posting Freshness**: Favors roles published recently.

---

## ❓ Frequently Asked Questions & Troubleshooting

### Q: `'python'` is not recognized as an internal or external command?
**Fix:** Python is installed but not added to your system environment variables. Re-run the Python installer from [python.org](https://python.org), click **"Modify"**, and make sure to check **"Add Python to environment variables"**.

### Q: How do I switch to real live jobs instead of demo data?
**Fix:** In your `.env` file, change `DEMO_MODE=true` to `DEMO_MODE=false`. Or open the **Integrations** tab in the dashboard and toggle Demo Mode off.

### Q: Are paid API keys required?
**Fix:** No! JobPilot is 100% free and open-source. Hugging Face free tier tokens work out of the box, and if left blank, offline rule-based generation works seamlessly.

### Q: Is my resume and personal data safe?
**Fix:** Yes! Everything runs locally on your own machine. Your resume, database, and logs remain strictly inside your local SQLite database (`data/jobpilot.db`). Nothing is transmitted to external servers.

### Q: Can the agent run automatically every morning?
**Fix:** Yes! Open **Automation Settings** in the dashboard $\rightarrow$ Set your preferred time (e.g. 09:00 AM) $\rightarrow$ Click **"Activate Local Daily Automation"**.

---

## ⭐ Star the Project & Connect!

If this project helps your job search, please consider giving it a **Star on GitHub**!

- **GitHub Repository**: [https://github.com/mathicianrahul/AI-Agent-that-Apply-Job-Automatically-](https://github.com/mathicianrahul/AI-Agent-that-Apply-Job-Automatically-)
- **Developer**: Rahul Girase (AI/ML Engineer & Open Source Developer)
- **Contribute**: Feel free to fork, submit issues, or create pull requests to add new job platform scrapers!
