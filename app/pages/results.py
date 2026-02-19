"""Unified results page – tier, risks, and controls in one view."""
import streamlit as st

from app.architecture import highlight_nodes, load_mermaid_file, render_mermaid
from app.ui_utils import render_chips, render_info_box, render_tier_badge, reset_assessment


def render_results():
    """Render the combined results page."""
    st.title("📊 Results")

    if not st.session_state.get("answers"):
        render_info_box(
            "Complete the assessment first to see your results.", "warning"
        )
        if st.button("Go to Assessment", type="primary", use_container_width=True):
            st.session_state.current_page = "Assessment"
            st.rerun()
        return

    loader = st.session_state.data_loader

    # ── Compute / reuse cached results ───────────────────────────────────────
    vayu = st.session_state.get("vayu_result")
    if not vayu:
        try:
            vayu = loader.calculate_vayu_tier(
                st.session_state.get("selected_use_cases", []),
                st.session_state.answers,
            )
            st.session_state.vayu_result = vayu
        except Exception:
            vayu = {"label": "—", "tier": 0, "escalatedRules": []}

    try:
        relevant_risks = loader.calculate_relevant_risks(
            st.session_state.answers,
            st.session_state.get("selected_personas", []),
        )
        st.session_state.relevant_risks = relevant_risks
    except Exception:
        relevant_risks = st.session_state.get("relevant_risks") or []

    controls = loader.get_controls_for_risks(relevant_risks) if relevant_risks else []
    st.session_state.recommended_controls = [c.get("id") for c in controls]

    # ── Tier overview ────────────────────────────────────────────────────────
    tier_label = vayu.get("label", "low")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown("**Risk Tier**")
        render_tier_badge(tier_label)
    col2.metric("Risks Found", len(relevant_risks))
    col3.metric("Controls", len(controls))
    # Unique categories
    categories = {
        loader.get_risk_details(rid).get("category", "")
        for rid in relevant_risks
        if loader.get_risk_details(rid)
    }
    col4.metric("Categories", len(categories))

    if vayu.get("escalatedRules"):
        with st.expander("Escalation triggers"):
            for r in vayu["escalatedRules"]:
                st.markdown(f"- {r}")

    st.markdown("---")

    if not relevant_risks:
        st.success(
            "No specific risks identified — your current security posture looks strong. "
            "Consider reviewing general AI security best practices to stay ahead."
        )
        _render_actions()
        return

    # ── Tabs: Risks | Controls | Deep Dive | Architecture ──────────────────
    tab_risks, tab_controls, tab_detail, tab_arch = st.tabs(
        [f"Risks ({len(relevant_risks)})", f"Controls ({len(controls)})", "Deep Dive", "Architecture"]
    )

    # -- Tab 1: Risks overview ------------------------------------------------
    with tab_risks:
        # Group by category
        by_cat: dict[str, list] = {}
        for rid in relevant_risks:
            risk = loader.get_risk_details(rid)
            if not risk:
                continue
            cat = risk.get("category", "Other").replace("risks", "").strip() or "Other"
            by_cat.setdefault(cat, []).append(risk)

        for cat, cat_risks in by_cat.items():
            st.markdown(f"#### {cat}")
            for risk in cat_risks:
                _render_risk_row(risk, loader)

    # -- Tab 2: Controls overview ----------------------------------------------
    with tab_controls:
        if not controls:
            render_info_box("No controls mapped to identified risks.", "info")
        else:
            # Group by category
            ctrl_by_cat: dict[str, list] = {}
            for ctrl in controls:
                raw = ctrl.get("category", "Other")
                cat = raw.replace("controls", "").replace("Control", "").strip() or "Other"
                ctrl_by_cat.setdefault(cat, []).append(ctrl)

            for cat, cat_ctrls in ctrl_by_cat.items():
                st.markdown(f"#### {cat}  ({len(cat_ctrls)})")
                for ctrl in cat_ctrls:
                    _render_control_row(ctrl, loader, relevant_risks)

    # -- Tab 3: Deep dive (select a risk) -------------------------------------
    with tab_detail:
        risk_map = {}
        for rid in relevant_risks:
            risk = loader.get_risk_details(rid)
            if risk:
                title = risk.get("title", rid)
                cat = risk.get("category", "").replace("risks", "").strip()
                display = f"{title} ({cat})" if cat else title
                risk_map[display] = rid

        if not risk_map:
            st.info("No risks to inspect.")
        else:
            selected_display = st.selectbox(
                "Select a risk to inspect",
                options=list(risk_map.keys()),
            )
            if selected_display:
                _render_risk_deep_dive(risk_map[selected_display], loader)

    # -- Tab 4: Architecture diagram with highlighted results ------------------
    with tab_arch:
        _render_results_architecture(loader, relevant_risks, controls)

    st.markdown("---")
    _render_actions()


# ── Architecture diagram in results ──────────────────────────────────────────

