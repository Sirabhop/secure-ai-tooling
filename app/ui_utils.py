"""UI utilities and styling for Streamlit app."""
from typing import List

import streamlit as st


def inject_custom_css():
    """Inject custom CSS for a clean, modern UI."""
    st.markdown("""
    <style>
    /* ---------- Global ---------- */
    .main { padding-top: 1.5rem; }
    section[data-testid="stSidebar"] > div:first-child { padding-top: 1rem; }

    /* ---------- Typography ---------- */
    h1 { font-weight: 700; letter-spacing: -0.02em; }
    h2 { font-weight: 600; margin-top: 1.5rem; }
    h3 { font-weight: 600; }

    /* ---------- Metric cards ---------- */
    [data-testid="stMetricValue"] { font-size: 1.8rem; font-weight: 700; }

    /* ---------- Buttons ---------- */
    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.2s ease;
    }
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 2px 8px rgba(0,0,0,0.12);
    }

    /* ---------- Step indicator ---------- */
    .step-bar {
        display: flex;
        align-items: center;
        gap: 0;
        margin: 1rem 0 1.5rem 0;
    }
    .step-item {
        display: flex;
        flex-direction: column;
        align-items: center;
        flex: 1;
        position: relative;
    }
    .step-circle {
        width: 36px; height: 36px;
        border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-weight: 700; font-size: 0.85rem;
        z-index: 2;
        transition: all 0.25s ease;
    }
    .step-circle.done   { background: #22c55e; color: #fff; }
    .step-circle.active { background: #2563eb; color: #fff; box-shadow: 0 0 0 4px rgba(37,99,235,0.2); }
    .step-circle.future { background: #e5e7eb; color: #9ca3af; }
    .step-label {
        margin-top: 6px;
        font-size: 0.75rem;
        font-weight: 600;
        text-align: center;
        white-space: nowrap;
    }
    .step-label.active { color: #2563eb; }
    .step-label.done   { color: #22c55e; }
    .step-label.future { color: #9ca3af; }
    .step-connector {
        flex: 1; height: 3px;
        margin-top: -18px;
        z-index: 1;
    }
    .step-connector.done   { background: #22c55e; }
    .step-connector.future { background: #e5e7eb; }

    /* ---------- Question cards ---------- */
    .q-card {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 1.25rem 1.5rem;
        margin-bottom: 1rem;
        transition: border-color 0.2s;
    }
    .q-card:hover { border-color: #cbd5e1; }
    .q-card.answered { border-left: 4px solid #22c55e; }
    .q-number {
        font-size: 0.75rem;
        font-weight: 700;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.25rem;
    }

    /* ---------- Result cards ---------- */
    .result-card {
        background: #fff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 1.25rem;
        margin-bottom: 0.75rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }

    /* ---------- Tier badge ---------- */
    .tier-badge {
        display: inline-block;
        padding: 0.35rem 1rem;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }
    .tier-low          { background: #dcfce7; color: #166534; }
    .tier-medium       { background: #fef9c3; color: #854d0e; }
    .tier-high         { background: #fed7aa; color: #9a3412; }
    .tier-unacceptable { background: #fecaca; color: #991b1b; }

    /* ---------- Tag chips ---------- */
    .chip {
        display: inline-block;
        padding: 0.2rem 0.6rem;
        background: #eff6ff;
        color: #1d4ed8;
        border-radius: 6px;
        font-size: 0.78rem;
        font-weight: 500;
        margin: 0.15rem 0.15rem;
    }
    .chip.green  { background: #f0fdf4; color: #15803d; }
    .chip.orange { background: #fff7ed; color: #c2410c; }
    .chip.purple { background: #faf5ff; color: #7e22ce; }
    .chip.red    { background: #fef2f2; color: #b91c1c; }

    /* ---------- Prefilled sections ---------- */
    .prefill-banner {
        background: #f0fdf4;
        border: 1px solid #bbf7d0;
        border-left: 4px solid #22c55e;
        border-radius: 8px;
        padding: 0.75rem 1rem;
        margin-bottom: 1rem;
        font-size: 0.9rem;
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
        border-left: 4px solid #22c55e;
        background: #f0fdf4;
    }

    /* ---------- Inventory form ---------- */
    .stSelectbox > div > div,
    .stMultiSelect > div > div {
        border-radius: 8px;
    }
    div[data-testid="stExpander"] {
        border-radius: 10px;
        border: 1px solid #e2e8f0;
        margin-bottom: 0.5rem;
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
# Tier badge
# ---------------------------------------------------------------------------

def render_tier_badge(label: str):
    """Render a colored tier badge."""
    css_cls = f"tier-{label.lower()}" if label.lower() in ("low", "medium", "high", "unacceptable") else "tier-low"
    st.markdown(f'<span class="tier-badge {css_cls}">{label.upper()}</span>', unsafe_allow_html=True)


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
