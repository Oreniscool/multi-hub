import streamlit as st
import google.generativeai as genai

def app():
    st.title("✨ AI Content Generator")
    st.markdown("Generate high-quality marketing content in seconds using Google Gemini.")

    # Check for API Key
    if 'api_key' not in st.session_state or not st.session_state['api_key']:
        st.error("⚠️ Please enter your Google API Key in the sidebar to proceed.")
        return

    # Configure Gemini
    try:
        genai.configure(api_key=st.session_state['api_key'])
        model = genai.GenerativeModel('models/gemma-3-27b-it')
    except Exception as e:
        st.error(f"Error configuring Gemini API: {e}")
        return

    # Input Form
    with st.form("content_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            content_type = st.selectbox(
                "Content Type",
                ["Social Media Post", "Email Newsletter", "Blog Article", "Ad Copy", "Product Description"]
            )
            tone = st.selectbox(
                "Tone",
                ["Professional", "Witty", "Urgent", "Empathetic"]
            )
            
        with col2:
            target_audience = st.text_input("Target Audience", placeholder="e.g. Gen Z, Tech Professionals, Parents")
            
        topic = st.text_area("Topic / Context", placeholder="Describe what you want to write about...", height=150)
        
        submitted = st.form_submit_button("Generate Content ✨")

    # Generation Logic
    if submitted:
        if not topic:
            st.warning("Please provide a topic or context.")
            return
            
        with st.spinner("Gemini is crafting your content..."):
            try:
                # Construct Prompt
                prompt = f"""
                Act as an expert marketing copywriter.
                Create a {content_type} for the following topic:
                "{topic}"
                
                Target Audience: {target_audience}
                Tone: {tone}
                
                Format the output professionally using Markdown.
                """
                
                response = model.generate_content(prompt)
                
                # Display Result
                st.success("Content Generated Successfully!")
                st.markdown("### Result")
                st.markdown("---")
                st.markdown(response.text)
                
                # Copy Helper (Streamlit doesn't have native copy-to-clipboard button easily without components, 
                # but code blocks have a copy button).
                st.markdown("### Copy Code")
                st.code(response.text, language="markdown")
                
            except Exception as e:
                st.error(f"An error occurred during generation: {e}")
