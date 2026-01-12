import streamlit as st
import google.generativeai as genai
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from pypdf import PdfReader
from sklearn.decomposition import PCA
import random
import time
import re

# --- Configuration & Setup ---
st.set_page_config(
    page_title="Vector Hub",
    page_icon="💠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for polished UI
st.markdown("""
<style>
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
    }
    .stTextInput>div>div>input {
        border-radius: 5px;
    }
    .reportview-container {
        background: #0E1117;
    }
    h1, h2, h3 {
        font-family: 'Inter', sans-serif;
    }
    .metric-card {
        background-color: #262730;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Set Default API Key via session state (like MarketingHub pattern)
if 'api_key' not in st.session_state:
    st.session_state['api_key'] = ""

# Demo Data
DEMO_EMAILS = [
    "Subject: Client Contract Deadline\n\nHi Team,\nWe need the signed contract for the Apex account finalized by 5 PM today. Please prioritize the redlines from legal and confirm once the client has countersigned.\n\nThanks,\nAlex",
    "Subject: Outage Response Coordination\n\nHi Support,\nProduction servers in the EU region started rejecting payments at 08:12 UTC. Spin up the incident bridge and post updates in #status-eu every 15 minutes.\n\nRegards,\nPriya",
    "Subject: Executive Briefing Deck\n\nHi Design Team,\nThe board wants the Q4 forecast deck by tomorrow morning. Focus on slides 6-12 and deliver the first draft for review tonight.\n\nBest,\nJordan",
    "Subject: Vendor Payment Approval\n\nHello Finance,\nSupplier invoice INV-99231 is past due by three days. Please prioritize approval in NetSuite before late fees accrue.\n\nThanks,\nMaria",
    "Subject: Security Patch Confirmation\n\nTeam,\nPlease verify that the emergency OpenSSL patch has been applied to all internet-facing hosts before midnight. Share the compliance report once complete.\n\nRegards,\nEthan",
    "Subject: Customer Escalation Follow-up\n\nHi CX,\nThe Falcon Corp renewal is at risk. Call the client within the hour and summarize the remediation steps in Salesforce.\n\nThanks,\nSofia",
    "Subject: Quarterly Hiring Plan\n\nHi People Ops,\nCan you draft the updated hiring plan for customer success by Friday? Include headcount by region and projected start dates.\n\nBest,\nLiam",
    "Subject: Marketing Newsletter Copy\n\nHello Content Team,\nWe need refreshed copy for the April newsletter by next Wednesday. Emphasize the new analytics features and include two customer quotes.\n\nCheers,\nMaya",
    "Subject: Office Renovation Update\n\nFacilities,\nPlease share the latest construction timeline for the Austin office retrofit. Leadership wants to ensure phase two still hits the June milestone.\n\nThanks,\nNoah",
    "Subject: Team Offsite Agenda\n\nHi All,\nDraft the offsite agenda with session owners by the end of the week so we can circulate to attendees Monday morning.\n\nRegards,\nHarper",
    "Subject: Data Backup Verification\n\nIT Team,\nConfirm last night’s backup replication completed successfully and attach the status report to this thread by noon.\n\nThanks,\nNina",
    "Subject: Training Survey Reminder\n\nHi Trainers,\nPlease remind attendees to complete the post-course survey by Friday so we can compile results before the leadership review.\n\nBest,\nCaleb",
    "Subject: Holiday Coverage Schedule\n\nSupport,\nShare the holiday coverage rota by next Tuesday. Include escalation contacts for each shift.\n\nThanks,\nOlivia",
    "Subject: Vendor NDA Draft\n\nHi Legal,\nWe need the NDA draft for the Solaris partnership by Thursday afternoon to keep timelines on track.\n\nRegards,\nMiles",
    "Subject: Travel Reimbursement Batch\n\nHello Finance Ops,\nPlease process the April travel reimbursements by the end of next week and notify employees when payments post.\n\nThank you,\nIsabella",
    "Subject: Monthly Metrics Review\n\nHi Analytics,\nPrepare the monthly KPI snapshot for Monday’s leadership sync. Focus on churn trends and expansion pipeline.\n\nBest,\nEli",
    "Subject: Policy Handbook Refresh\n\nPeople Ops,\nUpdate the employee handbook with the new remote-work guidelines before the all-hands on the 25th.\n\nThanks,\nRiley",
    "Subject: Office Supply Inventory\n\nHi Admin Team,\nPlease audit the supply closet and submit replenishment requests by the end of the month.\n\nRegards,\nGrace"
]

DEMO_URGENCY = [
    "High", "High", "High", "High", "High", "High",
    "Medium", "Medium", "Medium", "Medium", "Medium", "Medium",
    "Low", "Low", "Low", "Low", "Low", "Low"
]

# --- Helper Functions ---

def get_gemini_embeddings(text_list, api_key):
    """Generates embeddings using Gemini API."""
    genai.configure(api_key=api_key)
    embeddings = []
    
    progress_bar = st.progress(0)
    for i, text in enumerate(text_list):
        try:
            # Using embed_content for batch or single embedding
            result = genai.embed_content(
                model="models/text-embedding-004", # Or specific Gemini embedding model
                content=text,
                task_type="retrieval_document",
                title=None
            )
            embeddings.append(result['embedding'])
            progress_bar.progress((i + 1) / len(text_list))
        except Exception as e:
            st.error(f"Error generating embedding for chunk {i}: {e}")
            return None
    progress_bar.empty()
    return np.array(embeddings)

def get_demo_embeddings(count):
    """Generates random embeddings for demo mode."""
    # Simulate high-dimensional vectors (768 for standard embedding size)
    return np.random.rand(count, 768)

def split_text_into_chunks(text, chunk_size=500, chunk_overlap=50):
    """Simple text splitter to replace langchain dependency."""
    chunks = []
    text = text.strip()
    
    # Split by sentences approximately
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    current_chunk = ""
    for sentence in sentences:
        if len(current_chunk) + len(sentence) <= chunk_size:
            current_chunk += sentence + " "
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = sentence + " "
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks if chunks else [text]

def process_pdf(uploaded_file, chunk_size, chunk_overlap):
    """Extracts and chunks text from PDF."""
    pdf_reader = PdfReader(uploaded_file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()
    
    chunks = split_text_into_chunks(text, chunk_size, chunk_overlap)
    return chunks

# --- Sidebar ---
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Toggle switch (Checkbox style)
    demo_mode = st.toggle("Enable Demo Mode", value=False)
    
    if not demo_mode:
        st.subheader("🔑 API Setup")
        api_key = st.text_input(
            "Google API Key", 
            value=st.session_state['api_key'], 
            type="password",
            help="Your Gemini API Key"
        )
        # Update session state when user provides key
        if api_key:
            st.session_state['api_key'] = api_key
        
        st.subheader("📄 Data Ingestion")
        uploaded_file = st.file_uploader("Upload PDF", type=['pdf'])
        
        with st.expander("Chunk Settings"):
            chunk_size = st.slider("Chunk Size", 100, 2000, 500)
            chunk_overlap = st.slider("Chunk Overlap", 0, 500, 50)
            
    else:
        st.info("ℹ️ **Demo Mode Active**\n\nUsing professional email samples to demonstrate capabilities without API calls.")
        st.metric(label="Synthetic Documents", value=len(DEMO_EMAILS))

# --- Main Content ---
st.title("💠 Vector Hub")
st.markdown("### Semantic Search & Embedding Visualization")

# Session State Initialization
if 'embeddings' not in st.session_state:
    st.session_state.embeddings = None
if 'documents' not in st.session_state:
    st.session_state.documents = []
if 'is_demo_data' not in st.session_state:
    st.session_state.is_demo_data = False

# Data Loading Logic
if demo_mode:
    # Load demo data if not already loaded or if switching modes
    if st.session_state.embeddings is None or st.session_state.is_demo_data == False:
        with st.spinner("Generating synthetic embeddings..."):
            st.session_state.documents = DEMO_EMAILS
            st.session_state.embeddings = get_demo_embeddings(len(DEMO_EMAILS))
            st.session_state.is_demo_data = True
            time.sleep(0.5) # Fake loading for effect
            st.success(f"Loaded {len(DEMO_EMAILS)} synthetic documents.")

elif uploaded_file and api_key:
    # Process PDF logic
    # Check if we need to re-process (new file or settings change could be handled better, 
    # but for simple app, we'll re-run if "Process" button is clicked or just reactively)
    # To avoid re-running on every interaction, we use a process button
    
    if st.button("Process Document", use_container_width=True):
        with st.spinner("Processing PDF and generating embeddings..."):
            chunks = process_pdf(uploaded_file, chunk_size, chunk_overlap)
            embeddings = get_gemini_embeddings(chunks, api_key)
            
            if embeddings is not None:
                st.session_state.documents = chunks
                st.session_state.embeddings = embeddings
                st.session_state.is_demo_data = False
                st.success(f"Successfully processed {len(chunks)} chunks.")

# Tabs
tab1, tab2 = st.tabs(["🔍 Semantic Search", "🌌 Embedding Space"])

# --- Tab 1: Semantic Search ---
with tab1:
    st.header("Semantic Search")
    query = st.text_input("Enter your query:", placeholder="e.g., 'Financial market trends' or 'New tech innovations'")
    
    if query and st.session_state.embeddings is not None:
        if demo_mode:
            # Fake search results
            st.markdown("### Search Results (Synthetic)")
            # Pick 3 random indices
            indices = random.sample(range(len(st.session_state.documents)), 3)
            # Fake scores
            scores = sorted([random.uniform(0.7, 0.98) for _ in range(3)], reverse=True)
            
            for idx, score in zip(indices, scores):
                with st.container():
                    st.markdown(f"""
                    <div style="padding: 10px; border: 1px solid #444; border-radius: 5px; margin-bottom: 10px; background-color: #1E1E1E;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="font-size: 0.9em; color: #aaa;">Document #{idx}</span>
                            <span style="background-color: #00AA00; padding: 2px 8px; border-radius: 10px; font-size: 0.8em;">Similarity: {score:.4f}</span>
                        </div>
                        <p style="margin-top: 5px;">{st.session_state.documents[idx]}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
        else: # Real Mode
             if st.button("Search", key="real_search"):
                with st.spinner("Searching..."):
                    try:
                        genai.configure(api_key=api_key)
                        query_embedding = genai.embed_content(
                            model="models/text-embedding-004",
                            content=query,
                            task_type="retrieval_query"
                        )['embedding']
                        
                        # Calculate Cosine Similarity
                        # dot product of normalized vectors
                        # Assuming Gemini embeddings are normalized? Usually yes, but let's compute dot product
                        doc_embeddings = st.session_state.embeddings
                        scores = np.dot(doc_embeddings, query_embedding)
                        
                        # Get top K
                        k = 5
                        top_indices = np.argsort(scores)[::-1][:k]
                        
                        st.markdown("### Search Results")
                        for idx in top_indices:
                            score = scores[idx]
                            with st.container():
                                st.markdown(f"""
                                <div style="padding: 15px; border: 1px solid #444; border-radius: 8px; margin-bottom: 15px; background-color: #1E1E1E;">
                                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                                        <span style="font-size: 0.8em; color: #ccc; font-family: monospace;">Chunk #{idx}</span>
                                        <span style="background-color: rgba(33, 195, 84, 0.2); color: #21c354; padding: 4px 10px; border-radius: 12px; font-size: 0.85em; font-weight: 600;">{score:.4f}</span>
                                    </div>
                                    <div style="color: #eee; line-height: 1.5;">{st.session_state.documents[idx]}</div>
                                </div>
                                """, unsafe_allow_html=True)
                                
                    except Exception as e:
                        st.error(f"Search failed: {e}")

    elif st.session_state.embeddings is None:
        st.info("Upload a PDF or enable Demo Mode to start searching.")

# --- Tab 2: Embedding Space ---
with tab2:
    st.header("Embedding Visualization")
    
    if st.session_state.embeddings is not None:
        with st.spinner("Projecting embeddings to 2D space..."):
            
            # Reduce to 2D
            if len(st.session_state.documents) < 2:
                st.warning("Not enough data to visualize. Need at least 2 documents.")
            else:
                pca = PCA(n_components=2)
                projections = pca.fit_transform(st.session_state.embeddings)
                
                # Display variance explained
                variance_explained = pca.explained_variance_ratio_
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Documents", len(st.session_state.documents))
                with col2:
                    st.metric("PC1 Variance", f"{variance_explained[0]*100:.1f}%")
                with col3:
                    st.metric("PC2 Variance", f"{variance_explained[1]*100:.1f}%")
                
                # Prepare DataFrame for Plotly
                df = pd.DataFrame(projections, columns=['x', 'y'])
                df['text'] = [d[:100] + "..." if len(d) > 100 else d for d in st.session_state.documents]
                df['doc_id'] = [f"Doc {i+1}" for i in range(len(df))]
                
                # Use session state to determine data source
                if st.session_state.is_demo_data:
                    df['category'] = DEMO_URGENCY[:len(df)]
                    color_map = {
                        'High': '#FF6B6B',
                        'Medium': '#FFB347',
                        'Low': '#6DD47E'
                    }
                else:
                    df['category'] = "Document Chunk"
                    color_map = {'Document Chunk': '#45B7D1'}
                
                # Debug output
                st.write(f"📊 **Data Summary:** {len(df)} points")
                st.write(f"📍 X range: [{df['x'].min():.3f}, {df['x'].max():.3f}]")
                st.write(f"📍 Y range: [{df['y'].min():.3f}, {df['y'].max():.3f}]")
                st.write("**First 3 rows:**")
                st.dataframe(df[['x', 'y', 'category']].head(3))

                # Create enhanced Plot with explicit traces per category
                fig = go.Figure()

                for category in df['category'].unique():
                    subset = df[df['category'] == category]
                    fig.add_trace(
                        go.Scatter(
                            x=subset['x'],
                            y=subset['y'],
                            mode='markers',
                            name=category,
                            marker=dict(
                                size=22,
                                color=color_map.get(category, '#636EFA'),
                                line=dict(width=2, color='#FFFFFF'),
                                symbol='circle'
                            ),
                            text=subset['doc_id'],
                            customdata=subset[['text']].values,
                            hovertemplate=(
                                "<b>%{text}</b><br>"
                                f"Category: {category}<br>"
                                "PC1: %{x:.3f}<br>"
                                "PC2: %{y:.3f}<br><br>"
                                "%{customdata[0]}"
                                "<extra></extra>"
                            )
                        )
                    )

                fig.update_layout(
                    height=650,
                    plot_bgcolor='#1a1a2e',
                    paper_bgcolor='#0f0f1e',
                    font=dict(color='#ffffff', size=12),
                    title=dict(
                        text=f"2D Vector Space Visualization ({len(df)} embeddings)",
                        font=dict(size=20, color='#ffffff'),
                        x=0.5,
                        xanchor='center'
                    ),
                    xaxis=dict(
                        showgrid=True,
                        gridwidth=1,
                        gridcolor='rgba(128,128,128,0.2)',
                        zeroline=True,
                        zerolinewidth=2,
                        zerolinecolor='rgba(128,128,128,0.4)',
                        showticklabels=True,
                        title=dict(text='Principal Component 1', font=dict(size=14))
                    ),
                    yaxis=dict(
                        showgrid=True,
                        gridwidth=1,
                        gridcolor='rgba(128,128,128,0.2)',
                        zeroline=True,
                        zerolinewidth=2,
                        zerolinecolor='rgba(128,128,128,0.4)',
                        showticklabels=True,
                        title=dict(text='Principal Component 2', font=dict(size=14))
                    ),
                    legend=dict(
                        yanchor="top",
                        y=0.99,
                        xanchor="left",
                        x=0.01,
                        bgcolor='rgba(0,0,0,0.5)',
                        bordercolor='rgba(255,255,255,0.3)',
                        borderwidth=1
                    ),
                    hovermode='closest'
                )

                st.plotly_chart(fig, use_container_width=True)
                
                # Add explanation
                with st.expander("ℹ️ About this visualization"):
                    st.markdown("""
                    **What you're seeing:**
                    - Each point represents a document/text chunk in 2D space
                    - Similar documents cluster together
                    - Distance between points indicates semantic similarity
                    - PCA reduces high-dimensional embeddings (768D) to 2D for visualization
                    
                    **Variance Explained:** Shows how much information is retained in each component.
                    """)
    else:
        st.info("Upload a PDF or enable Demo Mode to visualize embeddings.")

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #666;'>"
    "Vector Hub | Powered by Gemini 2.0 Flash & Streamlit"
    "</div>", 
    unsafe_allow_html=True
)
