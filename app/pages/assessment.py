"""Wizard-style assessment page for CoSAI Risk Map."""
import streamlit as st

from app.ui_utils import render_chips, render_info_box, render_step_indicator

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


def _question_widget(question: dict, loader, prefix: str, idx: int, total: int):
    """Render one question card and return selected answer (or None)."""
    q_id = question.get("id")
    if not q_id:
        return
    text_items = [t for t in (question.get("text") or []) if t]
    if not text_items:
        return

    answered = q_id in st.session_state.answers
    css_cls = "answered" if answered else ""

    st.markdown(
        f'<div class="q-card {css_cls}">'
        f'<div class="q-number">Question {idx} of {total}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Question text
    st.markdown(f"**{text_items[0]}**")
    if len(text_items) > 1:
        st.caption(loader.format_text_list(text_items[1:]))

    answers_list = question.get("answers") or []
    labels = _extract_answer_labels(answers_list)
    if not labels:
        return

    # Use None sentinel so no option is pre-selected for unanswered questions
    current = st.session_state.answers.get(q_id)
    options = labels
    if current in options:
        idx_sel = options.index(current)
    else:
        idx_sel = None  # nothing selected yet

    selected = st.radio(
        "Your answer",
        options=options,
        index=idx_sel,
        key=f"{prefix}_{q_id}",
        label_visibility="collapsed",
        format_func=_format_answer_label,
    )

    if selected is not None:
        st.session_state.answers[q_id] = selected


# ── Step renderers ───────────────────────────────────────────────────────────

def _step_setup(loader):
    """Step 0 – use cases + persona selection."""
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

    selected_names = st.multiselect(
        "Use cases",
        options=list(uc_options.keys()),
        default=[n for n in uc_options if uc_options[n] in st.session_state.selected_use_cases],
        label_visibility="collapsed",
        placeholder="Pick one or more use cases…",
    )
    st.session_state.selected_use_cases = [uc_options[n] for n in selected_names]

    st.markdown("---")

    # Persona selection
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


def _step_context(loader):
    """Step 1 – Vayu / tier-setting questions."""
    vayu_qs = loader.get_vayu_questions()
    total = len(vayu_qs)
    answered = sum(1 for q in vayu_qs if q.get("id") in st.session_state.answers)

    st.subheader("Context questions")
    st.caption(
        "These questions determine your risk tier. "
        f"{answered} of {total} answered."
    )
    st.progress(answered / total if total else 0)

    for idx, q in enumerate(vayu_qs, 1):
        _question_widget(q, loader, "ctx", idx, total)

    return answered == total


def _step_risk_questions(loader):
    """Step 2 – persona-filtered risk questions."""
    all_qs = loader.get_questions()
    relevant = [
        q for q in all_qs
        if any(p in st.session_state.selected_personas for p in q.get("personas", []))
    ]

    if not relevant:
        render_info_box("No risk questions for your selected roles.", "info")
        return True

    total = len(relevant)
    answered = sum(1 for q in relevant if q.get("id") in st.session_state.answers)

    st.subheader("Risk questions")
    st.caption(
        f"Tailored to your role(s). {answered} of {total} answered."
    )
    st.progress(answered / total if total else 0)

    for idx, q in enumerate(relevant, 1):
        _question_widget(q, loader, "rsk", idx, total)
        # Show which personas this applies to
        q_personas = q.get("personas", [])
        if q_personas:
            names = [loader.personas.get(p, {}).get("title", p) for p in q_personas]
            render_chips(names, "purple")

    return answered == total


def _step_review(loader):
    """Step 3 – summary before navigating to results."""
    st.subheader("Review & submit")

    # Calculate results
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

    # Metrics
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

    # Unanswered warning
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

    # Submit
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
    st.title("🔍 Risk Assessment")

    step = st.session_state.get("assessment_step", 0)
    render_step_indicator(STEP_LABELS, step)

    loader = st.session_state.data_loader

    # Render current step
    can_advance = True
    if step == 0:
        can_advance = _step_setup(loader)
    elif step == 1:
        _step_context(loader)
        can_advance = True  # allow moving forward even if not all answered
    elif step == 2:
        _step_risk_questions(loader)
        can_advance = True
    elif step == 3:
        _step_review(loader)
        return  # review step has its own submit button

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
            for key in ("answers", "selected_personas", "selected_use_cases",
                        "vayu_result", "relevant_risks", "recommended_controls"):
                st.session_state[key] = [] if isinstance(st.session_state.get(key), list) else (
                    {} if isinstance(st.session_state.get(key), dict) else None
                )
            st.session_state.assessment_step = 0
            st.rerun()
