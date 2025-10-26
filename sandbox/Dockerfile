FROM python:3.12-alpine

RUN apk add --no-cache \
    gcc \
    g++ \
    musl-dev \
    libffi-dev \
    openblas-dev \
    freetype-dev \
    libpng-dev \
    jpeg-dev \
    && pip install --no-cache-dir \
    fastapi \
    uvicorn \
    numpy \
    pandas \
    matplotlib \
    scipy \
    requests \
    pillow \
    sympy \
    # Remove build deps to reduce image size
    && apk del gcc g++

### Create non-root user
RUN adduser -D sandboxuser
USER sandboxuser

WORKDIR /app
COPY app.py /app

### Use tmpfs inside the container for temp files --
### so Python writes code to an isolated in-memory /tmp
VOLUME [ "/tmp" ]

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8081"]
