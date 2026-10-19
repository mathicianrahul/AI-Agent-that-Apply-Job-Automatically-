import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    HRFlowable,
)
from reportlab.pdfgen import canvas

PDF_FILENAME = "JobPilot_AI_Setup_Guide.pdf"

class NumberedCanvas(canvas.Canvas):
    """Adds running headers and page numbers to all pages."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(colors.HexColor("#64748B"))
        
        # Header (Pages 2+)
        if self._pageNumber > 1:
            self.drawString(54, 11 * 72 - 32, "JobPilot AI — Complete Setup & Quickstart Guide")
            self.setFont("Helvetica", 8)
            self.drawRightString(8.5 * 72 - 54, 11 * 72 - 32, "github.com/mathicianrahul/AI-Agent-that-Apply-Job-Automatically-")
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.5)
            self.line(54, 11 * 72 - 38, 8.5 * 72 - 54, 11 * 72 - 38)
            
        # Footer (All pages)
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))
        footer_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(8.5 * 72 - 54, 25, footer_text)
        self.drawString(54, 25, "JobPilot AI • Personal AI Job Application Agent • Free & Open Source")
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.5)
        self.line(54, 35, 8.5 * 72 - 54, 35)
        
        self.restoreState()


def build_pdf():
    doc = SimpleDocTemplate(
        PDF_FILENAME,
        pagesize=letter,
        leftMargin=50,
        rightMargin=50,
        topMargin=46,
        bottomMargin=46,
    )

    styles = getSampleStyleSheet()

    primary_color = colors.HexColor("#0F172A")
    accent_blue = colors.HexColor("#2563EB")
    code_bg = colors.HexColor("#F8FAFC")
    callout_bg = colors.HexColor("#EFF6FF")

    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=22,
        leading=26,
        textColor=primary_color,
    )

    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10.5,
        leading=14,
        textColor=colors.HexColor("#475569"),
    )

    h1_style = ParagraphStyle(
        "SectionH1",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12.5,
        leading=16,
        textColor=primary_color,
        spaceBefore=8,
        spaceAfter=4,
    )

    h2_style = ParagraphStyle(
        "SectionH2",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=13,
        textColor=accent_blue,
        spaceBefore=6,
        spaceAfter=3,
    )

    body_style = ParagraphStyle(
        "BodyDark",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#1E293B"),
    )

    bullet_style = ParagraphStyle(
        "BulletText",
        parent=body_style,
        leftIndent=12,
        firstLineIndent=-8,
        spaceAfter=2,
    )

    code_style = ParagraphStyle(
        "CodeText",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#0F172A"),
    )

    callout_style = ParagraphStyle(
        "CalloutText",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.8,
        leading=12.5,
        textColor=colors.HexColor("#1E3A8A"),
    )

    story = []

    # ==========================
    # PAGE 1: HEADER & GETTING STARTED
    # ==========================
    header_table_data = [
        [
            Paragraph("<b>JobPilot AI</b>", title_style),
            Paragraph("<font color='#2563EB'><b>v1.0 • OPEN SOURCE</b></font>", ParagraphStyle("RAlign", parent=subtitle_style, alignment=2)),
        ],
        [
            Paragraph("The Personal AI Job Application Agent That Discovers, Matches & Drafts Applications For You", subtitle_style),
            Paragraph("<b>Author:</b> Rahul Girase", ParagraphStyle("Author", parent=subtitle_style, alignment=2)),
        ],
    ]
    header_table = Table(header_table_data, colWidths=[362, 150])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(header_table)
    story.append(HRFlowable(width="100%", thickness=1.5, color=accent_blue, spaceBefore=4, spaceAfter=8))

    # Introduction Callout
    intro_p = Paragraph(
        "<b>What is JobPilot AI?</b> An autonomous, production-grade agentic AI assistant. It continuously scans 10+ career "
        "sources (Greenhouse, Lever, Arbeitnow, LinkedIn, Naukri), extracts requirements, matches jobs against "
        "<b>your</b> skills and graduation year, and prepares tailored cover letters with a strict <b>Human-in-the-Loop</b> "
        "review model. No application is ever submitted without your explicit 1-click verification.",
        callout_style,
    )
    intro_box = Table([[intro_p]], colWidths=[512])
    intro_box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), callout_bg),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#BFDBFE")),
        ("LINEBEFORE", (0, 0), (0, -1), 3.5, accent_blue),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(intro_box)
    story.append(Spacer(1, 6))

    # Prerequisites
    story.append(Paragraph("System Prerequisites", h1_style))
    story.append(Paragraph("• <b>Python 3.11, 3.12, 3.13, or 3.14:</b> Download free from <font color='#2563EB'><u>python.org</u></font>. (<i>Crucial: check 'Add Python to PATH' during installation</i>).", bullet_style))
    story.append(Paragraph("• <b>Git:</b> Download from <font color='#2563EB'><u>git-scm.com</u></font> (or download ZIP from GitHub).", bullet_style))
    story.append(Spacer(1, 6))

    # Step 1: Clone
    story.append(Paragraph("Step 1: Clone or Download the Project", h1_style))
    story.append(Paragraph("Open your Terminal or PowerShell and run:", body_style))
    story.append(Spacer(1, 2))
    
    code_s1 = Paragraph(
        "git clone https://github.com/mathicianrahul/AI-Agent-that-Apply-Job-Automatically-.git<br/>"
        "cd AI-Agent-that-Apply-Job-Automatically-",
        code_style,
    )
    box_s1 = Table([[code_s1]], colWidths=[512])
    box_s1.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), code_bg),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(box_s1)
    story.append(Spacer(1, 6))

    # Step 2: 1-Click Launch
    story.append(Paragraph("Step 2: Start with One-Click (Recommended)", h1_style))
    story.append(Paragraph("We built zero-hassle launchers that set up the virtual environment, install requirements, and run the dashboard automatically:", body_style))
    story.append(Spacer(1, 3))

    launcher_table_data = [
        [
            Paragraph("<b>Windows:</b>", body_style),
            Paragraph("Double-click <b><font color='#2563EB'>run.bat</font></b> in the project folder (or type <code>.\\run.bat</code> in PowerShell).", body_style),
        ],
        [
            Paragraph("<b>Mac / Linux:</b>", body_style),
            Paragraph("Open Terminal and run <code>chmod +x run.sh &amp;&amp; ./run.sh</code>.", body_style),
        ],
    ]
    t_launchers = Table(launcher_table_data, colWidths=[100, 412])
    t_launchers.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(t_launchers)
    story.append(Spacer(1, 4))

    note_launch = Paragraph(
        "<b>What happens automatically:</b> The launcher detects Python, creates a dedicated virtual environment (<code>venv</code>), installs dependencies from <code>requirements.txt</code>, sets up <code>.env</code>, and starts the web dashboard at <b>http://localhost:8501</b>.",
        ParagraphStyle("Note", parent=body_style, fontSize=8.5, textColor=colors.HexColor("#475569")),
    )
    story.append(note_launch)
    story.append(Spacer(1, 5))

    story.append(Paragraph("<i>Manual Command-Line Alternative:</i>", h2_style))
    code_manual = Paragraph(
        "python -m venv venv &amp;&amp; .\\venv\\Scripts\\activate  # (Mac/Linux: source venv/bin/activate)<br/>"
        "pip install -r requirements.txt<br/>"
        "python -m streamlit run app.py",
        code_style,
    )
    box_manual = Table([[code_manual]], colWidths=[512])
    box_manual.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), code_bg),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(box_manual)

    story.append(PageBreak())

    # ==========================
    # PAGE 2: PERSONALIZATION & WORKFLOW
    # ==========================
    story.append(Paragraph("Step 3: Personalize Your Profile in the Dashboard", h1_style))
    story.append(Paragraph("Open <b>http://localhost:8501</b> in your browser and complete these 2 quick steps:", body_style))
    story.append(Spacer(1, 4))

    steps_data = [
        [
            Paragraph("<b>1. Resume Manager</b>", body_style),
            Paragraph("Navigate to <b>Resume Manager</b> &rarr; Upload your resume (PDF or DOCX). The parser automatically extracts all technical skills, projects, and education into your profile.", body_style),
        ],
        [
            Paragraph("<b>2. Candidate Profile</b>", body_style),
            Paragraph("Navigate to <b>Candidate Profile</b> tab. Fill in your <b>Full Name</b>, <b>Email</b>, <b>Graduation Year</b> (e.g. 2025, 2026, 2027), <b>Preferred Locations</b> (e.g. <i>Bangalore, Pune, Mumbai, Remote</i>), and <b>Target Roles</b> (e.g. <i>AI/ML Engineer, Data Scientist, Python Developer</i>). Click <b>'Save Profile Settings'</b>.", body_style),
        ],
    ]
    t_steps = Table(steps_data, colWidths=[130, 382])
    t_steps.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFFFFF")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(t_steps)
    story.append(Spacer(1, 8))

    # Step 4: Environment settings
    story.append(Paragraph("Step 4: AI LLM Token & Live Job Search (Optional)", h1_style))
    story.append(Paragraph("JobPilot works completely offline with high-accuracy rule-based fallbacks. To activate live AI cover letter drafting and daily email digests, configure your <code>.env</code> file:", body_style))
    story.append(Spacer(1, 3))

    code_env = Paragraph(
        "# Free Hugging Face Token for LLM Cover Letter Drafting:<br/>"
        "HF_TOKEN=hf_your_free_token_here<br/>"
        "HF_MODEL=meta-llama/Llama-3.2-3B-Instruct<br/><br/>"
        "# Your Email for Daily Job Application Alerts:<br/>"
        "DIGEST_RECIPIENT_EMAIL=your_email@gmail.com<br/><br/>"
        "# Live Internet Scan vs Demo Mode:<br/>"
        "DEMO_MODE=false   # Set to 'false' to search real live company job boards!",
        code_style,
    )
    box_env = Table([[code_env]], colWidths=[512])
    box_env.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), code_bg),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(box_env)
    story.append(Spacer(1, 3))
    story.append(Paragraph("<i>Get a free Hugging Face token at <b>huggingface.co/settings/tokens</b> (no credit card required).</i>", ParagraphStyle("Tip", parent=body_style, fontSize=8, textColor=accent_blue)))
    story.append(Spacer(1, 8))

    # Step 5: Run Workflow
    story.append(Paragraph("Step 5: Run Discovery & Review Application Drafts", h1_style))
    story.append(Paragraph("• Click <b>'Run Agent Discovery'</b> in the sidebar to execute the 13-stage LangGraph workflow.", bullet_style))
    story.append(Paragraph("• The agent scores all discovered opportunities (0-100%) against your skills, preferred cities, and graduation year.", bullet_style))
    story.append(Paragraph("• Under <b>Application Review</b>: Inspect drafted cover letters and Q&A answers. Click <b>Approve</b>, <b>Edit</b>, or <b>Reject</b>.", bullet_style))
    story.append(Paragraph("• Click <b>'Open Original Job URL'</b> to verify and submit directly on the company's verified ATS.", bullet_style))
    story.append(Spacer(1, 8))

    # Supported Platforms
    story.append(Paragraph("Supported Discovery Channels & Career Sources", h1_style))
    platforms_data = [
        [Paragraph("<b>Platform</b>", body_style), Paragraph("<b>Method</b>", body_style), Paragraph("<b>Status & Access</b>", body_style)],
        [Paragraph("Greenhouse", body_style), Paragraph("Public Boards API", body_style), Paragraph("<font color='#16A34A'><b>Live</b></font> (Public endpoint, no auth needed)", body_style)],
        [Paragraph("Lever", body_style), Paragraph("Postings REST API", body_style), Paragraph("<font color='#16A34A'><b>Live</b></font> (Public endpoint, no auth needed)", body_style)],
        [Paragraph("Arbeitnow", body_style), Paragraph("Job Board API", body_style), Paragraph("<font color='#16A34A'><b>Live</b></font> (Remote & tech listings)", body_style)],
        [Paragraph("LinkedIn / Naukri", body_style), Paragraph("Direct URL & CSV Importer", body_style), Paragraph("<font color='#2563EB'><b>Ready</b></font> (Paste vacancy link or upload CSV)", body_style)],
        [Paragraph("Custom Career Pages", body_style), Paragraph("Universal Ingestor", body_style), Paragraph("<font color='#16A34A'><b>Live</b></font> (Paste any employer URL)", body_style)],
    ]
    t_platforms = Table(platforms_data, colWidths=[120, 152, 240])
    t_platforms.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F1F5F9")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(t_platforms)

    story.append(PageBreak())

    # ==========================
    # PAGE 3: FAQ & CTA
    # ==========================
    story.append(Paragraph("Frequently Asked Questions & Troubleshooting", h1_style))
    story.append(Spacer(1, 3))

    faq_data = [
        [
            Paragraph("<b>'python' is not recognized in terminal?</b>", body_style),
            Paragraph("Re-run the Python installer from <font color='#2563EB'><u>python.org</u></font>, click 'Modify', and check <i>'Add Python to environment variables (PATH)'</i>.", body_style),
        ],
        [
            Paragraph("<b>How do I switch to live jobs instead of demo data?</b>", body_style),
            Paragraph("In <code>.env</code>, set <code>DEMO_MODE=false</code>. Or go to the <b>Integrations</b> tab in the dashboard and toggle Demo Mode off.", body_style),
        ],
        [
            Paragraph("<b>Are paid API keys required?</b>", body_style),
            Paragraph("No! JobPilot is 100% free to use. Hugging Face free tokens work out of the box, and if you leave it blank, offline rule-based generation works seamlessly.", body_style),
        ],
        [
            Paragraph("<b>Is my resume and private data safe?</b>", body_style),
            Paragraph("Yes! Everything runs locally on your PC. Your resume, database, and logs remain strictly inside your local <code>data/jobpilot.db</code> file.", body_style),
        ],
        [
            Paragraph("<b>Can the agent run automatically every morning?</b>", body_style),
            Paragraph("Yes! Open <b>Automation Settings</b> &rarr; Set time (e.g. 09:00 AM) &rarr; Click <i>'Activate Local Daily Automation'</i>.", body_style),
        ],
    ]
    t_faq = Table(faq_data, colWidths=[180, 332])
    t_faq.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFFFFF")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(t_faq)
    story.append(Spacer(1, 14))

    # Architecture Overview Callout
    arch_p = Paragraph(
        "<b>Deterministic Multi-Factor Scoring Architecture (0–100%):</b><br/>"
        "• <b>40% Skill Overlap:</b> Semantic keyword and technical skill match against your uploaded resume.<br/>"
        "• <b>25% Role Relevance:</b> Title alignment with your selected target roles.<br/>"
        "• <b>20% Hard Eligibility:</b> Strict experience limit and graduation batch verification.<br/>"
        "• <b>10% Location Match:</b> Evaluates against your selected preferred cities or remote preference.<br/>"
        "• <b>5% Posting Freshness:</b> Recency decay favoring recently published vacancies.",
        ParagraphStyle("ArchNote", parent=body_style, fontSize=8.5, leading=12.5, textColor=colors.HexColor("#334155")),
    )
    arch_box = Table([[arch_p]], colWidths=[512])
    arch_box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(arch_box)
    story.append(Spacer(1, 14))

    # Final CTA Banner
    cta_title = Paragraph("<b>Star the Project &amp; Connect!</b>", ParagraphStyle("CTATitle", parent=body_style, fontName="Helvetica-Bold", fontSize=11, textColor=accent_blue))
    cta_body = Paragraph(
        "If this agent helps your job hunt, please give it a <b>Star on GitHub</b>!<br/>"
        "• <b>GitHub Repo:</b> <font color='#2563EB'><u>https://github.com/mathicianrahul/AI-Agent-that-Apply-Job-Automatically-</u></font><br/>"
        "• <b>Developer:</b> Rahul Girase • AIML Engineer &amp; Open Source Developer<br/>"
        "• <b>Contribute:</b> Feel free to fork, submit issues, or add new platform scrapers!",
        ParagraphStyle("CTABody", parent=body_style, fontSize=8.8, leading=14),
    )
    cta_box = Table([[cta_title], [cta_body]], colWidths=[512])
    cta_box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F0FDF4")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#86EFAC")),
        ("LINEBEFORE", (0, 0), (0, -1), 3.5, colors.HexColor("#22C55E")),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(cta_box)

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"[SUCCESS] PDF generated: {PDF_FILENAME}")

if __name__ == "__main__":
    build_pdf()
