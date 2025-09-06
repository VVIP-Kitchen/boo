FROM nvidia/cuda:12.2.2-cudnn8-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 python3.10-venv python3-pip ca-certificates curl git \
  && rm -rf /var/lib/apt/lists/*

RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 1 \
 && python3 -m pip install --upgrade pip setuptools wheel

COPY rp_handler.py /app/

# Install CUDA-enabled PyTorch + other deps and your package
# NOTE: pin versions if you want reproducible builds. Adjust torch version / cuNN tag to match host.
RUN python3 -m pip install --no-cache-dir \
      torch -f https://download.pytorch.org/whl/cu122/torch_stable.html \
      transformers pillow runpod

# Expose nothing special; runtime will be started by runpod
CMD ["python3", "-u", "rp_handler.py"]

