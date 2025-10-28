import os
import voyageai
from PIL import Image
from io import BytesIO
from typing import List, Union
from utils.config import VOYAGEAI_API_KEY
from utils.logger import logger
from utils.image_utils import compress_image, validate_image_for_voyage, get_image_info
from utils.singleton import Singleton


class VoyageAiService(metaclass=Singleton):
  def __init__(self, model="voyage-multimodal-3"):
    self.vo = voyageai.Client(VOYAGEAI_API_KEY)
    self.model = model

  def generate_text_embeddings(self, text: str):
    """Generate embeddings for a single text."""
    result = self.vo.multimodal_embed([[text]], model=self.model)
    return result.embeddings[0]

  def generate_image_embeddings(self, img_bytes: Union[bytes, BytesIO]) -> List[float]:
    """
    Generate embeddings for a single image.
    Automatically compresses image if needed to meet Voyage AI requirements.
    """
    # Convert BytesIO to bytes if needed
    if isinstance(img_bytes, BytesIO):
      img_bytes = img_bytes.getvalue()

    # Log original image info
    img_info = get_image_info(img_bytes)
    logger.info(
      f"Original image: {img_info.get('width')}x{img_info.get('height')} "
      f"({img_info.get('pixels', 0):,} pixels, {img_info.get('size_mb', 0):.2f}MB)"
    )

    # Check if compression is needed
    is_valid, error_msg = validate_image_for_voyage(img_bytes)

    if not is_valid:
      logger.warning(f"Image validation failed: {error_msg}. Compressing...")
      img_bytes = compress_image(img_bytes)

      # Validate after compression
      is_valid, error_msg = validate_image_for_voyage(img_bytes)
      if not is_valid:
        raise ValueError(f"Image still invalid after compression: {error_msg}")

      logger.info("Image compressed successfully and validated")
    else:
      logger.info("Image meets requirements, no compression needed")

    # Generate embeddings
    img = Image.open(BytesIO(img_bytes))
    result = self.vo.multimodal_embed([[img]], model=self.model)
    return result.embeddings[0]

  def generate_batch_embeddings(
    self, inputs: List[Union[str, bytes, Image.Image, BytesIO]]
  ) -> List[List[float]]:
    """
    Generate embeddings for multiple inputs (text and/or images) in one API call.
    Automatically compresses images if needed.

    Args:
        inputs: List of strings (text) or bytes/PIL Images (images)

    Returns:
        List of embeddings, one per input
    """
    prepared_inputs = []

    for idx, item in enumerate(inputs):
      if isinstance(item, str):
        # Text input
        prepared_inputs.append([item])
      elif isinstance(item, (bytes, BytesIO)):
        # Image bytes - compress if needed
        img_bytes = item.getvalue() if isinstance(item, BytesIO) else item

        # Log and validate
        img_info = get_image_info(img_bytes)
        logger.info(
          f"Input {idx}: Image {img_info.get('width')}x{img_info.get('height')} "
          f"({img_info.get('pixels', 0):,} pixels, {img_info.get('size_mb', 0):.2f}MB)"
        )

        is_valid, error_msg = validate_image_for_voyage(img_bytes)

        if not is_valid:
          logger.warning(f"Input {idx}: Compression needed - {error_msg}")
          img_bytes = compress_image(img_bytes)

          # Validate after compression
          is_valid, error_msg = validate_image_for_voyage(img_bytes)
          if not is_valid:
            raise ValueError(
              f"Input {idx}: Still invalid after compression: {error_msg}"
            )

          logger.info(f"Input {idx}: Compressed successfully")
        else:
          logger.info(f"Input {idx}: No compression needed")

        img = Image.open(BytesIO(img_bytes))
        prepared_inputs.append([img])
      elif isinstance(item, Image.Image):
        # Already a PIL Image - check if we need to compress
        output = BytesIO()
        item.save(output, format="JPEG", quality=85)
        img_bytes = output.getvalue()

        is_valid, error_msg = validate_image_for_voyage(img_bytes)

        if not is_valid:
          logger.warning(f"Input {idx}: PIL Image needs compression - {error_msg}")
          img_bytes = compress_image(img_bytes)
          img = Image.open(BytesIO(img_bytes))
        else:
          img = item

        prepared_inputs.append([img])
      else:
        raise ValueError(f"Unsupported input type at index {idx}: {type(item)}")

    # Single API call for all inputs
    logger.info(f"Generating embeddings for {len(prepared_inputs)} inputs...")
    result = self.vo.multimodal_embed(prepared_inputs, model=self.model)
    logger.info(f"Successfully generated {len(result.embeddings)} embeddings")

    return result.embeddings
