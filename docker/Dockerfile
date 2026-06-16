# ── Smart Health Sync — Docker Image ─────────────────────────
# Authors: Enock Queenson Eduafo & Christabel Araba Edumadze | University of Ghana 2026

FROM python:3.11-slim

# Metadata
LABEL maintainer="Enock Queenson Eduafo & Christabel Araba Edumadze | University of Ghana"
LABEL description="Smart Health Sync — AI-Powered Clinical Diagnostic Platform"
LABEL version="2.0.0"

# Set working directory
WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Ensure models directory exists
RUN mkdir -p /app/models

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:5000/api/health || exit 1

# Production startup
CMD ["gunicorn", "main:app", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "120", "--log-level", "info"]
