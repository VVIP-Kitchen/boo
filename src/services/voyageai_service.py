import os
import voyageai

from PIL import Image
from io import BytesIO
from utils.config import VOYAGEAI_API_KEY

class VoyageAiService:
  def __init__(self, model="voyage-multimodal-3"):
    self.vo = voyageai.Client(VOYAGEAI_API_KEY)
    self.model = model

  def generate_text_embeddings(self, text: str):
    result = self.vo.multimodal_embed([[text]], model=self.model)
    return result.embeddings[0]

  def generate_image_embeddings(self, img_bytes):
    img = Image.open(BytesIO(img_bytes))
    result = self.vo.multimodal_embed([[img]], model=self.model)
    return result.embeddings[0]
