# Use a slim Python base image for efficiency
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Ollama
RUN curl https://ollama.ai/install.sh | sh

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ src/
COPY config.yaml .

# Create directories for data and ChromaDB
RUN mkdir -p /app/data /app/chroma_db /app/logs

# Copy sample data (optional, can be mounted at runtime)
COPY data/ /app/data/

# Expose FastAPI port
EXPOSE 8000

# Start Ollama server and FastAPI
CMD ["sh", "-c", "ollama serve & sleep 5 && ollama pull deepseek-llm:7b && uvicorn src.main:app --host 0.0.0.0 --port 8000"]