"""Assessment page for CoSAI Risk Map."""
import streamlit as st
from app.ui_utils import render_progress_bar, render_info_box


def _render_question_text(loader, text_items: list) -> None:
    """Render question text: first item as headline, rest as question (if multiple items)."""
    items = [t for t in (text_items or []) if t]
    if not items:
        return
    if len(items) == 1:
        st.markdown(f"**{items[0]}**")
    else:
        st.markdown(f"**{items[0]}**")
        st.markdown(loader.format_text_list(items[1:]))


def _format_use_case_label(label: str) -> str:
    """Format use case label for display (e.g. camelCase -> Title Case)."""
    if not label:
        return label
    return "".join(" " + c if c.isupper() else c for c in label).strip().replace(" Or ", " or ").title()


def render_assessment():
    """Render unified assessment (use cases → tier questions → personas → risk questions)."""
    st.title("🔍 AI Security Risk Assessment")
    st.markdown("---")

    loader = st.session_state.data_loader
    vayu_config = loader.get_vayu_config()
    vayu_questions = loader.get_vayu_questions()
    vayu_use_cases = loader.get_vayu_use_cases()

    if not vayu_config or not vayu_questions:
        st.error("❌ Assessment not fully configured. Please check data files.")
        return

    if "selected_use_cases" not in st.session_state:
        st.session_state.selected_use_cases = []

    # Step 1: Use cases
    st.header("Step 1: Select Use Cases")
    use_case_text = loader.format_text_list(vayu_use_cases.get("text", []))
    if use_case_text:
        st.markdown(f"**{use_case_text}**")
    use_case_options = {}
    for ans in vayu_use_cases.get("answers", []):
        label = ans.get("label", "")
        if label:
            use_case_options[_format_use_case_label(label)] = label
    selected_names = st.multiselect(
        "Select all that describe this AI system:",
        options=list(use_case_options.keys()),
        default=[n for n in use_case_options.keys() if use_case_options[n] in st.session_state.selected_use_cases],
        key="use_cases_multiselect",
    )
    st.session_state.selected_use_cases = [use_case_options[n] for n in selected_names]
    st.markdown("---")

    # Step 2: Tier questions (vayu)
    st.header("Step 2: Answer Context Questions")
    vayu_answered = sum(1 for q in vayu_questions if q.get("id") in st.session_state.answers)
    vayu_total = len(vayu_questions)
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"**{vayu_total} questions**")
    with col2:
        st.metric("Progress", f"{vayu_answered}/{vayu_total}")
    render_progress_bar(vayu_answered, vayu_total, "Progress")
    st.markdown("---")

    for idx, question in enumerate(vayu_questions, 1):
        q_id = question.get("id")
        if not q_id:
            continue
        text_items = question.get("text", [])
        if not text_items:
            continue
        with st.container():
            col1, col2 = st.columns([5, 1])
            with col1:
                st.markdown(f"**Question {idx} of {vayu_total}**")
            with col2:
                st.success("✓") if q_id in st.session_state.answers else st.info("○")
            _render_question_text(loader, text_items)
            answer_options_list = question.get("answers", [])
            if not answer_options_list:
                continue
            answer_options = {a["label"]: a["label"] for a in answer_options_list if a.get("label")}
            if not answer_options:
                continue
            current = st.session_state.answers.get(q_id)
            selected = st.radio(
                "Select your answer:",
                options=list(answer_options.keys()),
                key=f"q_{q_id}",
                index=list(answer_options.keys()).index(current) if current in answer_options else 0,
            )
            st.session_state.answers[q_id] = selected
        if idx < vayu_total:
            st.markdown("---")

    st.markdown("---")

    # Step 3: Personas
    st.header("Step 3: Select Your Role")
    persona_question = loader.get_persona_question()
    personas_data = loader.personas
    if not persona_question:
        st.error("❌ Unable to load role question. Please check data files.")
        return
    persona_text = loader.format_text_list(persona_question.get("text", []))
    if persona_text:
        st.markdown(f"**{persona_text}**")
    persona_options = {}
    persona_descriptions = {}
    for answer in persona_question.get("answers", []):
        persona_id = answer.get("label", "")
        if not persona_id:
            continue
        persona_info = personas_data.get(persona_id, {})
        display_name = persona_info.get("title", persona_id)
        persona_options[display_name] = persona_id
        persona_descriptions[display_name] = loader.format_text_list(persona_info.get("description", []))
    if not persona_options:
        st.error("❌ No roles available. Please check data files.")
        return
    selected_persona_names = st.multiselect(
        "Select all roles that apply to you:",
        options=list(persona_options.keys()),
        default=[n for n in persona_options.keys() if persona_options[n] in st.session_state.selected_personas],
        help="You can select multiple roles if they apply to your organization.",
    )
    st.session_state.selected_personas = [persona_options[n] for n in selected_persona_names]
    if selected_persona_names:
        with st.expander("📋 Selected Role Details", expanded=False):
            for name in selected_persona_names:
                desc = persona_descriptions.get(name, "No description available.")
                st.markdown(f"**{name}**")
                if desc:
                    st.caption(desc)
    if not st.session_state.selected_personas:
        render_info_box("Please select at least one role to continue.", "warning")
        return
    st.markdown("---")

    # Step 4: Risk questions
    st.header("Step 4: Answer Risk Questions")
    all_risk_questions = loader.get_questions()
    relevant_questions = [
        q for q in all_risk_questions
        if any(p in st.session_state.selected_personas for p in q.get("personas", []))
    ]
    if not relevant_questions:
        render_info_box("No questions available for the selected roles.", "warning")
        return
    risk_answered = sum(1 for q in relevant_questions if q.get("id") in st.session_state.answers)
    risk_total = len(relevant_questions)
    total_questions = vayu_total + risk_total
    total_answered = vayu_answered + risk_answered
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"**{risk_total} questions** based on your roles")
    with col2:
        st.metric("Progress", f"{total_answered}/{total_questions}")
    render_progress_bar(total_answered, total_questions, "Progress")
    st.markdown("---")

    for idx, question in enumerate(relevant_questions, 1):
        q_id = question.get("id")
        if not q_id:
            continue
        text_items = question.get("text", [])
        if not text_items:
            continue
        with st.container():
            col1, col2 = st.columns([5, 1])
            with col1:
                st.markdown(f"**Question {idx} of {risk_total}**")
            with col2:
                st.success("✓") if q_id in st.session_state.answers else st.info("○")
            _render_question_text(loader, text_items)
            answer_options_list = question.get("answers", [])
            if not answer_options_list:
                continue
            answer_options = {a["label"]: a["label"] for a in answer_options_list if a.get("label")}
            if not answer_options:
                continue
            current_answer = st.session_state.answers.get(q_id)
            selected = st.radio(
                "Select your answer:",
                options=list(answer_options.keys()),
                key=f"risk_q_{q_id}",
                index=list(answer_options.keys()).index(current_answer) if current_answer in answer_options else 0,
            )
            st.session_state.answers[q_id] = selected
            question_personas = question.get("personas", [])
            if question_personas:
                persona_names = [loader.personas.get(p, {}).get("title", p) for p in question_personas]
                st.caption(f"📌 Applies to: {', '.join(persona_names)}")
        if idx < risk_total:
            st.markdown("---")

    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("🔄 Reset Assessment", use_container_width=True):
            st.session_state.answers = {}
            st.session_state.selected_personas = []
            st.session_state.selected_use_cases = []
            st.session_state.relevant_risks = []
            st.session_state.vayu_result = None
            st.rerun()
    with col2:
        st.button("💾 Save Progress", use_container_width=True, disabled=True)
    with col3:
        all_done = total_answered == total_questions
        btn_label = "➡️ View Results" if all_done else f"➡️ View Results ({total_answered}/{total_questions})"
        if st.button(btn_label, use_container_width=True, type="primary"):
            if not all_done:
                render_info_box(
                    f"You have answered {total_answered} of {total_questions} questions. "
                    "You can still view results, but completing all questions provides better insights.",
                    "warning",
                )
            try:
                st.session_state.vayu_result = loader.calculate_vayu_tier(
                    st.session_state.selected_use_cases,
                    st.session_state.answers,
                )
                st.session_state.relevant_risks = loader.calculate_relevant_risks(
                    st.session_state.answers,
                    st.session_state.selected_personas,
                )
                st.session_state.current_page = "Control Mapping"
                st.rerun()
            except Exception as e:
                st.error(f"Error calculating results: {str(e)}")

    if st.session_state.answers:
        st.markdown("---")
        with st.expander("📊 Summary", expanded=False):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Questions Answered", f"{total_answered}/{total_questions}")
            try:
                vayu = loader.calculate_vayu_tier(
                    st.session_state.selected_use_cases,
                    st.session_state.answers,
                )
                with col2:
                    st.metric("Risk Tier", vayu.get("label", "—").upper())
            except Exception:
                pass
            try:
                risks = loader.calculate_relevant_risks(
                    st.session_state.answers,
                    st.session_state.selected_personas,
                )
                with col3:
                    st.metric("Risks Identified", len(risks))
            except Exception:
                pass
