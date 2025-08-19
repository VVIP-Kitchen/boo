FROM python:3.12-alpine

RUN apk add --no-cache gcc musl-dev libffi-dev \
    && pip install --no-cache-dir fastapi uvicorn

### Create non-root user
RUN useradd -m sandboxuser
USER sandboxuser

WORKDIR /app
COPY app.py /app

### Use tmpfs inside the container for temp files --
### so Python writes code to an isolated in-memory /tmp
VOLUME [ "/tmp" ]

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8081"]