#!/usr/bin/env python3
"""
RQ Worker for processing background tasks
"""

import redis
from rq import Worker, Queue
from utils.logger import logger
from utils.config import REDIS_HOST, REDIS_PORT, REDIS_TOKEN


def main():
  """Start the RQ worker."""
  try:
    # Connect to Redis
    redis_conn = redis.Redis(
      host=REDIS_HOST,
      port=REDIS_PORT,
      password=REDIS_TOKEN if REDIS_TOKEN else None,
      decode_responses=False,
    )

    # Test connection
    redis_conn.ping()
    logger.info("Worker connected to Redis")

    # Create queues to listen to
    queues = [Queue("image_processing", connection=redis_conn)]

    # Create and start worker
    worker = Worker(queues, connection=redis_conn)
    logger.info("Starting RQ worker for 'image_processing' queue...")
    worker.work()

  except Exception as e:
    logger.error(f"Worker failed to start: {e}")
    raise


if __name__ == "__main__":
  main()
