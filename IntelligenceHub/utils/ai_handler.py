import google.generativeai as genai
import json
import os

# Ideally this comes from secrets, but user provided it directly for this session.
API_KEY = "AIzaSyAF1pSbeOWw54HXdFaxHg0Oa3QsqlZitkI"

class AIHandler:
    def __init__(self):
        try:
            genai.configure(api_key=API_KEY)
            self.model = genai.GenerativeModel('gemini-2.0-flash')
        except Exception as e:
            print(f"Error configuring Gemini: {e}")
            self.model = None

    def generate_swot(self, company_name):
        if not self.model:
             return {"strengths": "Error", "weaknesses": "Check API Key", "opportunities": "", "threats": ""}
        
        prompt = f"""
        Generate a SWOT analysis for '{company_name}'.
        Return ONLY a raw JSON object (no markdown formatting) with keys: 'strengths', 'weaknesses', 'opportunities', 'threats'.
        Each value should be a string with bullet points (using - ).
        """
        try:
            response = self.model.generate_content(prompt)
            # clean response if it has markdown code blocks
            text = response.text.replace('```json', '').replace('```', '').strip()
            return json.loads(text)
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
        if not self.model or not headlines:
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
            response = self.model.generate_content(prompt)
            text = response.text.replace('```json', '').replace('```', '').strip()
            return json.loads(text)
        except Exception as e:
            # Fallback to just returning original with unknown
            return [{"headline": h, "category": "Unknown", "sentiment": "Neutral"} for h in headlines]

    def analyze_competition(self, data_summary):
        if not self.model:
            return "AI not configured."
            
        prompt = f"""
        Act as a Senior Market Analyst.
        Analyze the following competitive data summary and provide 3 key strategic insights.
        
        Data:
        {data_summary}
        
        Keep it concise and professional.
        """
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Error generating insights: {e}"

    def generate_competitive_data(self, industry):
        if not self.model:
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
            response = self.model.generate_content(prompt)
            text = response.text.replace('```json', '').replace('```', '').strip()
            return json.loads(text)
        except Exception as e:
            print(f"Error generating comp data: {e}")
            return None
