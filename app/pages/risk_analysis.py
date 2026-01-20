"""Risk Analysis page for CoSAI Risk Map."""
import streamlit as st


def render_risk_analysis():
    """Render the risk analysis page."""
    st.title("📊 Risk Analysis & Control Details")
    st.markdown("---")
    
    # Check if assessment is complete
    if 'answers' not in st.session_state or not st.session_state.answers:
        st.warning("⚠️ Please complete the assessment first.")
        return
    
    loader = st.session_state.data_loader
    
    # Get relevant risks
    if 'relevant_risks' not in st.session_state:
        st.session_state.relevant_risks = loader.calculate_relevant_risks(
            st.session_state.answers,
            st.session_state.get('selected_personas', [])
        )
    
    relevant_risks = st.session_state.relevant_risks
    
    if not relevant_risks:
        st.info("✅ Based on your answers, no specific risks were identified.")
        return
    
    # Get recommended controls
    if 'recommended_controls' not in st.session_state:
        controls = loader.get_controls_for_risks(relevant_risks)
        st.session_state.recommended_controls = [c.get('id') for c in controls]
    
    st.header("Detailed Risk Analysis")
    st.write(f"Analyzing **{len(relevant_risks)} risks** identified in your assessment")
    
    # Risk selector
    selected_risk_id = st.selectbox(
        "Select a risk to view detailed analysis:",
        options=relevant_risks,
        format_func=lambda x: loader.risks.get(x, {}).get('title', x)
    )
    
    if selected_risk_id:
        risk = loader.get_risk_details(selected_risk_id)
        
        if risk:
            st.markdown("---")
            
            # Risk title and category
            col1, col2 = st.columns([3, 1])
            with col1:
                st.header(risk.get('title', selected_risk_id))
            with col2:
                category = risk.get('category', 'Unknown')
                st.caption(f"Category: {category.replace('risks', '').strip()}")
            
            # Short description
            short_desc = loader.format_text_list(risk.get('shortDescription', []))
            if short_desc:
                st.info(f"💡 {short_desc}")
            
            # Long description
            long_desc = loader.format_text_list(risk.get('longDescription', []))
            if long_desc:
                with st.expander("📖 Full Description", expanded=True):
                    st.markdown(long_desc)
            
            # Impact types
            impact_types = risk.get('impactType', [])
            if impact_types:
                st.subheader("Impact Types")
                impact_badges = " ".join([f"`{it}`" for it in impact_types])
                st.markdown(impact_badges)
            
            # Lifecycle stages
            lifecycle_stages = risk.get('lifecycleStage', [])
            if lifecycle_stages:
                st.subheader("Lifecycle Stages")
                lifecycle_badges = " ".join([f"`{ls}`" for ls in lifecycle_stages])
                st.markdown(lifecycle_badges)
            
            # Examples
            examples = risk.get('examples', [])
            if examples:
                st.subheader("Real-World Examples")
                for example in examples:
                    st.markdown(f"• {loader.format_text_list([example])}")
            
            # Framework mappings
            mappings = risk.get('mappings', {})
            if mappings:
                st.subheader("Framework Mappings")
                for framework, framework_mappings in mappings.items():
                    if framework_mappings:
                        framework_name = framework.replace('-', ' ').title()
                        mapping_badges = " ".join([f"`{m}`" for m in framework_mappings])
                        st.markdown(f"**{framework_name}:** {mapping_badges}")
            
            st.markdown("---")
            
            # Controls that mitigate this risk
            st.subheader("🛡️ Controls to Mitigate This Risk")
            control_ids = risk.get('controls', [])
            
            if control_ids:
                st.write(f"**{len(control_ids)} controls** can help mitigate this risk:")
                
                for control_id in control_ids:
                    control = loader.get_control_details(control_id)
                    if control:
                        with st.expander(f"🛡️ {control.get('title', control_id)}", expanded=False):
                            # Control description
                            description = loader.format_text_list(control.get('description', []))
                            if description:
                                st.markdown(f"**Description:** {description}")
                            
                            # Implementation details
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                # Personas
                                personas = control.get('personas', [])
                                if personas:
                                    persona_names = [loader.personas.get(p, {}).get('title', p) for p in personas]
                                    st.markdown(f"**Responsible:** {', '.join(persona_names)}")
                                
                                # Components
                                components = control.get('components', [])
                                if components:
                                    st.markdown(f"**Applies to:** {', '.join(components)}")
                            
                            with col2:
                                # Category
                                category = control.get('category', 'Unknown')
                                st.markdown(f"**Category:** {category.replace('controls', '').strip()}")
                                
                                # Lifecycle stages
                                lifecycle = control.get('lifecycleStage', [])
                                if lifecycle:
                                    st.markdown(f"**Lifecycle:** {', '.join(lifecycle)}")
                            
                            # Framework mappings
                            control_mappings = control.get('mappings', {})
                            if control_mappings:
                                st.markdown("**Framework Mappings:**")
                                for framework, framework_mappings in control_mappings.items():
                                    if framework_mappings:
                                        framework_name = framework.replace('-', ' ').title()
                                        mapping_badges = " ".join([f"`{m}`" for m in framework_mappings])
                                        st.markdown(f"- **{framework_name}:** {mapping_badges}")
            else:
                st.info("No specific controls mapped to this risk. Consider general security best practices.")
            
            st.markdown("---")
    
    # Summary statistics
    st.header("📈 Assessment Summary")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Risks Identified", len(relevant_risks))
    
    with col2:
        total_controls = len(st.session_state.get('recommended_controls', []))
        st.metric("Recommended Controls", total_controls)
    
    with col3:
        # Count unique categories
        risk_categories = set()
        for risk_id in relevant_risks:
            risk = loader.get_risk_details(risk_id)
            if risk:
                category = risk.get('category', 'Unknown')
                risk_categories.add(category)
        st.metric("Risk Categories", len(risk_categories))
    
    st.markdown("---")
    
    if st.button("🔄 Start New Assessment", use_container_width=True):
        # Reset session state
        st.session_state.answers = {}
        st.session_state.selected_personas = []
        st.session_state.relevant_risks = []
        st.session_state.recommended_controls = []
        st.session_state.current_page = "Assessment"
        st.rerun()
