import streamlit as st
import sys
import os
import json
import re
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
    page_title="Prompt Builder — Build Apps from Conversation",
    page_icon="🎨",
    layout="wide"
)

PROMPT_BUILDER_URL = os.getenv("PROMPT_BUILDER_URL", "https://prompt-builder-frontend-q92uz0e5c-qitiyas-projects.vercel.app/")
PROMPT_MODEL = os.getenv("PROMPT_MODEL", "gemini-2.5-flash-lite")

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
st.session_state.setdefault('current_view', 'prompt_builder')
st.session_state.setdefault('selected_example', None)


def _safe_parse_json(raw_text: str):
    """Parse model JSON responses that may be wrapped in markdown fences."""
    if not raw_text:
        return {}
    text = raw_text.strip()
    try:
        return json.loads(text)
    except Exception:
        pass

    match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, flags=re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            return {}
    return {}

# OAuth and credential helper functions
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


# Helper functions for credential persistence
def _save_credentials_to_cache(creds, email):
    """Save credentials to local cache file"""
    try:
        cache_dir = Path.home() / '.multihub_cache'
        cache_dir.mkdir(exist_ok=True)
        cache_file = cache_dir / f'user_{hashlib.md5(email.encode()).hexdigest()}.pkl'
        
        creds_data = {
            'token': creds.token,
            'refresh_token': creds.refresh_token,
            'token_uri': creds.token_uri,
            'client_id': creds.client_id,
            'client_secret': creds.client_secret,
            'scopes': creds.scopes,
            'email': email
        }
        
        with open(cache_file, 'wb') as f:
            pickle.dump(creds_data, f)
        return True
    except Exception as e:
        print(f"Failed to save credentials: {e}")
        return False


def _load_credentials_from_cache():
    """Load credentials from local cache"""
    try:
        cache_dir = Path.home() / '.multihub_cache'
        if not cache_dir.exists():
            return None
        
        # Find the most recent cache file
        cache_files = list(cache_dir.glob('user_*.pkl'))
        if not cache_files:
            return None
        
        # Use the most recently modified file
        latest_cache = max(cache_files, key=lambda p: p.stat().st_mtime)
        
        with open(latest_cache, 'rb') as f:
            creds_data = pickle.load(f)
        
        # Reconstruct credentials
        creds = Credentials(
            token=creds_data['token'],
            refresh_token=creds_data['refresh_token'],
            token_uri=creds_data['token_uri'],
            client_id=creds_data['client_id'],
            client_secret=creds_data['client_secret'],
            scopes=creds_data['scopes']
        )
        
        return creds, creds_data['email']
    except Exception as e:
        print(f"Failed to load credentials: {e}")
        return None


def _clear_credentials_cache(email=None):
    """Clear cached credentials"""
    try:
        cache_dir = Path.home() / '.multihub_cache'
        if not cache_dir.exists():
            return
        
        if email:
            cache_file = cache_dir / f'user_{hashlib.md5(email.encode()).hexdigest()}.pkl'
            if cache_file.exists():
                cache_file.unlink()
        else:
            # Clear all cache files
            for cache_file in cache_dir.glob('user_*.pkl'):
                cache_file.unlink()
    except Exception as e:
        print(f"Failed to clear credentials: {e}")


