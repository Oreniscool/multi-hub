import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils import load_data, classify_text
import pandas as pd

def test_load_demo_data():
    print("Testing load_data('demo')...")
    df = load_data('demo')
    assert df is not None
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 15, f"Expected 15 rows, got {len(df)}"
    assert 'text' in df.columns
    print("PASS: 15 Demo emails loaded successfully.")

def test_classify_no_key():
    print("Testing classify_text with no key...")
    # Updated to pass a dummy prompt
    result = classify_text("Test", "", "Classify this")
    assert result == "Error: No API Key"
    print("PASS: Missing API key handled.")

if __name__ == "__main__":
    try:
        test_load_demo_data()
        test_classify_no_key()
        print("\nAll basic tests passed!")
    except AssertionError as e:
        print(f"\nFAIL: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR: {e}")
        sys.exit(1)
