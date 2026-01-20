"""Control Mapping page for CoSAI Risk Map."""
import streamlit as st


def render_control_mapping():
    """Render the control mapping page."""
    st.title("🛡️ Control Mapping")
    st.markdown("---")
    
    # Check if assessment is complete
    if 'answers' not in st.session_state or not st.session_state.answers:
        st.warning("⚠️ Please complete the assessment first.")
        return
    
    loader = st.session_state.data_loader
    
    # Calculate relevant risks if not already done
    if 'relevant_risks' not in st.session_state:
        st.session_state.relevant_risks = loader.calculate_relevant_risks(
            st.session_state.answers,
            st.session_state.get('selected_personas', [])
        )
    
    relevant_risks = st.session_state.relevant_risks
    
    if not relevant_risks:
        st.info("✅ Based on your answers, no specific risks were identified. This may indicate your organization has good security practices in place.")
        return
    
    # Get controls for these risks
    controls = loader.get_controls_for_risks(relevant_risks)
    
    st.header("Identified Risks")
    st.write(f"**{len(relevant_risks)} risks** identified based on your assessment")
    
    # Display risks
    risk_cols = st.columns(min(3, len(relevant_risks)))
    for idx, risk_id in enumerate(relevant_risks):
        risk = loader.get_risk_details(risk_id)
        if risk:
            col_idx = idx % len(risk_cols)
            with risk_cols[col_idx]:
                with st.container():
                    st.markdown(f"**{risk.get('title', risk_id)}**")
                    short_desc = loader.format_text_list(risk.get('shortDescription', []))
                    if short_desc:
                        st.caption(short_desc[:100] + "..." if len(short_desc) > 100 else short_desc)
    
    st.markdown("---")
    
    st.header("Recommended Controls")
    st.write(f"**{len(controls)} controls** recommended to mitigate the identified risks")
    
    # Group controls by category
    control_categories = {}
    for control in controls:
        category = control.get('category', 'Other')
        if category not in control_categories:
            control_categories[category] = []
        control_categories[category].append(control)
    
    # Display controls by category
    for category, category_controls in control_categories.items():
        st.subheader(category.replace('controls', '').replace('Control', '').strip())
        
        for control in category_controls:
            with st.expander(f"🛡️ {control.get('title', control.get('id', 'Unknown'))}", expanded=False):
                # Description
                description = loader.format_text_list(control.get('description', []))
                if description:
                    st.markdown(f"**Description:** {description}")
                
                # Applicable personas
                personas = control.get('personas', [])
                if personas:
                    persona_names = [loader.personas.get(p, {}).get('title', p) for p in personas]
                    st.markdown(f"**Applicable to:** {', '.join(persona_names)}")
                
                # Components
                components = control.get('components', [])
                if components:
                    st.markdown(f"**Applies to components:** {', '.join(components)}")
                
                # Mitigated risks
                mitigated_risks = control.get('risks', [])
                if mitigated_risks:
                    risk_titles = [loader.risks.get(r, {}).get('title', r) for r in mitigated_risks if r in relevant_risks]
                    if risk_titles:
                        st.markdown(f"**Mitigates:** {', '.join(risk_titles)}")
    
    st.markdown("---")
    
    # Store controls in session state for next page
    st.session_state.recommended_controls = [c.get('id') for c in controls]
