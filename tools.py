"""Utility functions and constants for MultiHub Streamlit app."""

import hashlib
import os
import pickle
import re
import sys
import time
from pathlib import Path
from typing import Dict, Optional, Tuple

import gspread
import streamlit as st
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build


SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "openid",
]

EXAMPLE_PROJECTS: Dict[str, Dict[str, str]] = {
    "CaseHub": {
        "icon": "📚",
        "file": "CaseHub/app.py",
        "desc": "Case study analysis & generation",
    },
    "SimulationHub": {
        "icon": "💼",
        "file": "SimulationHub/mba_sim_engine.py",
        "desc": "MBA business simulation engine",
    },
    "CourseHub": {
        "icon": "🎓",
        "file": "CourseHub/main.py",
        "desc": "Course creation & management",
    },
    "MarketingHub": {
        "icon": "🚀",
        "file": "MarketingHub/main.py",
        "desc": "Marketing content & analytics",
    },
    "IntelligenceHub": {
        "icon": "🛡️",
        "file": "IntelligenceHub/app.py",
        "desc": "Market & competitive intelligence",
    },
    "VectorisationHub": {
        "icon": "💠",
        "file": "VectorisationHub/app.py",
        "desc": "Document vectorisation pipeline",
    },
    "ClassificationHub": {
        "icon": "🏷️",
        "file": "ClassificationHub/app.py",
        "desc": "Content classification tools",
    },
}


def init_session_state() -> None:
    st.session_state.setdefault("hub_paths", [])
    st.session_state.setdefault("pb_chat", [])
    st.session_state.setdefault("pb_final_srs", "")
    st.session_state.setdefault("pb_title", "App SRS")
    st.session_state.setdefault("user_creds", None)
    st.session_state.setdefault("user_email", None)
    st.session_state.setdefault("user_name", None)
    st.session_state.setdefault("user_sheet_id", None)
    st.session_state.setdefault("current_view", "prompt_builder")
    st.session_state.setdefault("selected_example", None)
    st.session_state.setdefault("oauth_state", None)
    st.session_state.setdefault("oauth_code_verifier", None)


@st.cache_resource
def oauth_pkce_store():
    return {}


def apply_custom_css() -> None:
    st.markdown(
        """
<style>
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
    .hero-step { text-align: center; min-width: 90px; }
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
    .hero-step-label { font-size: 0.75rem; color: #9ca3af; line-height: 1.3; }
    .hero-step-arrow { color: rgba(102,126,234,0.4); font-size: 1.4rem; align-self: center; margin-top: -0.2rem; }
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
    .styled-divider {
        height: 1px;
        background: linear-gradient(to right, transparent, rgba(102,126,234,0.35), transparent);
        margin: 1.5rem 0;
        border: none;
    }
    .progress-bar-wrapper {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.07);
        border-radius: 10px;
        padding: 0.8rem 1.1rem;
        margin-bottom: 0.75rem;
    }
    .srs-output-wrap {
        background: rgba(102,126,234,0.04);
        border: 1px solid rgba(102,126,234,0.2);
        border-radius: 12px;
        padding: 1.25rem 1.5rem;
        margin-top: 0.5rem;
    }
    .srs-copy-hint { font-size: 0.78rem; color: #6b7280; margin-bottom: 0.6rem; }
    .hint-callout {
        background: rgba(59,130,246,0.07);
        border-left: 3px solid rgba(99,102,241,0.55);
        border-radius: 0 8px 8px 0;
        padding: 0.65rem 1rem;
        font-size: 0.85rem;
        color: #93c5fd;
        margin: 0.6rem 0;
    }
    .block-container { padding-top: 1.5rem !important; }
</style>
""",
        unsafe_allow_html=True,
    )


def get_user_info(creds) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    try:
        service = build("oauth2", "v2", credentials=creds)
        user_info = service.userinfo().get().execute()
        return user_info.get("email"), user_info.get("name"), None
    except Exception as exc:
        return None, None, f"Failed to get user info: {exc}"


