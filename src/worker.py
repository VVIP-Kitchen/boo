import redis
from rq import Worker, Queue, Connection
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

    # Create worker
    with Connection(redis_conn):
      worker = Worker(["image_processing"])
      logger.info("Starting RQ worker for 'image_processing' queue...")
      worker.work()

  except Exception as e:
    logger.error(f"Worker failed to start: {e}")
    raise


if __name__ == "__main__":
  main()
