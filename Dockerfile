FROM ghcr.io/astral-sh/uv:python3.12-alpine

WORKDIR /boo

COPY requirements.txt /boo
RUN uv pip install --no-cache-dir --system -r requirements.txt

COPY . /boo
