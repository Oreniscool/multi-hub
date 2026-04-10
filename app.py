import os
from datetime import datetime

import streamlit as st
from dotenv import load_dotenv

from agents import PromptBuilderAgents
from tools import (
    EXAMPLE_PROJECTS,
    append_prompt_row,
    apply_custom_css,
    bootstrap_cached_login,
    build_auth_url,
    clear_credentials_cache,
    handle_oauth_callback,
    init_session_state,
    is_oauth_callback_pending,
    run_hub_code,
    save_credentials_to_cache,
)

load_dotenv()

st.set_page_config(
    page_title="Prompt Builder - Build Apps from Conversation",
    page_icon="🎨",
    layout="wide",
)

PROMPT_MODEL = os.getenv("PROMPT_MODEL", "gemini-2.5-flash-lite")
MAX_EXCHANGES = 10

init_session_state()
apply_custom_css()
bootstrap_cached_login()
agents = PromptBuilderAgents(model_name=PROMPT_MODEL)

with st.sidebar:
    st.header("🔑 Settings")
    api_key = st.text_input(
        "Gemini API Key",
        type="password",
        value=st.session_state.get("api_key", ""),
        help="Enter your API key once here. It will be shared with all hubs.",
    )
    if api_key:
        st.session_state["api_key"] = api_key

    st.markdown("---")

    st.subheader("🔐 Google Account")
    if st.session_state.user_email:
        st.success(f"✅ **{st.session_state.user_name}**")
        st.caption(f"{st.session_state.user_email}")
        if st.session_state.user_sheet_id:
            sheet_url = f"https://docs.google.com/spreadsheets/d/{st.session_state.user_sheet_id}"
            st.markdown(f"📊 [Your Sheet]({sheet_url})")

        if st.button("🚪 Logout", key="sidebar_logout"):
            clear_credentials_cache(st.session_state.user_email)
            st.session_state.user_creds = None
            st.session_state.user_email = None
            st.session_state.user_name = None
            st.session_state.user_sheet_id = None
            st.rerun()
    else:
        st.info("Login to save prompts")
        if is_oauth_callback_pending():
            st.caption("Completing login...")
        else:
            auth_url, err = build_auth_url()
            if err:
                st.error("OAuth not configured")
                with st.expander("Setup Instructions"):
                    st.code(
                        "GOOGLE_OAUTH_CLIENT_ID=your_id\n"
                        "GOOGLE_OAUTH_CLIENT_SECRET=your_secret\n"
                        "OAUTH_REDIRECT_URI=http://localhost:8501"
                    )
            else:
                st.markdown(f"[🔗 Login with Google]({auth_url})")

    st.markdown("---")
    st.subheader("📍 Navigation")

    if st.button(
        "🎨  Prompt Builder",
        use_container_width=True,
        type="primary" if st.session_state.current_view == "prompt_builder" else "secondary",
    ):
        st.session_state.current_view = "prompt_builder"
        st.session_state.selected_example = None
        st.rerun()

    st.markdown("")
    st.caption("EXAMPLE PROJECTS")
    st.caption("Built with the Prompt Builder workflow")

    for name, info in EXAMPLE_PROJECTS.items():
        is_active = (
            st.session_state.current_view == "example"
            and st.session_state.selected_example == name
        )
        if st.button(
            f"{info['icon']}  {name}",
            key=f"nav_{name}",
            use_container_width=True,
            type="primary" if is_active else "secondary",
        ):
            st.session_state.current_view = "example"
            st.session_state.selected_example = name
            st.rerun()

