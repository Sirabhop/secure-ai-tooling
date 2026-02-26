"""Wizard-style assessment page for AI Risk Navigator."""
import re
import logging

import streamlit as st

from app.ui_utils import render_chips, render_info_box, render_page_header, render_step_indicator, reset_assessment
from app.storage import (
    is_database_ready,
    load_ai_inventory_submission,
    load_self_assessment_submission,
    save_self_assessment_submission,
)

logger = logging.getLogger(__name__)

# ── Helpers ──────────────────────────────────────────────────────────────────

STEP_LABELS = ["Setup", "Context", "Risk Questions", "Review"]


def _format_prefill_reason(reason: str) -> str:
    """Turn raw prefill reason into readable markdown (bullets, clean list values)."""
    if not reason or not reason.strip():
        return ""
    # Replace " in ['a','b']" with " = one of: a, b" (extract quoted items)
    def _clean_list(match):
        raw = match.group(1)
        items = re.findall(r"[\"']([^\"']*)[\"']", raw)
        return " = one of: " + ", ".join(items) if items else ""
    text = re.sub(r"\s+in\s+\[(.*?)\]", _clean_list, reason, flags=re.DOTALL)
    # Split by OR / AND and emit bullets
    clauses = re.split(r"\s+OR\s+|\s+AND\s+", text)
    bullets = []
    for c in clauses:
        c = c.strip()
        if not c:
            continue
        if c == "...":
            bullets.append("- *(other conditions)*")
        else:
            bullets.append(f"- {c}")
    return "\n".join(bullets) if bullets else reason


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


def _clear_assessment_widget_state() -> None:
    """Clear widget-backed assessment state before loading saved records."""
    for key in list(st.session_state.keys()):
        if key in ("assessment_uc", "assessment_personas") or key.startswith(("ctx_", "rsk_")):
            del st.session_state[key]


def _render_db_controls() -> None:
    """Render load-by-ID controls for assessment persistence."""
    if not is_database_ready():
        st.caption(
            "PostgreSQL persistence is disabled. Set `DATABASE_URL` or "
            "`PGHOST/PGPORT/PGDATABASE/PGUSER/PGPASSWORD` to enable save/load by ID."
        )
        return

    with st.expander("PostgreSQL persistence", expanded=False):
        current_id = st.session_state.get("_assessment_record_id")
        if current_id:
            st.caption(f"Current assessment ID: `{current_id}`")

        load_id = st.text_input(
            "Load assessment by ID",
            key="assessment_db_load_id",
            placeholder="ASMT-XXXXXXXXXX",
        ).strip()

        if st.button("Load Assessment", use_container_width=True, key="assessment_db_load_button"):
            if not load_id:
                st.warning("Please enter an assessment ID.")
                return

            try:
                record = load_self_assessment_submission(load_id)
            except Exception:
                logger.exception("Failed loading self-assessment id=%s", load_id)
                st.error("Failed to load assessment from PostgreSQL.")
                return

            if not record:
                st.warning(f"No assessment record found for ID `{load_id}`.")
                return

            st.session_state.answers = record.get("answers", {})
            st.session_state.selected_personas = record.get("selected_personas", [])
            st.session_state.selected_use_cases = record.get("selected_use_cases", [])
            st.session_state.vayu_result = record.get("vayu_result") or None
            st.session_state.relevant_risks = record.get("relevant_risks", [])
            st.session_state.recommended_controls = record.get("recommended_controls", [])
            st.session_state["_assessment_record_id"] = record.get("assessment_id")

            linked_use_case_id = record.get("ai_inventory_use_case_id")
            if linked_use_case_id:
                try:
                    inv_record = load_ai_inventory_submission(linked_use_case_id)
                except Exception:
                    logger.exception(
                        "Failed loading linked AI inventory id=%s", linked_use_case_id
                    )
                    inv_record = None
                if inv_record:
                    st.session_state["inventory_data"] = inv_record.get("payload", {})
                    for key in list(st.session_state.keys()):
                        if isinstance(key, str) and key.startswith("inventory_repeat_blocks_"):
                            del st.session_state[key]
                    for block_id, rows in inv_record.get("repeat_blocks", {}).items():
                        if isinstance(rows, list):
                            st.session_state[f"inventory_repeat_blocks_{block_id}"] = rows

            st.session_state.assessment_step = 0
            _clear_assessment_widget_state()
            st.success(f"Loaded assessment `{load_id}`.")
            st.rerun()


