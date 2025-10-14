import os
import discord.opus as opus
from pathlib import Path
from bot.bot import DiscordBot


def _try_load_opus():
  if opus.is_loaded():
    return

  candidates = []
  candidates += [
    "/opt/homebrew/opt/opus/lib/libopus.dylib",  # Apple Silicon
    "/usr/local/opt/opus/lib/libopus.dylib",  # Intel mac
  ]
  # Linux
  candidates += [
    "libopus.so",
    "libopus.so.0",  # runtime-only case
    "/usr/lib/x86_64-linux-gnu/libopus.so",
    "/usr/lib/x86_64-linux-gnu/libopus.so.0",
    "/usr/lib/aarch64-linux-gnu/libopus.so",
    "/usr/lib/aarch64-linux-gnu/libopus.so.0",
    "/usr/lib/libopus.so",  # Alpine
    "/usr/lib/libopus.so.0",
  ]

  for c in candidates:
    p = Path(c)
    try:
      opus.load_opus(str(p) if p.exists() else c)
      if opus.is_loaded():
        print(f"[voice] Loaded Opus from: {c}")
        return
    except Exception:
      pass

    raise RuntimeError(
      "Opus not found. Install the system library and/or set OPUS path. "
      "Examples:\n"
      "  macOS: brew install opus (then use /opt/homebrew/opt/opus/lib/libopus.dylib)\n"
      "  Ubuntu: apt install libopus0 libopus-dev"
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
