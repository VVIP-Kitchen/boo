"""Temporal worker process for boo: hosts every workflow + activity on a single task queue."""

import asyncio
from concurrent.futures import ThreadPoolExecutor

from temporalio.client import Client
from temporalio.worker import Worker

from utils.config import TEMPORAL_ADDRESS, TEMPORAL_TASK_QUEUE, TEMPORAL_NAMESPACE
from utils.logger import logger

from activities import discord_rest, llm, manager, meili, image
from workflows.chat_workflow import BooChatWorkflow
from workflows.image_workflows import ImageIndexWorkflow, DeleteImageWorkflow


ACTIVITIES = [
  discord_rest.add_reaction,
  discord_rest.remove_reaction,
  discord_rest.send_message,
  discord_rest.send_response,
  discord_rest.fetch_sticker_ids,
  discord_rest.download_attachment,
  llm.run_agentic_chat,
  manager.fetch_prompt,
  manager.get_chat_history,
  manager.update_chat_history,
  manager.delete_chat_history,
  manager.get_memories,
  manager.store_token_usage,
  meili.delete_document,
  image.process_and_index,
]

WORKFLOWS = [BooChatWorkflow, ImageIndexWorkflow, DeleteImageWorkflow]


async def main() -> None:
  logger.info(
    f"Connecting worker to Temporal at {TEMPORAL_ADDRESS} "
    f"(namespace={TEMPORAL_NAMESPACE}, queue={TEMPORAL_TASK_QUEUE})"
  )
  client = await Client.connect(TEMPORAL_ADDRESS, namespace=TEMPORAL_NAMESPACE)

  with ThreadPoolExecutor(max_workers=32) as executor:
    worker = Worker(
      client,
      task_queue=TEMPORAL_TASK_QUEUE,
      workflows=WORKFLOWS,
      activities=ACTIVITIES,
      activity_executor=executor,
    )
    logger.info(
      f"Worker started: {len(WORKFLOWS)} workflows, {len(ACTIVITIES)} activities"
    )
    await worker.run()


if __name__ == "__main__":
  asyncio.run(main())
