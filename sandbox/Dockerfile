FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ gfortran make pkg-config \
    libopenblas-dev liblapack-dev \
    libjpeg-dev zlib1g-dev libpng-dev \
    libfreetype6-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    fastapi uvicorn requests \
    numpy pandas matplotlib seaborn scipy sympy scikit-learn pillow

### Create non-root user
RUN useradd -m sandboxuser
USER sandboxuser

WORKDIR /app
COPY app.py /app

### Use tmpfs inside the container for temp files --
### so Python writes code to an isolated in-memory /tmp
VOLUME [ "/tmp" ]

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8081"]