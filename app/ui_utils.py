"""UI utilities and styling for Streamlit app."""
import streamlit as st
from typing import List, Dict, Any


def inject_custom_css():
    """Inject custom CSS for modern, beautiful UI."""
    st.markdown("""
    <style>
    /* Main styling improvements */
    .main {
        padding-top: 2rem;
    }
    
    /* Header styling */
    h1 {
        color: #1f77b4;
        border-bottom: 3px solid #1f77b4;
        padding-bottom: 0.5rem;
        margin-bottom: 1.5rem;
    }
    
    h2 {
        color: #2c3e50;
        margin-top: 2rem;
        margin-bottom: 1rem;
    }
    
    h3 {
        color: #34495e;
        margin-top: 1.5rem;
    }
    
    /* Card-like containers */
    .stContainer {
        background-color: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 4px solid #1f77b4;
        margin-bottom: 1rem;
    }
    
    /* Metric cards */
    [data-testid="stMetricValue"] {
        font-size: 2rem;
        font-weight: bold;
    }
    
    /* Button improvements */
    .stButton > button {
        width: 100%;
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    
    /* Sidebar improvements */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1f77b4 0%, #2c3e50 100%);
    }
    
    [data-testid="stSidebar"] .css-1d391kg {
        color: white;
    }
    
    [data-testid="stSidebar"] h1, 
    [data-testid="stSidebar"] h2, 
    [data-testid="stSidebar"] h3 {
        color: white;
    }
    
    /* Progress bar */
    .progress-container {
        background-color: #e9ecef;
        border-radius: 10px;
        padding: 1rem;
        margin: 1rem 0;
    }
    
    /* Badge styling */
    .badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        background-color: #1f77b4;
        color: white;
        border-radius: 12px;
        font-size: 0.875rem;
        margin: 0.25rem;
    }
    
    /* Info boxes */
    .info-box {
        background-color: #e7f3ff;
        border-left: 4px solid #1f77b4;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    
    /* Success styling */
    .success-box {
        background-color: #d4edda;
        border-left: 4px solid #28a745;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    
    /* Warning styling */
    .warning-box {
        background-color: #fff3cd;
        border-left: 4px solid #ffc107;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    
    /* Risk/Control cards */
    .risk-card, .control-card {
        background: white;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        transition: box-shadow 0.3s ease;
    }
    
    .risk-card:hover, .control-card:hover {
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
    }
    
    /* Expander styling */
    .streamlit-expanderHeader {
        font-weight: 600;
        color: #2c3e50;
    }
    
    /* Radio button improvements */
    .stRadio > div {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
    }
    
    /* Selectbox improvements */
    .stSelectbox > div > div {
        background-color: white;
    }
    
    /* Footer */
    .footer {
        margin-top: 3rem;
        padding-top: 2rem;
        border-top: 2px solid #dee2e6;
        text-align: center;
        color: #6c757d;
    }
    </style>
    """, unsafe_allow_html=True)


def render_progress_bar(current: int, total: int, label: str = "Progress"):
    """Render a progress bar."""
    if total == 0:
        return
    
    progress = current / total
    st.progress(progress)
    st.caption(f"{label}: {current}/{total} ({progress*100:.0f}%)")


def render_metric_card(label: str, value: Any, delta: str = None):
    """Render a metric card."""
    st.metric(label, value, delta)


def render_badge(text: str, color: str = "blue"):
    """Render a styled badge."""
    color_map = {
        "blue": "#1f77b4",
        "green": "#28a745",
        "orange": "#ffc107",
        "red": "#dc3545",
        "purple": "#6f42c1"
    }
    color_hex = color_map.get(color, color_map["blue"])
    st.markdown(
        f'<span class="badge" style="background-color: {color_hex}">{text}</span>',
        unsafe_allow_html=True
    )


def render_info_box(message: str, type: str = "info"):
    """Render an info box."""
    icon_map = {
        "info": "ℹ️",
        "success": "✅",
        "warning": "⚠️",
        "error": "❌"
    }
    icon = icon_map.get(type, icon_map["info"])
    st.info(f"{icon} {message}")


def render_risk_card(risk: Dict[str, Any], loader, compact: bool = False):
    """Render a risk card."""
    title = risk.get('title', risk.get('id', 'Unknown Risk'))
    short_desc = loader.format_text_list(risk.get('shortDescription', []))
    category = risk.get('category', 'Unknown')
    
    with st.container():
        st.markdown(f"### {title}")
        if short_desc and not compact:
            st.caption(short_desc)
        render_badge(category.replace('risks', '').strip(), "blue")
        return title


def render_control_card(control: Dict[str, Any], loader, compact: bool = False):
    """Render a control card."""
    title = control.get('title', control.get('id', 'Unknown Control'))
    description = loader.format_text_list(control.get('description', []))
    category = control.get('category', 'Unknown')
    
    with st.container():
        st.markdown(f"### 🛡️ {title}")
        if description and not compact:
            st.caption(description[:150] + "..." if len(description) > 150 else description)
        render_badge(category.replace('controls', '').strip(), "green")
        return title
