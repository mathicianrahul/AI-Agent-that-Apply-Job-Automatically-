CUSTOM_CSS = """
<style>
/* JobPilot AI - Premium Dark SaaS Theme */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}

/* Background & Main Container */
.stApp {
    background-color: #0B0F19;
    color: #F3F4F6;
}

/* Sidebar styling */
section[data-testid="stSidebar"] {
    background-color: #111827;
    border-right: 1px solid #1F2937;
}

section[data-testid="stSidebar"] .stRadio label {
    color: #9CA3AF !important;
    font-size: 0.95rem;
    font-weight: 500;
    padding: 6px 12px;
    border-radius: 6px;
    transition: all 0.2s ease;
}

section[data-testid="stSidebar"] .stRadio label:hover {
    color: #FFFFFF !important;
    background-color: #1F2937;
}

/* Cards & Containers */
.jobpilot-card {
    background: #111827;
    border: 1px solid #1F2937;
    border-radius: 10px;
    padding: 20px;
    margin-bottom: 16px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
}

.jobpilot-metric-card {
    background: linear-gradient(180deg, #161F30 0%, #111827 100%);
    border: 1px solid #1F2937;
    border-radius: 10px;
    padding: 18px;
    text-align: left;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
}

.metric-title {
    color: #9CA3AF;
    font-size: 0.85rem;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 6px;
}

.metric-value {
    color: #FFFFFF;
    font-size: 1.85rem;
    font-weight: 700;
    line-height: 1.2;
}

.metric-sub {
    color: #38BDF8;
    font-size: 0.8rem;
    font-weight: 500;
    margin-top: 4px;
}

/* Badges / Pills */
.pill-skill {
    display: inline-block;
    background-color: rgba(59, 130, 246, 0.15);
    color: #60A5FA;
    border: 1px solid rgba(59, 130, 246, 0.3);
    border-radius: 9999px;
    padding: 2px 10px;
    font-size: 0.75rem;
    font-weight: 500;
    margin: 2px 4px 2px 0;
}

.pill-missing {
    display: inline-block;
    background-color: rgba(239, 68, 68, 0.12);
    color: #F87171;
    border: 1px solid rgba(239, 68, 68, 0.25);
    border-radius: 9999px;
    padding: 2px 10px;
    font-size: 0.75rem;
    font-weight: 500;
    margin: 2px 4px 2px 0;
}

.pill-eligible {
    display: inline-block;
    background-color: rgba(16, 185, 129, 0.15);
    color: #34D399;
    border: 1px solid rgba(16, 185, 129, 0.3);
    border-radius: 6px;
    padding: 3px 10px;
    font-size: 0.8rem;
    font-weight: 600;
}

.pill-ineligible {
    display: inline-block;
    background-color: rgba(239, 68, 68, 0.15);
    color: #F87171;
    border: 1px solid rgba(239, 68, 68, 0.3);
    border-radius: 6px;
    padding: 3px 10px;
    font-size: 0.8rem;
    font-weight: 600;
}

.pill-demo {
    display: inline-block;
    background-color: rgba(139, 92, 246, 0.2);
    color: #A78BFA;
    border: 1px solid rgba(139, 92, 246, 0.4);
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: uppercase;
}

.pill-live {
    display: inline-block;
    background-color: rgba(16, 185, 129, 0.2);
    color: #10B981;
    border: 1px solid rgba(16, 185, 129, 0.4);
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: uppercase;
}

/* Headers */
h1, h2, h3, h4 {
    color: #FFFFFF !important;
    font-weight: 600;
}

/* Primary Buttons */
.stButton>button {
    border-radius: 8px;
    font-weight: 600;
    transition: all 0.2s ease;
}

.stButton>button[kind="primary"] {
    background: linear-gradient(135deg, #3B82F6 0%, #2563EB 100%);
    border: none;
    color: #FFFFFF;
}

.stButton>button[kind="primary"]:hover {
    background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%);
    box-shadow: 0 4px 12px rgba(37, 99, 235, 0.35);
}

/* Dataframe & Tables */
[data-testid="stDataFrame"] {
    border: 1px solid #1F2937;
    border-radius: 8px;
    overflow: hidden;
}
</style>
"""


def render_header(title: str, subtitle: str, badge_text: str = "JobPilot AI v1.0"):
    return f"""
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; border-bottom: 1px solid #1F2937; padding-bottom: 16px;">
        <div>
            <h1 style="margin: 0; font-size: 1.75rem; color: #FFFFFF;">{title}</h1>
            <p style="margin: 4px 0 0 0; color: #9CA3AF; font-size: 0.95rem;">{subtitle}</p>
        </div>
        <div>
            <span style="background: rgba(59, 130, 246, 0.15); color: #60A5FA; border: 1px solid rgba(59, 130, 246, 0.3); padding: 4px 12px; border-radius: 9999px; font-size: 0.8rem; font-weight: 600;">
                {badge_text}
            </span>
        </div>
    </div>
    """
