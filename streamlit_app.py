"""Main Streamlit app for CoSAI Risk Map."""
import logging
import sys
from pathlib import Path

import streamlit as st

# ── Logging ───────────────────────────────────────────────────────────────────
# force=True overrides Streamlit's existing handlers so logs appear in the terminal
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stderr,
    force=True,
)
logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).parent))
from app.data_loader import DataLoadError, RiskMapDataLoader
from app.ui_utils import inject_custom_css

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="KTB Risk Navigator",
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
    "inventory_data": {},
    "inventory_step": 0,
    "_assessment_record_id": None,
}
for key, default in _DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ── Data loader ──────────────────────────────────────────────────────────────
if st.session_state.data_loader is None or not hasattr(st.session_state.data_loader, "get_prefilled_assessment_data"):
    try:
        st.session_state.data_loader = RiskMapDataLoader()
        logger.info("RiskMapDataLoader initialized")
        if st.session_state.data_loader.has_load_errors():
            errors = st.session_state.data_loader.get_load_errors()
            st.error(f"Data loading errors: {', '.join(errors.keys())}")
    except DataLoadError as e:
        st.error(f"Failed to initialize data loader: {e}")
        st.stop()
    except Exception as e:
        st.error(f"Unexpected error: {e}")
        st.stop()

# ── Mock scenario helpers ─────────────────────────────────────────────────────

def _apply_scenario(sc: dict) -> None:
    """Populate session state from a mock-prefills scenario."""
    from app.data_loader import RiskMapDataLoader

    sc_id = sc.get("id", "unknown")
    flat, repeat_blocks = RiskMapDataLoader.flatten_inventory_scenario(sc)
    logger.info("Applying mock scenario id=%s, flat_fields=%d, repeat_blocks=%s", sc_id, len(flat), list(repeat_blocks.keys()))

    st.session_state["inventory_data"] = flat
    for block_id, rows in repeat_blocks.items():
        st.session_state[f"inventory_repeat_blocks_{block_id}"] = rows

    # Assessment not mocked - reset to blank so user fills it
    sa = sc.get("selfAssessment", {})
    va = sc.get("vayuAssessment", {})
    if sa or va:
        answers: dict = {}
        for q_id, ans in sa.get("answers", {}).items():
            answers[q_id] = ans
        for q_id, ans in va.get("answers", {}).items():
            answers[q_id] = ans
        st.session_state["answers"] = answers
        st.session_state["selected_personas"] = list(sa.get("personas", []))
        st.session_state["selected_use_cases"] = list(va.get("useCases", []))
    else:
        st.session_state["answers"] = {}
        st.session_state["selected_personas"] = []
        st.session_state["selected_use_cases"] = []

    st.session_state["inventory_step"] = 0
    st.session_state["assessment_step"] = 0
    st.session_state["vayu_result"] = None
    st.session_state["relevant_risks"] = []
    st.session_state["recommended_controls"] = []
    st.session_state["_assessment_record_id"] = None
    # Clear assessment widget state so prefill from inventory can take effect
    for k in list(st.session_state.keys()):
        if k in ("assessment_uc", "assessment_personas") or k.startswith(("ctx_", "rsk_")):
            del st.session_state[k]
    # Clear AI Inventory widget keys so widgets re-init from new inventory_data/repeat_blocks
    _clear_inventory_widget_state()
    logger.info("Scenario applied: inventory only, personas=%s, use_cases=%s", st.session_state["selected_personas"], st.session_state["selected_use_cases"])


def _clear_inventory_widget_state() -> None:
    """Remove AI Inventory form widget keys so next render uses inventory_data/repeat_blocks."""
    for k in list(st.session_state.keys()):
        if (
            (k.startswith("step") and "_" in k)  # step1_useCaseName, step2_sec2a_*, etc.
            or k.startswith("rep_")
            or k.startswith("del_")
            or k.startswith("add_")
            or k in ("inv_back", "inv_next", "inv_submit", "inv_reset")
        ):
            del st.session_state[k]


def _clear_scenario() -> None:
    """Reset session state to blank (undo a loaded scenario)."""
    logger.info("Clearing mock scenario prefill")
    st.session_state["inventory_data"] = {}
    _clear_inventory_widget_state()
    for k in list(st.session_state.keys()):
        if k in ("assessment_uc", "assessment_personas") or k.startswith(("ctx_", "rsk_")):
            del st.session_state[k]
    st.session_state["answers"] = {}
    st.session_state["selected_personas"] = []
    st.session_state["selected_use_cases"] = []
    st.session_state["vayu_result"] = None
    st.session_state["relevant_risks"] = []
    st.session_state["recommended_controls"] = []
    st.session_state["_assessment_record_id"] = None
    st.session_state["inventory_step"] = 0
    st.session_state["assessment_step"] = 0
    for k in list(st.session_state.keys()):
        if k.startswith("inventory_repeat_blocks_"):
            del st.session_state[k]


# ── Sidebar ──────────────────────────────────────────────────────────────────
NAV = ["Home", "AI Inventory", "Assessment", "Results", "Architecture"]

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

    # Mock scenario loader
    st.markdown("---")
    st.markdown("##### Demo Scenarios")
    loader_sb = st.session_state.data_loader
    scenarios = loader_sb.load_mock_prefills() if loader_sb else []

    def _on_scenario_change():
        chosen = st.session_state.get("sidebar_scenario_select", "— None —")
        if chosen == "— None —":
            _clear_scenario()
            st.session_state["_active_scenario"] = "— None —"
        else:
            sc = next(
                (s for s in scenarios if s.get("title", s.get("id", "")) == chosen),
                None,
            )
            if sc:
                _apply_scenario(sc)
                st.session_state["_active_scenario"] = chosen

    scenario_names = ["— None —"] + [s.get("title", s.get("id", "")) for s in scenarios]
    current = st.session_state.get("_active_scenario", "— None —")
    idx = scenario_names.index(current) if current in scenario_names else 0
    st.selectbox(
        "Load prefill",
        scenario_names,
        index=idx,
        key="sidebar_scenario_select",
        label_visibility="collapsed",
        on_change=_on_scenario_change,
    )

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

elif page == "AI Inventory":
    try:
        from app.pages.ai_inventory import render_ai_inventory
        render_ai_inventory()
    except Exception as e:
        st.error(f"Error loading AI Inventory: {e}")
        st.exception(e)

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

elif page == "Architecture":
    try:
        from app.architecture import render_architecture_page
        render_architecture_page()
    except Exception as e:
        st.error(f"Error loading architecture: {e}")
        st.exception(e)
