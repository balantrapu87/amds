FROM node:22-bookworm-slim

# Install system dependencies, Chromium, and FFmpeg with full filtergraph support
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-venv \
    ffmpeg \
    chromium \
    fonts-inter \
    fonts-freefont-ttf \
    curl \
    ca-certificates \
    libnss3 \
    libatk-bridge2.0-0 \
    libx11-xcb1 \
    libdrm2 \
    libgbm1 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true
ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Copy dependency definitions
COPY remotion/package*.json ./remotion/
COPY engine/requirements.txt ./engine/

# Install Node and Python dependencies
RUN cd remotion && npm install --legacy-peer-deps
RUN pip3 install --no-cache-dir --break-system-packages -r engine/requirements.txt

# Copy application source
COPY remotion ./remotion
COPY engine ./engine
COPY architecture ./architecture

# Create working directories
RUN mkdir -p output jobs assets/raw-svgs assets/audio

EXPOSE 8000

ENV REMOTION_ROOT=/app/remotion
ENV OUTPUT_DIR=/app/output
ENV JOBS_DIR=/app/jobs
ENV RENDER_CONCURRENCY=16
ENV LLM_ENDPOINT=http://llama-swap:8080/v1/chat/completions
ENV LLM_MODEL=qwen

CMD ["uvicorn", "engine.api:app", "--host", "0.0.0.0", "--port", "8000"]
