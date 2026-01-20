"""Assessment page for CoSAI Risk Map."""
import streamlit as st


def render_assessment():
    """Render the assessment page."""
    st.title("🔍 AI Security Risk Assessment")
    st.markdown("---")
    
    loader = st.session_state.data_loader
    
    st.header("Step 1: Select Your Role")
    
    # Get persona question
    persona_question = loader.get_persona_question()
    personas_data = loader.personas
    
    st.markdown(persona_question.get('text', [''])[0])
    
    # Persona selection
    persona_options = {}
    for answer in persona_question.get('answers', []):
        persona_id = answer['label']
        persona_info = personas_data.get(persona_id, {})
        display_name = persona_info.get('title', persona_id)
        persona_options[display_name] = persona_id
    
    selected_persona_names = st.multiselect(
        "Select all that apply:",
        options=list(persona_options.keys()),
        default=[name for name in persona_options.keys() 
                if persona_options[name] in st.session_state.selected_personas]
    )
    
    # Update selected personas
    st.session_state.selected_personas = [
        persona_options[name] for name in selected_persona_names
    ]
    
    if not st.session_state.selected_personas:
        st.warning("⚠️ Please select at least one role to continue.")
        return
    
    st.markdown("---")
    
    # Get questions filtered by selected personas
    all_questions = loader.get_questions()
    relevant_questions = [
        q for q in all_questions 
        if any(p in st.session_state.selected_personas for p in q.get('personas', []))
    ]
    
    st.header("Step 2: Answer Assessment Questions")
    st.markdown(f"**{len(relevant_questions)} questions** based on your selected roles")
    
    # Render questions
    for idx, question in enumerate(relevant_questions, 1):
        q_id = question['id']
        q_text = loader.format_text_list(question.get('text', []))
        
        st.subheader(f"Question {idx}")
        st.markdown(f"**{q_text}**")
        
        # Get answer options
        answer_options = {ans['label']: ans['label'] for ans in question.get('answers', [])}
        
        # Get current answer or default
        current_answer = st.session_state.answers.get(q_id, None)
        
        selected = st.radio(
            "Your answer:",
            options=list(answer_options.keys()),
            key=f"q_{q_id}",
            index=list(answer_options.keys()).index(current_answer) if current_answer else 0
        )
        
        st.session_state.answers[q_id] = selected
        st.markdown("---")
    
    # Navigation buttons
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if st.button("🔄 Reset Assessment", use_container_width=True):
            st.session_state.answers = {}
            st.session_state.selected_personas = []
            st.rerun()
    
    with col2:
        if st.button("➡️ View Control Mapping", use_container_width=True, type="primary"):
            # Calculate relevant risks
            relevant_risks = loader.calculate_relevant_risks(
                st.session_state.answers,
                st.session_state.selected_personas
            )
            st.session_state.relevant_risks = relevant_risks
            st.session_state.current_page = "Control Mapping"
            st.rerun()
    
    # Show summary if answers exist
    if st.session_state.answers:
        st.markdown("---")
        with st.expander("📊 Assessment Summary", expanded=False):
            st.write(f"**Selected Roles:** {', '.join([personas_data.get(p, {}).get('title', p) for p in st.session_state.selected_personas])}")
            st.write(f"**Questions Answered:** {len(st.session_state.answers)}/{len(relevant_questions)}")
            
            # Calculate risks preview
            relevant_risks = loader.calculate_relevant_risks(
                st.session_state.answers,
                st.session_state.selected_personas
            )
            st.write(f"**Relevant Risks Identified:** {len(relevant_risks)}")
            if relevant_risks:
                risk_titles = [loader.risks.get(r, {}).get('title', r) for r in relevant_risks[:5]]
                st.write("Top risks:", ", ".join(risk_titles))
                if len(relevant_risks) > 5:
                    st.write(f"... and {len(relevant_risks) - 5} more")
