import json
import os
import requests
import typing
import re

def _hf_config() -> typing.Tuple[str, str]:
    token = os.getenv("HF_API_TOKEN", "").strip() or os.getenv("HUGGINGFACEHUB_API_TOKEN", "").strip()
    model_id = os.getenv("HF_MODEL_ID", "mistralai/Mistral-7B-Instruct-v0.3").strip()
    api_url = os.getenv("HF_API_URL", f"https://router.huggingface.co/hf-inference/models/{model_id}").strip()
    return token, api_url


def _extract_json_array(text: str):
    cleaned = text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    if cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    try:
        return json.loads(cleaned)
    except Exception:
        match = re.search(r"\[.*\]", cleaned, flags=re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def _generate_with_mistral(prompt: str) -> str:
    token, api_url = _hf_config()
    if not token:
        raise ValueError("HF_API_TOKEN is not configured in environment.")

    response = requests.post(
        api_url,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={
            "inputs": prompt,
            "parameters": {"max_new_tokens": 1800, "temperature": 0.3, "return_full_text": False},
            "options": {"wait_for_model": True},
        },
        timeout=240,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"HF inference failed ({response.status_code}): {response.text}")

    data = response.json()
    if isinstance(data, list) and data and isinstance(data[0], dict):
        text = (data[0].get("generated_text") or "").strip()
        if text:
            return text
    raise RuntimeError("HF response did not include generated_text.")


def generate_course_content(subject: str, topics: str, duration: int) -> typing.Tuple[typing.Optional[dict], typing.Optional[str]]:
    """
    Generates a structured course using Hugging Face Mistral.
    
    Args:
        subject: The subject of the course.
        topics: The specific topics to cover.
        duration: The duration of the course in days.
        
    Returns:
        A tuple (course_data, error_message).
        course_data is a dictionary containing the course structure or None if generation fails.
        error_message is a string describing the error or None if success.
    """
    try:
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
        text = _generate_with_mistral(prompt)
        course_data = _extract_json_array(text)
        return course_data, None

    except Exception as e:
        return None, str(e)
