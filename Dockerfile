# Stillpoint — Dockerfile
#
# Base: python:3.11-slim
#
# IMPORTANT LIMITATION: The `notebooklm` CLI cannot be containerized. It
# requires browser-based Google OAuth (a one-time interactive login) that
# stores session cookies in ~/.notebooklm/storage_state.json. There is no
# headless, non-interactive authentication path compatible with Docker at
# build or runtime. NotebookLM grounding will return [UNGROUNDED] responses
# inside the container. To use NotebookLM grounding, run Stillpoint natively
# via scripts/setup.sh instead.
#
# What this container DOES support:
#   - The full Gradio web UI on port 7860
#   - The onboarding wizard (character design, config generation)
#   - Session memory (file-based and ChromaDB, mounted via volumes)
#   - Report generation
#   - All LLM providers (via env vars)
#
# Usage:
#   docker compose up
#   Open http://localhost:7860

FROM python:3.11-slim

# Install system dependencies required for ChromaDB's native extensions
# and any C-extension wheels that don't ship pre-built for linux/amd64.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libsqlite3-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python dependencies before copying the full source so that
# the pip layer is cached when only application code changes.
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy package manifest and install the stillpoint package in editable mode
# so the installed package reflects the mounted source at runtime.
COPY pyproject.toml ./
COPY stillpoint/ ./stillpoint/
COPY app/ ./app/
COPY templates/ ./templates/

# Install the local package (no-deps: all deps already installed above)
RUN pip install --no-cache-dir -e . --no-deps

# Create directories that will be populated via volume mounts at runtime.
# Having them in the image means the app can start without a mounted volume.
RUN mkdir -p /app/config /app/personas /app/sessions \
             /root/.stillpoint/palace

# Expose the Gradio default port
EXPOSE 7860

# Gradio binds to 0.0.0.0 inside the container so it's reachable from the host.
ENV GRADIO_SERVER_NAME=0.0.0.0
ENV GRADIO_SERVER_PORT=7860

# Launch the Gradio UI
CMD ["python", "-m", "app.main"]
