FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Create .streamlit directory if it doesn't exist
RUN mkdir -p .streamlit

# Expose proxy port
EXPOSE 8501

# Run Streamlit on 8502 and lightweight proxy on 8501 that serves /healthz and forwards other traffic
CMD ["sh", "-c", "streamlit run app.py --server.port=8502 --server.address=0.0.0.0 --server.headless=true & python proxy.py"]
