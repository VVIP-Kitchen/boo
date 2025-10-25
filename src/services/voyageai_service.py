import os
import voyageai
from PIL import Image
from io import BytesIO
from typing import List, Union
from utils.config import VOYAGEAI_API_KEY


class VoyageAiService:
  def __init__(self, model="voyage-multimodal-3"):
    self.vo = voyageai.Client(VOYAGEAI_API_KEY)
    self.model = model

  def generate_text_embeddings(self, text: str):
    """Generate embeddings for a single text."""
    result = self.vo.multimodal_embed([[text]], model=self.model)
    return result.embeddings[0]

  def generate_image_embeddings(self, img_bytes):
    """Generate embeddings for a single image."""
    img = Image.open(BytesIO(img_bytes))
    result = self.vo.multimodal_embed([[img]], model=self.model)
    return result.embeddings[0]

  def generate_batch_embeddings(
    self, inputs: List[Union[str, bytes, Image.Image]]
  ) -> List[List[float]]:
    """
    Generate embeddings for multiple inputs (text and/or images) in one API call.

    Args:
        inputs: List of strings (text) or bytes/PIL Images (images)

    Returns:
        List of embeddings, one per input

    Example:
        inputs = [image_bytes, "VLM caption text", "User caption"]
        embeddings = service.generate_batch_embeddings(inputs)
        # Returns [image_emb, vlm_caption_emb, user_caption_emb]
    """
    # Prepare inputs for VoyageAI
    prepared_inputs = []

    for item in inputs:
      if isinstance(item, str):
        # Text input
        prepared_inputs.append([item])
      elif isinstance(item, bytes):
        # Image bytes - convert to PIL Image
        img = Image.open(BytesIO(item))
        prepared_inputs.append([img])
      elif isinstance(item, Image.Image):
        # Already a PIL Image
        prepared_inputs.append([item])
      else:
        raise ValueError(f"Unsupported input type: {type(item)}")

    # Single API call for all inputs
    result = self.vo.multimodal_embed(prepared_inputs, model=self.model)
    return result.embeddings
