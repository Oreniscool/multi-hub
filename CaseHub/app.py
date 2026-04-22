import streamlit as st
import utils

# Page Config
st.set_page_config(
    page_title="Case Study Hub",
    page_icon="cb",
    layout="wide"
)

# Sidebar Configuration
st.sidebar.title("Configuration")

st.sidebar.markdown("---")

# Input Form
st.sidebar.header("Case Study Parameters")
industry = st.sidebar.selectbox(
    "Industry",
    ["Technology", "Healthcare", "Finance", "Retail", "Manufacturing", "Education", "Energy", "Other"]
)
if industry == "Other":
    industry = st.sidebar.text_input("Specify Industry")

topic = st.sidebar.text_input("Specific Topic", "Supply Chain Disruption")

difficulty = st.sidebar.selectbox(
    "Difficulty Level",
    ["Undergraduate", "MBA", "Executive Education"]
)

company_size = st.sidebar.selectbox(
    "Company Size",
    ["Startup", "Small/Medium Business (SMB)", "Enterprise"]
)

generate_btn = st.sidebar.button("Generate Case Study", type="primary")

# Main Panel
st.title("📚 Case Study Hub")
st.markdown("Generate structured business case studies tailored to your needs using AI.")

if generate_btn:
    with st.spinner("Generating case study... This may take a moment."):
        case_study_content = utils.generate_case_study(
            industry,
            topic,
            difficulty,
            company_size,
        )

        if "Error" in case_study_content and len(case_study_content) < 300:
            st.error(case_study_content)
        else:
            st.session_state['generated_content'] = case_study_content
            st.success("Case Study Generated Successfully!")

# Display Results if available
if 'generated_content' in st.session_state:
    content = st.session_state['generated_content']
    
    # Output Area
    st.markdown("---")
    st.markdown(content)
    
    st.markdown("---")
    st.subheader("Download Options")
    
    col1, col2 = st.columns(2)
    
    # PDF Download
    try:
        pdf_bytes = utils.create_pdf(content)
        col1.download_button(
            label="📄 Download as PDF",
            data=pdf_bytes,
            file_name="case_study.pdf",
            mime="application/pdf"
        )
    except Exception as e:
        col1.error(f"PDF Generation Error: {e}")

    # Word Download
    try:
        docx_buffer = utils.create_docx(content)
        col2.download_button(
            label="📝 Download as Word",
            data=docx_buffer,
            file_name="case_study.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
    except Exception as e:
        col2.error(f"Word Generation Error: {e}")
