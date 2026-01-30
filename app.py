import streamlit as st
import sys
import os
import json
import requests
import gspread
import google.generativeai as genai
from datetime import datetime
from pathlib import Path
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
import pickle
import hashlib
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Page Configuration - MUST be first Streamlit command
st.set_page_config(
    page_title="MultiHub Dashboard",
    page_icon="🚀",
    layout="wide"
)

PROMPT_BUILDER_URL = os.getenv("PROMPT_BUILDER_URL", "https://prompt-builder-frontend-q92uz0e5c-qitiyas-projects.vercel.app/")
PROMPT_MODEL = os.getenv("PROMPT_MODEL", "gemini-2.5-flash")

# OAuth Configuration
OAUTH_CLIENT_ID = os.getenv("GOOGLE_OAUTH_CLIENT_ID", "")
OAUTH_CLIENT_SECRET = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", "")
OAUTH_REDIRECT_URI = os.getenv("OAUTH_REDIRECT_URI", "http://localhost:8501")
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
    'openid'
]

# Session state initialization
st.session_state.setdefault('api_key', "")
st.session_state.setdefault('hub_paths', [])
st.session_state.setdefault('pb_chat', [])
st.session_state.setdefault('pb_final_srs', "")
st.session_state.setdefault('pb_title', "App SRS")
st.session_state.setdefault('user_creds', None)
st.session_state.setdefault('user_email', None)
st.session_state.setdefault('user_name', None)
st.session_state.setdefault('user_sheet_id', None)

# Custom CSS
st.markdown(
    """
<style>
    .main-title {
        font-size: 2.5rem;
        font-weight: bold;
        text-align: center;
        margin-bottom: 1rem;
    }
</style>
""",
    unsafe_allow_html=True,
)

# Sidebar - Global API Key
with st.sidebar:
    st.header("🔑 Global Settings")
    api_key = st.text_input(
        "Gemini API Key",
        type="password",
        value=st.session_state.get('api_key', ""),
        help="Enter your API key once here. It will be shared with all hubs.",
    )
    if api_key:
        st.session_state['api_key'] = api_key
    st.markdown("---")
    st.subheader("🔗 Other Apps")
    st.markdown(
        f'<a href="{PROMPT_BUILDER_URL}" target="_blank" rel="noopener noreferrer">Open Prompt Builder (Next.js) ↗</a>',
        unsafe_allow_html=True,
    )

# Title
st.markdown('<div class="main-title">🚀 MultiHub - Integrated Dashboard</div>', unsafe_allow_html=True)
st.caption("Use the hub switcher below.")

# Hub selector
st.markdown("### Open app:")
selected_hub = st.radio(
    "Select application:",
    [
        "📚 CaseHub",
        "💼 SimulationHub",
        "🎓 CourseHub",
        "🚀 MarketingHub",
        "🛡️ IntelligenceHub",
        "💠 VectorisationHub",
        "🏷️ ClassificationHub",
        "🎨 PromptBuilder",
    ],
    horizontal=True,
    label_visibility="collapsed",
)
st.markdown("---")


def _get_user_info(creds):
    """Get user info from Google OAuth credentials"""
    try:
        service = build('oauth2', 'v2', credentials=creds)
        user_info = service.userinfo().get().execute()
        return user_info.get('email'), user_info.get('name'), None
    except Exception as exc:
        return None, None, f"Failed to get user info: {exc}"


def _get_or_create_user_sheet(creds, user_email):
    """Get or create a Google Sheet for the user"""
    try:
        # Create gspread client with user's OAuth credentials
        client = gspread.authorize(creds)
        
        # Generate a consistent sheet name for the user
        sheet_name = f"Prompts - {user_email}"
        
        # Try to find existing sheet
        try:
            sheet = client.open(sheet_name)
            return sheet.id, None
        except gspread.SpreadsheetNotFound:
            # Create new sheet
            sheet = client.create(sheet_name)
            # Set up the header row
            worksheet = sheet.get_worksheet(0)
            worksheet.update('A1:E1', [['Timestamp', 'Prompt/SRS', 'Feature Count', 'Features', 'Conversation Length']])
            # User is already the owner via OAuth, no need to share
            return sheet.id, None
    except Exception as exc:
        return None, f"Failed to get/create sheet: {exc}"


def _append_prompt_row(creds, sheet_id: str, row: list):
    """Append a row to user's Google Sheet using their OAuth credentials"""
    try:
        client = gspread.authorize(creds)
        sh = client.open_by_key(sheet_id)
        ws = sh.get_worksheet(0)  # Use first worksheet
        ws.append_row(row, value_input_option="USER_ENTERED")
        return True, None
    except Exception as exc:
        return False, f"Google Sheets error: {exc}"


