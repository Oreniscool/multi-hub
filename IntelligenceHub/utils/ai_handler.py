import json
import os
import requests


def _extract_json(text: str):
    cleaned = text.replace("```json", "").replace("```", "").strip()
    return json.loads(cleaned)

class AIHandler:
    def __init__(self):
        self.token = os.getenv("HF_API_TOKEN", "").strip() or os.getenv("HUGGINGFACEHUB_API_TOKEN", "").strip()
        model_id = os.getenv("HF_MODEL_ID", "mistralai/Mistral-7B-Instruct-v0.3").strip()
        self.api_url = os.getenv("HF_API_URL", f"https://router.huggingface.co/hf-inference/models/{model_id}").strip()

    def _generate(self, prompt: str, max_new_tokens: int = 900, temperature: float = 0.2) -> str:
        if not self.token:
            raise ValueError("HF_API_TOKEN is not configured in environment.")

        response = requests.post(
            self.api_url,
            headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"},
            json={
                "inputs": prompt,
                "parameters": {
                    "max_new_tokens": max_new_tokens,
                    "temperature": temperature,
                    "return_full_text": False,
                },
                "options": {"wait_for_model": True},
            },
            timeout=180,
        )
        if response.status_code >= 400:
            raise RuntimeError(f"HF inference failed ({response.status_code}): {response.text}")

        data = response.json()
        if isinstance(data, list) and data and isinstance(data[0], dict):
            text = (data[0].get("generated_text") or "").strip()
            if text:
                return text
        raise RuntimeError("HF response did not include generated_text.")

    def generate_swot(self, company_name):
        if not self.token:
             return {"strengths": "Error", "weaknesses": "Set HF_API_TOKEN in .env", "opportunities": "", "threats": ""}
        
        prompt = f"""
        Generate a SWOT analysis for '{company_name}'.
        Return ONLY a raw JSON object (no markdown formatting) with keys: 'strengths', 'weaknesses', 'opportunities', 'threats'.
        Each value should be a string with bullet points (using - ).
        """
        try:
            text = self._generate(prompt, max_new_tokens=700, temperature=0.2)
            return _extract_json(text)
        except Exception as e:
            return {
                "strengths": f"Error generating: {str(e)}", 
                "weaknesses": "", "opportunities": "", "threats": ""
            }

    def categorize_news(self, headlines):
        """
        headlines: list of strings
        Returns: list of dicts {headline, category, sentiment}
        """
        if not self.token or not headlines:
            return []

        prompt = f"""
        Analyze the following news headlines.
        For EACH headline, determine its:
        1. Category (e.g., Technology, Finance, Politics, Global, Market)
        2. Sentiment (Positive, Negative, Neutral)

        Headlines:
        {json.dumps(headlines)}

        Return ONLY a raw JSON list of objects (no markdown) with keys: 'headline', 'category', 'sentiment'.
        """
        try:
            text = self._generate(prompt, max_new_tokens=700, temperature=0.1)
            return _extract_json(text)
        except Exception as e:
            # Fallback to just returning original with unknown
            return [{"headline": h, "category": "Unknown", "sentiment": "Neutral"} for h in headlines]

    def analyze_competition(self, data_summary):
        if not self.token:
            return "AI not configured."
            
        prompt = f"""
        Act as a Senior Market Analyst.
        Analyze the following competitive data summary and provide 3 key strategic insights.
        
        Data:
        {data_summary}
        
        Keep it concise and professional.
        """
        try:
            return self._generate(prompt, max_new_tokens=500, temperature=0.2)
        except Exception as e:
            return f"Error generating insights: {e}"

    def generate_competitive_data(self, industry):
        if not self.token:
            return None
        
        prompt = f"""
        Generate realistic competitive analysis data for the '{industry}' industry.
        Create 5-8 fake or real companies.
        IMPORTANT: Ensure Market Shares are UNEQUAL and REALISTIC (e.g., one leader with 40%, others with 20%, 15%, etc.). Do NOT make them equal.
        Return ONLY a raw JSON list of objects (no markdown) where each object has:
        - 'Competitor': string (Company Name)
        - 'Market Share (%)': number (float, e.g. 45.5, not string)
        - 'Revenue ($M)': number (integer, e.g. 5000)
        """
        try:
            text = self._generate(prompt, max_new_tokens=800, temperature=0.2)
            return _extract_json(text)
        except Exception as e:
            print(f"Error generating comp data: {e}")
            return None
