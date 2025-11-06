# Multi-stage Dockerfile for FastAPI backend (development optimized)

# ---- Base ----
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System dependencies installation
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       git build-essential curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt /app/requirements.txt

RUN pip install --upgrade pip \
    && pip install -r /app/requirements.txt

# ---- Development ----
FROM base AS dev

# Create a non-root user for safer container execution
RUN useradd -ms /bin/bash appuser

# Copy the entire backend folder to /app/backend/
COPY backend/ /app/backend/

# Environment is provided via docker-compose env_file; do not COPY .env here

# Fix ownership so appuser owns the files
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose the FastAPI port
EXPOSE 8000

# Set environment variables for development mode
ENV ENVIRONMENT=development \
    DEBUG=true
# Ensure Python can import the backend package
ENV PYTHONPATH=/app

# Add healthcheck for container to verify FastAPI is running
HEALTHCHECK --interval=30s --timeout=5s --retries=5 CMD curl -fsS http://localhost:8000/health || exit 1

# Start FastAPI with hot reload enabled
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
