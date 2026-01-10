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
