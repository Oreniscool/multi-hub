import streamlit as st
import importlib

# Page Configuration
st.set_page_config(
    page_title="Intelligence Hub",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Preserve Streamlit's default theme (no forced CSS overrides)

# Set Default API Key via session state (like MarketingHub pattern)
if 'api_key' not in st.session_state:
    st.session_state['api_key'] = ""

# Sidebar Navigation
st.sidebar.title("🛡️ Intel Hub")

# API Key Input (like MarketingHub)
with st.sidebar.expander("🔑 API Settings", expanded=True):
    api_key = st.text_input(
        "Google API Key",
        type="password",
        value=st.session_state['api_key'],
        help="Enter your Gemini API Key to enable AI features."
    )
    if api_key:
        st.session_state['api_key'] = api_key

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
