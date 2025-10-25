import meilisearch
from datetime import datetime
from typing import List, Optional, Dict
from utils.config import MEILI_MASTER_KEY
from utils.logger import logger


class MeilisearchService:
  def __init__(self, host="http://meilisearch:7700"):
    self.client = meilisearch.Client(host, MEILI_MASTER_KEY)
    self.index_name = "boo"
    self._init_index()

  def _init_index(self):
    """Init index with config"""
    try:
      self.index = self.client.get_index(self.index_name)
    except:
      self.client.create_index(self.index_name, {"primaryKey": "image_id"})
      self.index = self.client.index(self.index_name)

    self.index.update_settings(
      {
        "searchableAttributes": [
          "vlm_caption",
          "user_caption",
          "author_name",
          "server_name",
        ],
        "sortableAttributes": ["created_at"],
        "filterableAttributes": ["created_at", "server_id", "author_id", "channel_id"],
        "embedders": {
          "image": {"source": "userProvided", "dimensions": 1024},
          "vlm_caption": {"source": "userProvided", "dimensions": 1024},
          "user_caption": {"source": "userProvided", "dimensions": 1024},
        },
      }
    )

  def add_document(
    self,
    image_id: str,
    image_embedding: List[float],
    vlm_caption: str,
    vlm_caption_embedding: List[float],
    user_caption: Optional[str] = None,
    user_caption_embedding: Optional[List[float]] = None,
    # Discord-specific metadata
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
  ):
    """Add image document with embeddings and Discord metadata."""
    document = {
      "image_id": image_id,
      "_vectors": {"image": image_embedding, "vlm_caption": vlm_caption_embedding},
      "vlm_caption": vlm_caption,
      "created_at": datetime.utcnow().isoformat(),
    }

    if user_caption and user_caption_embedding:
      document["_vectors"]["user_caption"] = user_caption_embedding
      document["user_caption"] = user_caption

    if message_url:
      document["message_url"] = message_url
    if message_id:
      document["message_id"] = message_id
    if server_id:
      document["server_id"] = server_id
    if server_name:
      document["server_name"] = server_name
    if channel_id:
      document["channel_id"] = channel_id
    if channel_name:
      document["channel_name"] = channel_name
    if author_id:
      document["author_id"] = author_id
    if author_name:
      document["author_name"] = author_name
    if attachment_url:
      document["attachment_url"] = attachment_url

    if metadata:
      document.update(metadata)

    return self.index.add_documents([document])

  def search_by_text(
    self,
    query: str,
    query_embedding: List[float],
    server_id: Optional[str] = None,
    limit: int = 10,
    semantic_ratio: float = 0.7,
  ) -> Dict:
    """
    Search images by text query using hybrid search.
    Searches across both VLM captions and user captions.
    """
    search_params = {
      "hybrid": {
        "semanticRatio": semantic_ratio,
        "embedder": "vlm_caption",  # Primary embedder for text search
      },
      "vector": query_embedding,
      "limit": limit,
      "showRankingScore": True,
    }

    if server_id:
      search_params["filter"] = f"server_id = '{server_id}'"

    return self.index.search(query, search_params)

  def search_by_image(
    self,
    image_embedding: List[float],
    server_id: Optional[str] = None,
    limit: int = 10,
    semantic_ratio: float = 0.95,  # Higher semantic ratio for image similarity
  ) -> Dict:
    """
    Search images by visual similarity using image embeddings.
    """
    search_params = {
      "hybrid": {
        "semanticRatio": semantic_ratio,
        "embedder": "image",  # Use image embedder
      },
      "vector": image_embedding,
      "limit": limit,
      "showRankingScore": True,
      "q": "",  # Empty query for pure vector search
    }

    if server_id:
      search_params["filter"] = f"server_id = '{server_id}'"

    return self.index.search("", search_params)

  def update_document(self, image_id, **fields):
    """Update specific fields of a document"""
    document = {"image_id": image_id, **fields}
    return self.index.update_documents([document])

  def delete_document(self, image_id):
    """Delete a document by ID"""
    return self.index.delete_document(image_id)

  def get_document(self, image_id):
    """Get document by ID"""
    return self.index.get_document(image_id)

  def delete_all_documents(self):
    """Delete all documents from index"""
    return self.index.delete_all_documents()

  def get_stats(self) -> Dict:
    """Get index statistics."""
    try:
      # Method 1: Try get_stats() on index
      index = self.client.get_index(self.index_name)
      stats = index.get_stats()
      doc_count = stats.get("numberOfDocuments", 0)

      logger.info(f"Meilisearch: {doc_count} documents indexed")

      return {
        "total_documents": doc_count,
        "is_indexing": False,  # Simplified - don't check indexing status
      }

    except Exception as e:
      logger.error(f"Error getting Meilisearch stats: {e}")

      # Fallback: Use search with limit 0 to get count
      try:
        result = self.index.search("", {"limit": 0})
        total = result.get("estimatedTotalHits", 0)
        logger.info(f"Meilisearch (via search): {total} documents")

        return {
          "total_documents": total,
          "is_indexing": False,
        }
      except Exception as e2:
        logger.error(f"All methods failed: {e2}")
        return {
          "total_documents": 0,
          "is_indexing": False,
          "error": f"{str(e)} | {str(e2)}",
        }
