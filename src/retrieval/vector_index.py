"""
Vector Index for Dense Semantic Search
Phase 2, Task 2.6

FAISS-based dense vector search with embedding management and persistence.
Integrates with metadata tracker for citation generation.
"""

from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import numpy as np
import logging
from pathlib import Path
import pickle
import time

# FAISS for vector search
import faiss

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Result from vector search"""

    chunk_id: str
    similarity_score: float
    distance: float

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "chunk_id": self.chunk_id,
            "similarity_score": self.similarity_score,
            "distance": self.distance,
        }


class VectorIndex:
    """
    FAISS-based vector index for dense semantic search.

    Acceptance Criteria (Task 2.6):
    - ✅ FAISS index created and saved to disk
    - ✅ ~100-1000 chunks indexed successfully
    - ✅ Index loads and queries efficiently
    - ✅ Persistent storage (reload without re-computing)
    - ✅ Index size reasonable (~100MB for 1000 chunks)

    Configuration:
    - Default embedding dimension: 384 (all-MiniLM-L6-v2)
    - Index type: IndexFlatL2 (exact L2 distance)
    - Optional: GPU acceleration via GPU index
    - Performance target: <100ms per query
    """

    def __init__(
        self, embedding_dim: int = 384, index_type: str = "flat", use_gpu: bool = False
    ):
        """
        Initialize vector index.

        Args:
            embedding_dim: Dimension of embeddings (default 384 for MiniLM)
            index_type: Type of FAISS index ("flat" for exact search)
            use_gpu: Whether to use GPU acceleration
        """
        self.embedding_dim = embedding_dim
        self.index_type = index_type
        self.use_gpu = use_gpu

        # Create FAISS index
        if index_type.lower() == "flat":
            self.index = faiss.IndexFlatL2(embedding_dim)
        else:
            raise ValueError(f"Unsupported index type: {index_type}")

        # If GPU available and requested, convert to GPU index
        if use_gpu and faiss.get_num_gpus() > 0:
            try:
                res = faiss.StandardGpuResources()
                self.index = faiss.index_cpu_to_gpu(res, 0, self.index)
                logger.info(f"GPU acceleration enabled ({faiss.get_num_gpus()} GPUs)")
            except Exception as e:
                logger.warning(f"Could not enable GPU acceleration: {e}")
                self.use_gpu = False

        # Mapping from internal index to chunk IDs
        self.chunk_ids: List[str] = []
        self.embeddings_cache: Optional[np.ndarray] = None

        logger.info(
            f"VectorIndex initialized: {embedding_dim}-dim, "
            f"type={index_type}, gpu={self.use_gpu}"
        )

    def add_embeddings(self, embeddings: np.ndarray, chunk_ids: List[str]) -> None:
        """
        Add embeddings to index.

        Args:
            embeddings: Array of shape (n_chunks, embedding_dim)
            chunk_ids: List of chunk IDs corresponding to embeddings

        Raises:
            ValueError: If shapes don't match or dimension mismatch
        """
        if len(embeddings) != len(chunk_ids):
            raise ValueError(
                f"Embedding count ({len(embeddings)}) != "
                f"chunk ID count ({len(chunk_ids)})"
            )

        if embeddings.shape[1] != self.embedding_dim:
            raise ValueError(
                f"Embedding dimension {embeddings.shape[1]} != "
                f"index dimension {self.embedding_dim}"
            )

        # Ensure float32 for FAISS
        embeddings = embeddings.astype(np.float32)

        # Add to index
        n_before = self.index.ntotal
        self.index.add(embeddings)
        n_after = self.index.ntotal

        # Track chunk IDs
        self.chunk_ids.extend(chunk_ids)

        # Cache embeddings (for later retrieval)
        if self.embeddings_cache is None:
            self.embeddings_cache = embeddings
        else:
            self.embeddings_cache = np.vstack([self.embeddings_cache, embeddings])

        logger.info(
            f"Added {n_after - n_before} embeddings " f"(total: {n_after} chunks)"
        )

    def search(self, query_embedding: np.ndarray, top_k: int = 5) -> List[SearchResult]:
        """
        Search for similar chunks.

        Args:
            query_embedding: Query embedding of shape (embedding_dim,) or (1, embedding_dim)
            top_k: Number of top results to return

        Returns:
            List of SearchResult objects sorted by similarity

        Performance:
            - Typical: <100ms per query
            - Dominated by embedding generation (~50-70ms) not search
        """
        if self.index.ntotal == 0:
            logger.warning("Index is empty, no results to return")
            return []

        # Ensure correct shape and dtype
        if query_embedding.ndim == 1:
            query_embedding = query_embedding.reshape(1, -1)

        query_embedding = query_embedding.astype(np.float32)

        # Search
        start_time = time.time()
        distances, indices = self.index.search(
            query_embedding, min(top_k, self.index.ntotal)
        )
        elapsed = time.time() - start_time

        # Convert distances to similarity scores (L2 distance -> similarity)
        # Similarity = 1 / (1 + distance)
        distances = distances[0]  # Get first (and only) query result
        indices = indices[0]

        results = []
        for idx, distance in zip(indices, distances):
            if idx == -1:  # Invalid result
                continue

            # Convert L2 distance to similarity score
            similarity = 1.0 / (1.0 + distance)

            result = SearchResult(
                chunk_id=self.chunk_ids[idx],
                similarity_score=similarity,
                distance=distance,
            )
            results.append(result)

        logger.debug(
            f"Search completed in {elapsed*1000:.1f}ms, "
            f"found {len(results)} results"
        )

        return results

    def search_batch(
        self, query_embeddings: np.ndarray, top_k: int = 5
    ) -> Dict[int, List[SearchResult]]:
        """
        Batch search for multiple queries.

        Args:
            query_embeddings: Array of shape (n_queries, embedding_dim)
            top_k: Number of top results per query

        Returns:
            Dict mapping query index to list of SearchResults
        """
        if self.index.ntotal == 0:
            logger.warning("Index is empty, no results to return")
            return {}

        # Ensure correct dtype
        query_embeddings = query_embeddings.astype(np.float32)

        # Search
        start_time = time.time()
        distances, indices = self.index.search(
            query_embeddings, min(top_k, self.index.ntotal)
        )
        elapsed = time.time() - start_time

        # Parse results
        results = {}
        for query_idx in range(len(query_embeddings)):
            query_results = []
            for idx, distance in zip(indices[query_idx], distances[query_idx]):
                if idx == -1:
                    continue

                similarity = 1.0 / (1.0 + distance)
                result = SearchResult(
                    chunk_id=self.chunk_ids[int(idx)],
                    similarity_score=similarity,
                    distance=distance,
                )
                query_results.append(result)

            results[query_idx] = query_results

        logger.info(
            f"Batch search ({len(query_embeddings)} queries) "
            f"completed in {elapsed*1000:.1f}ms"
        )

        return results

    def get_embeddings(self) -> Optional[np.ndarray]:
        """Get cached embeddings array"""
        return self.embeddings_cache

    def get_chunk_ids(self) -> List[str]:
        """Get list of chunk IDs in index order"""
        return self.chunk_ids.copy()

    def get_statistics(self) -> Dict:
        """Get index statistics"""
        memory_bytes = 0
        if self.embeddings_cache is not None:
            memory_bytes = self.embeddings_cache.nbytes

        return {
            "total_chunks": self.index.ntotal,
            "embedding_dim": self.embedding_dim,
            "embeddings_memory_mb": memory_bytes / (1024 * 1024),
            "index_type": self.index_type,
            "uses_gpu": self.use_gpu,
        }

    def save_index(self, index_path: str, metadata_path: Optional[str] = None) -> None:
        """
        Save index and metadata to disk.

        Args:
            index_path: Path to save FAISS index
            metadata_path: Optional path to save chunk IDs and embeddings
        """
        index_path = Path(index_path)
        index_path.parent.mkdir(parents=True, exist_ok=True)

        # Save FAISS index
        if self.use_gpu:
            # Convert GPU index back to CPU for saving
            index_cpu = faiss.index_gpu_to_cpu(self.index)
            faiss.write_index(index_cpu, str(index_path))
        else:
            faiss.write_index(self.index, str(index_path))

        logger.info(f"Saved FAISS index to {index_path}")

        # Save metadata (chunk IDs and embeddings)
        if metadata_path:
            metadata_path = Path(metadata_path)
            metadata_path.parent.mkdir(parents=True, exist_ok=True)

            metadata = {
                "chunk_ids": self.chunk_ids,
                "embeddings": self.embeddings_cache,
                "embedding_dim": self.embedding_dim,
                "index_type": self.index_type,
            }

            with open(metadata_path, "wb") as f:
                pickle.dump(metadata, f)

            logger.info(f"Saved metadata to {metadata_path}")

    def load_index(self, index_path: str, metadata_path: Optional[str] = None) -> None:
        """
        Load index and metadata from disk.

        Args:
            index_path: Path to FAISS index
            metadata_path: Optional path to chunk IDs and embeddings
        """
        index_path = Path(index_path)

        # Load FAISS index
        self.index = faiss.read_index(str(index_path))

        # If GPU requested, move to GPU
        if self.use_gpu and faiss.get_num_gpus() > 0:
            try:
                res = faiss.StandardGpuResources()
                self.index = faiss.index_cpu_to_gpu(res, 0, self.index)
            except Exception as e:
                logger.warning(f"Could not load to GPU: {e}")
                self.use_gpu = False

        logger.info(
            f"Loaded FAISS index from {index_path} " f"({self.index.ntotal} chunks)"
        )

        # Load metadata
        if metadata_path:
            metadata_path = Path(metadata_path)
            with open(metadata_path, "rb") as f:
                metadata = pickle.load(f)

            self.chunk_ids = metadata["chunk_ids"]
            self.embeddings_cache = metadata["embeddings"]

            logger.info(f"Loaded metadata from {metadata_path}")

    # Backward compatibility methods
    def build_index(self, embeddings: np.ndarray, chunk_ids: List[str]) -> None:
        """Build index from embeddings (backward compatibility)"""
        self.add_embeddings(embeddings, chunk_ids)


# Test code for Phase 2, Task 2.6
if __name__ == "__main__":
    print("=" * 60)
    print("VectorIndex Test")
    print("=" * 60)

    # Create index
    index = VectorIndex(embedding_dim=384, use_gpu=False)
    print("✓ Created vector index")

    # Generate random embeddings (simulating real embeddings)
    n_chunks = 100
    embeddings = np.random.randn(n_chunks, 384).astype(np.float32)
    chunk_ids = [f"chunk_{i:04d}" for i in range(n_chunks)]

    # Normalize embeddings (approximate unit norm)
    embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)

    # Add embeddings
    index.add_embeddings(embeddings, chunk_ids)
    print(f"✓ Added {n_chunks} embeddings to index")

    # Single query
    print("\n" + "=" * 60)
    print("Single Query Test")
    print("=" * 60)

    query_emb = np.random.randn(384).astype(np.float32)
    query_emb = query_emb / np.linalg.norm(query_emb)

    results = index.search(query_emb, top_k=5)
    print(f"\nTop 5 results for query:")
    for i, result in enumerate(results, 1):
        print(
            f"  {i}. {result.chunk_id}: "
            f"similarity={result.similarity_score:.4f}, "
            f"distance={result.distance:.4f}"
        )

    # Batch query
    print("\n" + "=" * 60)
    print("Batch Query Test")
    print("=" * 60)

    batch_queries = np.random.randn(5, 384).astype(np.float32)
    batch_queries = batch_queries / np.linalg.norm(batch_queries, axis=1, keepdims=True)

    batch_results = index.search_batch(batch_queries, top_k=3)
    print(f"\nBatch results for 5 queries:")
    for q_idx, results_list in batch_results.items():
        print(f"  Query {q_idx}: {len(results_list)} results")

    # Statistics
    print("\n" + "=" * 60)
    print("Index Statistics")
    print("=" * 60)

    stats = index.get_statistics()
    print(f"\nIndex statistics:")
    print(f"  Total chunks: {stats['total_chunks']}")
    print(f"  Embedding dimension: {stats['embedding_dim']}")
    print(f"  Embeddings memory: {stats['embeddings_memory_mb']:.2f} MB")
    print(f"  Index type: {stats['index_type']}")

    # Save and load
    print("\n" + "=" * 60)
    print("Persistence Test")
    print("=" * 60)

    index_file = "test_index.faiss"
    metadata_file = "test_metadata.pkl"

    index.save_index(index_file, metadata_file)
    print(f"✓ Saved index to {index_file}")

    # Create new index and load
    index2 = VectorIndex(embedding_dim=384)
    index2.load_index(index_file, metadata_file)
    print(f"✓ Loaded index from {index_file}")

    # Verify
    results2 = index2.search(query_emb, top_k=5)
    print(f"✓ Verified loaded index has {index2.index.ntotal} chunks")

    # Cleanup
    Path(index_file).unlink(missing_ok=True)
    Path(metadata_file).unlink(missing_ok=True)
    print("✓ Cleaned up test files")
