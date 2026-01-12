import streamlit as st
import pandas as pd
import plotly.express as px
from utils import load_data, classify_batch

# Page Config
st.set_page_config(
    page_title="Classification Hub",
    page_icon="🏷️",
    layout="wide"
)

# Custom CSS for aesthetics - Dark Mode Optimized
st.markdown("""
    <style>
    /* Global styles provided by config.toml, adding specific overrides */
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        border-radius: 8px;
        border: none;
    }
    .stButton>button:hover {
        background-color: #45a049;
    }
    </style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.title("⚙️ Configuration")
    
    # Use session_state for API key (no hardcoded keys)
    if 'api_key' not in st.session_state:
        st.session_state['api_key'] = ""
    
    api_key = st.text_input("Google Gemini API Key", value=st.session_state['api_key'], type="password")
    if api_key:
        st.session_state['api_key'] = api_key
    
    st.divider()
    
    st.subheader("Data Input")
    upload_option = st.radio("Choose Input Method", ["Upload CSV", "Load Demo Data"])
    
    uploaded_file = None
    classification_criteria = None
    if upload_option == "Upload CSV":
        uploaded_file = st.file_uploader("Upload CSV", type=["csv"])
        if uploaded_file:
            st.subheader("Classification Setup")
            classification_criteria = st.text_input(
                "What should I classify?",
                placeholder="e.g., sentiment, urgency, topic, priority, category",
                help="Specify what aspect of the data you want to classify"
            )
    
    if upload_option == "Load Demo Data":
        if st.button("Load Demo Data"):
            st.session_state.data = load_data("demo")
            st.session_state.data_loaded = True
            st.rerun()

# Main Content
st.title("🏷️ Classification Hub")
st.markdown("Categorize your text datasets using **Google Gemini**.")

if uploaded_file and upload_option == "Upload CSV":
    st.session_state.data = load_data(uploaded_file)
    st.session_state.data_loaded = True

if 'data_loaded' in st.session_state and st.session_state.data_loaded:
    df = st.session_state.data
    
    st.subheader("📊 Data Preview")
    st.dataframe(df.head(), use_container_width=True)
    
    # Column Selector - Auto-select text column for demo data
    default_column = 0
    if upload_option == "Load Demo Data" and 'email_content' in df.columns:
        default_column = list(df.columns).index('email_content')
    
    text_column = st.selectbox("Select Text Column", df.columns, index=default_column)
    
    # Custom Object Logic (Dynamic Prompt)
    default_prompt = ""
    if upload_option == "Load Demo Data":
        default_prompt = "Classify the urgency of this email into: High, Medium, Low. Return only the category name."
    elif upload_option == "Upload CSV" and 'classification_criteria' in locals() and classification_criteria:
        default_prompt = f"Classify this text based on {classification_criteria}. Return only the category name."
    
    prompt = st.text_area(
        "Classification Instructions (Prompt)",
        value=default_prompt,
        placeholder="e.g., Classify this text into: Positive, Negative, Neutral",
        help="Customize the classification instructions for the AI model"
    )
    
    if st.button("Start Classification", key="start_btn"):
        if not api_key:
            st.error("Please enter your Google Gemini API Key in the sidebar.")
        elif not prompt:
            st.error("Please enter classification instructions.")
        else:
            with st.spinner("Classifying texts..."):
                progress_bar = st.progress(0)
                # Pass prompt to text
                categories = classify_batch(df, text_column, api_key, prompt, progress_bar)
                
                df['Predicted_Category'] = categories
                st.session_state.results = df
                st.success("Classification Complete!")

    # Results Area
    if 'results' in st.session_state:
        results_df = st.session_state.results
        
        st.divider()
        st.subheader("📈 Results Analysis")
        
        col1, col2 = st.columns(2)
        
        # Metrics
        with col1:
            st.metric("Total Processed", len(results_df))
        
        with col2:
            st.metric("Unique Categories", results_df['Predicted_Category'].nunique())
            
        # Visualization
        # Prepare data ensures correct column names
        counts_df = results_df['Predicted_Category'].value_counts().reset_index()
        counts_df.columns = ['Category', 'Count'] # Explicit rename for compatibility
        
        fig = px.bar(
            counts_df,
            x='Category',
            y='Count',
            title="Category Distribution",
            color='Category',
            template="plotly_dark"
        )
        fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)
        
        # Data Table
        st.subheader("Recent Classifications")
        st.dataframe(results_df, use_container_width=True)
        
        # Export
        csv = results_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Results as CSV",
            data=csv,
            file_name="classification_results.csv",
            mime="text/csv"
        )
else:
    st.info("Please upload a CSV file or load demo data to get started.")

