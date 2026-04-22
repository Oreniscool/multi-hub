import streamlit as st
import os
import requests


def _generate_with_mistral(prompt: str) -> str:
    token = os.getenv("HF_API_TOKEN", "").strip() or os.getenv("HUGGINGFACEHUB_API_TOKEN", "").strip()
    model_id = os.getenv("HF_MODEL_ID", "mistralai/Mistral-7B-Instruct-v0.3").strip()
    api_url = os.getenv("HF_API_URL", f"https://router.huggingface.co/hf-inference/models/{model_id}").strip()

    if not token:
        raise ValueError("HF_API_TOKEN is not configured in environment.")

    response = requests.post(
        api_url,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={
            "inputs": prompt,
            "parameters": {"max_new_tokens": 900, "temperature": 0.4, "return_full_text": False},
            "options": {"wait_for_model": True},
        },
        timeout=180,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"HF inference failed ({response.status_code}): {response.text}")

    data = response.json()
    if isinstance(data, list) and data and isinstance(data[0], dict):
        text = (data[0].get("generated_text") or "").strip()
        if text:
            return text
    raise RuntimeError("HF response did not include generated_text.")

def app():
    st.title("✨ AI Content Generator")
    st.markdown("Generate high-quality marketing content in seconds using Mistral via Hugging Face.")

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
            
        with st.spinner("Mistral is crafting your content..."):
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
                generated_text = _generate_with_mistral(prompt)
                
                # Display Result
                st.success("Content Generated Successfully!")
                st.markdown("### Result")
                st.markdown("---")
                st.markdown(generated_text)
                
                # Copy Helper (Streamlit doesn't have native copy-to-clipboard button easily without components, 
                # but code blocks have a copy button).
                st.markdown("### Copy Code")
                st.code(generated_text, language="markdown")
                
            except Exception as e:
                st.error(f"An error occurred during generation: {e}")
