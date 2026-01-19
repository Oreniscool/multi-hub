import streamlit as st
import importlib

def run_ai_swot():
    company = st.session_state.get('company_input_val', '')
    if not company:
        st.error("Enter a company name.")
        return

    from utils.ai_handler import AIHandler
    ai = AIHandler()
    result = ai.generate_swot(company)
    
    # Update session state keys that are bound to the text areas
    # However, since text areas use 'key', we can't just set the variable, we need to set the key in session state
    st.session_state['swot_s'] = result.get('strengths', '')
    st.session_state['swot_w'] = result.get('weaknesses', '')
    st.session_state['swot_o'] = result.get('opportunities', '')
    st.session_state['swot_t'] = result.get('threats', '')
    
    # Also update the keys used by text_area widgets if they differ, but here we used 'swot_s' etc as defaults.
    # Actually, in the previous code, I used value=st.session_state.get('swot_s').
    # If I want the widget to update, I should just set the key associated with the widget if it has one, OR set the value used in 'value' param and trigger rerun.
    # The previous code used `key="s_input"`. So I should update `st.session_state["s_input"]`?
    # No, Streamlit widgets are tricky. If `value` is provided, it sets the initial value.
    # To update it programmatically, we should set the key `s_input` in session_state.
    
    st.session_state['s_input'] = result.get('strengths', '')
    st.session_state['w_input'] = result.get('weaknesses', '')
    st.session_state['o_input'] = result.get('opportunities', '')
    st.session_state['t_input'] = result.get('threats', '')

def show():
    st.title("📋 SWOT Generator")
    st.markdown("---")

    st.write("Analyze the Strengths, Weaknesses, Opportunities, and Threats for your target entity.")

    # We need to render text areas. 
    # If we want them to be updatable by AI, they should read from a source of truth or their keys should be managed.
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Strengths")
        # No 'value' argument if we want it to correspond 1:1 with key in session state for updates?
        # Actually providing 'value' usually overrides unless key is in session state?
        # Best practice: Do not pass 'value' if you want to control via session_state[key], OR pass value=session_state[key].
        # Let's use the key approach.
        s = st.text_area("Internal positive attributes", key="s_input", height=150, placeholder="- Strong brand recognition\n- High cash reserves")
        
        st.subheader("Opportunities")
        o = st.text_area("External positive factors", key="o_input", height=150, placeholder="- Emerging markets\n- New technology adoption")
        
    with col2:
        st.subheader("Weaknesses")
        w = st.text_area("Internal negative attributes", key="w_input", height=150, placeholder="- High debt\n- Outdated infrastructure")
        
        st.subheader("Threats")
        t = st.text_area("External negative factors", key="t_input", height=150, placeholder="- New regulations\n- intense competition")

    col_btn1, col_btn2 = st.columns([1, 1])
    
    # We remove the "Generate Report" flag logic and just use the Render button at the bottom for simplicity
    
    with col_btn2:
        # Use key for input to read it in callback
        st.text_input("Company Name for AI", key="company_input_val", placeholder="e.g. Tesla")
        # Button with on_click callback
        st.button("✨ Generate with AI", on_click=run_ai_swot)

    st.markdown("---")
    if st.button("Render Matrix View", type="primary"): 
        st.subheader("SWOT Analysis Matrix")
        
        # Display as a grid
        st.markdown(f"""
        <style>
        .swot-box {{
            padding: 20px;
            border-radius: 10px;
            height: 100%;
            color: black;
        }}
        </style>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
            <div class="swot-box" style="background-color: #a8e6cf;">
                <h3>Strengths</h3>
                <p>{s.replace(chr(10), '<br>')}</p>
            </div>
            <div class="swot-box" style="background-color: #ffaaa5;">
                <h3>Weaknesses</h3>
                <p>{w.replace(chr(10), '<br>')}</p>
            </div>
            <div class="swot-box" style="background-color: #dcedc1;">
                <h3>Opportunities</h3>
                <p>{o.replace(chr(10), '<br>')}</p>
            </div>
            <div class="swot-box" style="background-color: #ff8b94;">
                <h3>Threats</h3>
                <p>{t.replace(chr(10), '<br>')}</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
