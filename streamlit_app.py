"""Main Streamlit app for CoSAI Risk Map."""
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))
from app.data_loader import DataLoadError, RiskMapDataLoader
from app.ui_utils import inject_custom_css

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="CoSAI Risk Map",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": None,
        "Report a bug": None,
        "About": "CoSAI Risk Map – Coalition for Secure AI Risk Assessment Tool",
    },
)

inject_custom_css()

# ── Session state defaults ───────────────────────────────────────────────────
_DEFAULTS = {
    "data_loader": None,
    "answers": {},
    "selected_personas": [],
    "selected_use_cases": [],
    "vayu_result": None,
    "relevant_risks": [],
    "recommended_controls": [],
    "current_page": "Home",
    "assessment_step": 0,
}
for key, default in _DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ── Data loader ──────────────────────────────────────────────────────────────
if st.session_state.data_loader is None:
    try:
        st.session_state.data_loader = RiskMapDataLoader()
        if st.session_state.data_loader.has_load_errors():
            errors = st.session_state.data_loader.get_load_errors()
            st.error(f"Data loading errors: {', '.join(errors.keys())}")
    except DataLoadError as e:
        st.error(f"Failed to initialize data loader: {e}")
        st.stop()
    except Exception as e:
        st.error(f"Unexpected error: {e}")
        st.stop()

# ── Sidebar ──────────────────────────────────────────────────────────────────
NAV = ["Home", "Assessment", "Results"]

with st.sidebar:
    st.markdown("### 🛡️ CoSAI Risk Map")
    st.caption("Coalition for Secure AI")
    st.markdown("---")

    try:
        nav_index = NAV.index(st.session_state.current_page)
    except ValueError:
        nav_index = 0

    page = st.radio("Navigate", NAV, index=nav_index, label_visibility="collapsed")
    st.session_state.current_page = page

    # Progress summary
    if st.session_state.answers:
        loader = st.session_state.data_loader
        vayu_q = loader.get_vayu_questions()
        all_q = loader.get_questions()
        risk_q = [
            q for q in all_q
            if any(p in st.session_state.selected_personas for p in q.get("personas", []))
        ]
        total = len(vayu_q) + len(risk_q)
        answered = sum(1 for q in vayu_q + risk_q if q.get("id") in st.session_state.answers)
        if total > 0:
            st.markdown("---")
            st.progress(answered / total)
            st.caption(f"{answered}/{total} questions answered")

    st.markdown("---")
    st.caption("[Learn more on GitHub](https://github.com/CoalitionForSecureAI/secure-ai-tooling)")

# ── Page routing ─────────────────────────────────────────────────────────────
if page == "Home":
    loader = st.session_state.data_loader

    st.title("🛡️ CoSAI Risk Map")
    st.markdown(
        "Identify and mitigate security risks in your AI systems with an "
        "interactive, guided assessment."
    )

    col1, col2, col3 = st.columns(3)
    col1.metric("Risks Cataloged", len(loader.risks))
    col2.metric("Controls Available", len(loader.controls))
    col3.metric("Frameworks Mapped", 4)

    st.markdown("---")
    st.subheader("How it works")
    cols = st.columns(3)
    info = [
        ("1. Setup", "Pick your use cases and roles — takes 30 seconds."),
        ("2. Assess", "Answer context and risk questions tailored to your profile."),
        ("3. Results", "Get your risk tier, identified risks, and recommended controls."),
    ]
    for col, (title, desc) in zip(cols, info):
        with col:
            st.markdown(f"**{title}**")
            st.caption(desc)

    st.markdown("---")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("Start Assessment", type="primary", use_container_width=True):
            st.session_state.current_page = "Assessment"
            st.session_state.assessment_step = 0
            st.rerun()

    if st.session_state.answers:
        st.markdown("---")
        vayu = st.session_state.vayu_result
        if not vayu:
            try:
                vayu = loader.calculate_vayu_tier(
                    st.session_state.selected_use_cases, st.session_state.answers
                )
            except Exception:
                vayu = {"label": "—"}
        try:
            risks = loader.calculate_relevant_risks(
                st.session_state.answers, st.session_state.selected_personas
            )
        except Exception:
            risks = []
        c1, c2, c3 = st.columns(3)
        c1.metric("Questions Answered", len(st.session_state.answers))
        c2.metric("Risk Tier", vayu.get("label", "—").upper())
        c3.metric("Risks Found", len(risks))

        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("Continue Assessment", use_container_width=True):
                st.session_state.current_page = "Assessment"
                st.rerun()

elif page == "Assessment":
    try:
        from app.pages.assessment import render_assessment
        render_assessment()
    except Exception as e:
        st.error(f"Error loading assessment: {e}")
        st.exception(e)

elif page == "Results":
    try:
        from app.pages.results import render_results
        render_results()
    except Exception as e:
        st.error(f"Error loading results: {e}")
        st.exception(e)
