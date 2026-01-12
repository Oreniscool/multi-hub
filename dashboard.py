import streamlit as st
import sys
import os
from pathlib import Path

# Page Configuration - MUST be first Streamlit command
st.set_page_config(
    page_title="MultiHub Dashboard",
    page_icon="🚀",
    layout="wide"
)

# Initialize API key in session state (like MarketingHub pattern - no hardcoded keys)
if 'api_key' not in st.session_state:
    st.session_state['api_key'] = ""

# Custom CSS
st.markdown("""
<style>
    .main-title {
        font-size: 2.5rem;
        font-weight: bold;
        text-align: center;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar - Global API Key
with st.sidebar:
    st.header("🔑 Global Settings")
    api_key = st.text_input(
        "Gemini API Key",
        type="password",
        value=st.session_state['api_key'],
        help="Enter your API key once here. It will be shared with all hubs."
    )
    if api_key:
        st.session_state['api_key'] = api_key
    st.markdown("---")

# Title
st.markdown('<div class="main-title">🚀 MultiHub - Integrated Dashboard</div>', unsafe_allow_html=True)

# Hub selector
st.markdown("### Open app:")

selected_hub = st.radio(
    "Select application:",
    ["📚 CaseHub", "💼 SimulationHub", "🎓 CourseHub", "🚀 MarketingHub", 
     "🛡️ IntelligenceHub", "💠 VectorisationHub", "🏷️ ClassificationHub"],
    horizontal=True,
    label_visibility="collapsed"
)

st.markdown("---")

# Store hub directories to clean up
if 'hub_paths' not in st.session_state:
    st.session_state.hub_paths = []

# Helper function to run hub code
def run_hub_code(file_path):
    """Read and execute hub code with proper encoding"""
    # Get absolute path from workspace root
    workspace_root = Path(__file__).parent.resolve()
    abs_path = (workspace_root / file_path).resolve()
    
    # Clean up previous hub paths from sys.path
    for old_path in st.session_state.hub_paths:
        if old_path in sys.path:
            sys.path.remove(old_path)
    st.session_state.hub_paths = []
    
    # Clear module cache for common module names to avoid conflicts
    modules_to_clear = ['utils', 'analytics', 'content_generator', 'modules', 'competitive_analysis', 
                        'market_intelligence', 'news_scraper', 'swot_generator', 'ai_handler', 'data_handler']
    for mod_name in list(sys.modules.keys()):
        if any(mod_name == m or mod_name.startswith(m + '.') for m in modules_to_clear):
            try:
                del sys.modules[mod_name]
            except KeyError:
                pass
    
    try:
        with open(abs_path, 'r', encoding='utf-8') as f:
            code = f.read()
    except UnicodeDecodeError:
        with open(abs_path, 'r', encoding='latin-1') as f:
            code = f.read()
    
    # Remove st.set_page_config calls completely using regex
    import re
    # Match st.set_page_config(...) including multi-line
    code = re.sub(r'st\.set_page_config\([^)]*\)', '# Page config removed by dashboard', code, flags=re.DOTALL)
    
    # Add hub directory to sys.path for imports (at the beginning for priority)
    hub_dir = str(abs_path.parent)
    sys.path.insert(0, hub_dir)
    st.session_state.hub_paths.append(hub_dir)
    
    # Change working directory temporarily
    original_dir = os.getcwd()
    os.chdir(hub_dir)
    
    try:
        exec(code, {'__name__': '__main__', '__file__': str(abs_path)})
    finally:
        os.chdir(original_dir)

# Display selected hub content
hub_name = selected_hub.split(" ")[1]  # Extract hub name without emoji

if hub_name == "CaseHub":
    run_hub_code("CaseHub/app.py")
    
elif hub_name == "SimulationHub":
    run_hub_code("SimulationHub/mba_sim_engine.py")
    
elif hub_name == "CourseHub":
    run_hub_code("CourseHub/main.py")
    
elif hub_name == "MarketingHub":
    run_hub_code("MarketingHub/main.py")
    
elif hub_name == "IntelligenceHub":
    run_hub_code("IntelligenceHub/app.py")
    
elif hub_name == "VectorisationHub":
    run_hub_code("VectorisationHub/app.py")
    
elif hub_name == "ClassificationHub":
    run_hub_code("ClassificationHub/app.py")
