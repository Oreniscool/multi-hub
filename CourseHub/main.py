
import streamlit as st
import utils

# Page Configuration
st.set_page_config(
    page_title="AI Course Generator",
    page_icon="🎓",
    layout="wide"
)

# Initialize Session State
if 'course_data' not in st.session_state:
    st.session_state.course_data = None
if 'generated_course' not in st.session_state: # Flag to track generation
    st.session_state.generated_course = False

# Sidebar Configuration
with st.sidebar:
    st.header("Configuration")
    
    # API Key Input (Pre-filled for convenience as per prompt, but editable)
    default_api_key = "AIzaSyAF1pSbeOWw54HXdFaxHg0Oa3QsqlZitkI"
    api_key = st.text_input("Gemini API Key", value=default_api_key, type="password")
    
    st.divider()
    
    # Course Preferences
    subject = st.text_input("Subject", placeholder="e.g., Python Programming")
    topics = st.text_area("Topics to Cover", placeholder="e.g., Data Types, Loops, Functions, Classes")
    duration = st.slider("Duration (Days)", min_value=1, max_value=10, value=3)
    
    generate_btn = st.button("Generate Course", type="primary")

# Main Content Area
st.title("🎓 AI Course Generator")

if generate_btn:
    if not api_key:
        st.error("Please enter a valid Google Gemini API Key.")
    elif not subject or not topics:
        st.error("Please provide both a Subject and Topics to cover.")
    else:
        with st.spinner(f"Generating your {duration}-day course on '{subject}'..."):
            course_data, error_message = utils.generate_course_content(api_key, subject, topics, duration)
            
            if course_data:
                st.session_state.course_data = course_data
                st.session_state.generated_course = True
                st.success("Course generated successfully!")
                st.balloons()
            else:
                st.error(f"Failed to generate course. Error: {error_message}")
                st.info("Check your API key and try again.")

# Display Course Content
if st.session_state.generated_course and st.session_state.course_data:
    course = st.session_state.course_data
    
    # Day Navigation
    days = [f"Day {day['day_number']}: {day['topic_title']}" for day in course]
    selected_day_idx = st.radio("Navigate Course", range(len(course)), format_func=lambda i: days[i], horizontal=True)
    
    current_day_data = course[selected_day_idx]
    
    st.divider()
    
    # Header & Content
    st.header(f"Day {current_day_data['day_number']}: {current_day_data['topic_title']}")
    st.markdown(current_day_data['content_markdown'])
    
    st.divider()
    
    # Quiz Section
    st.subheader("📝 Daily Quiz")
    
    with st.form(key=f"quiz_form_{current_day_data['day_number']}"):
        user_answers = {}
        for i, q in enumerate(current_day_data['quiz']):
            st.markdown(f"**Q{i+1}. {q['question']}**")
            user_answers[i] = st.radio(f"Select answer for Q{i+1}", q['options'], key=f"q_{current_day_data['day_number']}_{i}", label_visibility="collapsed")
            st.write("") # Spacer

        submitted = st.form_submit_button("Submit Answers")
        
        if submitted:
            score = 0
            total = len(current_day_data['quiz'])
            
            for i, q in enumerate(current_day_data['quiz']):
                correct_option = q['options'][q['correct_index']]
                if user_answers[i] == correct_option:
                    score += 1
                    st.success(f"Q{i+1}: Correct!")
                else:
                    st.error(f"Q{i+1}: Incorrect. The correct answer was: {correct_option}")
            
            st.info(f"**Your Score: {score}/{total}**")

else:
    st.info("👈 Enter your course preferences in the sidebar and click 'Generate Course' to begin!")