# Custom CSS
st.markdown(
    """
<style>
    /* ── Typography ── */
    .main-title {
        font-size: 2.8rem;
        font-weight: 800;
        text-align: center;
        margin-bottom: 0.3rem;
        background: linear-gradient(135deg, #667eea 0%, #a78bfa 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        letter-spacing: -0.02em;
    }
    .main-subtitle {
        font-size: 1.1rem;
        text-align: center;
        color: #9ca3af;
        margin-bottom: 0.5rem;
        letter-spacing: 0.01em;
    }

    /* ── Hero banner ── */
    .hero-banner {
        background: linear-gradient(135deg, rgba(102,126,234,0.08) 0%, rgba(167,139,250,0.06) 100%);
        border: 1px solid rgba(102,126,234,0.25);
        border-radius: 16px;
        padding: 1.25rem 1.75rem;
        margin-bottom: 1.5rem;
        display: flex;
        gap: 2rem;
        flex-wrap: wrap;
        justify-content: center;
    }
    .hero-step {
        text-align: center;
        min-width: 90px;
    }
    .hero-step-num {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 2rem;
        height: 2rem;
        border-radius: 50%;
        background: linear-gradient(135deg, #667eea, #a78bfa);
        color: #fff;
        font-weight: 700;
        font-size: 0.85rem;
        margin-bottom: 0.35rem;
    }
    .hero-step-label {
        font-size: 0.75rem;
        color: #9ca3af;
        line-height: 1.3;
    }
    .hero-step-arrow {
        color: rgba(102,126,234,0.4);
        font-size: 1.4rem;
        align-self: center;
        margin-top: -0.2rem;
    }

    /* ── Section headings ── */
    .section-header {
        font-size: 1rem;
        font-weight: 700;
        color: #c4b5fd;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        padding-bottom: 0.4rem;
        border-bottom: 1px solid rgba(102,126,234,0.25);
        margin-bottom: 0.9rem;
    }

    /* ── Styled divider ── */
    .styled-divider {
        height: 1px;
        background: linear-gradient(to right, transparent, rgba(102,126,234,0.35), transparent);
        margin: 1.5rem 0;
        border: none;
    }

    /* ── Progress info bar ── */
    .progress-bar-wrapper {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.07);
        border-radius: 10px;
        padding: 0.8rem 1.1rem;
        margin-bottom: 0.75rem;
    }

    /* ── Chat message bubbles ── */
    .msg-bubble-user {
        background: rgba(102,126,234,0.10);
        border: 1px solid rgba(102,126,234,0.22);
        border-radius: 10px;
        padding: 0.7rem 1rem;
        margin-bottom: 0.4rem;
    }
    .msg-bubble-ai {
        background: rgba(167,139,250,0.08);
        border: 1px solid rgba(167,139,250,0.18);
        border-radius: 10px;
        padding: 0.7rem 1rem;
        margin-bottom: 0.4rem;
    }
    .msg-label {
        font-size: 0.7rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        margin-bottom: 0.25rem;
    }
    .msg-label-user  { color: #818cf8; }
    .msg-label-ai    { color: #c084fc; }
    .msg-preview     { font-size: 0.88rem; color: #d1d5db; line-height: 1.5; }

    /* ── SRS output ── */
    .srs-output-wrap {
        background: rgba(102,126,234,0.04);
        border: 1px solid rgba(102,126,234,0.2);
        border-radius: 12px;
        padding: 1.25rem 1.5rem;
        margin-top: 0.5rem;
    }
    .srs-copy-hint {
        font-size: 0.78rem;
        color: #6b7280;
        margin-bottom: 0.6rem;
    }

    /* ── Example card ── */
    .example-card {
        border: 1px solid rgba(102,126,234,0.2);
        border-radius: 10px;
        padding: 0.9rem 1rem;
        margin-bottom: 0.45rem;
        background: rgba(102,126,234,0.03);
    }
    .example-card:hover { border-color: rgba(102,126,234,0.45); }
    .example-card h4 { margin: 0 0 0.2rem 0; font-size: 0.95rem; color: #e2e8f0; }
    .example-card p  { margin: 0; font-size: 0.8rem; color: #9ca3af; }

    /* ── Hint / info callout ── */
    .hint-callout {
        background: rgba(59,130,246,0.07);
        border-left: 3px solid rgba(99,102,241,0.55);
        border-radius: 0 8px 8px 0;
        padding: 0.65rem 1rem;
        font-size: 0.85rem;
        color: #93c5fd;
        margin: 0.6rem 0;
    }

    /* ── Hide Streamlit's default top padding ── */
    .block-container { padding-top: 1.5rem !important; }
</style>
""",
    unsafe_allow_html=True,
)