def _render_results_architecture(loader, relevant_risks: list, controls: list):
    """Render risk-map architecture diagram with identified risks/controls highlighted."""
    diagram_type = st.radio(
        "Diagram",
        ["Risk Mapping", "Controls Mapping", "Component Architecture"],
        horizontal=True,
        key="results_arch_radio",
    )
    type_map = {
        "Risk Mapping": "risk",
        "Controls Mapping": "control",
        "Component Architecture": "component",
    }
    height_map = {"risk": 1400, "control": 1000, "component": 700}
    dtype = type_map[diagram_type]

    raw = load_mermaid_file(dtype)
    if raw is None:
        render_info_box(
            "Architecture diagram files not found. Run the validator to generate them.",
            "warning",
        )
        return

    highlight_ids = list(relevant_risks)
    highlight_ids += [c.get("id") for c in controls if c.get("id")]
    for ctrl in controls:
        for comp_id in ctrl.get("components", []):
            if comp_id not in ("all", "none") and comp_id not in highlight_ids:
                highlight_ids.append(comp_id)

    code = highlight_nodes(raw, highlight_ids) if highlight_ids else raw

    st.caption(
        f"Nodes highlighted in **yellow** are relevant to your assessment "
        f"({len(relevant_risks)} risks, {len(controls)} controls)."
    )
    render_mermaid(code, height=height_map.get(dtype, 1000), key=f"results_{dtype}")


# ── Action buttons ───────────────────────────────────────────────────────────

def _render_actions():
    col1, col2 = st.columns(2)
    with col1:
        if st.button("← Back to Assessment", use_container_width=True):
            st.session_state.current_page = "Assessment"
            st.rerun()
    with col2:
        if st.button("Start New Assessment", use_container_width=True, type="primary"):
            reset_assessment()
            st.session_state.current_page = "Assessment"
            st.rerun()


# ── Risk row ─────────────────────────────────────────────────────────────────

def _render_risk_row(risk: dict, loader):
    title = risk.get("title", risk.get("id", "?"))
    short = loader.format_text_list(risk.get("shortDescription", []))
    ctrl_count = len(risk.get("controls", []))

    with st.expander(f"{title}  ·  {ctrl_count} controls"):
        if short:
            st.markdown(short)
        impact = risk.get("impactType", [])
        lifecycle = risk.get("lifecycleStage", [])
        c1, c2 = st.columns(2)
        with c1:
            if impact:
                st.markdown("**Impact**")
                render_chips(impact, "orange")
        with c2:
            if lifecycle:
                st.markdown("**Lifecycle**")
                render_chips(lifecycle, "purple")


# ── Control row ──────────────────────────────────────────────────────────────

def _render_control_row(ctrl: dict, loader, relevant_risks: list):
    title = ctrl.get("title", ctrl.get("id", "?"))
    desc = loader.format_text_list(ctrl.get("description", []))

    with st.expander(f"🛡️ {title}"):
        if desc:
            st.markdown(desc)

        c1, c2 = st.columns(2)
        with c1:
            personas = ctrl.get("personas", [])
            if personas:
                names = [loader.personas.get(p, {}).get("title", p) for p in personas]
                st.markdown(f"**Responsible:** {', '.join(names)}")
            components = ctrl.get("components", [])
            if components:
                render_chips(components)
        with c2:
            lifecycle = ctrl.get("lifecycleStage", [])
            if lifecycle:
                render_chips(lifecycle, "purple")

        # Which of the user's risks does this control mitigate?
        mitigates = [r for r in ctrl.get("risks", []) if r in relevant_risks]
        if mitigates:
            st.markdown("**Mitigates:**")
            for rid in mitigates:
                rdata = loader.get_risk_details(rid)
                if rdata:
                    st.markdown(f"- {rdata.get('title', rid)}")

        _render_framework_mappings(ctrl.get("mappings", {}))


# ── Deep dive view ───────────────────────────────────────────────────────────

def _render_risk_deep_dive(risk_id: str, loader):
    risk = loader.get_risk_details(risk_id)
    if not risk:
        st.error("Risk not found.")
        return

    st.markdown(f"### {risk.get('title', risk_id)}")

    short = loader.format_text_list(risk.get("shortDescription", []))
    if short:
        st.info(short)

    # Tabs inside the deep dive
    t1, t2, t3, t4 = st.tabs(["Description", "Impact & Lifecycle", "Examples", "Frameworks"])

    with t1:
        long_desc = loader.format_text_list(risk.get("longDescription", []))
        st.markdown(long_desc if long_desc else "*No detailed description available.*")

    with t2:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Impact Types**")
            items = risk.get("impactType", [])
            render_chips(items, "orange") if items else st.caption("None specified")
        with c2:
            st.markdown("**Lifecycle Stages**")
            items = risk.get("lifecycleStage", [])
            render_chips(items, "purple") if items else st.caption("None specified")

    with t3:
        examples = risk.get("examples", [])
        if examples:
            for i, ex in enumerate(examples, 1):
                txt = loader.format_text_list([ex]) if isinstance(ex, str) else str(ex)
                st.markdown(f"**{i}.** {txt}")
        else:
            st.caption("No examples available.")

    with t4:
        _render_framework_mappings(risk.get("mappings", {}))

    # Controls for this risk
    st.markdown("---")
    st.markdown("#### Recommended controls for this risk")
    control_ids = risk.get("controls", [])
    if not control_ids:
        st.caption("No controls mapped.")
        return

    for cid in control_ids:
        ctrl = loader.get_control_details(cid)
        if ctrl:
            title = ctrl.get("title", cid)
            desc = loader.format_text_list(ctrl.get("description", []))
            with st.expander(f"🛡️ {title}"):
                if desc:
                    st.markdown(desc)
                _render_framework_mappings(ctrl.get("mappings", {}))


# ── Framework mappings ───────────────────────────────────────────────────────

def _render_framework_mappings(mappings: dict):
    if not mappings:
        return
    st.markdown("**Framework mappings**")
    for fw, items in mappings.items():
        if items:
            name = fw.replace("-", " ").title()
            badges = " ".join(f"`{m}`" for m in items)
            st.markdown(f"- **{name}:** {badges}")
