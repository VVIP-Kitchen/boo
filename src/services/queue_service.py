import json
import asyncio
from typing import Dict, Any
import redis.asyncio as redis
from utils.logger import logger

REDIS_HOST = "redis"
REDIS_PORT = 6379

class QueueService:
  def __init__(self):
    self.redis_client = None
    self.queue_name = "cf_requests"
    self.processing_lock = "processing_lock"
    self.rate_limit_key = "cf_rate_limit"
    self.max_concurrent = 3
    self.rate_limit_window = 60   # 60s window
    self.max_requests_per_window = 100
  
  async def connect(self):
    if not self.redis_client:
      self.redis_client = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5
      )
      try:
        await self.redis_client.ping()
        logger.info("Connected to redis queue")
      except Exception as e:
        logger.error(f"Failed to conect to redis: {e}")
        raise
  
  async def add_to_queue(self, req_data: Dict[str, Any]) -> str:
    await self.connect()
    req_id = f"req_{int(asyncio.get_event_loop().time() * 1_000_000)}"
    req_payload = {
      "id": req_id,
      "data": req_data,
      "timestamp": asyncio.get_event_loop().time()
    }

    await self.redis_client.lpush(self.queue_name, json.dumps(req_payload))
    logger.info(f"Added req: {req_id} to queue")
    return req_id
  
  async def process_queue(self):
    await self.connect()
    while True:
      try:
        ### Check if we can process more requests
        if not await self._can_process_req():
          await asyncio.sleep(1)
          continue

        ### Get request from queue
        req_json = await self.redis_client.brpop(self.queue_name, timeout=1)
        if not req_json:
          continue

        req_data = json.loads(req_json[1])
        await self._process_req(req_data)
      except Exception as e:
        logger.error(f"Error processing queue: {e}")
        await asyncio.sleep(5)
  
  async def _can_process_req(self) -> bool:
    ### Check concurrent requests
    current_processing = await self.redis_client.scard(self.processing_lock)
    if current_processing >= self.max_concurrent:
      return False

    ### Check rate limit window
    current_count = await self.redis_client.get(self.rate_limit_key)
    if current_count and int(current_count) >= self.max_requests_per_window:
      return False
    
    return True

  async def _process_req(self, req_data: Dict[str, Any]):
    req_id = req_data["id"]
    try:
      ### Mark as processing
      await self.redis_client.sadd(self.processing_lock, req_id)

      ### Increment rate limit counter
      await self.redis_client.incr(self.rate_limit_key)
      await self.redis_client.expire(self.rate_limit_key, self.rate_limit_window)

      ### Process the req
      from services.workers_service import WorkersService
      workers_service = WorkersService()

      req_type = req_data["data"]["type"]
      result = None

      if req_type == "chat_completion":
        result = workers_service._direct_chat_completions(**req_data["data"]["params"])
      elif req_type == "image_generation":
        result = workers_service._direct_generate_image(**req_data["data"]["params"])
      
      ### Store result
      await self.redis_client.setex(
        f"result_{req_id}",
        300,  # TTL 5m
        json.dumps({
          "status": "success",
          "result": result
        })
      )
    except Exception as e:
      logger.error(f"Error processing request {req_id}: {e}")
      await self.redis_client.setex(
        f"result_{req_id}",
        300,
        json.dumps({
          "status": "error",
          "error": str(e)
        })
      )
    finally:
      await self.redis_client.srem(self.processing_lock, req_id)
  
  async def get_result(self, req_id: str, timeout: int = 30) -> Dict[str, Any]:
    await self.connect()
    start_time = asyncio.get_event_loop().time()
    
    while (asyncio.get_event_loop().time() - start_time) < timeout:
      result = await self.redis_client.get(f"result_{req_id}")
      if result:
        return json.loads(result)
      await asyncio.sleep(0.5)
    
    return {
      "status": "timeout",
      "error": "Request timed out"
    }
  
  async def get_queue_status(self) -> Dict[str, int]:
    await self.connect()
    queue_length = await self.redis_client.llen(self.queue_name)
    processing_count = await self.redis_client.scard(self.processing_lock)
    rate_limit_count = await self.redis_client.get(self.rate_limit_key) or 0

    return {
      "queue_length": queue_length,
      "processing_count": processing_count,
      "rate_limit_count": int(rate_limit_count)
    }

queue_service = QueueService()
