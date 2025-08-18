FROM ghcr.io/astral-sh/uv:python3.12-alpine

WORKDIR /boo

COPY pyproject.toml ./
COPY uv.lock ./

RUN uv sync --system --frozen --no-dev

COPY . .
