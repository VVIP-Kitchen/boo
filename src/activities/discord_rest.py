import json
import base64
from urllib.parse import quote
from typing import Optional

import httpx
from temporalio import activity

from utils.config import DISCORD_TOKEN
from utils.logger import logger
from activities.models import SendResponseInput

DISCORD_API = "https://discord.com/api/v10"
DEFAULT_HEADERS = {
  "Authorization": f"Bot {DISCORD_TOKEN}",
  "User-Agent": "DiscordBot (https://github.com/VVIP-Kitchen/boo, 1.1.0)",
}
MAX_INLINE_LENGTH = 1800


def _strict_status(resp: httpx.Response, context: str) -> None:
  if resp.status_code in (200, 201, 204):
    return
  if resp.status_code in (403, 404, 429):
    logger.warning(f"{context}: {resp.status_code} {resp.text}")
    return
  resp.raise_for_status()


@activity.defn
async def add_reaction(channel_id: str, message_id: str, emoji: str) -> None:
  url = (
    f"{DISCORD_API}/channels/{channel_id}/messages/{message_id}"
    f"/reactions/{quote(emoji)}/@me"
  )
  async with httpx.AsyncClient(timeout=10.0) as client:
    resp = await client.put(url, headers=DEFAULT_HEADERS)
    _strict_status(resp, f"add_reaction({emoji})")


@activity.defn
async def remove_reaction(channel_id: str, message_id: str, emoji: str) -> None:
  url = (
    f"{DISCORD_API}/channels/{channel_id}/messages/{message_id}"
    f"/reactions/{quote(emoji)}/@me"
  )
  async with httpx.AsyncClient(timeout=10.0) as client:
    resp = await client.delete(url, headers=DEFAULT_HEADERS)
    _strict_status(resp, f"remove_reaction({emoji})")


@activity.defn
async def send_message(
  channel_id: str,
  content: str,
  reply_to: Optional[str] = None,
) -> None:
  payload: dict = {"content": content}
  if reply_to:
    payload["message_reference"] = {"message_id": reply_to, "fail_if_not_exists": False}
  url = f"{DISCORD_API}/channels/{channel_id}/messages"
  async with httpx.AsyncClient(timeout=15.0) as client:
    resp = await client.post(url, headers=DEFAULT_HEADERS, json=payload)
    _strict_status(resp, "send_message")


@activity.defn
async def send_response(payload: SendResponseInput) -> None:
  """Send a final bot response: handles long text → file attachment, generated images, sticker_ids."""
  files: list[tuple[str, tuple[str, bytes, str]]] = []

  # Long text becomes an attachment
  text_as_file = len(payload.content) > MAX_INLINE_LENGTH
  if text_as_file:
    files.append(
      ("files[0]", ("output.txt", payload.content.encode("utf-8"), "text/plain"))
    )

  # Generated images as multipart attachments
  for idx, img in enumerate(payload.generated_images):
    raw = base64.b64decode(img.data)
    name = f"generated_image_{idx + 1}.{img.format}"
    files.append((f"files[{len(files)}]", (name, raw, f"image/{img.format}")))

  json_payload: dict = {}
  if not text_as_file:
    json_payload["content"] = payload.content
  if payload.reply_to:
    json_payload["message_reference"] = {
      "message_id": payload.reply_to,
      "fail_if_not_exists": False,
    }
  if payload.sticker_ids:
    json_payload["sticker_ids"] = payload.sticker_ids

  url = f"{DISCORD_API}/channels/{payload.channel_id}/messages"

  async with httpx.AsyncClient(timeout=60.0) as client:
    if files:
      data = {"payload_json": json.dumps(json_payload)}
      resp = await client.post(
        url, headers=DEFAULT_HEADERS, data=data, files=files
      )
    else:
      resp = await client.post(url, headers=DEFAULT_HEADERS, json=json_payload)
    _strict_status(resp, "send_response")


@activity.defn
async def fetch_sticker_ids(sticker_ids: list[str]) -> list[str]:
  """Filter out invalid sticker IDs by hitting Discord's sticker endpoint."""
  if not sticker_ids:
    return []
  valid: list[str] = []
  async with httpx.AsyncClient(timeout=10.0) as client:
    for sid in sticker_ids:
      resp = await client.get(
        f"{DISCORD_API}/stickers/{sid}", headers=DEFAULT_HEADERS
      )
      if resp.status_code == 200:
        valid.append(sid)
      else:
        logger.info(f"Sticker not found: {sid}")
  return valid


@activity.defn
async def download_attachment(url: str) -> bytes:
  """Download a Discord CDN attachment as raw bytes."""
  async with httpx.AsyncClient(timeout=30.0) as client:
    resp = await client.get(url)
    resp.raise_for_status()
    return resp.content


__all__ = [
  "add_reaction",
  "remove_reaction",
  "send_message",
  "send_response",
  "fetch_sticker_ids",
  "download_attachment",
]
