from typing import Optional
from utils.logger import logger


def process_image_task(
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
) -> dict:
  """
  Process image in background: generate embeddings and store in Meilisearch.

  This function runs in a separate worker process.
  """
  try:
    logger.info(f"[Worker] Processing image: {image_id}")

    # Import here to avoid circular dependencies
    from services.llm_service import LLMService
    from services.voyageai_service import VoyageAiService
    from services.meilisearch_service import MeilisearchService
    from services.image_processing_service import ImageProcessingService

    # Initialize services
    llm_service = LLMService()
    voyage_service = VoyageAiService()
    meili_service = MeilisearchService()

    image_processor = ImageProcessingService(
      llm_service=llm_service,
      voyage_service=voyage_service,
      meilisearch_service=meili_service,
    )

    # Process and store image
    image_id, vlm_caption, storage_result = image_processor.process_and_store_image(
      image=image_bytes,
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
      metadata={
        "attachment_filename": attachment_filename,
        "attachment_size": attachment_size,
      },
    )

    logger.info(f"[Worker] Successfully processed image: {image_id}")

    return {
      "status": "success",
      "image_id": image_id,
      "vlm_caption": vlm_caption,
    }

  except Exception as e:
    logger.error(f"[Worker] Error processing image {image_id}: {e}")
    return {
      "status": "error",
      "image_id": image_id,
      "error": str(e),
    }
