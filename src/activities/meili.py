from temporalio import activity

from services.meilisearch_service import MeilisearchService


@activity.defn
def delete_document(image_id: str) -> None:
  MeilisearchService().delete_document(image_id)
