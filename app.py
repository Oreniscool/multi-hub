import streamlit as st
import sys
import os
import json
import requests
import gspread
import google.generativeai as genai
from datetime import datetime
from pathlib import Path

# Page Configuration - MUST be first Streamlit command
st.set_page_config(
    page_title="MultiHub Dashboard",
    page_icon="🚀",
    layout="wide"
)

PROMPT_BUILDER_URL = os.getenv("PROMPT_BUILDER_URL", "https://prompt-builder-frontend-q92uz0e5c-qitiyas-projects.vercel.app/")
PROMPT_MODEL = os.getenv("PROMPT_MODEL", "gemini-2.5-flash")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "1kifjalBeYoTqgYXHG3g-XsbiEAhh3fDuqfRnkRll1ug")
GOOGLE_APPS_SCRIPT_WEBHOOK_URL = os.getenv(
    "GOOGLE_APPS_SCRIPT_WEBHOOK_URL",
    "https://script.google.com/macros/s/AKfycbxyds2ERAkPa1m-S5ilL3PmumsYWLlhMdzEJm11xYq0Oe7fVslRdqgegf7Fo0KQmvpGYg/exec",
)

# Session state initialization
st.session_state.setdefault('api_key', "")
st.session_state.setdefault('hub_paths', [])
st.session_state.setdefault('pb_chat', [])
st.session_state.setdefault('pb_final_srs', "")
st.session_state.setdefault('pb_title', "App SRS")
st.session_state.setdefault('pb_sheet_id', "")
st.session_state.setdefault('pb_ws', "")

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
        value=st.session_state['api_key'],
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


def _get_sheets_client():
    raw_creds = None
    if "google_service_account" in st.secrets:
        raw_creds = st.secrets["google_service_account"]
    elif os.getenv("GOOGLE_SHEETS_CREDS"):
        raw_creds = os.getenv("GOOGLE_SHEETS_CREDS")

    if not raw_creds:
        return None, "Set google_service_account in Streamlit secrets or GOOGLE_SHEETS_CREDS env var"

    try:
        creds_dict = json.loads(raw_creds) if isinstance(raw_creds, str) else raw_creds
        client = gspread.service_account_from_dict(creds_dict)
        return client, None
    except Exception as exc:
        return None, f"Failed to init Google Sheets client: {exc}"


def _append_prompt_row(sheet_id: str, worksheet: str, row: list):
    # Prefer Apps Script webhook; fallback to gspread if webhook missing
    if GOOGLE_APPS_SCRIPT_WEBHOOK_URL:
        try:
            payload = {
                "timestamp": row[0],
                "prompt": row[1],
                "featureCount": row[2],
                "features": row[3] if isinstance(row[3], list) else row[3],
                "conversation": row[4],
            }
            resp = requests.post(
                GOOGLE_APPS_SCRIPT_WEBHOOK_URL,
                json=payload,
                timeout=10,
            )
            if resp.status_code == 200:
                body = {}
                try:
                    body = resp.json()
                except Exception:
                    body = {}
                if body.get("success") is True or resp.status_code == 200:
                    return True, None
                return False, f"Webhook error: {resp.status_code} {resp.text}"
            return False, f"Webhook error: {resp.status_code} {resp.text}"
        except Exception as exc:
            return False, f"Webhook request failed: {exc}"

    client, err = _get_sheets_client()
    if err:
        return False, err
    try:
        sh = client.open_by_key(sheet_id)
        ws = sh.worksheet(worksheet if worksheet else "Prompts")
        ws.append_row(row, value_input_option="USER_ENTERED")
        return True, None
    except Exception as exc:
        return False, f"Google Sheets error: {exc}"


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
    st.caption("One chat to define your app. Generate SRS and save to Google Sheets.")

    # Sheet settings (fixed targets)
    with st.expander("Google Sheets settings", expanded=True):
        st.markdown(f"**Sheet ID:** `{GOOGLE_SHEET_ID}`")
        st.markdown(f"**Webhook:** `{GOOGLE_APPS_SCRIPT_WEBHOOK_URL}`")
        st.info("Saves always go to the fixed sheet via the Apps Script webhook.")

    st.markdown("---")
    st.markdown("#### Chat")
    for msg in st.session_state.pb_chat:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

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
            if st.button("Save to Google Sheets", type="primary"):
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
                    feature_lines or features_blob,  # Features (list preferred)
                    convo_length,           # Conversation Length
                ]
                ok, err = _append_prompt_row(GOOGLE_SHEET_ID, "", row)
                if ok:
                    st.success("Saved to Google Sheets.")
                else:
                    st.error(err)