def get_or_create_user_sheet(creds, user_email: str) -> Tuple[Optional[str], Optional[str]]:
    try:
        client = gspread.authorize(creds)
        sheet_name = f"Prompts - {user_email}"
        try:
            sheet = client.open(sheet_name)
            return sheet.id, None
        except gspread.SpreadsheetNotFound:
            sheet = client.create(sheet_name)
            worksheet = sheet.get_worksheet(0)
            worksheet.update(
                "A1:E1",
                [["Timestamp", "Prompt/SRS", "Feature Count", "Features", "Conversation Length"]],
            )
            return sheet.id, None
    except Exception as exc:
        return None, f"Failed to get/create sheet: {exc}"


def append_prompt_row(creds, sheet_id: str, row: list) -> Tuple[bool, Optional[str]]:
    try:
        client = gspread.authorize(creds)
        sh = client.open_by_key(sheet_id)
        ws = sh.get_worksheet(0)
        ws.append_row(row, value_input_option="USER_ENTERED")
        return True, None
    except Exception as exc:
        return False, f"Google Sheets error: {exc}"


def init_oauth_flow() -> Tuple[Optional[Flow], Optional[str]]:
    oauth_client_id = os.getenv("GOOGLE_OAUTH_CLIENT_ID", "").strip()
    oauth_client_secret = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", "").strip()
    oauth_redirect_uri = os.getenv("OAUTH_REDIRECT_URI", "http://localhost:8501").strip()

    if not oauth_client_id or not oauth_client_secret:
        return (
            None,
            "OAuth credentials not configured. Set GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET environment variables.",
        )

    try:
        client_config = {
            "web": {
                "client_id": oauth_client_id,
                "client_secret": oauth_client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [oauth_redirect_uri],
            }
        }
        flow = Flow.from_client_config(
            client_config,
            scopes=SCOPES,
            redirect_uri=oauth_redirect_uri,
            autogenerate_code_verifier=True,
        )
        return flow, None
    except Exception as exc:
        return None, f"Failed to initialize OAuth: {exc}"


def query_param_value(query_params, key: str):
    value = query_params.get(key)
    if isinstance(value, list):
        return value[0] if value else None
    return value


def is_oauth_callback_pending() -> bool:
    return bool(query_param_value(st.query_params, "code"))


def store_oauth_code_verifier(state: str, code_verifier: str) -> None:
    if not state or not code_verifier:
        return
    store = oauth_pkce_store()
    now = time.time()
    ttl_seconds = 15 * 60

    expired = [k for k, v in store.items() if now - v.get("created_at", 0) > ttl_seconds]
    for key in expired:
        store.pop(key, None)

    store[state] = {
        "code_verifier": code_verifier,
        "created_at": now,
    }


def take_oauth_code_verifier(state: str):
    if not state:
        return None
    store = oauth_pkce_store()
    data = store.pop(state, None)
    if not data:
        return None
    return data.get("code_verifier")


def build_auth_url() -> Tuple[Optional[str], Optional[str]]:
    flow, err = init_oauth_flow()
    if err:
        return None, err

    auth_url, state = flow.authorization_url(prompt="consent")
    st.session_state.oauth_state = state
    st.session_state.oauth_code_verifier = flow.code_verifier
    store_oauth_code_verifier(state, flow.code_verifier)
    return auth_url, None


def handle_oauth_callback() -> Tuple[Optional[bool], Optional[str]]:
    code = query_param_value(st.query_params, "code")
    if not code:
        return False, None

    flow, err = init_oauth_flow()
    if err:
        return None, err

    try:
        callback_state = query_param_value(st.query_params, "state")
        expected_state = st.session_state.get("oauth_state")
        if expected_state and callback_state != expected_state:
            return None, "OAuth callback error: state mismatch. Please retry login."

        code_verifier = st.session_state.get("oauth_code_verifier")
        if not code_verifier:
            code_verifier = take_oauth_code_verifier(callback_state)
        if not code_verifier:
            return None, "OAuth callback error: missing PKCE verifier in session. Please retry login."

        flow.code_verifier = code_verifier
        flow.fetch_token(code=code)
        creds = flow.credentials

        st.session_state.user_creds = creds

        email, name, err = get_user_info(creds)
        if err:
            return None, err

        st.session_state.user_email = email
        st.session_state.user_name = name

        sheet_id, err = get_or_create_user_sheet(creds, email)
        if err:
            return None, err

        st.session_state.user_sheet_id = sheet_id
        st.query_params.clear()
        st.session_state.oauth_state = None
        st.session_state.oauth_code_verifier = None
        return True, None
    except Exception as exc:
        return None, f"OAuth callback error: {exc}"


