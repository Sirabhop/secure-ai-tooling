"""Risk Analysis page for CoSAI Risk Map."""
import streamlit as st
from app.ui_utils import render_info_box, render_badge


def render_risk_analysis():
    """Render the risk analysis page."""
    st.title("📊 Risk Analysis & Control Details")
    st.markdown("---")
    
    # Check if assessment is complete
    if 'answers' not in st.session_state or not st.session_state.answers:
        render_info_box(
            "Please complete the assessment first to view detailed risk analysis.",
            "warning"
        )
        if st.button("🔍 Go to Assessment", use_container_width=True):
            st.session_state.current_page = "Assessment"
            st.rerun()
        return
    
    loader = st.session_state.data_loader
    
    # Get relevant risks
    if 'relevant_risks' not in st.session_state:
        try:
            st.session_state.relevant_risks = loader.calculate_relevant_risks(
                st.session_state.answers,
                st.session_state.get('selected_personas', [])
            )
        except Exception as e:
            st.error(f"Error calculating risks: {str(e)}")
            return
    
    relevant_risks = st.session_state.relevant_risks
    
    if not relevant_risks:
        render_info_box(
            "Based on your answers, no specific risks were identified.",
            "success"
        )
        return
    
    # Get recommended controls
    if 'recommended_controls' not in st.session_state:
        try:
            controls = loader.get_controls_for_risks(relevant_risks)
            st.session_state.recommended_controls = [c.get('id') for c in controls]
        except Exception as e:
            st.error(f"Error loading controls: {str(e)}")
            st.session_state.recommended_controls = []
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Risks", len(relevant_risks))
    with col2:
        total_controls = len(st.session_state.get('recommended_controls', []))
        st.metric("Total Controls", total_controls)
    with col3:
        # Count unique categories
        risk_categories = set()
        for risk_id in relevant_risks:
            risk = loader.get_risk_details(risk_id)
            if risk:
                category = risk.get('category', 'Unknown')
                risk_categories.add(category)
        st.metric("Risk Categories", len(risk_categories))
    with col4:
        # Average controls per risk
        if len(relevant_risks) > 0:
            avg_controls = total_controls / len(relevant_risks)
            st.metric("Avg Controls/Risk", f"{avg_controls:.1f}")
    
    st.markdown("---")
    
    st.header("🔍 Detailed Risk Analysis")
    st.caption(f"Select a risk from the {len(relevant_risks)} identified risks to view detailed analysis")
    
    # Risk selector with better formatting
    risk_options = {}
    for risk_id in relevant_risks:
        risk = loader.get_risk_details(risk_id)
        if risk:
            title = risk.get('title', risk_id)
            category = risk.get('category', 'Unknown')
            display_name = f"{title} ({category.replace('risks', '').strip()})"
            risk_options[display_name] = risk_id
    
    if not risk_options:
        st.error("No valid risks found.")
        return
    
    selected_display = st.selectbox(
        "Select a risk to analyze:",
        options=list(risk_options.keys()),
        index=0,
        help="Choose a risk to view detailed information, impact types, lifecycle stages, and recommended controls."
    )
    
    selected_risk_id = risk_options[selected_display]
    
    if selected_risk_id:
        risk = loader.get_risk_details(selected_risk_id)
        
        if risk:
            st.markdown("---")
            
            # Risk header with category badge
            col1, col2 = st.columns([4, 1])
            with col1:
                st.header(risk.get('title', selected_risk_id))
            with col2:
                category = risk.get('category', 'Unknown')
                category_clean = category.replace('risks', '').strip()
                render_badge(category_clean, "blue")
            
            # Short description
            short_desc = loader.format_text_list(risk.get('shortDescription', []))
            if short_desc:
                st.info(f"💡 {short_desc}")
            
            # Risk details in tabs
            tab1, tab2, tab3, tab4 = st.tabs(["📖 Description", "🎯 Impact & Lifecycle", "📚 Examples", "🔗 Frameworks"])
            
            with tab1:
                # Long description
                long_desc = loader.format_text_list(risk.get('longDescription', []))
                if long_desc:
                    st.markdown(long_desc)
                else:
                    st.info("No detailed description available.")
            
            with tab2:
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("Impact Types")
                    impact_types = risk.get('impactType', [])
                    if impact_types:
                        for it in impact_types:
                            render_badge(it, "orange")
                    else:
                        st.caption("No impact types specified.")
                
                with col2:
                    st.subheader("Lifecycle Stages")
                    lifecycle_stages = risk.get('lifecycleStage', [])
                    if lifecycle_stages:
                        for ls in lifecycle_stages:
                            render_badge(ls, "purple")
                    else:
                        st.caption("No lifecycle stages specified.")
            
            with tab3:
                examples = risk.get('examples', [])
                if examples:
                    st.subheader("Real-World Examples")
                    for idx, example in enumerate(examples, 1):
                        example_text = loader.format_text_list([example]) if isinstance(example, str) else str(example)
                        st.markdown(f"**Example {idx}:** {example_text}")
                else:
                    st.info("No examples available for this risk.")
            
            with tab4:
                mappings = risk.get('mappings', {})
                if mappings:
                    st.subheader("Framework Mappings")
                    for framework, framework_mappings in mappings.items():
                        if framework_mappings:
                            framework_name = framework.replace('-', ' ').title()
                            st.markdown(f"**{framework_name}:**")
                            mapping_badges = " ".join([f"`{m}`" for m in framework_mappings])
                            st.markdown(mapping_badges)
                            st.markdown("---")
                else:
                    st.info("No framework mappings available.")
            
            st.markdown("---")
            
            # Controls that mitigate this risk
            st.subheader("🛡️ Recommended Controls")
            control_ids = risk.get('controls', [])
            
            if control_ids:
                # Filter to only show controls relevant to user's risks
                relevant_control_ids = [cid for cid in control_ids if cid in st.session_state.get('recommended_controls', [])]
                
                if relevant_control_ids:
                    st.success(f"**{len(relevant_control_ids)} controls** from your assessment can help mitigate this risk:")
                    st.markdown("---")
                    
                    for control_id in relevant_control_ids:
                        control = loader.get_control_details(control_id)
                        if control:
                            _render_control_details(control, loader)
                    
                    # Show other controls if any
                    other_controls = [cid for cid in control_ids if cid not in relevant_control_ids]
                    if other_controls:
                        with st.expander(f"View {len(other_controls)} additional controls", expanded=False):
                            for control_id in other_controls:
                                control = loader.get_control_details(control_id)
                                if control:
                                    _render_control_details(control, loader)
                else:
                    # Show all controls if none are in recommended
                    st.write(f"**{len(control_ids)} controls** can help mitigate this risk:")
                    st.markdown("---")
                    for control_id in control_ids:
                        control = loader.get_control_details(control_id)
                        if control:
                            _render_control_details(control, loader)
            else:
                render_info_box(
                    "No specific controls mapped to this risk. Consider general security best practices.",
                    "info"
                )
            
            st.markdown("---")
    
    # Summary statistics
    st.markdown("---")
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
    
    # Navigation buttons
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔙 Back to Controls", use_container_width=True):
            st.session_state.current_page = "Control Mapping"
            st.rerun()
    
    with col2:
        if st.button("🔍 Back to Assessment", use_container_width=True):
            st.session_state.current_page = "Assessment"
            st.rerun()
    
    with col3:
        if st.button("🔄 Start New Assessment", use_container_width=True, type="primary"):
            # Reset session state
            st.session_state.answers = {}
            st.session_state.selected_personas = []
            st.session_state.relevant_risks = []
            st.session_state.recommended_controls = []
            st.session_state.current_page = "Assessment"
            st.rerun()


def _render_control_details(control, loader):
    """Render detailed control information."""
    title = control.get('title', control.get('id', 'Unknown'))
    
    with st.expander(f"🛡️ {title}", expanded=False):
        # Control description
        description = loader.format_text_list(control.get('description', []))
        if description:
            st.markdown("**Description:**")
            st.markdown(description)
        
        # Implementation details in columns
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
            category_clean = category.replace('controls', '').strip()
            if category_clean:
                st.markdown(f"**Category:** {category_clean}")
            
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
    
    st.markdown("---")
