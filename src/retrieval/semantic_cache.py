"""
Semantic Cache for RAG Queries
Phase 12: Academic Features

Caches user query embeddings and outputs cached results if semantic similarity
exceeds a configurable threshold.
"""

from datetime import datetime
import logging
from typing import Dict, Optional, List
import numpy as np

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

logger = logging.getLogger(__name__)

class SemanticCache:
    def __init__(
        self, 
        similarity_threshold: float = 0.92, 
        max_size: int = 200,
        embedding_model: str = "sentence-transformers/all-mpnet-base-v2"
    ):
        self.similarity_threshold = similarity_threshold
        self.max_size = max_size
        self.model_name = embedding_model
        self.model = None

        if SentenceTransformer is not None:
            try:
                self.model = SentenceTransformer(embedding_model)
                logger.info(f"Loaded SemanticCache embedding model: {embedding_model}")
            except Exception as e:
                logger.error(f"Failed to load SemanticCache embedding model: {e}")
        else:
            logger.warning("sentence-transformers not installed. Semantic Cache disabled.")

        # Cache format: List of Dict containing:
        # {
        #   "query": str,
        #   "embedding": np.ndarray,
        #   "result": dict,
        #   "timestamp": datetime,
        #   "hits": int
        # }
        self._cache: List[Dict] = []
        self.hits = 0
        self.misses = 0

    def get(self, query: str) -> Optional[Dict]:
        """
        Check if query exists in cache with semantic similarity above threshold.
        """
        if self.model is None or not self._cache:
            self.misses += 1
            return None

        try:
            # Embed the incoming query
            query_emb = self.model.encode(query, convert_to_numpy=True)
            # Normalize embedding
            query_emb = query_emb / np.linalg.norm(query_emb)

            best_sim = -1.0
            best_entry = None

            for entry in self._cache:
                cached_emb = entry["embedding"]
                # Cosine similarity (since both are normalized, it is just dot product)
                sim = float(np.dot(query_emb, cached_emb))
                if sim > best_sim:
                    best_sim = sim
                    best_entry = entry

            if best_sim >= self.similarity_threshold and best_entry is not None:
                self.hits += 1
                best_entry["hits"] += 1
                best_entry["timestamp"] = datetime.now()
                logger.info(f"SemanticCache HIT (similarity: {best_sim:.4f}) for: '{query}'")
                return best_entry["result"]

            self.misses += 1
            logger.debug(f"SemanticCache MISS (best similarity: {best_sim:.4f}) for: '{query}'")
            return None

        except Exception as e:
            logger.error(f"Error reading from semantic cache: {e}")
            self.misses += 1
            return None

    def set(self, query: str, result: Dict) -> None:
        """
        Cache a new query and its result.
        """
        if self.model is None:
            return

        try:
            # Embed query
            query_emb = self.model.encode(query, convert_to_numpy=True)
            query_emb = query_emb / np.linalg.norm(query_emb)

            # Evict if max size reached
            if len(self._cache) >= self.max_size:
                # Least recently used/hit eviction (LRU + low hit count)
                # Sort by timestamp (older first) and then by hits (fewer first)
                self._cache.sort(key=lambda x: (x["hits"], x["timestamp"]))
                removed = self._cache.pop(0)
                logger.debug(f"SemanticCache Evicted: '{removed['query']}'")

            new_entry = {
                "query": query,
                "embedding": query_emb,
                "result": result,
                "timestamp": datetime.now(),
                "hits": 0
            }
            self._cache.append(new_entry)
            logger.debug(f"Cached query: '{query}'")

        except Exception as e:
            logger.error(f"Failed to set semantic cache entry: {e}")

    def clear(self) -> None:
        """Clear cache and reset stats"""
        self._cache = []
        self.hits = 0
        self.misses = 0
        logger.info("SemanticCache cleared.")

    def stats(self) -> Dict:
        """Get cache statistics"""
        total = self.hits + self.misses
        hit_rate = (self.hits / total) if total > 0 else 0.0
        return {
            "enabled": self.model is not None,
            "total_cached": len(self._cache),
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": hit_rate,
            "threshold": self.similarity_threshold,
            "max_size": self.max_size
        }
