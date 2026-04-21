from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
  from activities import image, meili
  from activities.models import ImageIndexInput


_index_retry = RetryPolicy(
  initial_interval=timedelta(seconds=2),
  backoff_coefficient=2.0,
  maximum_interval=timedelta(minutes=1),
  maximum_attempts=4,
)


@workflow.defn
class ImageIndexWorkflow:
  """Background indexing for one Discord image attachment."""

  @workflow.run
  async def run(self, payload: ImageIndexInput) -> dict:
    return await workflow.execute_activity(
      image.process_and_index,
      payload,
      start_to_close_timeout=timedelta(minutes=5),
      retry_policy=_index_retry,
    )


@workflow.defn
class DeleteImageWorkflow:
  """Remove a stored image from Meilisearch when the source Discord message is deleted."""

  @workflow.run
  async def run(self, image_id: str) -> None:
    await workflow.execute_activity(
      meili.delete_document,
      image_id,
      start_to_close_timeout=timedelta(seconds=15),
      retry_policy=RetryPolicy(maximum_attempts=3),
    )
