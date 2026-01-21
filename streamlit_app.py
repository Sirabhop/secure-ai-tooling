"""Main Streamlit app for CoSAI Risk Map."""
import streamlit as st
import sys
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent))
from app.data_loader import RiskMapDataLoader, DataLoadError
from app.ui_utils import inject_custom_css, render_info_box

# Page config
st.set_page_config(
    page_title="CoSAI Risk Map",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': "CoSAI Risk Map - Coalition for Secure AI Risk Assessment Tool"
    }
)

# Inject custom CSS
inject_custom_css()

# Initialize session state
if 'data_loader' not in st.session_state:
    try:
        st.session_state.data_loader = RiskMapDataLoader()
        # Validate data loading
        if st.session_state.data_loader.has_load_errors():
            errors = st.session_state.data_loader.get_load_errors()
            st.error(f"⚠️ Data loading errors detected: {', '.join(errors.keys())}")
    except DataLoadError as e:
        st.error(f"❌ Failed to initialize data loader: {str(e)}")
        st.stop()
    except Exception as e:
        st.error(f"❌ Unexpected error initializing application: {str(e)}")
        st.stop()

if 'answers' not in st.session_state:
    st.session_state.answers = {}

if 'selected_personas' not in st.session_state:
    st.session_state.selected_personas = []

if 'current_page' not in st.session_state:
    st.session_state.current_page = "Home"

# Sidebar navigation
st.sidebar.title("🛡️ CoSAI Risk Map")
st.sidebar.markdown("---")

# Navigation menu
nav_options = ["Home", "Assessment", "Control Mapping", "Risk Analysis"]
try:
    current_index = nav_options.index(st.session_state.current_page)
except ValueError:
    current_index = 0

page = st.sidebar.radio(
    "Navigation",
    nav_options,
    index=current_index,
    label_visibility="visible"
)

st.session_state.current_page = page

st.sidebar.markdown("---")

# Assessment progress indicator
if st.session_state.answers:
    loader = st.session_state.data_loader
    all_questions = loader.get_questions()
    relevant_questions = [
        q for q in all_questions 
        if any(p in st.session_state.selected_personas for p in q.get('personas', []))
    ]
    answered_count = len(st.session_state.answers)
    total_count = len(relevant_questions)
    
    if total_count > 0:
        progress = answered_count / total_count
        st.sidebar.progress(progress)
        st.sidebar.caption(f"Assessment: {answered_count}/{total_count}")

st.sidebar.markdown("---")
st.sidebar.markdown("""
### About
The **Coalition for Secure AI Risk Map** helps identify and mitigate security risks in AI systems.

[Learn More](https://github.com/CoalitionForSecureAI/secure-ai-tooling)
""")

# Route to appropriate page
if page == "Home":
    st.title("🛡️ Coalition for Secure AI Risk Map")
    st.markdown("---")
    
    # Hero section
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
        ### Welcome to the CoSAI Risk Assessment Tool
        
        This interactive tool helps you assess your AI security posture and identify 
        relevant risks and controls for your organization.
        """)
    
    with col2:
        loader = st.session_state.data_loader
        total_risks = len(loader.risks)
        total_controls = len(loader.controls)
        st.metric("Risks Cataloged", total_risks)
        st.metric("Controls Available", total_controls)
    
    st.markdown("---")
    
    # How it works section
    st.subheader("📋 How It Works")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        #### 🔍 Step 1: Assessment
        Answer questions about your AI implementation based on your role.
        """)
    
    with col2:
        st.markdown("""
        #### 🛡️ Step 2: Control Mapping
        View recommended security controls that address your identified risks.
        """)
    
    with col3:
        st.markdown("""
        #### 📊 Step 3: Risk Analysis
        Explore detailed information about risks and mitigation strategies.
        """)
    
    st.markdown("---")
    
    # Information sections
    col1, col2 = st.columns(2)
    
    with col1:
        with st.container():
            st.markdown("""
            ### 🎯 About CoSAI Risk Map
            
            The **Coalition for Secure AI Risk Map** provides a comprehensive framework 
            for identifying, analyzing, and mitigating security risks in AI systems.
            
            **Key Elements:**
            - **Components**: Fundamental building blocks of AI systems
            - **Risks**: Potential security threats and vulnerabilities
            - **Controls**: Security measures to mitigate risks
            - **Personas**: Key roles (Model Creator, Model Consumer)
            """)
    
    with col2:
        with st.container():
            st.markdown("""
            ### 🔗 Framework Mappings
            
            The CoSAI Risk Map includes mappings to established security frameworks:
            
            - **MITRE ATLAS** - Adversarial Threat Landscape for AI Systems
            - **NIST AI RMF** - NIST Artificial Intelligence Risk Management Framework
            - **STRIDE** - Microsoft Threat Modeling Framework
            - **OWASP Top 10 for LLM** - Top security risks for Large Language Models
            """)
    
    st.markdown("---")
    
    # CTA section
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🚀 Start Assessment", type="primary", use_container_width=True):
            st.session_state.current_page = "Assessment"
            st.rerun()
    
    # Quick stats if assessment started
    if st.session_state.answers:
        st.markdown("---")
        with st.expander("📊 Your Assessment Progress", expanded=False):
            loader = st.session_state.data_loader
            relevant_risks = loader.calculate_relevant_risks(
                st.session_state.answers,
                st.session_state.selected_personas
            )
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Questions Answered", len(st.session_state.answers))
            with col2:
                st.metric("Risks Identified", len(relevant_risks))

elif page == "Assessment":
    try:
        from app.pages.assessment import render_assessment
        render_assessment()
    except Exception as e:
        st.error(f"❌ Error loading assessment page: {str(e)}")
        st.exception(e)

elif page == "Control Mapping":
    try:
        from app.pages.control_mapping import render_control_mapping
        render_control_mapping()
    except Exception as e:
        st.error(f"❌ Error loading control mapping page: {str(e)}")
        st.exception(e)

elif page == "Risk Analysis":
    try:
        from app.pages.risk_analysis import render_risk_analysis
        render_risk_analysis()
    except Exception as e:
        st.error(f"❌ Error loading risk analysis page: {str(e)}")
        st.exception(e)