def _init_oauth_flow():
    """Initialize OAuth flow for Google authentication"""
    if not OAUTH_CLIENT_ID or not OAUTH_CLIENT_SECRET:
        return None, "OAuth credentials not configured. Set GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET environment variables."
    
    try:
        client_config = {
            "web": {
                "client_id": OAUTH_CLIENT_ID,
                "client_secret": OAUTH_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [OAUTH_REDIRECT_URI]
            }
        }
        flow = Flow.from_client_config(
            client_config,
            scopes=SCOPES,
            redirect_uri=OAUTH_REDIRECT_URI
        )
        return flow, None
    except Exception as exc:
        return None, f"Failed to initialize OAuth: {exc}"


def _handle_oauth_callback():
    """Handle OAuth callback and exchange code for credentials"""
    # Check if we have an authorization code in query params
    query_params = st.query_params
    if 'code' in query_params:
        flow, err = _init_oauth_flow()
        if err:
            return None, err
        
        try:
            # Exchange code for credentials
            flow.fetch_token(code=query_params['code'])
            creds = flow.credentials
            
            # Store credentials in session
            st.session_state.user_creds = creds
            
            # Get user info
            email, name, err = _get_user_info(creds)
            if err:
                return None, err
            
            st.session_state.user_email = email
            st.session_state.user_name = name
            
            # Get or create user's sheet
            sheet_id, err = _get_or_create_user_sheet(creds, email)
            if err:
                return None, err
            
            st.session_state.user_sheet_id = sheet_id
            
            # Clear the code from URL
            st.query_params.clear()
            
            return True, None
        except Exception as exc:
            return None, f"OAuth callback error: {exc}"
    
    return False, None


def _chat_reply(user_msg: str, history: list, api_key: str):
    if not api_key:
        return None, "Provide a Gemini API key in the sidebar."
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(PROMPT_MODEL)
        system_prompt = (
            "You are a concise, formal product analyst helping draft an app SRS. "
            "Keep replies short (2-4 sentences max). Ask only targeted questions. "
            "Focus on: app goal, target users, platform, key flows, data captured, preferred database, integrations, auth/compliance, scale/timeline. "
            "Do not draft the SRS or long summaries until the user explicitly requests generation."
        )
        messages = [{"role": "user", "parts": [system_prompt]}]
        for h in history:
            role = "user" if h["role"] == "user" else "model"
            messages.append({"role": role, "parts": [h["content"]]})
        messages.append({"role": "user", "parts": [user_msg]})
        resp = model.generate_content(messages)
        return resp.text, None
    except Exception as exc:
        return None, f"Gemini error: {exc}"


def _generate_srs_from_chat(chat: list, api_key: str):
    if not api_key:
        return None, "Provide a Gemini API key in the sidebar."
    transcript = []
    for msg in chat:
        role = msg.get("role", "user")
        prefix = "User" if role == "user" else "Assistant"
        transcript.append(f"{prefix}: {msg.get('content','')}")
    transcript_text = "\n".join(transcript)
    prompt = f"""
You are an expert product engineer. Using the conversation below, produce a concise, implementable Software Requirements Specification for an app builder. The output must be directly usable as a build prompt.

Required sections (use the exact order and headers):
1) Product Summary
2) Primary Users & Roles
3) Core Use Cases
4) Functional Requirements
5) Non-Functional Requirements (performance, security, availability, compliance)
6) Data Model (entities, key fields, relationships)
7) Integrations & APIs
8) Screens/Pages with key components
9) Critical Flows (step-by-step)
10) Edge Cases & Constraints
11) Acceptance Criteria

Conversation:
{transcript_text}
"""
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(PROMPT_MODEL)
        resp = model.generate_content(prompt)
        return resp.text, None
    except Exception as exc:
        return None, f"Gemini error: {exc}"


def run_hub_code(file_path):
    workspace_root = Path(__file__).parent.resolve()
    abs_path = (workspace_root / file_path).resolve()

    for old_path in st.session_state.hub_paths:
        if old_path in sys.path:
            sys.path.remove(old_path)
    st.session_state.hub_paths = []

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

    import re
    code = re.sub(r'st\.set_page_config\([^)]*\)', '# Page config removed by dashboard', code, flags=re.DOTALL)

    hub_dir = str(abs_path.parent)
    sys.path.insert(0, hub_dir)
    st.session_state.hub_paths.append(hub_dir)

    original_dir = os.getcwd()
    os.chdir(hub_dir)
    try:
        exec(code, {'__name__': '__main__', '__file__': str(abs_path)})
    finally:
        os.chdir(original_dir)


