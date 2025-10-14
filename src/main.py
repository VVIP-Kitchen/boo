import os
import discord.opus as opus
from pathlib import Path
from bot.bot import DiscordBot
from ctypes.util import find_library


def _try_load_opus():
  if opus.is_loaded():
    return

  candidates = [
    # macOS (Homebrew)
    "/opt/homebrew/opt/opus/lib/libopus.dylib",
    "/usr/local/opt/opus/lib/libopus.dylib",
    # Generic/Ubuntu/Debian
    "libopus.so",
    "libopus.so.0",
    "/usr/lib/x86_64-linux-gnu/libopus.so",
    "/usr/lib/x86_64-linux-gnu/libopus.so.0",
    "/usr/lib/aarch64-linux-gnu/libopus.so",
    "/usr/lib/aarch64-linux-gnu/libopus.so.0",
    # Alpine (musl)
    "/usr/lib/libopus.so",
    "/usr/lib/libopus.so.0",
  ]

  # Try explicit candidates
  for c in candidates:
    try:
      p = Path(c)
      opus.load_opus(str(p) if p.exists() else c)
      if opus.is_loaded():
        print(f"[voice] Loaded Opus from: {c}")
        return
    except Exception:
      pass  # try next candidate

  # Last resort: let the system find it (works on some distros)
  try:
    name = find_library("opus")
    if name:
      opus.load_opus(name)
      if opus.is_loaded():
        print(f"[voice] Loaded Opus via find_library: {name}")
        return
  except Exception:
    pass

  # Only raise AFTER trying everything
  raise RuntimeError(
    "Opus not found. Install the system library and/or set OPUS path. Examples:\n"
    "  macOS: brew install opus (then use /opt/homebrew/opt/opus/lib/libopus.dylib)\n"
    "  Ubuntu/Debian: apt install libopus0 libopus-dev\n"
    "  Alpine: apk add opus opus-dev"
  )


def main() -> None:
  """
  Main entry point for the Discord bot.
  Initializes and runs the DiscordBot instance.
  """
  bot = DiscordBot()
  bot.run()


if __name__ == "__main__":
  _try_load_opus()
  main()
