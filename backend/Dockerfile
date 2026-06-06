# =============================================================================
# AI Video SaaS — backend/Dockerfile
# Multi-stage build for the FastAPI API server.
# Stage 1 (builder): installs Python deps into a venv.
# Stage 2 (runtime): copies only the venv + app code — no build tools in prod.
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1 — builder
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS builder

# Prevent .pyc files and enable unbuffered stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    VENV_PATH=/opt/venv

# Install build dependencies (needed to compile some Python extensions)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create isolated virtual environment
RUN python -m venv $VENV_PATH
ENV PATH="$VENV_PATH/bin:$PATH"

# Copy and install Python dependencies first (layer-cache friendly)
WORKDIR /build
COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt

# -----------------------------------------------------------------------------
# Stage 2 — runtime
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VENV_PATH=/opt/venv \
    APP_HOME=/app \
    PATH="/opt/venv/bin:$PATH"

# Install runtime system dependencies only
# ffmpeg + ffprobe: video processing
# piper: TTS binary (installed separately — see entrypoint note)
# curl: health checks
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    ffmpeg \
    curl \
    wget \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Piper TTS binary
ARG PIPER_VERSION=2023.11.14-2
RUN ARCH=$(dpkg --print-architecture) && \
    wget -q "https://github.com/rhasspy/piper/releases/download/${PIPER_VERSION}/piper_${ARCH}.tar.gz" \
    -O /tmp/piper.tar.gz && \
    tar -xzf /tmp/piper.tar.gz -C /usr/local/bin --strip-components=1 && \
    rm /tmp/piper.tar.gz && \
    piper --help > /dev/null 2>&1 || true

# Create non-root user for security
RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid appgroup --shell /bin/bash --create-home appuser

# Copy virtual environment from builder
COPY --from=builder $VENV_PATH $VENV_PATH

# Set up application directory
WORKDIR $APP_HOME

# Create required directories with correct ownership
RUN mkdir -p \
    $APP_HOME/media/uploads \
    $APP_HOME/media/processed \
    $APP_HOME/media/thumbnails \
    $APP_HOME/media/audio \
    $APP_HOME/logs \
    $APP_HOME/models/piper \
    $APP_HOME/models/whisper \
    && chown -R appuser:appgroup $APP_HOME

# Copy application source code
COPY --chown=appuser:appgroup . $APP_HOME

# Switch to non-root user
USER appuser

# Expose API port
EXPOSE 8000

# Health check — /health returns 200 when the app is ready
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command: production Uvicorn (override in docker-compose for dev --reload)
CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "1", \
     "--loop", "uvloop", \
     "--http", "httptools", \
     "--log-level", "info", \
     "--access-log"]