if not st.session_state.user_email:
    callback_result, callback_err = (
        handle_oauth_callback() if is_oauth_callback_pending() else (False, None)
    )
    if callback_err:
        st.error(f"Login error: {callback_err}")
    elif callback_result:
        if st.session_state.user_creds and st.session_state.user_email:
            save_credentials_to_cache(
                st.session_state.user_creds,
                st.session_state.user_email,
            )
        st.success(f"✅ Logged in as {st.session_state.user_email}")
        st.rerun()

    st.markdown('<div class="main-title">🔐 Login Required</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="main-subtitle">Sign in with Google to access the Prompt Builder and all features</div>',
        unsafe_allow_html=True,
    )
    st.markdown("---")

    col1, col2 = st.columns([1, 1])
    with col1:
        st.markdown("### Why sign in?")
        st.markdown(
            """
        - 📊 Save your prompts to Google Sheets
        - 💾 Access your history
        - 🔗 Manage all your app projects
        - 🔐 Secure authentication
        """
        )

    with col2:
        st.markdown("### Get started")
        if is_oauth_callback_pending():
            st.info("Completing login...")
        else:
            auth_url, err = build_auth_url()
            if err:
                st.error("OAuth not configured. Please check your environment variables.")
                with st.expander("Setup Instructions"):
                    st.code(
                        "GOOGLE_OAUTH_CLIENT_ID=your_id\n"
                        "GOOGLE_OAUTH_CLIENT_SECRET=your_secret\n"
                        "OAUTH_REDIRECT_URI=http://localhost:8501"
                    )
            else:
                st.markdown(
                    f"""
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
                """,
                    unsafe_allow_html=True,
                )

    st.stop()

if st.session_state.current_view == "example" and st.session_state.selected_example:
    proj = EXAMPLE_PROJECTS[st.session_state.selected_example]
    st.caption(
        f"📂 Example Project  ›  {proj['icon']} {st.session_state.selected_example}"
    )
    st.markdown(f"### {proj['icon']} {st.session_state.selected_example}")
    st.caption(proj["desc"])
    st.info(
        "💡 This project was built using the Prompt Builder workflow. "
        "Head back to the Prompt Builder to create your own!"
    )
    st.markdown("---")
    run_hub_code(proj["file"])
    st.stop()

st.markdown(
        '<div class="main-subtitle">Define your app in one conversation, then generate a production-ready SRS.</div>',
    unsafe_allow_html=True,
)
st.caption("🧠 Agent Mode: Planner -> Critic -> Interviewer loop is active every turn.")

st.markdown("### Workflow")
st.markdown(
        """
```text
[1] Add Gemini API Key (sidebar)
                        |
                        v
[2] Describe app goals and constraints in chat
                        |
                        v
[3] Answer follow-up questions from agents
                        |
                        v
[4] Generate SRS and save/export to build
```
"""
)

st.markdown('<div class="section-header">💬 Conversation</div>', unsafe_allow_html=True)
user_messages = [msg for msg in st.session_state.pb_chat if msg["role"] == "user"]
current_count = len(user_messages)
progress_pct = min(current_count / MAX_EXCHANGES, 1.0)

st.markdown('<div class="progress-bar-wrapper">', unsafe_allow_html=True)
col_prog, col_count = st.columns([5, 1])
with col_prog:
    st.progress(progress_pct)
with col_count:
    st.caption(f"**{current_count}** / {MAX_EXCHANGES}")
st.markdown("</div>", unsafe_allow_html=True)

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
    st.markdown(
        '<div class="hint-callout">✅ 10 exchanges complete - you are ready to generate your SRS below.</div>',
        unsafe_allow_html=True,
    )
elif current_count >= 7:
    st.markdown(
        f'<div class="hint-callout">💡 {MAX_EXCHANGES - current_count} more exchange(s) until the SRS generator unlocks automatically.</div>',
        unsafe_allow_html=True,
    )
elif current_count == 0:
    st.markdown(
        '<div class="hint-callout">👋 Start by describing your app idea - its goal, target users, and key features.</div>',
        unsafe_allow_html=True,
    )

