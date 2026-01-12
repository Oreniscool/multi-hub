
import google.generativeai as genai

# API key should be passed as argument or environment variable - not hardcoded
api_key = ""  # Enter your API key here for testing
genai.configure(api_key=api_key)

try:
    print("Listing models...")
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"- {m.name}")
except Exception as e:
    print(f"Error listing models: {e}")