# Try to load cached credentials on startup
if not st.session_state.user_email:
    cached_data = _load_credentials_from_cache()
    if cached_data:
        creds, cached_email = cached_data
        # Verify credentials are still valid
        try:
            email, name, err = _get_user_info(creds)
            if not err and email:
                st.session_state.user_creds = creds
                st.session_state.user_email = email
                st.session_state.user_name = name
                # Get sheet ID
                sheet_id, _ = _get_or_create_user_sheet(creds, email)
                st.session_state.user_sheet_id = sheet_id
        except:
            # If credentials are invalid, clear cache
            _clear_credentials_cache()

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("🔑 Settings")
    api_key = st.text_input(
        "Gemini API Key",
        type="password",
        value=st.session_state.get('api_key', ""),
        help="Enter your API key once here. It will be shared with all hubs.",
    )
    if api_key:
        st.session_state['api_key'] = api_key
    
    st.markdown("---")
    
    # Google Authentication in Sidebar
    st.subheader("🔐 Google Account")
    if st.session_state.user_email:
        st.success(f"✅ **{st.session_state.user_name}**")
        st.caption(f"{st.session_state.user_email}")
        if st.session_state.user_sheet_id:
            sheet_url = f"https://docs.google.com/spreadsheets/d/{st.session_state.user_sheet_id}"
            st.markdown(f"📊 [Your Sheet]({sheet_url})")
        
        if st.button("🚪 Logout", key="sidebar_logout"):
            _clear_credentials_cache(st.session_state.user_email)
            st.session_state.user_creds = None
            st.session_state.user_email = None
            st.session_state.user_name = None
            st.session_state.user_sheet_id = None
            st.rerun()
    else:
        st.info("Login to save prompts")
        
        flow, err = _init_oauth_flow()
        if err:
            st.error("OAuth not configured")
            with st.expander("Setup Instructions"):
                st.code("GOOGLE_OAUTH_CLIENT_ID=your_id\nGOOGLE_OAUTH_CLIENT_SECRET=your_secret\nOAUTH_REDIRECT_URI=http://localhost:8501")
        else:
            auth_url, _ = flow.authorization_url(prompt='consent')
            st.markdown(f"[🔗 Login with Google]({auth_url})")

    st.markdown("---")

    # Navigation
    st.subheader("📍 Navigation")

    if st.button("🎨  Prompt Builder", use_container_width=True, type="primary" if st.session_state.current_view == 'prompt_builder' else "secondary"):
        st.session_state.current_view = 'prompt_builder'
        st.session_state.selected_example = None
        st.rerun()

    st.markdown("")
    st.caption("EXAMPLE PROJECTS")
    st.caption("Built with the Prompt Builder workflow")

    EXAMPLE_PROJECTS = {
        "CaseHub":           {"icon": "📚", "file": "CaseHub/app.py",                  "desc": "Case study analysis & generation"},
        "SimulationHub":     {"icon": "💼", "file": "SimulationHub/mba_sim_engine.py",  "desc": "MBA business simulation engine"},
        "CourseHub":         {"icon": "🎓", "file": "CourseHub/main.py",                "desc": "Course creation & management"},
        "MarketingHub":      {"icon": "🚀", "file": "MarketingHub/main.py",             "desc": "Marketing content & analytics"},
        "IntelligenceHub":   {"icon": "🛡️", "file": "IntelligenceHub/app.py",           "desc": "Market & competitive intelligence"},
        "VectorisationHub":  {"icon": "💠", "file": "VectorisationHub/app.py",          "desc": "Document vectorisation pipeline"},
        "ClassificationHub": {"icon": "🏷️", "file": "ClassificationHub/app.py",         "desc": "Content classification tools"},
    }

    for name, info in EXAMPLE_PROJECTS.items():
        is_active = (st.session_state.current_view == 'example' and st.session_state.selected_example == name)
        btn_type = "primary" if is_active else "secondary"
        if st.button(f"{info['icon']}  {name}", key=f"nav_{name}", use_container_width=True, type=btn_type):
            st.session_state.current_view = 'example'
            st.session_state.selected_example = name
            st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def _chat_reply(user_msg: str, history: list, api_key: str):
    if not api_key:
        return None, None, "Provide a Gemini API key in the sidebar."
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(PROMPT_MODEL)
        transcript = []
        for h in history:
            role = "User" if h["role"] == "user" else "Assistant"
            transcript.append(f"{role}: {h['content']}")
        transcript.append(f"User: {user_msg}")
        transcript_text = "\n".join(transcript)

        planner_prompt = f"""
You are Agent Planner in a collaborative multi-agent system.
Extract requirement signals and identify information gaps from the conversation.

Return strict JSON with this schema:
{{
  "known_requirements": ["..."],
  "missing_dimensions": ["..."],
  "risk_flags": ["..."],
  "priority_question": "one high-value question",
  "question_goal": "what this question unlocks"
}}

Conversation:
{transcript_text}
"""
        planner_resp = model.generate_content(planner_prompt)
        planner_text = (planner_resp.text or "").strip()
        planner_data = _safe_parse_json(planner_text)

        critic_prompt = f"""
You are Agent Critic in a collaborative multi-agent system.
Review the Planner output and improve the next question quality.
Make sure the next question is specific, practical, and non-redundant.

Return strict JSON with this schema:
{{
  "improved_question": "one precise question",
  "why_best_next": "brief reason",
  "micro_probes": ["optional short probe", "optional short probe"]
}}

Planner JSON:
{planner_text}

Conversation:
{transcript_text}
"""
        critic_resp = model.generate_content(critic_prompt)
        critic_text = (critic_resp.text or "").strip()
        critic_data = _safe_parse_json(critic_text)

        interviewer_prompt = f"""
You are Agent Interviewer in a collaborative multi-agent system.
Use the planner and critic outputs to produce the user-facing response.

Response rules:
- Keep to 2-4 concise sentences.
- Start with a one-sentence understanding summary.
- Ask exactly one primary question.
- Optionally add one short line with 1-2 concrete examples to help the user answer.
- Do not generate the final SRS yet.

Planner JSON:
{planner_text}

Critic JSON:
{critic_text}

Conversation:
{transcript_text}
"""
        interviewer_resp = model.generate_content(interviewer_prompt)
        agent_trace = {
            "planner": {
                "known_requirements": planner_data.get("known_requirements", []),
                "missing_dimensions": planner_data.get("missing_dimensions", []),
                "risk_flags": planner_data.get("risk_flags", []),
            },
            "critic": {
                "improved_question": critic_data.get("improved_question", ""),
                "why_best_next": critic_data.get("why_best_next", ""),
                "micro_probes": critic_data.get("micro_probes", []),
            },
        }
        return interviewer_resp.text, agent_trace, None
    except Exception as exc:
        return None, None, f"Gemini error: {exc}"


