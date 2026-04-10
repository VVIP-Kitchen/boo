FROM ghcr.io/astral-sh/uv:python3.12-alpine

# Install build dependencies for scientific packages
RUN apk add --no-cache \
    gcc \
    g++ \
    musl-dev \
    libffi-dev \
    openblas-dev \
    freetype-dev \
    libpng-dev \
    jpeg-dev

WORKDIR /app

# Copy dependency files
COPY pyproject.toml ./

# Install dependencies using uv (without lockfile)
RUN uv sync --no-install-project --no-dev

# Remove build deps to reduce image size
RUN apk del gcc g++

# Create non-root user and .cache directory with proper ownership
RUN adduser -D sandboxuser && \
    mkdir -p /home/sandboxuser/.cache && \
    chown -R sandboxuser:sandboxuser /home/sandboxuser/.cache
USER sandboxuser

# Copy application code
COPY app.py /app

# Use tmpfs inside the container for temp files --
# so Python writes code to an isolated in-memory /tmp
VOLUME [ "/tmp" ]

CMD ["/app/.venv/bin/python", "-c", "import uvicorn; uvicorn.run('app:app', host='0.0.0.0', port=8081)"]
