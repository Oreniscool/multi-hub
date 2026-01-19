import streamlit as st
import content_generator
import analytics

# Page Configuration
st.set_page_config(
    page_title="AI Marketing Hub",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for "Visual Excellence" and premium feel
st.markdown("""
    <style>
    .main {
        padding-top: 2rem;
    }
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        height: 3em;
        background-color: #FF4B4B; 
        color: white;
        font-weight: 600;
        border: none;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #FF2B2B;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .stTextInput>div>div>input {
        border-radius: 8px;
    }
    /* Removed h1 color override to allow theme to handle it */
    /* Removed sidebar background override to allow theme to handle it */
    
    /* Improve alert visibility */
    .stAlert {
        border-radius: 8px;
    }
    </style>
    """, unsafe_allow_html=True)

def main():
    # Set Default API Key
    if 'api_key' not in st.session_state:
        st.session_state['api_key'] = "AIzaSyAF1pSbeOWw54HXdFaxHg0Oa3QsqlZitkI"

    # Sidebar
    st.sidebar.title("🚀 Marketing Hub")
    
    # API Key Input
    with st.sidebar.expander("🔑 Global Settings", expanded=True):
        api_key = st.text_input(
            "Google API Key",
            type="password",
            value=st.session_state['api_key'],
            help="Enter your Gemini API Key to enable content generation features.",
            key="api_key_input"
        )
        # Update session state if user changes it
        if api_key != st.session_state['api_key']:
             st.session_state['api_key'] = api_key
             st.success("API Key updated!")

    # Navigation using Sidebar Radio
    st.sidebar.markdown("---")
    page = st.sidebar.radio(
        "Navigation",
        ["🏠 Home", "✨ Content Generator", "📊 Analytics Dashboard"],
        label_visibility="collapsed"
    )

    # Routing
    if page == "🏠 Home":
        render_home()
    elif page == "✨ Content Generator":
        content_generator.app()
    elif page == "📊 Analytics Dashboard":
        analytics.app()

def render_home():
    st.title("Welcome to AI Marketing Hub 🚀")
    
    st.markdown("""
    ### A centralized platform for modern marketers.
    
    Leverage the power of **Google Gemini** for instant content creation and visualize your campaign success with our **Analytics Dashboard**.
    
    #### Quick Stats 📈
    """)
    
    # Placeholder Quick Stats
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="Active Campaigns", value="12", delta="2")
    with col2:
        st.metric(label="Content Generated", value="128", delta="15")
    with col3:
        st.metric(label="Avg. ROI", value="324%", delta="12%")
        
    st.markdown("---")
    st.markdown("Select a tool from the sidebar to get started.")

if __name__ == "__main__":
    main()
