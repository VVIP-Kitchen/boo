FROM python:3.12-slim

### Install build deps only for packages we need, then cleanup
RUN apt-get update
RUN apt-get install -y --no-install-recommends gcc g++ make libffi-dev \
    && pip install --no-cache-dir fastapi uvicorn numpy pandas matplotlib seaborn scipy sympy scikit-learn pillow \
    && apt-get purge -y gcc g++ make libffi-dev \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

### Create non-root user
RUN useradd -m sandboxuser
USER sandboxuser

WORKDIR /app
COPY app.py /app

### Use tmpfs inside the container for temp files --
### so Python writes code to an isolated in-memory /tmp
VOLUME [ "/tmp" ]

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8081"]