_DEPLOY_PY_TEMPLATE = """\
import os
from huggingface_hub import HfApi, create_repo

def deploy():
    token = os.getenv("HF_TOKEN")
    if not token:
        print("❌ Error: Please set your HF_TOKEN in Antigravity settings/env.")
        return

    repo_id = "your-username/my-auto-app"  # Customise with the app name

    try:
        # 1. Create the Space (if it doesn't exist)
        create_repo(repo_id, repo_type="space", space_sdk="gradio", token=token, exist_ok=True)

        # 2. Upload the entire folder
        api = HfApi()
        api.upload_folder(
            folder_path=".",
            repo_id=repo_id,
            repo_type="space",
            token=token
        )
        print(f"✅ Success! View your app at: https://huggingface.co/spaces/{repo_id}")
    except Exception as e:
        print(f"⚠️ Deployment failed: {e}")

if __name__ == "__main__":
    deploy()
"""


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
IMPORTANT — MANDATORY GENERATION REQUIREMENTS:
Use the conversation to generate an implementation-ready SRS/build prompt that strictly enforces ALL constraints below:

1) File Count Constraint
- Exactly 4 files total must be generated.
- Mandatory files: app.py, tools.py, agents.py.
- Include one additional file only when required for execution/setup.

2) app.py Constraint
- app.py must contain the full application entrypoint and runtime wiring.
- Must use FastAPI for the web app layer and expose chat endpoints.

3) tools.py Constraint
- tools.py must contain all LangChain tools.
- Use library-provided tools where available.
- When unavailable, define custom tools using decorators/runnable tool patterns.
- Do not use if/else conditional statements for answer routing logic.

