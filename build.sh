#!/bin/bash

# MultiHub Build Script for HuggingFace Spaces

echo "🚀 Building MultiHub for HuggingFace Spaces..."

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    exit 1
fi

echo "✓ Python 3 found"

# Check if pip is available
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 is required but not installed."
    exit 1
fi

echo "✓ pip3 found"

# Install requirements
echo "📦 Installing dependencies..."
pip3 install -r requirements.txt --quiet

if [ $? -eq 0 ]; then
    echo "✓ Dependencies installed successfully"
else
    echo "❌ Failed to install dependencies"
    exit 1
fi

# Verify .streamlit directory and config
if [ ! -d ".streamlit" ]; then
    echo "📁 Creating .streamlit directory..."
    mkdir -p .streamlit
fi

echo "✓ Streamlit configuration ready"

echo ""
echo "✅ MultiHub is ready for deployment!"
echo ""
echo "To run locally:"
echo "  streamlit run app.py"
echo ""
echo "To deploy to HuggingFace Spaces:"
echo "  git add ."
echo "  git commit -m 'MultiHub ready for HF deployment'"
echo "  git push"
