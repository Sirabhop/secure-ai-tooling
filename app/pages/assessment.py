"""Assessment page for CoSAI Risk Map."""
import streamlit as st
from app.ui_utils import render_progress_bar, render_info_box


def render_assessment():
    """Render the assessment page."""
    st.title("🔍 AI Security Risk Assessment")
    st.markdown("---")
    
    loader = st.session_state.data_loader
    
    # Step 1: Persona Selection
    st.header("Step 1: Select Your Role")
    
    # Get persona question
    persona_question = loader.get_persona_question()
    personas_data = loader.personas
    
    if not persona_question:
        st.error("❌ Unable to load persona question. Please check data files.")
        return
    
    persona_text = loader.format_text_list(persona_question.get('text', []))
    if persona_text:
        st.markdown(f"**{persona_text}**")
    
    # Persona selection with better UI
    persona_options = {}
    persona_descriptions = {}
    
    for answer in persona_question.get('answers', []):
        persona_id = answer.get('label', '')
        if not persona_id:
            continue
        persona_info = personas_data.get(persona_id, {})
        display_name = persona_info.get('title', persona_id)
        persona_options[display_name] = persona_id
        persona_descriptions[display_name] = loader.format_text_list(
            persona_info.get('description', [])
        )
    
    if not persona_options:
        st.error("❌ No personas available. Please check data files.")
        return
    
    selected_persona_names = st.multiselect(
        "Select all roles that apply to you:",
        options=list(persona_options.keys()),
        default=[name for name in persona_options.keys() 
                if persona_options[name] in st.session_state.selected_personas],
        help="You can select multiple roles if they apply to your organization."
    )
    
    # Show persona descriptions
    if selected_persona_names:
        with st.expander("📋 Selected Role Details", expanded=False):
            for name in selected_persona_names:
                desc = persona_descriptions.get(name, "No description available.")
                st.markdown(f"**{name}**")
                if desc:
                    st.caption(desc)
    
    # Update selected personas
    st.session_state.selected_personas = [
        persona_options[name] for name in selected_persona_names
    ]
    
    if not st.session_state.selected_personas:
        render_info_box("Please select at least one role to continue with the assessment.", "warning")
        return
    
    st.markdown("---")
    
    # Get questions filtered by selected personas
    all_questions = loader.get_questions()
    relevant_questions = [
        q for q in all_questions 
        if any(p in st.session_state.selected_personas for p in q.get('personas', []))
    ]
    
    if not relevant_questions:
        render_info_box("No questions available for the selected roles.", "warning")
        return
    
    # Step 2: Questions
    st.header("Step 2: Answer Assessment Questions")
    
    # Progress indicator
    answered_count = sum(1 for q in relevant_questions if q.get('id') in st.session_state.answers)
    total_count = len(relevant_questions)
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"**{total_count} questions** based on your selected roles")
    with col2:
        if total_count > 0:
            progress = answered_count / total_count
            st.metric("Progress", f"{answered_count}/{total_count}")
    
    render_progress_bar(answered_count, total_count, "Assessment Progress")
    
    st.markdown("---")
    
    # Render questions with improved UI
    for idx, question in enumerate(relevant_questions, 1):
        q_id = question.get('id')
        if not q_id:
            continue
        
        q_text = loader.format_text_list(question.get('text', []))
        if not q_text:
            continue
        
        # Question container
        with st.container():
            # Question header with status indicator
            col1, col2 = st.columns([5, 1])
            with col1:
                st.subheader(f"Question {idx} of {total_count}")
            with col2:
                if q_id in st.session_state.answers:
                    st.success("✓")
                else:
                    st.info("○")
            
            st.markdown(f"**{q_text}**")
            
            # Get answer options
            answer_options_list = question.get('answers', [])
            if not answer_options_list:
                st.warning("⚠️ No answer options available for this question.")
                continue
            
            answer_options = {}
            for ans in answer_options_list:
                label = ans.get('label', '')
                if label:
                    answer_options[label] = label
            
            if not answer_options:
                st.warning("⚠️ Invalid answer options for this question.")
                continue
            
            # Get current answer
            current_answer = st.session_state.answers.get(q_id, None)
            
            # Radio buttons with better styling
            selected = st.radio(
                "Select your answer:",
                options=list(answer_options.keys()),
                key=f"q_{q_id}",
                index=list(answer_options.keys()).index(current_answer) if current_answer in answer_options else 0,
                horizontal=False
            )
            
            # Store answer
            st.session_state.answers[q_id] = selected
            
            # Show question context if available
            question_personas = question.get('personas', [])
            if question_personas:
                persona_names = [loader.personas.get(p, {}).get('title', p) for p in question_personas]
                st.caption(f"📌 Applies to: {', '.join(persona_names)}")
        
        if idx < total_count:
            st.markdown("---")
    
    st.markdown("---")
    
    # Navigation and actions
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if st.button("🔄 Reset Assessment", use_container_width=True):
            st.session_state.answers = {}
            st.session_state.selected_personas = []
            st.session_state.relevant_risks = []
            st.rerun()
    
    with col2:
        if st.button("💾 Save Progress", use_container_width=True, disabled=True):
            # Future: Implement save functionality
            st.info("Save functionality coming soon!")
    
    with col3:
        all_answered = answered_count == total_count
        button_label = "➡️ View Control Mapping" if all_answered else f"➡️ View Results ({answered_count}/{total_count})"
        
        if st.button(button_label, use_container_width=True, type="primary"):
            if not all_answered:
                render_info_box(
                    f"You have answered {answered_count} out of {total_count} questions. "
                    "You can still view results, but completing all questions provides better insights.",
                    "warning"
                )
            
            # Calculate relevant risks
            try:
                relevant_risks = loader.calculate_relevant_risks(
                    st.session_state.answers,
                    st.session_state.selected_personas
                )
                st.session_state.relevant_risks = relevant_risks
                st.session_state.current_page = "Control Mapping"
                st.rerun()
            except Exception as e:
                st.error(f"Error calculating risks: {str(e)}")
    
    # Assessment summary
    if st.session_state.answers:
        st.markdown("---")
        with st.expander("📊 Assessment Summary", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Selected Roles:**")
                role_names = [personas_data.get(p, {}).get('title', p) for p in st.session_state.selected_personas]
                for role in role_names:
                    st.markdown(f"- {role}")
            
            with col2:
                st.metric("Questions Answered", f"{answered_count}/{total_count}")
            
            # Calculate risks preview
            try:
                relevant_risks = loader.calculate_relevant_risks(
                    st.session_state.answers,
                    st.session_state.selected_personas
                )
                
                st.markdown("**Relevant Risks Identified:**")
                st.metric("Total Risks", len(relevant_risks))
                
                if relevant_risks:
                    st.markdown("**Top Risks:**")
                    risk_titles = [
                        loader.risks.get(r, {}).get('title', r) 
                        for r in relevant_risks[:5]
                        if loader.risks.get(r)
                    ]
                    for risk_title in risk_titles:
                        st.markdown(f"- {risk_title}")
                    if len(relevant_risks) > 5:
                        st.caption(f"... and {len(relevant_risks) - 5} more")
                else:
                    render_info_box(
                        "Based on your answers, no specific risks were identified. "
                        "This may indicate good security practices in place.",
                        "success"
                    )
            except Exception as e:
                st.error(f"Error calculating risk summary: {str(e)}")
