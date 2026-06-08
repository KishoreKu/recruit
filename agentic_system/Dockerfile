# ============================================================
#  Dockerfile for Agentic Placement System
# ============================================================
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (including curl for health checks if needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy pyproject.toml first to cache dependency installation
COPY pyproject.toml .

# Install dependencies using pip (since pyproject.toml is modern, we can use pip install)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# Copy the rest of the application files
COPY . .

# Expose orchestrator port (standard port 8200)
EXPOSE 8200

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV ORCHESTRATOR_PORT=8200

# Run the FastAPI app via uvicorn
CMD ["uvicorn", "orchestrator:app", "--host", "0.0.0.0", "--port", "8200"]
