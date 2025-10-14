FROM ghcr.io/astral-sh/uv:python3.12-alpine

# For voice
RUN apk add --no-cache opus opus-dev ffmpeg

WORKDIR /boo

COPY pyproject.toml ./
COPY uv.lock ./

RUN uv sync --frozen --no-install-project --no-dev

COPY . .
