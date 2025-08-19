FROM python:3.12-alpine

RUN apk add --no-cache gcc musl-dev libffi-dev \
    && pip install --no-cache-dir fastapi uvicorn

WORKDIR /app
COPY app.py /app

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8081"]