4) agents.py Constraint
- agents.py must contain minimalistic agent code built with LangChain + LangGraph.
- Include explicit prompt instructions for each agent role.
- Gemini must be configured as the primary reasoning LLM ("brain").
- Agents must collaborate with each other and invoke a LangGraph chat interface.

5) UI Constraint
- UI must mirror Anthropic Claude-style chatbot interaction patterns (clean conversational layout, message bubbles, compact composer, and focused reading area).

6) Conversation Intelligence Constraint
- Chat agents must conduct a structured Q&A flow to collect complete user requirements before final answers.
- Agents must ask targeted follow-up questions for missing details.

7) Logic Constraint
- Avoid conditional branching instructions for response generation behavior.
- Prefer declarative orchestration through graph/state transitions and tool invocation patterns.

Now produce a concise, implementable SRS with the exact sections below:
1) Product Summary
2) Primary Users & Roles
3) Core Use Cases
4) Functional Requirements
5) Non-Functional Requirements
6) Agent Architecture (roles, collaboration, LangGraph flow)
7) Tooling Architecture (LangChain tools and custom decorators)
8) API Design (FastAPI routes and contracts)
9) UI/UX Specification (Claude-style chat layout and behavior)
10) Project File Plan (exactly 4 files with responsibilities)
11) Critical Q&A Collection Strategy
12) Acceptance Criteria

In section 6 and section 11, explicitly define a multi-agent loop with at least these roles:
- Planner Agent: extracts known requirements and missing dimensions.
- Critic Agent: improves the next best question quality.
- Interviewer Agent: asks one high-value question to the user.

The loop must run iteratively across turns until requirement completeness is reached.

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


# ─────────────────────────────────────────────────────────────────────────────
# MAIN CONTENT AREA
# ─────────────────────────────────────────────────────────────────────────────