# Display selected hub content
hub_name = selected_hub.split(" ")[1]

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
elif hub_name == "PromptBuilder":
    st.subheader("Prompt Builder (Streamlit)")
    st.caption("One chat to define your app. Generate SRS and save to your personal Google Sheets.")

    # Handle OAuth callback
    callback_result, callback_err = _handle_oauth_callback()
    if callback_err:
        st.error(callback_err)
    elif callback_result:
        st.success(f"Logged in as {st.session_state.user_email}")
        st.rerun()

    # User authentication section
    with st.expander("🔐 Google Account Login", expanded=not st.session_state.user_email):
        if st.session_state.user_email:
            st.success(f"✅ Logged in as: **{st.session_state.user_name}** ({st.session_state.user_email})")
            if st.session_state.user_sheet_id:
                sheet_url = f"https://docs.google.com/spreadsheets/d/{st.session_state.user_sheet_id}"
                st.markdown(f"📊 Your sheet: [Open in Google Sheets]({sheet_url})")
            
            if st.button("🚪 Logout"):
                st.session_state.user_creds = None
                st.session_state.user_email = None
                st.session_state.user_name = None
                st.session_state.user_sheet_id = None
                st.rerun()
        else:
            st.info("Please login with your Google account to save prompts to your personal sheet.")
            
            flow, err = _init_oauth_flow()
            if err:
                st.error(err)
                st.warning("To enable Google login, set these environment variables:")
                st.code("GOOGLE_OAUTH_CLIENT_ID=your_client_id\nGOOGLE_OAUTH_CLIENT_SECRET=your_client_secret\nOAUTH_REDIRECT_URI=http://localhost:8501")
            else:
                auth_url, _ = flow.authorization_url(prompt='consent')
                st.markdown(f"[🔗 Login with Google]({auth_url})")
                st.caption("You'll be redirected to Google to authorize this app.")

    st.markdown("---")
    st.markdown("#### Chat")
    for idx, msg in enumerate(st.session_state.pb_chat):
        role = msg["role"]
        content = msg["content"]
        # Create preview (first 100 characters)
        preview = content[:100] + "..." if len(content) > 100 else content
        emoji = "👤" if role == "user" else "🤖"
        label = f"{emoji} {'You' if role == 'user' else 'Assistant'}: {preview}"
        
        with st.expander(label, expanded=False):
            st.markdown(content)

    user_chat = st.chat_input("Describe the app (goal, users, platform, data, DB, auth, integrations). Keep it concise.")
    if user_chat:
        st.session_state.pb_chat.append({"role": "user", "content": user_chat})
        reply, err = _chat_reply(user_chat, st.session_state.pb_chat[:-1], st.session_state.get("api_key", ""))
        if err:
            st.error(err)
            st.session_state.pb_chat.pop()
        else:
            st.session_state.pb_chat.append({"role": "assistant", "content": reply})
            st.rerun()

    st.markdown("---")
    satisfied = st.checkbox("I have provided enough detail; generate the SRS now.", value=False)
    col_gen, col_title = st.columns([2, 1])
    with col_gen:
        if satisfied and st.button("Generate prompt (SRS)", type="primary"):
            srs_text, err = _generate_srs_from_chat(st.session_state.pb_chat, st.session_state.get("api_key", ""))
            if err:
                st.error(err)
            else:
                st.session_state.pb_final_srs = srs_text or ""
                st.success("Generated SRS. Review below.")
                st.rerun()
    with col_title:
        st.session_state.pb_title = st.text_input("Title/label", value=st.session_state.get("pb_title", "App SRS"))

    if st.session_state.get("pb_final_srs"):
        st.markdown("---")
        st.markdown("#### Final SRS prompt (for app builder)")
        st.code(st.session_state.pb_final_srs)

        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                label="Download prompt.json",
                data=json.dumps({
                    "title": st.session_state.get("pb_title", "App SRS"),
                    "prompt": st.session_state.pb_final_srs,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                }, indent=2),
                file_name="prompt.json",
                mime="application/json",
                key="pb_download"
            )
        with col2:
            if st.button("Save to Google Sheets", type="primary", disabled=not st.session_state.user_email):
                if not st.session_state.user_email:
                    st.error("Please login with Google first.")
                elif not st.session_state.user_sheet_id:
                    st.error("No sheet found. Please try logging in again.")
                else:
                    srs = st.session_state.pb_final_srs or ""
                    timestamp = datetime.utcnow().isoformat() + "Z"
                    feature_lines = [ln.strip() for ln in srs.splitlines() if ln.strip().startswith(('-','•','*'))]
                    feature_count = len(feature_lines)
                    features_blob = "\n".join(feature_lines)
                    convo_length = len(st.session_state.pb_chat)

                    row = [
                        timestamp,              # Timestamp
                        srs,                    # Prompt / SRS
                        feature_count,          # Feature Count
                        features_blob,          # Features as text blob
                        convo_length,           # Conversation Length
                    ]
                    ok, err = _append_prompt_row(
                        st.session_state.user_creds,
                        st.session_state.user_sheet_id,
                        row
                    )
                    if ok:
                        sheet_url = f"https://docs.google.com/spreadsheets/d/{st.session_state.user_sheet_id}"
                        st.success(f"✅ Saved to your Google Sheet! [Open Sheet]({sheet_url})")
                    else:
                        st.error(err)
            
            if not st.session_state.user_email:
                st.caption("⚠️ Login required to save")
