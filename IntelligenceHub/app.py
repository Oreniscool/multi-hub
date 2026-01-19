import streamlit as st
import importlib

# Page Configuration
st.set_page_config(
    page_title="Intelligence Hub",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for "Dark Mode Command Center" vibe
st.markdown("""
<style>
    .stApp {
        background-color: #0e1117;
    }
    section[data-testid="stSidebar"] {
        background-color: #161b22;
        border-right: 1px solid #30363d;
    }
    h1, h2, h3 {
        color: #e6edf3 !important;
    }
    .stButton>button {
        background-color: #238636;
        color: white;
        border: none;
        width: 100%;
    }
    .stButton>button:hover {
        background-color: #2ea043;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar Navigation
st.sidebar.title("🛡️ Intel Hub")
st.sidebar.markdown("---")

module_selection = st.sidebar.radio(
    "Navigation",
    ["Market Intelligence", "Competitive Analysis", "News Scraper", "SWOT Generator"]
)

st.sidebar.markdown("---")
st.sidebar.info("v1.0 | Command Center")

# Header
st.markdown(f"## {module_selection}")

# Module Loading
if module_selection == "Market Intelligence":
    from modules import market_intelligence
    market_intelligence.show()

elif module_selection == "Competitive Analysis":
    from modules import competitive_analysis
    competitive_analysis.show()

elif module_selection == "News Scraper":
    from modules import news_scraper
    news_scraper.show()

elif module_selection == "SWOT Generator":
    from modules import swot_generator
    swot_generator.show()
