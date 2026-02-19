"""Wizard-style assessment page for CoSAI Risk Map."""
import streamlit as st

from app.ui_utils import render_chips, render_info_box, render_step_indicator, reset_assessment

# ── Helpers ──────────────────────────────────────────────────────────────────

STEP_LABELS = ["Setup", "Context", "Risk Questions", "Review"]


def _format_answer_label(value):
    """Render human-friendly labels for boolean YAML values."""
    if value is True:
        return "Yes"
    if value is False:
        return "No"
    return str(value)


def _extract_answer_labels(answer_defs: list[dict]) -> list:
    """Extract labels while preserving boolean values like False ('No')."""
    labels = []
    for ans in answer_defs:
        if "label" not in ans:
            continue
        label = ans["label"]
        if label is None or label == "":
            continue
        labels.append(label)
    return labels


def _fmt_use_case(label: str) -> str:
    """camelCase → Title Case."""
    if not label:
        return label
    spaced = "".join(" " + c if c.isupper() else c for c in label).strip()
    return spaced.replace(" Or ", " or ").title()


def _question_widget(
    question: dict, loader, prefix: str, idx: int, total: int,
    *, prefilled: bool = False,
):
    """Render one question card with radio selector.

    When *prefilled* is True the card uses prefilled styling.
    """
    q_id = question.get("id")
    if not q_id:
        return
    text_items = [t for t in (question.get("text") or []) if t]
    if not text_items:
        return

    if prefilled:
        css_cls = "answered prefilled"
        label_prefix = "Prefilled"
    else:
        css_cls = "answered" if q_id in st.session_state.answers else ""
        label_prefix = "Question"

    st.markdown(
        f'<div class="q-card {css_cls}">'
        f'<div class="q-number">{label_prefix} {idx} of {total}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown(f"**{text_items[0]}**")
    if len(text_items) > 1:
        st.caption(loader.format_text_list(text_items[1:]))

    answers_list = question.get("answers") or []
    labels = _extract_answer_labels(answers_list)
    if not labels:
        return

    current = st.session_state.answers.get(q_id)
    idx_sel = labels.index(current) if current in labels else None

    selected = st.radio(
        "Your answer",
        options=labels,
        index=idx_sel,
        key=f"{prefix}_{q_id}",
        label_visibility="collapsed",
        format_func=_format_answer_label,
    )

    if selected is not None:
        st.session_state.answers[q_id] = selected


# ── Prefill data computation ────────────────────────────────────────────────

def _get_prefill_data(loader) -> dict:
    """Compute prefill data from AI inventory if available."""
    inventory_data = st.session_state.get("inventory_data", {})
    has_data = inventory_data and any(v for v in inventory_data.values() if v)
    if not has_data:
        return {"facts": {}, "prefilled_answers": {}, "prefilled_use_cases": [], "prefilled_personas": [], "hidden_questions": set()}

    repeat_blocks = {}
    for k in st.session_state:
        if isinstance(k, str) and k.startswith("inventory_repeat_blocks_"):
            v = st.session_state[k]
            if isinstance(v, list):
                repeat_blocks[k[len("inventory_repeat_blocks_"):]] = v

    return loader.get_prefilled_assessment_data(inventory_data, repeat_blocks)


def _apply_prefills(prefill_data: dict):
    """Auto-populate session state from prefill data (only for empty slots)."""
    for q_id, answer in prefill_data.get("prefilled_answers", {}).items():
        if q_id not in st.session_state.answers:
            st.session_state.answers[q_id] = answer

    if not st.session_state.selected_use_cases and prefill_data.get("prefilled_use_cases"):
        st.session_state.selected_use_cases = list(prefill_data["prefilled_use_cases"])

    if not st.session_state.selected_personas and prefill_data.get("prefilled_personas"):
        st.session_state.selected_personas = list(prefill_data["prefilled_personas"])


# ── Step renderers ───────────────────────────────────────────────────────────

def _step_setup(loader, prefill_data: dict):
    """Step 0 – use cases + persona selection."""
    has_prefill = bool(prefill_data.get("prefilled_use_cases") or prefill_data.get("prefilled_personas"))

    # ─ Use cases ─
    st.subheader("Select your use cases")
    vayu_uc = loader.get_vayu_use_cases()
    uc_text = loader.format_text_list(vayu_uc.get("text", []))
    if uc_text:
        st.caption(uc_text)

    uc_options = {}
    for ans in vayu_uc.get("answers", []):
        lbl = ans.get("label", "")
        if lbl:
            uc_options[_fmt_use_case(lbl)] = lbl

    if has_prefill and prefill_data.get("prefilled_use_cases"):
        prefilled_uc_labels = set(prefill_data["prefilled_use_cases"])
        prefilled_display = [n for n, v in uc_options.items() if v in prefilled_uc_labels]
        if prefilled_display:
            st.markdown(
                f'<div class="prefill-badge">Prefilled from AI Inventory: '
                f'<strong>{", ".join(prefilled_display)}</strong></div>',
                unsafe_allow_html=True,
            )

    selected_names = st.multiselect(
        "Use cases",
        options=list(uc_options.keys()),
        default=[n for n in uc_options if uc_options[n] in st.session_state.selected_use_cases],
        label_visibility="collapsed",
        placeholder="Pick one or more use cases…",
    )
    st.session_state.selected_use_cases = [uc_options[n] for n in selected_names]

    st.markdown("---")

    # ─ Persona selection ─
    st.subheader("Select your role(s)")
    persona_q = loader.get_persona_question()
    personas_data = loader.personas
    if not persona_q:
        st.error("Unable to load role options.")
        return False

    persona_text = loader.format_text_list(persona_q.get("text", []))
    if persona_text:
        st.caption(persona_text)

    persona_opts = {}
    persona_descs = {}
    for ans in persona_q.get("answers", []):
        pid = ans.get("label", "")
        if not pid:
            continue
        pinfo = personas_data.get(pid, {})
        display = pinfo.get("title", pid)
        persona_opts[display] = pid
        persona_descs[display] = loader.format_text_list(pinfo.get("description", []))

    if not persona_opts:
        st.error("No roles available.")
        return False

    if has_prefill and prefill_data.get("prefilled_personas"):
        prefilled_pids = set(prefill_data["prefilled_personas"])
        prefilled_display = [n for n, v in persona_opts.items() if v in prefilled_pids]
        if prefilled_display:
            st.markdown(
                f'<div class="prefill-badge">Prefilled from AI Inventory: '
                f'<strong>{", ".join(prefilled_display)}</strong></div>',
                unsafe_allow_html=True,
            )

    selected_persona_names = st.multiselect(
        "Roles",
        options=list(persona_opts.keys()),
        default=[n for n in persona_opts if persona_opts[n] in st.session_state.selected_personas],
        label_visibility="collapsed",
        placeholder="Pick one or more roles…",
    )
    st.session_state.selected_personas = [persona_opts[n] for n in selected_persona_names]

    if selected_persona_names:
        for name in selected_persona_names:
            desc = persona_descs.get(name)
            if desc:
                st.caption(f"**{name}** — {desc}")

    if not st.session_state.selected_personas:
        st.info("Please select at least one role to continue.")
        return False
    return True


def _step_context(loader, prefill_data: dict):
    """Step 1 – Vayu / tier-setting questions."""
    hidden_ids = prefill_data.get("hidden_questions", set())
    prefilled_ids = set(prefill_data.get("prefilled_answers", {}).keys())

    vayu_qs = [q for q in loader.get_vayu_questions() if q.get("id") not in hidden_ids]

    prefilled_qs = [q for q in vayu_qs if q.get("id") in prefilled_ids]
    manual_qs = [q for q in vayu_qs if q.get("id") not in prefilled_ids]

    total_all = len(vayu_qs)
    answered_all = sum(1 for q in vayu_qs if q.get("id") in st.session_state.answers)

    st.subheader("Context questions")
    st.caption(
        f"These questions determine your risk tier. "
        f"{answered_all} of {total_all} answered."
    )
    st.progress(answered_all / total_all if total_all else 0)

    # Prefilled section (collapsed)
    if prefilled_qs:
        with st.expander(
            f"Prefilled from AI Inventory ({len(prefilled_qs)} questions)",
            expanded=False,
        ):
            st.caption("These answers were derived from your AI Inventory. Expand to review or edit.")
            for idx, q in enumerate(prefilled_qs, 1):
                _question_widget(q, loader, "ctx_pf", idx, len(prefilled_qs), prefilled=True)

    # Manual questions
    if manual_qs:
        total_manual = len(manual_qs)
        for idx, q in enumerate(manual_qs, 1):
            _question_widget(q, loader, "ctx", idx, total_manual)
    elif not prefilled_qs:
        render_info_box("No context questions available.", "info")

    return answered_all == total_all


def _step_risk_questions(loader, prefill_data: dict):
    """Step 2 – persona-filtered risk questions."""
    hidden_ids = prefill_data.get("hidden_questions", set())
    all_qs = loader.get_questions()
    relevant = [
        q for q in all_qs
        if q.get("id") not in hidden_ids
        and any(p in st.session_state.selected_personas for p in q.get("personas", []))
    ]

    if not relevant:
        render_info_box("No risk questions for your selected roles.", "info")
        return True

    prefilled_ids = set(prefill_data.get("prefilled_answers", {}).keys())
    prefilled_qs = [q for q in relevant if q.get("id") in prefilled_ids]
    manual_qs = [q for q in relevant if q.get("id") not in prefilled_ids]

    total_all = len(relevant)
    answered_all = sum(1 for q in relevant if q.get("id") in st.session_state.answers)

    st.subheader("Risk questions")
    st.caption(
        f"Tailored to your role(s). {answered_all} of {total_all} answered."
    )
    st.progress(answered_all / total_all if total_all else 0)

    # Prefilled section (collapsed)
    if prefilled_qs:
        with st.expander(
            f"Prefilled from AI Inventory ({len(prefilled_qs)} questions)",
            expanded=False,
        ):
            st.caption("These answers were derived from your AI Inventory. Expand to review or edit.")
            for idx, q in enumerate(prefilled_qs, 1):
                _question_widget(q, loader, "rsk_pf", idx, len(prefilled_qs), prefilled=True)
                q_personas = q.get("personas", [])
                if q_personas:
                    names = [loader.personas.get(p, {}).get("title", p) for p in q_personas]
                    render_chips(names, "purple")

    # Manual questions
    for idx, q in enumerate(manual_qs, 1):
        _question_widget(q, loader, "rsk", idx, len(manual_qs))
        q_personas = q.get("personas", [])
        if q_personas:
            names = [loader.personas.get(p, {}).get("title", p) for p in q_personas]
            render_chips(names, "purple")

    return answered_all == total_all


def _step_review(loader):
    """Step 3 – summary before navigating to results."""
    st.subheader("Review & submit")

    try:
        vayu = loader.calculate_vayu_tier(
            st.session_state.selected_use_cases,
            st.session_state.answers,
        )
    except Exception:
        vayu = {"label": "—", "tier": 0, "escalatedRules": []}

    try:
        risks = loader.calculate_relevant_risks(
            st.session_state.answers,
            st.session_state.selected_personas,
        )
    except Exception:
        risks = []

    controls = loader.get_controls_for_risks(risks) if risks else []

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Questions Answered", len(st.session_state.answers))
    c2.metric("Risk Tier", vayu.get("label", "—").upper())
    c3.metric("Risks Found", len(risks))
    c4.metric("Controls", len(controls))

    if vayu.get("escalatedRules"):
        with st.expander("Escalation triggers"):
            for r in vayu["escalatedRules"]:
                st.markdown(f"- {r}")

    st.markdown("---")

    vayu_qs = loader.get_vayu_questions()
    all_risk_qs = loader.get_questions()
    relevant_qs = [
        q for q in all_risk_qs
        if any(p in st.session_state.selected_personas for p in q.get("personas", []))
    ]
    total_q = len(vayu_qs) + len(relevant_qs)
    total_a = sum(1 for q in vayu_qs + relevant_qs if q.get("id") in st.session_state.answers)
    if total_a < total_q:
        st.warning(
            f"You answered {total_a} of {total_q} questions. "
            "You can still view results, but answering all gives better insights."
        )

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("View Results", type="primary", use_container_width=True):
            st.session_state.vayu_result = vayu
            st.session_state.relevant_risks = risks
            st.session_state.recommended_controls = [c.get("id") for c in controls]
            st.session_state.current_page = "Results"
            st.rerun()


# ── Main renderer ────────────────────────────────────────────────────────────

def render_assessment():
    """Render the wizard-style assessment."""
    st.title("Risk Assessment")

    step = st.session_state.get("assessment_step", 0)
    render_step_indicator(STEP_LABELS, step)

    loader = st.session_state.data_loader

    # Compute prefill data from inventory
    prefill_data = _get_prefill_data(loader)
    _apply_prefills(prefill_data)

    has_prefill = bool(prefill_data.get("prefilled_answers"))
    if has_prefill:
        n = len(prefill_data["prefilled_answers"])
        st.markdown(
            f'<div class="prefill-banner">'
            f'<strong>{n} assessment question(s)</strong> prefilled from your AI Inventory. '
            f'Look for the collapsed sections below to review or edit.'
            f'</div>',
            unsafe_allow_html=True,
        )

    # Render current step
    can_advance = True
    if step == 0:
        can_advance = _step_setup(loader, prefill_data)
    elif step == 1:
        _step_context(loader, prefill_data)
        can_advance = True
    elif step == 2:
        _step_risk_questions(loader, prefill_data)
        can_advance = True
    elif step == 3:
        _step_review(loader)
        return

    # Navigation buttons
    st.markdown("---")
    col_left, col_spacer, col_right = st.columns([1, 3, 1])

    with col_left:
        if step > 0:
            if st.button("← Back", use_container_width=True):
                st.session_state.assessment_step = step - 1
                st.rerun()

    with col_right:
        if step < len(STEP_LABELS) - 1:
            if st.button("Next →", use_container_width=True, type="primary", disabled=not can_advance):
                st.session_state.assessment_step = step + 1
                st.rerun()

    # Reset at bottom
    if st.session_state.answers:
        st.markdown("---")
        if st.button("Reset assessment", type="secondary"):
            reset_assessment()
            st.rerun()
