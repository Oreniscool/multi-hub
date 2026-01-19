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

# Health check uses PORT if set, else 8501
HEALTHCHECK CMD sh -c "curl --fail http://localhost:${PORT:-8501}/_stcore/health || exit 1"

# Run Streamlit on PORT (defaults to 8501) and serve at /healthz so health probes succeed
CMD ["sh", "-c", "streamlit run app.py --server.port=${PORT:-8501} --server.address=0.0.0.0 --server.baseUrlPath=healthz"]
