import httpx
from temporalio import activity

from services.llm_service import LLMService
from services.voyageai_service import VoyageAiService
from services.meilisearch_service import MeilisearchService
from services.image_processing_service import ImageProcessingService
from activities.models import ImageIndexInput


@activity.defn
def process_and_index(payload: ImageIndexInput) -> dict:
  with httpx.Client(timeout=30.0) as client:
    resp = client.get(payload.image_url)
    resp.raise_for_status()
    image_bytes = resp.content

  processor = ImageProcessingService(
    llm_service=LLMService(),
    voyage_service=VoyageAiService(),
    meilisearch_service=MeilisearchService(),
  )
  image_id, vlm_caption, _ = processor.process_and_store_image(
    image=image_bytes,
    user_caption=payload.user_caption,
    image_id=payload.image_id,
    message_url=payload.message_url,
    message_id=payload.message_id,
    server_id=payload.server_id,
    server_name=payload.server_name,
    channel_id=payload.channel_id,
    channel_name=payload.channel_name,
    author_id=payload.author_id,
    author_name=payload.author_name,
    attachment_url=payload.image_url,
    metadata={
      "attachment_filename": payload.attachment_filename,
      "attachment_size": payload.attachment_size,
    },
  )
  return {"image_id": image_id, "vlm_caption": vlm_caption}
