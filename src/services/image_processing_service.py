"""
Service to handle image captioning, embedding generation, and storage
"""

import io
import uuid
from typing import Optional, Union, Tuple
from utils.logger import logger


class ImageProcessingService:
  def __init__(self, llm_service, voyage_service, meilisearch_service):
    """
    Initialize the image processing service.

    Args:
        llm_service: Instance of LLMService for image captioning
        voyage_service: Instance of VoyageAiService for embeddings
        meilisearch_service: Instance of MeilisearchService for storage
    """
    self.llm = llm_service
    self.voyage = voyage_service
    self.meili = meilisearch_service

  def process_and_store_image(
    self,
    image: Union[io.BytesIO, bytes],
    user_caption: Optional[str] = None,
    image_id: Optional[str] = None,
    # Discord metadata
    message_url: Optional[str] = None,
    message_id: Optional[str] = None,
    server_id: Optional[str] = None,
    server_name: Optional[str] = None,
    channel_id: Optional[str] = None,
    channel_name: Optional[str] = None,
    author_id: Optional[str] = None,
    author_name: Optional[str] = None,
    attachment_url: Optional[str] = None,
    metadata: Optional[dict] = None,
  ) -> Tuple[str, str, dict]:
    """
    Process an image: generate caption, create embeddings, and store in Meilisearch.

    Args:
        image: Image as BytesIO or bytes
        user_caption: Optional user-provided caption
        image_id: Optional custom image ID (auto-generated if not provided)
        message_url: Discord message jump URL
        message_id: Discord message ID
        server_id: Discord server/guild ID
        server_name: Discord server name
        channel_id: Discord channel ID
        channel_name: Discord channel name
        author_id: Discord user ID
        author_name: Discord username
        attachment_url: Original Discord attachment URL
        metadata: Optional additional metadata

    Returns:
        Tuple of (image_id, vlm_caption, storage_result)
    """
    try:
      # Generate unique image ID if not provided
      if not image_id:
        image_id = str(uuid.uuid4())

      logger.info(f"Processing image: {image_id}")

      # Step 1: Get VLM caption from LLM
      logger.info("Step 1: Generating VLM caption...")
      vlm_caption = self._generate_caption(image, user_caption)
      logger.info(f"VLM Caption: {vlm_caption}")

      # Step 2: Prepare inputs for batch embedding generation
      logger.info("Step 2: Generating embeddings in batch...")
      image_bytes = image.getvalue() if isinstance(image, io.BytesIO) else image

      # Build input list based on what we have
      embedding_inputs = [image_bytes, vlm_caption]
      has_user_caption = bool(user_caption and user_caption.strip())

      if has_user_caption:
        embedding_inputs.append(user_caption)

      # Generate all embeddings in one API call
      embeddings = self.voyage.generate_batch_embeddings(embedding_inputs)

      image_embedding = embeddings[0]
      vlm_caption_embedding = embeddings[1]
      user_caption_embedding = embeddings[2] if has_user_caption else None

      logger.info(f"Generated {len(embeddings)} embeddings")

      # Step 3: Store in Meilisearch with Discord metadata
      logger.info("Step 3: Storing in Meilisearch...")
      storage_result = self.meili.add_document(
        image_id=image_id,
        image_embedding=image_embedding,
        vlm_caption=vlm_caption,
        vlm_caption_embedding=vlm_caption_embedding,
        user_caption=user_caption if has_user_caption else None,
        user_caption_embedding=user_caption_embedding,
        # Discord metadata
        message_url=message_url,
        message_id=message_id,
        server_id=server_id,
        server_name=server_name,
        channel_id=channel_id,
        channel_name=channel_name,
        author_id=author_id,
        author_name=author_name,
        attachment_url=attachment_url,
        metadata=metadata,
      )

      logger.info(f"Successfully stored image {image_id} with Discord context")

      return image_id, vlm_caption, storage_result

    except Exception as e:
      logger.error(f"Error processing image: {e}")
      raise

  def _generate_caption(
    self, image: Union[io.BytesIO, bytes], user_caption: Optional[str]
  ) -> str:
    """Generate caption for image using LLM."""
    if user_caption and user_caption.strip():
      prompt = (
        f"The user has provided this caption: '{user_caption}'. "
        "Please generate a detailed description of this image that complements "
        "the user's caption. Focus on visual details, objects, colors, and context."
      )
    else:
      prompt = (
        "Please provide a detailed description of this image. "
        "Include objects, people, colors, setting, and any notable details."
      )

    # Generate caption (disable tools for image description)
    caption, _, _ = self.llm.chat_completions(
      prompt=prompt,
      image=image,
      temperature=0.7,
      max_tokens=300,
      enable_tools=False,
    )

    return caption.strip()
