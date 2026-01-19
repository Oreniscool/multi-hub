
import google.generativeai as genai

api_key = "AIzaSyAF1pSbeOWw54HXdFaxHg0Oa3QsqlZitkI"
genai.configure(api_key=api_key)

try:
    print("Listing models...")
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"- {m.name}")
except Exception as e:
    print(f"Error listing models: {e}")