def _question_widget(
    question: dict, loader, prefix: str, idx: int, total: int,
    *, prefilled: bool = False, prefill_reason: str = "",
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

    if prefilled and prefill_reason:
        formatted = _format_prefill_reason(prefill_reason)
        if formatted:
            with st.expander("From inventory", expanded=False):
                st.markdown(formatted)

    answers_list = question.get("answers") or []
    labels = _extract_answer_labels(answers_list)
    if not labels:
        return

    current = st.session_state.answers.get(q_id)
    idx_sel = labels.index(current) if current and current in labels else 0

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
        return {
            "facts": {}, "prefilled_answers": {}, "prefilled_use_cases": [],
            "prefilled_personas": [], "hidden_questions": set(),
            "prefill_reasons": {"use_cases": {}, "personas": {}, "answers": {}},
        }

    repeat_blocks = {}
    for k in st.session_state:
        if isinstance(k, str) and k.startswith("inventory_repeat_blocks_"):
            v = st.session_state[k]
            if isinstance(v, list):
                repeat_blocks[k[len("inventory_repeat_blocks_"):]] = v

    return loader.get_prefilled_assessment_data(inventory_data, repeat_blocks)


def _apply_prefills(prefill_data: dict):
    """Auto-populate session state from prefill data (only for empty slots)."""
    n_before = len(st.session_state.answers)
    for q_id, answer in prefill_data.get("prefilled_answers", {}).items():
        if q_id not in st.session_state.answers:
            st.session_state.answers[q_id] = answer

    if not st.session_state.selected_use_cases and prefill_data.get("prefilled_use_cases"):
        st.session_state.selected_use_cases = list(prefill_data["prefilled_use_cases"])

    if not st.session_state.selected_personas and prefill_data.get("prefilled_personas"):
        st.session_state.selected_personas = list(prefill_data["prefilled_personas"])

    n_after = len(st.session_state.answers)
    if n_after > n_before:
        logger.info("Applied %d prefilled answers from inventory", n_after - n_before)


# ── Step renderers ───────────────────────────────────────────────────────────

def _step_setup(loader, prefill_data: dict):
    """Step 0 – use cases + persona selection."""
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

    reasons = prefill_data.get("prefill_reasons", {}).get("use_cases", {})
    prefilled_uc_labels = set(prefill_data.get("prefilled_use_cases", []))
    prefilled_display = [n for n, v in uc_options.items() if v in prefilled_uc_labels]
    if prefilled_display:
        reason_lines = [f"<strong>{n}</strong>: {reasons.get(uc_options[n], '—')}" for n in prefilled_display]
        st.markdown(
            '<div class="prefill-badge">Prefilled from AI Inventory: '
            + "<br>".join(reason_lines) + "</div>",
            unsafe_allow_html=True,
        )

    uc_key = "assessment_uc"
    if uc_key not in st.session_state:
        st.session_state[uc_key] = [n for n in uc_options if uc_options[n] in st.session_state.selected_use_cases]
    selected_names = st.multiselect(
        "Use cases",
        options=list(uc_options.keys()),
        key=uc_key,
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

    persona_reasons = prefill_data.get("prefill_reasons", {}).get("personas", {})
    prefilled_pids = set(prefill_data.get("prefilled_personas", []))
    prefilled_persona_display = [n for n, v in persona_opts.items() if v in prefilled_pids]
    if prefilled_persona_display:
        reason_lines = [f"<strong>{n}</strong>: {persona_reasons.get(persona_opts[n], '—')}" for n in prefilled_persona_display]
        st.markdown(
            '<div class="prefill-badge">Prefilled from AI Inventory: '
            + "<br>".join(reason_lines) + "</div>",
            unsafe_allow_html=True,
        )

    persona_key = "assessment_personas"
    if persona_key not in st.session_state:
        st.session_state[persona_key] = [n for n in persona_opts if persona_opts[n] in st.session_state.selected_personas]
    selected_persona_names = st.multiselect(
        "Roles",
        options=list(persona_opts.keys()),
        key=persona_key,
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
    answer_reasons = prefill_data.get("prefill_reasons", {}).get("answers", {})
    if prefilled_qs:
        with st.expander(
            f"Prefilled from AI Inventory ({len(prefilled_qs)} questions)",
            expanded=False,
        ):
            st.caption("These answers were derived from your AI Inventory. Expand to review or edit.")
            for idx, q in enumerate(prefilled_qs, 1):
                reason = answer_reasons.get(q.get("id", ""), "")
                _question_widget(q, loader, "ctx_pf", idx, len(prefilled_qs), prefilled=True, prefill_reason=reason)

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
    answer_reasons = prefill_data.get("prefill_reasons", {}).get("answers", {})
    if prefilled_qs:
        with st.expander(
            f"Prefilled from AI Inventory ({len(prefilled_qs)} questions)",
            expanded=False,
        ):
            st.caption("These answers were derived from your AI Inventory. Expand to review or edit.")
            for idx, q in enumerate(prefilled_qs, 1):
                reason = answer_reasons.get(q.get("id", ""), "")
                _question_widget(q, loader, "rsk_pf", idx, len(prefilled_qs), prefilled=True, prefill_reason=reason)
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
    logger.info("Assessment review: tier=%s, risks=%d, controls=%d", vayu.get("label"), len(risks), len(controls))

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

    col_save, col_view, _ = st.columns([1, 1, 1])

    with col_save:
        if is_database_ready():
            if st.button("Save Assessment", use_container_width=True):
                ai_inventory_use_case_id = (st.session_state.get("inventory_data") or {}).get("useCaseId")
                try:
                    assessment_id = save_self_assessment_submission(
                        assessment_id=st.session_state.get("_assessment_record_id"),
                        ai_inventory_use_case_id=ai_inventory_use_case_id,
                        selected_personas=st.session_state.selected_personas,
                        selected_use_cases=st.session_state.selected_use_cases,
                        answers=st.session_state.answers,
                        vayu_result=vayu,
                        relevant_risks=risks,
                        recommended_controls=[c.get("id") for c in controls],
                    )
                    st.session_state["_assessment_record_id"] = assessment_id
                    st.success(f"Assessment saved to PostgreSQL with ID `{assessment_id}`.")
                except Exception:
                    logger.exception("Failed saving self-assessment to PostgreSQL")
                    st.error("Could not save assessment to PostgreSQL.")
        else:
            st.caption("Configure PostgreSQL to persist assessment records by ID.")

    with col_view:
        if st.button("View Results", type="primary", use_container_width=True):
            if is_database_ready():
                ai_inventory_use_case_id = (st.session_state.get("inventory_data") or {}).get("useCaseId")
                try:
                    assessment_id = save_self_assessment_submission(
                        assessment_id=st.session_state.get("_assessment_record_id"),
                        ai_inventory_use_case_id=ai_inventory_use_case_id,
                        selected_personas=st.session_state.selected_personas,
                        selected_use_cases=st.session_state.selected_use_cases,
                        answers=st.session_state.answers,
                        vayu_result=vayu,
                        relevant_risks=risks,
                        recommended_controls=[c.get("id") for c in controls],
                    )
                    st.session_state["_assessment_record_id"] = assessment_id
                except Exception:
                    logger.exception("Failed auto-saving self-assessment before results")

            st.session_state.vayu_result = vayu
            st.session_state.relevant_risks = risks
            st.session_state.recommended_controls = [c.get("id") for c in controls]
            logger.info("Assessment complete: navigating to Results, tier=%s", vayu.get("label"))
            st.session_state.current_page = "Results"
            st.rerun()


# ── Main renderer ────────────────────────────────────────────────────────────

def render_assessment():
    """Render the wizard-style assessment."""
    render_page_header("🔍", "Risk Assessment", "Answer questions to identify risks and get tailored security recommendations.")
    _render_db_controls()

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
