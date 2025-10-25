import meilisearch

from utils.config import MEILI_MASTER_KEY

class MeilisearchService:
  def __init__(self, host="http://meilisearch:7700"):
    self.client = meilisearch.Client(host, MEILI_MASTER_KEY)
    self.index_name = 'boo'
    self._init_index()

  def _init_index(self):
    """
    Init index with config
    """
    try:
      self.index = self.client.get_index(self.index_name)
    except:
      self.client.create_index(self.index_name, {
        "primaryKey": "image_id"
      })
      self.index = self.client.index(self.index_name)

    self.index.update_settings({
      "searchableAttributes": ["vlm_caption", "user_caption"],
      "embedders": {
        "image": {
          "source": "userProvided",
          "dimensions": 1024
        },
        "vlm_caption": {
          "source": "userProvided",
          "dimensions": 1024
        },
        "user_caption": {
          "source": "userProvided",
          "dimensions": 1024
        }
      }
    })

  def add_document(self, image_id, image_embedding, vlm_caption, vlm_caption_embedding, user_caption=None, user_caption_embedding=None):
    """
    Add image document with embeddings
    """
    document = {
      "image_id": image_id,
      "_vectors": {
        "image": image_embedding,
        "vlm_caption": vlm_caption_embedding
      },
      "vlm_caption": vlm_caption
    }

    if user_caption and user_caption_embedding:
      document['_vectors']['user_caption'] = user_caption_embedding
      document['user_caption'] = user_caption

    return self.index.add_documents([document])

  def update_document(self, image_id, **fields):
    """
    Update specific fields of a document
    """
    document = {'image_id': image_id, **fields}
    return self.index.update_documents([document])

  def delete_document(self, image_id):
    """
    Delete a document by ID
    """
    return self.index.delete_document(image_id)

  def search(self, query, query_embedding, embedder='image', semantic_ratio=0.5, limit=20):
    """
    Hybrid search with vector and keyword
    """
    return self.index.search(query, {
      'hybrid': {
        'semanticRatio': semantic_ratio,
        'embedder': embedder
      },
      'vector': query_embedding,
      'limit': limit,
      'showRankingScore': True
    })

  def get_document(self, image_id):
    """Get document by ID"""
    return self.index.get_document(image_id)

  def delete_all_documents(self):
    """Delete all documents from index"""
    return self.index.delete_all_documents()
