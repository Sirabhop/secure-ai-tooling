"""Main Streamlit app for CoSAI Risk Map."""
import streamlit as st
import sys
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent))
from app.data_loader import RiskMapDataLoader

# Page config
st.set_page_config(
    page_title="CoSAI Risk Map",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'data_loader' not in st.session_state:
    st.session_state.data_loader = RiskMapDataLoader()

if 'answers' not in st.session_state:
    st.session_state.answers = {}

if 'selected_personas' not in st.session_state:
    st.session_state.selected_personas = []

# Sidebar navigation
st.sidebar.title("🛡️ CoSAI Risk Map")
st.sidebar.markdown("---")

# Initialize page state
if 'current_page' not in st.session_state:
    st.session_state.current_page = "Home"

page = st.sidebar.radio(
    "Navigation",
    ["Home", "Assessment", "Control Mapping", "Risk Analysis"],
    index=["Home", "Assessment", "Control Mapping", "Risk Analysis"].index(st.session_state.current_page)
)

st.session_state.current_page = page

st.sidebar.markdown("---")
st.sidebar.markdown("""
### About
The Coalition for Secure AI Risk Map helps identify and mitigate security risks in AI systems.
""")

# Route to appropriate page
if page == "Home":
    st.title("🛡️ Coalition for Secure AI Risk Map")
    st.markdown("---")
    
    st.markdown("""
    ### Welcome to the CoSAI Risk Assessment Tool
    
    This interactive tool helps you assess your AI security posture and identify 
    relevant risks and controls for your organization.
    
    **How it works:**
    
    1. **🔍 Assessment** - Answer questions about your AI implementation
    2. **🛡️ Control Mapping** - See which security controls address your risks
    3. **📊 Risk Analysis** - Get detailed information about risks and mitigation strategies
    
    ---
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        ### About CoSAI Risk Map
        
        The **Coalition for Secure AI Risk Map** provides a framework for identifying, 
        analyzing, and mitigating security risks in Artificial Intelligence systems.
        
        - **Components**: Fundamental building blocks of AI systems
        - **Risks**: Potential security threats
        - **Controls**: Security measures to mitigate risks
        - **Personas**: Key roles (Model Creator, Model Consumer)
        """)
    
    with col2:
        st.markdown("""
        ### Framework Mappings
        
        The CoSAI Risk Map includes mappings to established security frameworks:
        
        - **MITRE ATLAS** - Adversarial Threat Landscape for AI Systems
        - **NIST AI RMF** - NIST Artificial Intelligence Risk Management Framework
        - **STRIDE** - Microsoft Threat Modeling Framework
        - **OWASP Top 10 for LLM** - Top security risks for Large Language Models
        """)
    
    st.markdown("---")
    
    if st.button("🚀 Start Assessment", type="primary", use_container_width=True):
        st.session_state.current_page = "Assessment"
        st.rerun()

elif page == "Assessment":
    from app.pages.assessment import render_assessment
    render_assessment()

elif page == "Control Mapping":
    from app.pages.control_mapping import render_control_mapping
    render_control_mapping()

elif page == "Risk Analysis":
    from app.pages.risk_analysis import render_risk_analysis
    render_risk_analysis()