# Check if user is logged in - mandatory login before accessing any features
if not st.session_state.user_email:
    # ── Login Page (Mandatory) ──
    st.markdown('<div class="main-title">🔐 Login Required</div>', unsafe_allow_html=True)
    st.markdown('<div class="main-subtitle">Sign in with Google to access the Prompt Builder and all features</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    col1, col2 = st.columns([1, 1])
    with col1:
        st.markdown("### Why sign in?")
        st.markdown("""
        - 📊 Save your prompts to Google Sheets
        - 💾 Access your history
        - 🔗 Manage all your app projects
        - 🔐 Secure authentication
        """)
    
    with col2:
        st.markdown("### Get started")
        
        flow, err = _init_oauth_flow()
        if err:
            st.error("OAuth not configured. Please check your environment variables.")
            with st.expander("Setup Instructions"):
                st.code("GOOGLE_OAUTH_CLIENT_ID=your_id\nGOOGLE_OAUTH_CLIENT_SECRET=your_secret\nOAUTH_REDIRECT_URI=http://localhost:8501")
        else:
            auth_url, _ = flow.authorization_url(prompt='consent')
            st.markdown(f"""
            <a href="{auth_url}" target="_self">
                <button style="
                    background-color: #4285F4;
                    color: white;
                    padding: 12px 24px;
                    font-size: 16px;
                    border: none;
                    border-radius: 4px;
                    cursor: pointer;
                    width: 100%;
                    font-weight: bold;
                ">
                    🔗 Sign in with Google
                </button>
            </a>
            """, unsafe_allow_html=True)
        
        # Handle OAuth callback on login page
        callback_result, callback_err = _handle_oauth_callback()
        if callback_err:
            st.error(f"Login error: {callback_err}")
        elif callback_result:
            if st.session_state.user_creds and st.session_state.user_email:
                _save_credentials_to_cache(st.session_state.user_creds, st.session_state.user_email)
            st.success(f"✅ Logged in as {st.session_state.user_email}")
            st.rerun()
    
    st.stop()  # Stop execution - don't show any other content until logged in

elif st.session_state.current_view == 'example' and st.session_state.selected_example:
    # ── Example project view ──
    proj = EXAMPLE_PROJECTS[st.session_state.selected_example]
    st.caption(f"📂 Example Project  ›  {proj['icon']} {st.session_state.selected_example}")
    st.markdown(f"### {proj['icon']} {st.session_state.selected_example}")
    st.caption(proj['desc'])
    st.info("💡 This project was built using the Prompt Builder workflow. "
            "Head back to the **Prompt Builder** to create your own!")
    st.markdown("---")
    run_hub_code(proj['file'])

else:
    # ── Prompt Builder (default / main view) ──
    st.markdown('<div class="main-title">🎨 Prompt Builder</div>', unsafe_allow_html=True)
    st.markdown('<div class="main-subtitle">One conversation to define your app — generate a Gradio SRS and ship it.</div>', unsafe_allow_html=True)
    st.caption("🧠 Agent Mode: Planner → Critic → Interviewer loop is active every turn.")

    # Step-flow banner
    st.markdown(
        """
        <div class="hero-banner">
          <div class="hero-step">
            <div class="hero-step-num">1</div>
            <div class="hero-step-label">Add API Key<br>in sidebar</div>
          </div>
          <div class="hero-step-arrow">›</div>
          <div class="hero-step">
            <div class="hero-step-num">2</div>
            <div class="hero-step-label">Chat about<br>your app</div>
          </div>
          <div class="hero-step-arrow">›</div>
          <div class="hero-step">
            <div class="hero-step-num">3</div>
            <div class="hero-step-label">Generate<br>Gradio SRS</div>
          </div>
          <div class="hero-step-arrow">›</div>
          <div class="hero-step">
            <div class="hero-step-num">4</div>
            <div class="hero-step-label">Copy &amp;<br>Build it</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Chat section ──
    st.markdown('<div class="section-header">💬 Conversation</div>', unsafe_allow_html=True)

    # Progress tracking
    MAX_EXCHANGES = 10
    user_messages = [msg for msg in st.session_state.pb_chat if msg["role"] == "user"]
    current_count = len(user_messages)
    progress_pct = min(current_count / MAX_EXCHANGES, 1.0)

    st.markdown('<div class="progress-bar-wrapper">', unsafe_allow_html=True)
    col_prog, col_count = st.columns([5, 1])
    with col_prog:
        st.progress(progress_pct)
    with col_count:
        st.caption(f"**{current_count}** / {MAX_EXCHANGES}")
    st.markdown('</div>', unsafe_allow_html=True)

    latest_trace = None
    for msg in reversed(st.session_state.pb_chat):
        if msg.get("role") == "assistant" and msg.get("agent_trace"):
            latest_trace = msg.get("agent_trace")
            break

    if latest_trace:
        planner = latest_trace.get("planner", {})
        critic = latest_trace.get("critic", {})
        known_count = len(planner.get("known_requirements", []))
        missing_count = len(planner.get("missing_dimensions", []))
        risk_count = len(planner.get("risk_flags", []))
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("✅ Known requirements", known_count)
        col_b.metric("❓ Open dimensions", missing_count)
        col_c.metric("⚠️ Risk flags", risk_count)
        if critic.get("improved_question"):
            st.info(f"**Next best question:** {critic.get('improved_question')}")

    if current_count >= MAX_EXCHANGES:
        st.markdown('<div class="hint-callout">✅ 10 exchanges complete — you\'re ready to generate your Gradio SRS below.</div>', unsafe_allow_html=True)
    elif current_count >= 7:
        st.markdown(f'<div class="hint-callout">💡 {MAX_EXCHANGES - current_count} more exchange(s) until the SRS generator unlocks automatically.</div>', unsafe_allow_html=True)
    elif current_count == 0:
        st.markdown('<div class="hint-callout">👋 Start by describing your app idea — its goal, target users, and key features.</div>', unsafe_allow_html=True)

    for idx, msg in enumerate(st.session_state.pb_chat):
        role = msg["role"]
        content = msg["content"]
        preview = content[:120] + "…" if len(content) > 120 else content
        bubble_class = "msg-bubble-user" if role == "user" else "msg-bubble-ai"
        label_class  = "msg-label-user"  if role == "user" else "msg-label-ai"
        label_text   = "You" if role == "user" else "Assistant"

        with st.expander(
            f"{'👤' if role == 'user' else '🤖'}  {label_text} — {preview}",
            expanded=False
        ):
            st.markdown(content)
            if role == "assistant" and msg.get("agent_trace"):
                trace = msg.get("agent_trace", {})
                planner = trace.get("planner", {})
                critic = trace.get("critic", {})
                st.markdown("---")
                st.caption("Agent activity")
                if planner.get("known_requirements"):
                    st.markdown("**Planner captured:**")
                    for item in planner.get("known_requirements", [])[:5]:
                        st.markdown(f"- {item}")
                if planner.get("missing_dimensions"):
                    st.markdown("**Planner still missing:**")
                    for item in planner.get("missing_dimensions", [])[:5]:
                        st.markdown(f"- {item}")
                if critic.get("why_best_next"):
                    st.markdown(f"**Critic rationale:** {critic.get('why_best_next')}")
                if critic.get("micro_probes"):
                    st.markdown("**Optional micro-probes:**")
                    for probe in critic.get("micro_probes", [])[:3]:
                        st.markdown(f"- {probe}")

    chat_disabled = current_count >= MAX_EXCHANGES
    chat_placeholder = "Limit reached \u2014 scroll down to generate your Gradio SRS." if chat_disabled else "Describe your app: goal, target users, platform, data, DB, auth, integrations\u2026"
    
    user_chat = st.chat_input(chat_placeholder, disabled=chat_disabled)
    if user_chat:
        st.session_state.pb_chat.append({"role": "user", "content": user_chat})
        reply, agent_trace, err = _chat_reply(user_chat, st.session_state.pb_chat[:-1], st.session_state.get("api_key", ""))
        if err:
            st.error(err)
            st.session_state.pb_chat.pop()
        else:
            st.session_state.pb_chat.append({
                "role": "assistant",
                "content": reply,
                "agent_trace": agent_trace or {}
            })
            st.rerun()

    st.markdown('<hr class="styled-divider">', unsafe_allow_html=True)

    # ── Generate SRS ──
    st.markdown('<div class="section-header">📄 Generate Gradio SRS</div>', unsafe_allow_html=True)

    satisfied = st.checkbox(
        "I've provided enough detail — generate the SRS now.",
        value=current_count >= MAX_EXCHANGES
    )

    col_gen, col_title = st.columns([2, 1])
    with col_gen:
        gen_disabled = not satisfied
        if st.button(
            "⚡ Generate Gradio SRS",
            type="primary",
            disabled=gen_disabled,
            help="Generates a Gradio-based Software Requirements Specification from your conversation"
        ):
            with st.spinner("Generating your Gradio SRS…"):
                srs_text, err = _generate_srs_from_chat(st.session_state.pb_chat, st.session_state.get("api_key", ""))
            if err:
                st.error(err)
            else:
                st.session_state.pb_final_srs = srs_text or ""
                st.success("✅ SRS generated — review and copy it below.")
                st.rerun()
    with col_title:
        st.session_state.pb_title = st.text_input(
            "Title / label",
            value=st.session_state.get("pb_title", "App SRS"),
            placeholder="e.g. Customer Churn Predictor"
        )

    if st.session_state.get("pb_final_srs"):
        st.markdown('<hr class="styled-divider">', unsafe_allow_html=True)
        st.markdown(
            '<div class="section-header">📋 Gradio SRS Prompt</div>',
            unsafe_allow_html=True
        )

        # Toggle between rendered and raw view
        view_mode = st.radio(
            "View mode:",
            ["Rendered (Markdown)", "Raw (Copy-able)"],
            horizontal=True,
            label_visibility="collapsed"
        )

        st.markdown('<div class="srs-output-wrap">', unsafe_allow_html=True)
        if view_mode == "Rendered (Markdown)":
            st.markdown(st.session_state.pb_final_srs)
        else:
            st.markdown('<div class="srs-copy-hint">Use the copy icon (⧉) in the top-right corner of the code block to copy the full prompt.</div>', unsafe_allow_html=True)
            st.code(st.session_state.pb_final_srs, language=None)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("")
        if st.button("💾 Save to Google Sheets", type="primary", disabled=not st.session_state.user_email):
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
                    timestamp,
                    srs,
                    feature_count,
                    features_blob,
                    convo_length,
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
