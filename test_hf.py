import os
from huggingface_hub import InferenceClient

def test_calls():
    token = os.getenv("HF_API_TOKEN")
    if not token:
        print("HF_API_TOKEN not found in environment")
        return

    client = InferenceClient(token=token)
    models = ['mistralai/Mistral-7B-Instruct-v0.3:novita', 'mistralai/Mistral-Small-24B-Instruct-2501:novita']
    
    print(f"Testing with token: {'<REDACTED>' if token else 'None'}")

    # 1. client.text_generation
    print("\n--- Test 1: client.text_generation (Mistral-7B) ---")
    try:
        res = client.text_generation(model=models[0], prompt='Reply with ok', max_new_tokens=8)
        print(f"Result: {res}")
    except Exception as e:
        print(f"Error: {e}")

    # 2. client.chat.completions.create
    print("\n--- Test 2: client.chat.completions.create (Mistral-7B) ---")
    try:
        res = client.chat.completions.create(model=models[0], messages=[{'role':'user','content':'Reply with ok'}], max_tokens=8)
        print(f"Result: {res.choices[0].message.content}")
    except Exception as e:
        print(f"Error: {e}")

    # 3. client.conversational
    print("\n--- Test 3: client.conversational (Mistral-7B) ---")
    try:
        if hasattr(client, 'conversational'):
            res = client.conversational(model=models[0], messages=[{'role':'user','content':'Reply with ok'}])
            print(f"Result: {res}")
        else:
            print("client.conversational not available")
    except Exception as e:
        print(f"Error: {e}")

    # 4. client.chat.completions.create (Mistral-Small-24B)
    print("\n--- Test 4: client.chat.completions.create (Mistral-Small-24B) ---")
    try:
        res = client.chat.completions.create(model=models[1], messages=[{'role':'user','content':'Reply with ok'}], max_tokens=8)
        print(f"Result: {res.choices[0].message.content}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_calls()
