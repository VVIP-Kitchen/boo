import asyncio

async def to_thread(func, *args, **kwargs):
  loop = asyncio.get_running_loop()
  return await loop.run_in_executor(None, lambda: func(*args, **kwargs))
