"""
Cross-Encoder Re-ranker
Phase 8: Advanced RAG

Re-scores retrieved chunks using a HuggingFace CrossEncoder to improve accuracy
by evaluating the query and chunk simultaneously rather than just using cosine similarity.
"""

from typing import List, Optional
import logging
import time

try:
    from sentence_transformers import CrossEncoder
except ImportError:
    CrossEncoder = None

from .hybrid_retriever import SearchResult

logger = logging.getLogger(__name__)


class CrossEncoderReRanker:
    """
    Re-ranks search results using a CrossEncoder.

    A CrossEncoder passes both the query and the chunk text through the transformer
    together, outputting a highly accurate relevance score. This is significantly more
    accurate than a BiEncoder (used in initial dense retrieval) but much slower,
    which is why we only re-rank the top K candidate chunks.
    """

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        """
        Initialize the CrossEncoder model.

        Args:
            model_name: HuggingFace model identifier. Defaults to a fast MS-MARCO model.
        """
        self.model_name = model_name
        self.model = None

        if CrossEncoder is not None:
            try:
                logger.info(f"Loading CrossEncoder model: {model_name}")
                start_time = time.time()
                self.model = CrossEncoder(model_name, max_length=512)
                logger.info(f"Loaded CrossEncoder in {time.time() - start_time:.2f}s")
            except Exception as e:
                logger.error(f"Failed to load CrossEncoder model {model_name}: {e}")
        else:
            logger.warning("sentence-transformers not installed. Re-ranking disabled.")

    def rerank(
        self, query: str, results: List[SearchResult], chunk_texts: dict, top_k: int = 5
    ) -> List[SearchResult]:
        """
        Re-score and sort the provided SearchResults using the CrossEncoder.

        Args:
            query: The user's search query.
            results: List of candidate SearchResults from the initial retriever.
            chunk_texts: Dictionary mapping chunk_id to its text content.
            top_k: Number of final results to return.

        Returns:
            List of SearchResults, re-sorted and truncated to top_k, with their
            hybrid_score attribute updated to reflect the CrossEncoder score.
        """
        if self.model is None or not results:
            return results[:top_k]

        start_time = time.time()

        # Prepare inputs: list of (query, chunk_text) pairs
        # We must filter out any results whose text we don't have
        valid_results = []
        pairs = []

        for res in results:
            text = chunk_texts.get(res.chunk_id)
            if text:
                pairs.append((query, text))
                valid_results.append(res)

        if not pairs:
            return results[:top_k]

        try:
            # Score all pairs
            # This returns a 1D array of logits (or probabilities if the model has a sigmoid output)
            scores = self.model.predict(pairs)

            # Update the scores and re-sort
            for i, res in enumerate(valid_results):
                # The raw cross-encoder score can be negative or positive depending on the model.
                # MS-MARCO models usually output logits.
                res.hybrid_score = float(scores[i])

            # Sort by the new score descending
            valid_results.sort(key=lambda x: x.hybrid_score, reverse=True)

            # Re-assign ranks
            for rank, res in enumerate(valid_results, 1):
                res.rank = rank

            elapsed = (time.time() - start_time) * 1000
            logger.debug(f"Re-ranked {len(valid_results)} chunks in {elapsed:.2f}ms")

            return valid_results[:top_k]

        except Exception as e:
            logger.error(f"Re-ranking failed: {e}. Falling back to original order.")
            return results[:top_k]

    @property
    def is_loaded(self) -> bool:
        return self.model is not None
