# ---- Build stage ----
FROM python:3.12-slim AS base

# Prevent Python from writing .pyc files and ensure stdout/stderr are unbuffered
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install system deps (if httpx/http2 needs ca-certificates, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
 && rm -rf /var/lib/apt/lists/*

# Copy project
COPY . /app

# Install python deps in editable mode (includes accuro_adapter)
RUN pip install --upgrade pip && \
    pip install -e . && \
    pip install fastapi uvicorn[standard] python-dotenv "httpx[http2]"

# Expose the default uvicorn port
EXPOSE 8000

# Default command
CMD ["uvicorn", "accuro_adapter.api:app", "--host", "0.0.0.0", "--port", "8000"]
