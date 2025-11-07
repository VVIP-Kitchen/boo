from typing import Dict, Optional, Tuple
from threading import RLock
from datetime import datetime, timedelta
from utils.logger import logger


class ServerCache:
  """
  Thread-safe singleton for caching server-level data with TTL.

  Cache entries expire after a configurable TTL to prevent stale data.
  """

  _instance: Optional["ServerCache"] = None
  _lock = RLock()

  def __new__(cls, *args, **kwargs) -> "ServerCache":
    if cls._instance is None:
      with cls._lock:
        if cls._instance is None:
          cls._instance = super().__new__(cls)
          cls._instance._initialized = False
    return cls._instance

  def __init__(self, ttl_minutes: int = 30) -> None:
    if self._initialized:
      return

    # Store tuples of (value, expiry_time)
    self._lore_cache: Dict[str, Tuple[str, datetime]] = {}
    self._ttl = timedelta(minutes=ttl_minutes)
    self._initialized = True
    logger.debug(f"ServerCache initialized with TTL: {ttl_minutes} minutes")

  def get_lore(self, server_id: str) -> Optional[str]:
    """Get cached server lore if not expired."""
    with self._lock:
      if server_id not in self._lore_cache:
        return None

      lore, expiry = self._lore_cache[server_id]

      # Check if expired
      if datetime.now() > expiry:
        logger.debug(f"Cache expired for server: {server_id}")
        del self._lore_cache[server_id]
        return None

      return lore

  def set_lore(self, server_id: str, lore: str) -> None:
    """Cache server lore with expiry time."""
    with self._lock:
      expiry = datetime.now() + self._ttl
      self._lore_cache[server_id] = (lore, expiry)
      logger.debug(f"Cached lore for server: {server_id}, expires at: {expiry}")

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

  def cleanup_expired(self) -> int:
    """Remove all expired entries. Returns number of entries removed."""
    with self._lock:
      now = datetime.now()
      expired_keys = [
        server_id for server_id, (_, expiry) in self._lore_cache.items() if now > expiry
      ]

      for key in expired_keys:
        del self._lore_cache[key]

      if expired_keys:
        logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")

      return len(expired_keys)

  def get_cache_stats(self) -> Dict[str, int]:
    """Get statistics about cache usage."""
    with self._lock:
      now = datetime.now()
      active_entries = sum(
        1 for _, expiry in self._lore_cache.values() if now <= expiry
      )
      return {
        "total_entries": len(self._lore_cache),
        "active_entries": active_entries,
        "expired_entries": len(self._lore_cache) - active_entries,
      }


# Export singleton instance with 5 minute TTL
server_cache = ServerCache(ttl_minutes=5)
