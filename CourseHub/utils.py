
import google.generativeai as genai
import json
import typing
import traceback

def generate_course_content(api_key: str, subject: str, topics: str, duration: int) -> typing.Tuple[typing.Optional[dict], typing.Optional[str]]:
    """
    Generates a structured course using Google Gemini API.
    
    Args:
        api_key: The Google Gemini API key.
        subject: The subject of the course.
        topics: The specific topics to cover.
        duration: The duration of the course in days.
        
    Returns:
        A tuple (course_data, error_message).
        course_data is a dictionary containing the course structure or None if generation fails.
        error_message is a string describing the error or None if success.
    """
    try:
        genai.configure(api_key=api_key)
        
        # Try multiple model versions including newer ones
        models_to_try = [
            'gemini-2.0-flash',
            'gemini-2.0-flash-lite',
            'gemini-flash-latest',
            'gemini-1.5-flash',
            'gemini-1.5-pro',
            'gemini-pro',
            'models/gemini-1.5-flash'
        ]
        
        last_exception = None
        model = None
        
        for model_name in models_to_try:
            try:
                print(f"Trying model: {model_name}")
                model = genai.GenerativeModel(model_name)
                # Test connectivity with a dummy prompt (optional, but good to fail fast?) 
                # Actually, just run the real prompt. If it fails due to model not found, catch it.
                break 
                # Note: creating GenerativeModel object doesn't validate it. 
                # Validation happens at generate_content.
            except Exception as e:
                print(f"Model {model_name} failed setup: {e}")
                last_exception = e
                continue
        
        if not model:
             # Just use the first one if all failed setup (unlikely) or last used
             model = genai.GenerativeModel('gemini-2.0-flash')

        prompt = f"""
        Act as an expert educational content creator. Create a strictly structured {duration}-day course on the subject "{subject}".
        
        Focus on these specific topics:
        {topics}
        
        For each day, provide:
        1. A topic title.
        2. Detailed lesson content in Markdown format.
        3. A quiz with 3-5 multiple choice questions.
        
        You must output strictly conformant JSON with no markdown formatting around it (no ```json or ```). 
        The JSON structure must be a list of objects, one for each day.
        
        JSON Structure Example:
        [
            {{
                "day_number": 1,
                "topic_title": "Introduction to ...",
                "content_markdown": "# Lesson Header\\n\\nLesson content...",
                "quiz": [
                    {{
                        "question": "What is...?",
                        "options": ["Option A", "Option B", "Option C", "Option D"],
                        "correct_index": 0
                    }}
                ]
            }}
        ]
        """
        
        # We need to loop again for generation because that's where the 404/400 happens
        for model_name in models_to_try:
            try:
                print(f"Generating content with model: {model_name}")
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt)
                
                # Check if response has text (caught by safety filters?)
                if not response.text:
                     raise ValueError("Empty response (possibly blocked by safety settings)")

                # Clean up response text if it contains markdown code blocks
                text = response.text.strip()
                if text.startswith("```json"):
                    text = text[7:]
                if text.startswith("```"):
                    text = text[3:]
                if text.endswith("```"):
                    text = text[:-3]
                    
                course_data = json.loads(text)
                return course_data, None
            except Exception as e:
                print(f"Model {model_name} failed generation: {e}")
                last_exception = e
                continue
        
        # If we reach here, all models failed
        return None, f"All models failed. Last error: {str(last_exception)}"

    except Exception as e:
        print(f"Error generating course: {traceback.format_exc()}")
        return None, str(e)
