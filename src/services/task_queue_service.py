"""
Background task queue service using Redis and RQ
"""

import redis
from rq import Queue
from typing import Optional
from utils.config import REDIS_HOST, REDIS_PORT
from utils.logger import logger


class TaskQueueService:
  """Service for managing background tasks with Redis Queue."""

  def __init__(self):
    """Initialize Redis connection and RQ queue."""
    try:
      # Connect to Redis
      self.redis_conn = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        password=None,
        decode_responses=False,  # We'll handle binary data
        socket_connect_timeout=5,
        socket_timeout=5,
      )

      # Test connection
      self.redis_conn.ping()
      logger.info("Connected to Redis successfully")

      # Create queue
      self.queue = Queue("image_processing", connection=self.redis_conn)
      logger.info("Task queue initialized")

    except Exception as e:
      logger.error(f"Failed to connect to Redis: {e}")
      self.redis_conn = None
      self.queue = None

  def enqueue_image_processing(
    self,
    image_bytes: bytes,
    user_caption: Optional[str],
    image_id: str,
    message_url: str,
    message_id: str,
    server_id: str,
    server_name: str,
    channel_id: str,
    channel_name: str,
    author_id: str,
    author_name: str,
    attachment_url: str,
    attachment_filename: str,
    attachment_size: int,
  ) -> Optional[str]:
    """
    Enqueue an image processing task.

    Returns:
        Job ID if successful, None otherwise
    """
    if not self.queue:
      logger.error("Queue not initialized, cannot enqueue task")
      return None

    try:
      from tasks.image_tasks import process_image_task

      job = self.queue.enqueue(
        process_image_task,
        image_bytes=image_bytes,
        user_caption=user_caption,
        image_id=image_id,
        message_url=message_url,
        message_id=message_id,
        server_id=server_id,
        server_name=server_name,
        channel_id=channel_id,
        channel_name=channel_name,
        author_id=author_id,
        author_name=author_name,
        attachment_url=attachment_url,
        attachment_filename=attachment_filename,
        attachment_size=attachment_size,
        job_timeout="5m",  # 5 minute timeout
        result_ttl=3600,  # Keep result for 1 hour
        failure_ttl=86400,  # Keep failed jobs for 24 hours
      )

      logger.info(f"Enqueued image processing job: {job.id}")
      return job.id

    except Exception as e:
      logger.error(f"Failed to enqueue image processing task: {e}")
      return None

  def get_queue_info(self) -> dict:
    """Get information about the queue."""
    if not self.queue:
      return {"error": "Queue not initialized"}

    try:
      return {
        "name": self.queue.name,
        "count": len(self.queue),
        "failed_count": len(self.queue.failed_job_registry),
        "finished_count": len(self.queue.finished_job_registry),
        "started_count": len(self.queue.started_job_registry),
      }
    except Exception as e:
      logger.error(f"Failed to get queue info: {e}")
      return {"error": str(e)}
