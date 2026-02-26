"""UI utilities and styling for AI Risk Navigator."""
from typing import List

import streamlit as st


def inject_custom_css():
    """Inject custom CSS for a clean, modern UI."""
    st.markdown("""
    <style>
    /* ================================================================
       AI RISK NAVIGATOR — Design System
       ================================================================ */

    /* ---------- CSS Variables (Design Tokens) ---------- */
    :root {
        --nav-primary:    #1e3a5f;
        --nav-accent:     #3b82f6;
        --nav-accent-rgb: 59, 130, 246;
        --nav-success:    #10b981;
        --nav-warning:    #f59e0b;
        --nav-danger:     #ef4444;
        --nav-surface:    #ffffff;
        --nav-surface-2:  #f8fafc;
        --nav-surface-3:  #f1f5f9;
        --nav-border:     #e2e8f0;
        --nav-border-2:   #cbd5e1;
        --nav-text:       #1e293b;
        --nav-text-2:     #475569;
        --nav-text-3:     #94a3b8;
        --nav-radius:     12px;
        --nav-radius-sm:  8px;
        --nav-radius-lg:  16px;
        --nav-shadow-sm:  0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04);
        --nav-shadow:     0 4px 6px -1px rgba(0,0,0,0.07), 0 2px 4px -2px rgba(0,0,0,0.05);
        --nav-shadow-lg:  0 10px 15px -3px rgba(0,0,0,0.08), 0 4px 6px -4px rgba(0,0,0,0.04);
        --nav-transition:  all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    }

    /* ---------- Global ---------- */
    .main { padding-top: 1rem; }
    .main .block-container { max-width: 1200px; padding: 1rem 2rem 3rem 2rem; }

    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
    }
    section[data-testid="stSidebar"] > div:first-child { padding-top: 1.5rem; }
    section[data-testid="stSidebar"] .stMarkdown p,
    section[data-testid="stSidebar"] .stMarkdown li,
    section[data-testid="stSidebar"] .stMarkdown h1,
    section[data-testid="stSidebar"] .stMarkdown h2,
    section[data-testid="stSidebar"] .stMarkdown h3,
    section[data-testid="stSidebar"] .stMarkdown h4,
    section[data-testid="stSidebar"] .stMarkdown h5,
    section[data-testid="stSidebar"] .stCaption p {
        color: #cbd5e1 !important;
    }
    section[data-testid="stSidebar"] .stMarkdown a {
        color: #93c5fd !important;
    }
    section[data-testid="stSidebar"] hr {
        border-color: rgba(255,255,255,0.1);
    }
    section[data-testid="stSidebar"] .stRadio label span {
        color: #e2e8f0 !important;
        font-weight: 500;
    }
    section[data-testid="stSidebar"] .stRadio label[data-checked="true"] span,
    section[data-testid="stSidebar"] .stRadio label:has(input:checked) span {
        color: #ffffff !important;
        font-weight: 700;
    }
    section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] {
        color: #e2e8f0;
    }

    /* ---------- Typography ---------- */
    h1 {
        font-weight: 800 !important;
        letter-spacing: -0.03em;
        color: var(--nav-text) !important;
        font-size: 2rem !important;
        line-height: 1.2 !important;
    }
    h2 {
        font-weight: 700 !important;
        margin-top: 1.5rem;
        color: var(--nav-text) !important;
        font-size: 1.4rem !important;
    }
    h3 {
        font-weight: 600 !important;
        color: var(--nav-text) !important;
    }
    h4 {
        font-weight: 600 !important;
        color: var(--nav-text-2) !important;
        font-size: 1rem !important;
    }

    /* ---------- Metric cards ---------- */
    [data-testid="stMetric"] {
        background: var(--nav-surface);
        border: 1px solid var(--nav-border);
        border-radius: var(--nav-radius);
        padding: 1rem 1.25rem;
        box-shadow: var(--nav-shadow-sm);
        transition: var(--nav-transition);
    }
    [data-testid="stMetric"]:hover {
        box-shadow: var(--nav-shadow);
        border-color: var(--nav-border-2);
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.78rem !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: var(--nav-text-3) !important;
    }
    [data-testid="stMetricLabel"] p { color: var(--nav-text-3) !important; }
    [data-testid="stMetricValue"] {
        font-size: 1.9rem !important;
        font-weight: 800 !important;
        color: var(--nav-primary) !important;
    }
    [data-testid="stMetricValue"] div { color: var(--nav-primary) !important; }

    /* ---------- Buttons ---------- */
    .stButton > button {
        border-radius: var(--nav-radius-sm) !important;
        font-weight: 600 !important;
        transition: var(--nav-transition) !important;
        letter-spacing: 0.01em;
    }
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: var(--nav-shadow) !important;
    }
    .stButton > button:active {
        transform: translateY(0);
    }
    .stButton > button[kind="primary"],
    .stButton > button[data-testid="stBaseButton-primary"] {
        background: linear-gradient(135deg, var(--nav-accent) 0%, #2563eb 100%) !important;
        border: none !important;
        color: white !important;
    }
    .stButton > button[kind="primary"]:hover,
    .stButton > button[data-testid="stBaseButton-primary"]:hover {
        box-shadow: 0 4px 14px rgba(var(--nav-accent-rgb), 0.4) !important;
    }

    /* ---------- Step indicator ---------- */
    .step-bar {
        display: flex;
        align-items: center;
        gap: 0;
        margin: 0.5rem 0 1.5rem 0;
        padding: 1rem 1.5rem;
        background: var(--nav-surface);
        border: 1px solid var(--nav-border);
        border-radius: var(--nav-radius-lg);
        box-shadow: var(--nav-shadow-sm);
    }
    .step-item {
        display: flex;
        flex-direction: column;
        align-items: center;
        flex: 0 0 auto;
        position: relative;
        min-width: 60px;
    }
    .step-circle {
        width: 38px; height: 38px;
        border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-weight: 700; font-size: 0.85rem;
        z-index: 2;
        transition: var(--nav-transition);
    }
    .step-circle.done {
        background: var(--nav-success);
        color: #fff;
        box-shadow: 0 2px 8px rgba(16, 185, 129, 0.3);
    }
    .step-circle.active {
        background: var(--nav-accent);
        color: #fff;
        box-shadow: 0 0 0 4px rgba(var(--nav-accent-rgb), 0.15), 0 2px 8px rgba(var(--nav-accent-rgb), 0.3);
        animation: stepPulse 2s ease-in-out infinite;
    }
    @keyframes stepPulse {
        0%, 100% { box-shadow: 0 0 0 4px rgba(var(--nav-accent-rgb), 0.15); }
        50%      { box-shadow: 0 0 0 8px rgba(var(--nav-accent-rgb), 0.08); }
    }
    .step-circle.future {
        background: var(--nav-surface-3);
        color: var(--nav-text-3);
        border: 2px solid var(--nav-border);
    }
    .step-label {
        margin-top: 8px;
        font-size: 0.72rem;
        font-weight: 600;
        text-align: center;
        white-space: nowrap;
        letter-spacing: 0.02em;
    }
    .step-label.active { color: var(--nav-accent); }
    .step-label.done   { color: var(--nav-success); }
    .step-label.future { color: var(--nav-text-3); }
    .step-connector {
        flex: 1; height: 3px;
        margin-top: -20px;
        z-index: 1;
        border-radius: 2px;
        min-width: 20px;
    }
    .step-connector.done   { background: linear-gradient(90deg, var(--nav-success), var(--nav-success)); }
    .step-connector.future { background: var(--nav-border); }

    /* ---------- Question cards ---------- */
    .q-card {
        background: var(--nav-surface);
        border: 1px solid var(--nav-border);
        border-radius: var(--nav-radius);
        padding: 1.25rem 1.5rem;
        margin-bottom: 1rem;
        transition: var(--nav-transition);
    }
    .q-card:hover {
        border-color: var(--nav-border-2);
        box-shadow: var(--nav-shadow-sm);
    }
    .q-card.answered {
        border-left: 4px solid var(--nav-success);
    }
    .q-number {
        font-size: 0.7rem;
        font-weight: 700;
        color: var(--nav-text-3);
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 0.25rem;
    }

    /* ---------- Result cards ---------- */
    .result-card {
        background: var(--nav-surface);
        border: 1px solid var(--nav-border);
        border-radius: var(--nav-radius);
        padding: 1.25rem;
        margin-bottom: 0.75rem;
        box-shadow: var(--nav-shadow-sm);
        transition: var(--nav-transition);
    }
    .result-card:hover {
        box-shadow: var(--nav-shadow);
    }

    /* ---------- Tier badge ---------- */
    .tier-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 0.4rem 1.1rem;
        border-radius: 24px;
        font-weight: 700;
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .tier-low          { background: #dcfce7; color: #166534; }
    .tier-medium       { background: #fef3c7; color: #92400e; }
    .tier-high         { background: #fed7aa; color: #9a3412; }
    .tier-unacceptable { background: #fecaca; color: #991b1b; }

    /* ---------- Tag chips ---------- */
    .chip {
        display: inline-block;
        padding: 0.2rem 0.65rem;
        background: #eff6ff;
        color: #1d4ed8;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 600;
        margin: 0.15rem 0.15rem;
        letter-spacing: 0.01em;
    }
    .chip.green  { background: #f0fdf4; color: #15803d; }
    .chip.orange { background: #fff7ed; color: #c2410c; }
    .chip.purple { background: #faf5ff; color: #7e22ce; }
    .chip.red    { background: #fef2f2; color: #b91c1c; }
    .chip.slate  { background: #f1f5f9; color: #475569; }

    /* ---------- Prefilled sections ---------- */
    .prefill-banner {
        background: linear-gradient(135deg, #f0fdf4 0%, #ecfdf5 100%);
        border: 1px solid #bbf7d0;
        border-left: 4px solid var(--nav-success);
        border-radius: var(--nav-radius-sm);
        padding: 0.75rem 1rem;
        margin-bottom: 1rem;
        font-size: 0.88rem;
        color: #15803d;
    }
    .prefill-badge {
        background: #f0fdf4;
        border: 1px solid #bbf7d0;
        border-radius: 6px;
        padding: 0.4rem 0.75rem;
        margin-bottom: 0.5rem;
        font-size: 0.82rem;
        color: #15803d;
    }
    .q-card.prefilled {
        border-left: 4px solid var(--nav-success);
        background: #f0fdf4;
    }

    /* ---------- Hero card ---------- */
    .hero-card {
        background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 50%, #1e40af 100%);
        border-radius: var(--nav-radius-lg);
        padding: 2.5rem 2.5rem;
        margin-bottom: 1.5rem;
        color: white;
        position: relative;
        overflow: hidden;
    }
    .hero-card::before {
        content: '';
        position: absolute;
        top: -50%;
        right: -20%;
        width: 400px;
        height: 400px;
        background: radial-gradient(circle, rgba(59,130,246,0.15) 0%, transparent 70%);
        pointer-events: none;
    }
    .hero-card h1 {
        color: white !important;
        font-size: 2.2rem !important;
        margin-bottom: 0.5rem;
    }
    .hero-card p {
        color: #94a3b8 !important;
        font-size: 1.05rem;
        margin: 0;
        line-height: 1.6;
    }

    /* ---------- Stat card ---------- */
    .stat-card {
        background: var(--nav-surface);
        border: 1px solid var(--nav-border);
        border-radius: var(--nav-radius);
        padding: 1.25rem 1.5rem;
        text-align: center;
        box-shadow: var(--nav-shadow-sm);
        transition: var(--nav-transition);
    }
    .stat-card:hover {
        box-shadow: var(--nav-shadow);
        transform: translateY(-2px);
    }
    .stat-card .stat-icon {
        font-size: 1.6rem;
        margin-bottom: 0.3rem;
    }
    .stat-card .stat-value {
        font-size: 2rem;
        font-weight: 800;
        color: var(--nav-primary);
        line-height: 1.2;
    }
    .stat-card .stat-label {
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: var(--nav-text-3);
        margin-top: 0.25rem;
    }

    /* ---------- Info card ---------- */
    .info-card {
        background: var(--nav-surface);
        border: 1px solid var(--nav-border);
        border-radius: var(--nav-radius);
        padding: 1.5rem;
        margin-bottom: 0.75rem;
        transition: var(--nav-transition);
    }
    .info-card:hover {
        box-shadow: var(--nav-shadow-sm);
        border-color: var(--nav-border-2);
    }
    .info-card .card-title {
        font-weight: 700;
        font-size: 1rem;
        color: var(--nav-text);
        margin-bottom: 0.35rem;
    }
    .info-card .card-desc {
        font-size: 0.88rem;
        color: var(--nav-text-2);
        line-height: 1.5;
    }

    /* ---------- Section header ---------- */
    .section-header {
        display: flex;
        align-items: center;
        gap: 10px;
        margin: 1.5rem 0 1rem 0;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid var(--nav-surface-3);
    }
    .section-header .section-icon {
        font-size: 1.3rem;
    }
    .section-header .section-title {
        font-weight: 700;
        font-size: 1.1rem;
        color: var(--nav-text);
    }

    /* ---------- Inventory form ---------- */
    .stSelectbox > div > div,
    .stMultiSelect > div > div {
        border-radius: var(--nav-radius-sm) !important;
    }
    div[data-testid="stExpander"] {
        border-radius: var(--nav-radius) !important;
        border: 1px solid var(--nav-border) !important;
        margin-bottom: 0.5rem;
        box-shadow: var(--nav-shadow-sm);
    }
    div[data-testid="stExpander"]:hover {
        border-color: var(--nav-border-2) !important;
    }
    .stTextInput > div > div,
    .stTextArea > div > div > textarea {
        border-radius: var(--nav-radius-sm) !important;
    }

    /* ---------- Tabs ---------- */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        background: var(--nav-surface-3);
        border-radius: var(--nav-radius-sm);
        padding: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 6px !important;
        font-weight: 600;
        font-size: 0.85rem;
        padding: 0.5rem 1rem;
    }
    .stTabs [aria-selected="true"] {
        background: var(--nav-surface) !important;
        box-shadow: var(--nav-shadow-sm);
    }

    /* ---------- Progress bar ---------- */
    .stProgress > div > div > div {
        background: linear-gradient(90deg, var(--nav-accent), #2563eb) !important;
        border-radius: 4px;
    }

    /* ---------- Divider override ---------- */
    hr {
        border: none;
        height: 1px;
        background: var(--nav-surface-3);
        margin: 1.5rem 0;
    }

    /* ---------- Page title bar ---------- */
    .page-title-bar {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 0.5rem;
    }
    .page-title-bar .page-icon {
        font-size: 1.8rem;
    }
    .page-title-bar .page-title {
        font-size: 1.8rem;
        font-weight: 800;
        color: var(--nav-text);
        letter-spacing: -0.02em;
    }
    .page-subtitle {
        color: var(--nav-text-2);
        font-size: 0.95rem;
        margin-bottom: 1.5rem;
        line-height: 1.5;
    }

    /* ---------- Sidebar logo ---------- */
    .sidebar-logo {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 0.25rem 0 0.75rem 0;
    }
    .sidebar-logo .logo-icon {
        width: 36px;
        height: 36px;
        background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.2rem;
        box-shadow: 0 2px 8px rgba(59,130,246,0.3);
    }
    .sidebar-logo .logo-text {
        font-size: 1.1rem;
        font-weight: 700;
        color: #f1f5f9;
        letter-spacing: -0.01em;
    }
    .sidebar-logo .logo-sub {
        font-size: 0.65rem;
        color: #64748b;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }
    </style>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Step indicator
# ---------------------------------------------------------------------------

def render_step_indicator(steps: List[str], current: int):
    """Render a horizontal step indicator. `current` is 0-based."""
    parts: list[str] = []
    parts.append('<div class="step-bar">')
    for i, label in enumerate(steps):
        if i < current:
            cls = "done"
            icon = "&#10003;"
        elif i == current:
            cls = "active"
            icon = str(i + 1)
        else:
            cls = "future"
            icon = str(i + 1)
        parts.append(
            f'<div class="step-item">'
            f'<div class="step-circle {cls}">{icon}</div>'
            f'<div class="step-label {cls}">{label}</div>'
            f'</div>'
        )
        if i < len(steps) - 1:
            conn_cls = "done" if i < current else "future"
            parts.append(f'<div class="step-connector {conn_cls}"></div>')
    parts.append("</div>")
    st.markdown("".join(parts), unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Page header
# ---------------------------------------------------------------------------

def render_page_header(icon: str, title: str, subtitle: str = ""):
    """Render a consistent page header with icon and subtitle."""
    st.markdown(
        f'<div class="page-title-bar">'
        f'<span class="page-icon">{icon}</span>'
        f'<span class="page-title">{title}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
    if subtitle:
        st.markdown(f'<div class="page-subtitle">{subtitle}</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Stat cards
# ---------------------------------------------------------------------------

def render_stat_cards(stats: list[dict]):
    """Render a row of stat cards. Each dict: icon, value, label."""
    cols = st.columns(len(stats))
    for col, s in zip(cols, stats):
        with col:
            st.markdown(
                f'<div class="stat-card">'
                f'<div class="stat-icon">{s.get("icon", "")}</div>'
                f'<div class="stat-value">{s.get("value", 0)}</div>'
                f'<div class="stat-label">{s.get("label", "")}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )


# ---------------------------------------------------------------------------
# Tier badge
# ---------------------------------------------------------------------------

def render_tier_badge(label: str):
    """Render a colored tier badge."""
    tier_icons = {"low": "●", "medium": "●", "high": "●", "unacceptable": "●"}
    css_cls = f"tier-{label.lower()}" if label.lower() in ("low", "medium", "high", "unacceptable") else "tier-low"
    icon = tier_icons.get(label.lower(), "●")
    st.markdown(f'<span class="tier-badge {css_cls}">{icon} {label.upper()}</span>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Chips / tags
# ---------------------------------------------------------------------------

def render_chips(items: List[str], color: str = "blue"):
    """Render a row of small tag chips."""
    if not items:
        return
    chip_cls = f"chip {color}" if color != "blue" else "chip"
    html = " ".join(f'<span class="{chip_cls}">{item}</span>' for item in items)
    st.markdown(html, unsafe_allow_html=True)


def render_info_box(message: str, type: str = "info"):
    icon_map = {"info": "ℹ️", "success": "✅", "warning": "⚠️", "error": "❌"}
    icon = icon_map.get(type, "ℹ️")
    fn = {"info": st.info, "success": st.success, "warning": st.warning, "error": st.error}.get(type, st.info)
    fn(f"{icon} {message}")


def reset_assessment():
    """Clear all assessment-related session state and rewind to step 0."""
    _ASSESSMENT_KEYS = {
        "answers": {},
        "selected_personas": [],
        "selected_use_cases": [],
        "vayu_result": None,
        "relevant_risks": [],
        "recommended_controls": [],
        "_assessment_record_id": None,
    }
    for key, default in _ASSESSMENT_KEYS.items():
        st.session_state[key] = default
    st.session_state.assessment_step = 0
