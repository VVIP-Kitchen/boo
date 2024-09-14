import numpy as np

from typing import Optional, List
from fastembed import TextEmbedding
from qdrant_client import QdrantClient
from utils.config import QDRANT_HOST, QDRANT_PORT, QDRANT_COLLECTION


class VectorService:
  _instance: Optional["VectorService"] = None
  embedding_model: TextEmbedding
  client: QdrantClient

  def __new__(cls, model_name: str = "BAAI/bge-small-en-v1.5") -> "VectorService":
    if cls._instance is None:
      cls._instance = super(VectorService, cls).__new__(cls)
      cls._instance._initialize(model_name)

    return cls._instance

  def _initialize(self, model_name: str) -> None:
    qdrant_url = f"http://{QDRANT_HOST}:{QDRANT_PORT}"
    self.client = QdrantClient(url=qdrant_url)
    self.embedding_model = TextEmbedding(model_name=model_name)

  def _is_null(self, string: str) -> bool:
    if string is None:
      return True
    if len(string.strip()) == 0:
      return True
    return False

  def embed(self, string: str) -> Optional[np.ndarray]:
    if self._is_null(string):
      return None

    embeddings: List[np.ndarray] = list(self.embedding_model.embed(string))
    return embeddings[0] if embeddings else None

  def search(self, query: str, limit=3) -> str:
    if self._is_null(query):
      return None

    search_results = self.client.query_points(
      collection_name=QDRANT_COLLECTION, query=self.embed(query), limit=3
    ).points

    output = ""
    for result in search_results:
      output += result.payload["Answer"] + "\n"

    return output
