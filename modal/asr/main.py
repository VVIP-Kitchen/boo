from __future__ import annotations
import base64
import hmac
import os
import time
from hashlib import sha256
from typing import Optional, List, Dict, Any

import numpy as np
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel, Field

# Faster-Whisper (CTranslate2 backend) – efficient on GPU/CPU
from faster_whisper import WhisperModel

# ---------- App & config ----------
web = FastAPI(title="Boo Whisper API", version="0.1.0")

WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")
HMAC_SECRET = os.getenv("HMAC_SECRET")  # optional
MAX_SECONDS = int(os.getenv("MAX_SECONDS", "15"))  # max audio seconds per request

_model: Optional[WhisperModel] = None
_device: Optional[str] = None
_compute_type: Optional[str] = None


def _pick_device_and_compute() -> tuple[str, str]:
  # Try CUDA via environment hint; fall back to CPU.
  # faster-whisper picks device via string; we don’t import torch.
  prefer = os.getenv("DEVICE", "auto").lower()
  if prefer in {"cuda", "gpu"}:
    return "cuda", os.getenv("COMPUTE_TYPE", "float16")
  # Auto: try CUDA; otherwise CPU. We can be conservative and let runtime decide.
  # ctranslate2 treats "auto" device as cpu if cuda isn’t present; compute_type remains valid.
  device = "auto"
  compute_type = os.getenv("COMPUTE_TYPE", "int8_float16")
  return device, compute_type


def get_model() -> WhisperModel:
  global _model, _device, _compute_type
  if _model is None:
    _device, _compute_type = _pick_device_and_compute()
    t0 = time.time()
    _model = WhisperModel(
      WHISPER_MODEL,
      device=_device,
      compute_type=_compute_type,
      download_root=os.getenv("WHISPER_CACHE", "/root/.cache/whisper"),
    )
    # Force a tiny graph warmup with a silent frame (optional, cheap)
    try:
      _ = list(_model.transcribe(np.zeros(1600, dtype=np.float32), language=os.getenv("LANGUAGE"), beam_size=1))[0:0]
    except Exception:
      pass
    print(f"[whisper] loaded '{WHISPER_MODEL}' on { _device } ({ _compute_type }) in {time.time()-t0:.2f}s")
  return _model


# ---------- Security (optional HMAC) ----------

def _check_hmac(x_sign: Optional[str], x_ts: Optional[str], body_bytes: bytes) -> None:
  if not HMAC_SECRET:
    return
  if not x_sign or not x_ts:
    raise HTTPException(status_code=401, detail="missing auth headers")
  msg = x_ts.encode() + b"." + body_bytes
  mac = hmac.new(HMAC_SECRET.encode(), msg, sha256).hexdigest()
  if not hmac.compare_digest(mac, x_sign):
    raise HTTPException(status_code=401, detail="bad signature")


# ---------- Schemas ----------
class TranscribeIn(BaseModel):
  pcm16_base64: str = Field(..., description="Base64 of int16 mono 16 kHz PCM")
  sample_rate: int = Field(16000, description="Sampling rate of the PCM")
  language: Optional[str] = Field(default=None, description="ISO 639-1/2 code; None = auto")
  temperature: float = Field(0.0, ge=0.0, le=1.0)
  beam_size: int = Field(1, ge=1, le=5, description="1 for low-latency live captions")
  logprob_threshold: Optional[float] = Field(default=None)
  no_speech_threshold: Optional[float] = Field(default=None)


class Segment(BaseModel):
  start: float
  end: float
  text: str


class TranscribeOut(BaseModel):
  text: str
  segments: List[Segment]
  language: Optional[str]
  duration_s: float
  asr_ms: int
  model: Dict[str, Any]


# ---------- Routes ----------
@web.get("/health")
@web.get("/preload")
def health():
  get_model()
  return {"status": "ok", "model": WHISPER_MODEL, "device": _device, "compute_type": _compute_type}


@web.post("/transcribe", response_model=TranscribeOut)
async def transcribe(
  body: TranscribeIn,
  x_sign: Optional[str] = Header(default=None),
  x_ts: Optional[str] = Header(default=None),
):
  body_bytes = body.model_dump_json().encode()
  _check_hmac(x_sign, x_ts, body_bytes)

  if body.sample_rate != 16000:
    # Keep server simple; have client send proper 16k mono
    raise HTTPException(status_code=400, detail="sample_rate must be 16000")

  # Decode PCM16 → float32 [-1, 1]
  try:
    pcm_bytes = base64.b64decode(body.pcm16_base64)
    pcm_i16 = np.frombuffer(pcm_bytes, dtype=np.int16)
    if pcm_i16.ndim != 1:
      raise ValueError("expected mono int16")
    audio = (pcm_i16.astype(np.float32) / 32768.0).copy()
  except Exception as e:
    raise HTTPException(status_code=400, detail=f"bad pcm: {e}")

  duration_s = len(audio) / 16000.0
  if duration_s <= 0 or duration_s > MAX_SECONDS:
    raise HTTPException(status_code=400, detail=f"chunk duration must be 0 < t <= {MAX_SECONDS}s")

  model = get_model()
  t0 = time.time()

  # Run inference
  try:
    segments_iter, info = model.transcribe(
      audio,
      language=body.language,
      temperature=body.temperature,
      beam_size=body.beam_size,
      log_prob_threshold=body.logprob_threshold,
      no_speech_threshold=body.no_speech_threshold,
      condition_on_previous_text=False,  # more stable for chunked live
    )
    segments_list = []
    texts = []
    for seg in segments_iter:
      segments_list.append(Segment(start=float(seg.start), end=float(seg.end), text=seg.text))
      texts.append(seg.text)
    text = "".join(texts).strip()
  except Exception as e:
    raise HTTPException(status_code=500, detail=f"transcription failed: {e}")

  asr_ms = int((time.time() - t0) * 1000)

  return TranscribeOut(
    text=text,
    segments=segments_list,
    language=getattr(info, "language", None),
    duration_s=duration_s,
    asr_ms=asr_ms,
    model={"name": WHISPER_MODEL, "device": _device, "compute_type": _compute_type},
  )


# ---------- Modal glue ----------
# Create the Modal app and image here to keep this file standalone.
import modal  # noqa: E402

app = modal.App("boo-whisper-api")

image = (
  modal.Image.from_registry(
    "nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04", add_python="3.11"
  )
  .apt_install("ffmpeg")                     # optional, but handy
  .pip_install(
    "fastapi[standard]",
    "numpy",
    "faster-whisper==1.0.3",
    "ctranslate2==4.5.0",  # optional explicit pin
  )
)

@app.function(
  image=image,
  gpu=os.getenv("MODAL_GPU", "T4"),  # e.g., "any", "t4", "a10g"
  timeout=int(os.getenv("MODAL_TIMEOUT", "180")),
  memory=int(os.getenv("MODAL_MEMORY", "2048")),
  max_containers=int(os.getenv("MODAL_CONCURRENCY", "2")),
)
@modal.asgi_app()
def fastapi_app():
  # Lazy-load model on cold start so /health is fast, but trigger a light prewarm here too.
  try:
    get_model()
  except Exception as e:
    # Don’t crash cold start if model cache is warming; /health will retry.
    print("[warn] model preload failed:", e)
  return web
