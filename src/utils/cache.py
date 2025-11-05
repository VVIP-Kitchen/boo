from typing import Dict, Optional
from threading import RLock
from utils.logger import logger


class ServerCache:
  """
  Thread-safe singleton for caching server-level data.

  This cache stores frequently accessed data like server lore (system prompts)
  to avoid repeated database calls. The source of truth remains the database.
  """

  _instance: Optional["ServerCache"] = None
  _lock = RLock()

  def __new__(cls) -> "ServerCache":
    if cls._instance is None:
      with cls._lock:
        if cls._instance is None:
          cls._instance = super().__new__(cls)
          cls._instance._initialized = False
    return cls._instance

  def __init__(self) -> None:
    if self._initialized:
      return

    self._lore_cache: Dict[str, str] = {}
    self._initialized = True
    logger.debug("ServerCache initialized")

  def get_lore(self, server_id: str) -> Optional[str]:
    """Get cached server lore (system prompt)."""
    with self._lock:
      return self._lore_cache.get(server_id)

  def set_lore(self, server_id: str, lore: str) -> None:
    """Cache server lore (system prompt)."""
    with self._lock:
      self._lore_cache[server_id] = lore
      logger.debug(f"Cached lore for server: {server_id}")

  def invalidate_lore(self, server_id: str) -> None:
    """Remove server lore from cache."""
    with self._lock:
      if server_id in self._lore_cache:
        del self._lore_cache[server_id]
        logger.debug(f"Invalidated lore cache for server: {server_id}")

  def clear_all(self) -> None:
    """Clear all cached data."""
    with self._lock:
      self._lore_cache.clear()
      logger.info("Cleared all server cache")

  def get_cache_stats(self) -> Dict[str, int]:
    """Get statistics about cache usage."""
    with self._lock:
      return {
        "lore_entries": len(self._lore_cache),
      }


# Export singleton instance
server_cache = ServerCache()
