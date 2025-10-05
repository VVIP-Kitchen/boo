import hmac
import time
import httpx
import base64

from hashlib import sha256
from typing import Optional


class RemoteASR:
  def __init__(
    self, base_url: str, *, hmac_secret: Optional[str] = None, timeout_s: float = 5.0
  ):
    self.base_url = "https://kashifulhaque--boo-whisper-api-fastapi-app.modal.run"
    self.hmac_secret = hmac_secret.encode() if hmac_secret else None
    self.client = httpx.AsyncClient(timeout=timeout_s)

  async def close(self):
    await self.client.aclose()

  async def preload(self):
    r = await self.client.get(f"{self.base_url}/preload")
    r.raise_for_status()
    return r.json()

  def _headers(self, body_bytes: bytes):
    if not self.hmac_secret:
      return {}

    ts = str(int(time.time()))
    mac = hmac.new(
      self.hmac_secret, ts.encode() + b"." + body_bytes, sha256
    ).hexdigest()
    return {"X-Ts": ts, "X-Sign": mac}

  async def transcribe_pcm16(
    self, pcm16_mono_16k: bytes, *, language: Optional[str] = None
  ):
    # payload mirrors the FastAPI schema
    payload = {
      "pcm16_base64": base64.b64encode(pcm16_mono_16k).decode(),
      "sample_rate": 16000,
      "language": language,
      "temperature": 0.0,
      "beam_size": 1,
    }
    body = httpx.Request("POST", "http://x", json=payload).read()  # serialize once
    r = await self.client.post(
      f"{self.base_url}/transcribe",
      headers={"Content-Type": "application/json", **self._headers(body)},
      content=body,
    )
    r.raise_for_status()
    return r.json()
