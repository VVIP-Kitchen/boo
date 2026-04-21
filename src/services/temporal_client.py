from typing import Optional

from temporalio.client import Client

from utils.config import TEMPORAL_ADDRESS, TEMPORAL_NAMESPACE
from utils.logger import logger

_client: Optional[Client] = None


async def get_client() -> Client:
  """Lazy-singleton Temporal client. Reused across the bot process."""
  global _client
  if _client is None:
    logger.info(f"Connecting to Temporal at {TEMPORAL_ADDRESS} (namespace={TEMPORAL_NAMESPACE})")
    _client = await Client.connect(TEMPORAL_ADDRESS, namespace=TEMPORAL_NAMESPACE)
    logger.info("Temporal client connected")
  return _client
