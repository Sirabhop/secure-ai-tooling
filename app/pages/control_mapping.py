"""Control Mapping page for CoSAI Risk Map."""
import streamlit as st
from app.ui_utils import render_info_box, render_badge, render_risk_card, render_control_card


def render_control_mapping():
    """Render the control mapping page."""
    st.title("🛡️ Control Mapping")
    st.markdown("---")

    if 'answers' not in st.session_state or not st.session_state.answers:
        render_info_box(
            "Please complete the assessment first to view recommended controls.",
            "warning"
        )
        if st.button("🔍 Go to Assessment", use_container_width=True):
            st.session_state.current_page = "Assessment"
            st.rerun()
        return

    loader = st.session_state.data_loader

    # Tier summary (from context questions)
    vayu = st.session_state.get("vayu_result")
    if not vayu:
        try:
            vayu = loader.calculate_vayu_tier(
                st.session_state.get("selected_use_cases", []),
                st.session_state.answers,
            )
        except Exception:
            vayu = {}
    if vayu:
        tier = vayu.get("label", "low").upper()
        tier_colors = {"LOW": "green", "MEDIUM": "orange", "HIGH": "red", "UNACCEPTABLE": "red"}
        st.metric("Risk Tier", tier)
        render_badge(tier, tier_colors.get(tier, "gray"))
        if vayu.get("escalatedRules"):
            with st.expander("Escalation triggers", expanded=False):
                for r in vayu["escalatedRules"]:
                    st.markdown(f"- {r}")
        st.markdown("---")

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
            "Based on your answers, no specific risks were identified. "
            "This may indicate your organization has good security practices in place.",
            "success"
        )
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔙 Back to Assessment", use_container_width=True):
                st.session_state.current_page = "Assessment"
                st.rerun()
        return

    # Get controls for these risks
    try:
        controls = loader.get_controls_for_risks(relevant_risks)
    except Exception as e:
        st.error(f"Error loading controls: {str(e)}")
        return
    
    # Summary metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Risks Identified", len(relevant_risks))
    with col2:
        st.metric("Recommended Controls", len(controls))
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
    
    # Identified Risks Section
    st.header("📋 Identified Risks")
    st.caption(f"{len(relevant_risks)} risks identified based on your assessment")
    
    # Display risks in a more organized way
    if len(relevant_risks) <= 6:
        # Show in columns for small lists
        num_cols = min(3, len(relevant_risks))
        risk_cols = st.columns(num_cols)
        for idx, risk_id in enumerate(relevant_risks):
            risk = loader.get_risk_details(risk_id)
            if risk:
                col_idx = idx % num_cols
                with risk_cols[col_idx]:
                    with st.container():
                        title = risk.get('title', risk_id)
                        st.markdown(f"**{title}**")
                        short_desc = loader.format_text_list(risk.get('shortDescription', []))
                        if short_desc:
                            st.caption(short_desc[:80] + "..." if len(short_desc) > 80 else short_desc)
                        category = risk.get('category', 'Unknown')
                        render_badge(category.replace('risks', '').strip(), "blue")
    else:
        # Show in expandable sections for larger lists
        with st.expander(f"View all {len(relevant_risks)} identified risks", expanded=False):
            for risk_id in relevant_risks:
                risk = loader.get_risk_details(risk_id)
                if risk:
                    st.markdown(f"**{risk.get('title', risk_id)}**")
                    short_desc = loader.format_text_list(risk.get('shortDescription', []))
                    if short_desc:
                        st.caption(short_desc)
                    st.markdown("---")
    
    st.markdown("---")
    
    # Recommended Controls Section
    st.header("🛡️ Recommended Controls")
    st.caption(f"{len(controls)} controls recommended to mitigate the identified risks")
    
    if not controls:
        render_info_box(
            "No specific controls found for the identified risks. "
            "Consider general security best practices.",
            "info"
        )
        return
    
    # Group controls by category
    control_categories = {}
    for control in controls:
        category = control.get('category', 'Other')
        category_clean = category.replace('controls', '').replace('Control', '').strip() or 'Other'
        if category_clean not in control_categories:
            control_categories[category_clean] = []
        control_categories[category_clean].append(control)
    
    # Display controls by category with tabs
    if len(control_categories) > 1:
        category_tabs = st.tabs(list(control_categories.keys()))
        for tab, (category, category_controls) in zip(category_tabs, control_categories.items()):
            with tab:
                st.markdown(f"**{len(category_controls)} controls** in this category")
                st.markdown("---")
                _render_controls_list(category_controls, loader, relevant_risks)
    else:
        # Single category, no tabs needed
        for category, category_controls in control_categories.items():
            _render_controls_list(category_controls, loader, relevant_risks)
    
    st.markdown("---")
    
    # Navigation
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔙 Back to Assessment", use_container_width=True):
            st.session_state.current_page = "Assessment"
            st.rerun()
    with col2:
        if st.button("📊 View Risk Analysis →", use_container_width=True, type="primary"):
            st.session_state.current_page = "Risk Analysis"
            st.rerun()
    
    # Store controls in session state for next page
    st.session_state.recommended_controls = [c.get('id') for c in controls]


def _render_controls_list(controls, loader, relevant_risks):
    """Render a list of controls."""
    for idx, control in enumerate(controls, 1):
        control_id = control.get('id', f'control_{idx}')
        title = control.get('title', control_id)
        
        with st.expander(f"🛡️ {title}", expanded=False):
            # Description
            description = loader.format_text_list(control.get('description', []))
            if description:
                st.markdown("**Description:**")
                st.markdown(description)
            
            # Metadata in columns
            col1, col2 = st.columns(2)
            
            with col1:
                # Applicable personas
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
            
            # Mitigated risks (only show relevant ones)
            mitigated_risks = control.get('risks', [])
            relevant_mitigated = [r for r in mitigated_risks if r in relevant_risks]
            if relevant_mitigated:
                st.markdown("**Mitigates these risks:**")
                for risk_id in relevant_mitigated:
                    risk = loader.get_risk_details(risk_id)
                    if risk:
                        st.markdown(f"- {risk.get('title', risk_id)}")
            
            # Framework mappings
            mappings = control.get('mappings', {})
            if mappings:
                st.markdown("**Framework Mappings:**")
                for framework, framework_mappings in mappings.items():
                    if framework_mappings:
                        framework_name = framework.replace('-', ' ').title()
                        mapping_badges = " ".join([f"`{m}`" for m in framework_mappings])
                        st.markdown(f"- **{framework_name}:** {mapping_badges}")
        
        if idx < len(controls):
            st.markdown("---")