def save_credentials_to_cache(creds, email: str) -> bool:
    try:
        cache_dir = Path.home() / ".multihub_cache"
        cache_dir.mkdir(exist_ok=True)
        cache_file = cache_dir / f"user_{hashlib.md5(email.encode()).hexdigest()}.pkl"

        creds_data = {
            "token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
            "scopes": creds.scopes,
            "email": email,
        }

        with open(cache_file, "wb") as handle:
            pickle.dump(creds_data, handle)
        return True
    except Exception as exc:
        print(f"Failed to save credentials: {exc}")
        return False


def load_credentials_from_cache():
    try:
        cache_dir = Path.home() / ".multihub_cache"
        if not cache_dir.exists():
            return None

        cache_files = list(cache_dir.glob("user_*.pkl"))
        if not cache_files:
            return None

        latest_cache = max(cache_files, key=lambda p: p.stat().st_mtime)

        with open(latest_cache, "rb") as handle:
            creds_data = pickle.load(handle)

        creds = Credentials(
            token=creds_data["token"],
            refresh_token=creds_data["refresh_token"],
            token_uri=creds_data["token_uri"],
            client_id=creds_data["client_id"],
            client_secret=creds_data["client_secret"],
            scopes=creds_data["scopes"],
        )
        return creds, creds_data["email"]
    except Exception as exc:
        print(f"Failed to load credentials: {exc}")
        return None


def clear_credentials_cache(email: Optional[str] = None) -> None:
    try:
        cache_dir = Path.home() / ".multihub_cache"
        if not cache_dir.exists():
            return

        if email:
            cache_file = cache_dir / f"user_{hashlib.md5(email.encode()).hexdigest()}.pkl"
            if cache_file.exists():
                cache_file.unlink()
        else:
            for cache_file in cache_dir.glob("user_*.pkl"):
                cache_file.unlink()
    except Exception as exc:
        print(f"Failed to clear credentials: {exc}")


def bootstrap_cached_login() -> None:
    if st.session_state.user_email:
        return

    cached_data = load_credentials_from_cache()
    if not cached_data:
        return

    creds, _ = cached_data
    try:
        email, name, err = get_user_info(creds)
        if not err and email:
            st.session_state.user_creds = creds
            st.session_state.user_email = email
            st.session_state.user_name = name
            sheet_id, _ = get_or_create_user_sheet(creds, email)
            st.session_state.user_sheet_id = sheet_id
    except Exception:
        clear_credentials_cache()


def run_hub_code(file_path: str) -> None:
    workspace_root = Path(__file__).parent.resolve()
    abs_path = (workspace_root / file_path).resolve()

    for old_path in st.session_state.hub_paths:
        if old_path in sys.path:
            sys.path.remove(old_path)
    st.session_state.hub_paths = []

    modules_to_clear = [
        "utils",
        "analytics",
        "content_generator",
        "modules",
        "competitive_analysis",
        "market_intelligence",
        "news_scraper",
        "swot_generator",
        "ai_handler",
        "data_handler",
    ]
    for mod_name in list(sys.modules.keys()):
        if any(mod_name == mod or mod_name.startswith(mod + ".") for mod in modules_to_clear):
            try:
                del sys.modules[mod_name]
            except KeyError:
                pass

    try:
        with open(abs_path, "r", encoding="utf-8") as handle:
            code = handle.read()
    except UnicodeDecodeError:
        with open(abs_path, "r", encoding="latin-1") as handle:
            code = handle.read()

    code = re.sub(
        r"st\.set_page_config\([^)]*\)",
        "# Page config removed by dashboard",
        code,
        flags=re.DOTALL,
    )

    hub_dir = str(abs_path.parent)
    sys.path.insert(0, hub_dir)
    st.session_state.hub_paths.append(hub_dir)

    original_dir = os.getcwd()
    os.chdir(hub_dir)
    try:
        exec(code, {"__name__": "__main__", "__file__": str(abs_path)})
    finally:
        os.chdir(original_dir)