for msg in st.session_state.pb_chat:
    role = msg["role"]
    content = msg["content"]
    preview = content[:120] + "…" if len(content) > 120 else content
    label_text = "You" if role == "user" else "Assistant"

    with st.expander(
        f"{'👤' if role == 'user' else '🤖'}  {label_text} - {preview}",
        expanded=False,
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
chat_placeholder = (
    "Limit reached - scroll down to generate your SRS."
    if chat_disabled
    else "Describe your app: goal, target users, platform, data, DB, auth, integrations..."
)

user_chat = st.chat_input(chat_placeholder, disabled=chat_disabled)
if user_chat:
    st.session_state.pb_chat.append({"role": "user", "content": user_chat})
    reply, agent_trace, err = agents.chat_reply(
        user_chat,
        st.session_state.pb_chat[:-1],
        st.session_state.get("api_key", ""),
    )
    if err:
        st.error(err)
        st.session_state.pb_chat.pop()
    else:
        st.session_state.pb_chat.append(
            {
                "role": "assistant",
                "content": reply,
                "agent_trace": agent_trace or {},
            }
        )
        st.rerun()

st.markdown('<hr class="styled-divider">', unsafe_allow_html=True)
st.markdown('<div class="section-header">📄 Generate SRS</div>', unsafe_allow_html=True)

satisfied = st.checkbox(
    "I've provided enough detail - generate the SRS now.",
    value=current_count >= MAX_EXCHANGES,
)

col_gen, col_title = st.columns([2, 1])
with col_gen:
    if st.button(
        "⚡ Generate SRS",
        type="primary",
        disabled=not satisfied,
        help="Generates a 5-file architecture SRS from your conversation",
    ):
        with st.spinner("Generating your SRS..."):
            srs_text, err = agents.generate_srs(
                st.session_state.pb_chat,
                st.session_state.get("api_key", ""),
            )
        if err:
            st.error(err)
        else:
            st.session_state.pb_final_srs = srs_text or ""
            st.success("✅ SRS generated - review and copy it below.")
            st.rerun()
with col_title:
    st.session_state.pb_title = st.text_input(
        "Title / label",
        value=st.session_state.get("pb_title", "App SRS"),
        placeholder="e.g. Customer Churn Predictor",
    )

if st.session_state.get("pb_final_srs"):
    st.markdown('<hr class="styled-divider">', unsafe_allow_html=True)
    st.markdown('<div class="section-header">📋 SRS Prompt</div>', unsafe_allow_html=True)

    view_mode = st.radio(
        "View mode:",
        ["Rendered (Markdown)", "Raw (Copy-able)"],
        horizontal=True,
        label_visibility="collapsed",
    )

    st.markdown('<div class="srs-output-wrap">', unsafe_allow_html=True)
    if view_mode == "Rendered (Markdown)":
        st.markdown(st.session_state.pb_final_srs)
    else:
        st.markdown(
            '<div class="srs-copy-hint">Use the copy icon (⧉) in the top-right corner of the code block to copy the full prompt.</div>',
            unsafe_allow_html=True,
        )
        st.code(st.session_state.pb_final_srs, language=None)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("")
    if st.button(
        "💾 Save to Google Sheets",
        type="primary",
        disabled=not st.session_state.user_email,
    ):
        if not st.session_state.user_email:
            st.error("Please login with Google first.")
        elif not st.session_state.user_sheet_id:
            st.error("No sheet found. Please try logging in again.")
        else:
            srs = st.session_state.pb_final_srs or ""
            timestamp = datetime.utcnow().isoformat() + "Z"
            feature_lines = [
                line.strip()
                for line in srs.splitlines()
                if line.strip().startswith(("-", "•", "*"))
            ]
            row = [
                timestamp,
                srs,
                len(feature_lines),
                "\n".join(feature_lines),
                len(st.session_state.pb_chat),
            ]
            ok, err = append_prompt_row(
                st.session_state.user_creds,
                st.session_state.user_sheet_id,
                row,
            )
            if ok:
                sheet_url = (
                    f"https://docs.google.com/spreadsheets/d/{st.session_state.user_sheet_id}"
                )
                st.success(f"✅ Saved to your Google Sheet! [Open Sheet]({sheet_url})")
            else:
                st.error(err)

    if not st.session_state.user_email:
        st.caption("⚠️ Login required to save")
