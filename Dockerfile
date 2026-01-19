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

# Expose default Streamlit port (overridable via PORT)
EXPOSE 8501

# No container healthcheck (disabled to avoid platform probe conflicts)

# Run Streamlit on fixed port 8501 (ignore platform PORT env to satisfy health probe)
CMD ["sh", "-c", "streamlit run app.py --server.port=8501 --server.address=0.0.0.0 --server.headless=true"]
