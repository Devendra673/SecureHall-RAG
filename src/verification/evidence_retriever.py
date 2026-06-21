"""
Task 4.3: Evidence Retrieval Per-Claim

Finds supporting evidence for each claim independently.
Supports both re-querying and caching from original retrieval.

Author: Verification Engineering Team
Version: 1.0
"""

import sys
import logging
from pathlib import Path
from typing import List, Optional, Dict
from dataclasses import field

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.verification.data_structures import Claim, ClaimMetadata, EvidenceSet, Chunk

logger = logging.getLogger(__name__)


class EvidenceRetriever:
    """Retrieves evidence for claims"""

    def __init__(self, hybrid_retriever=None, cache_original_results: bool = True):
        """
        Initialize evidence retriever

        Args:
            hybrid_retriever: Hybrid retriever instance (dense + sparse)
            cache_original_results: Use cached results from original query if available
        """
        self.hybrid_retriever = hybrid_retriever
        self.cache_original_results = cache_original_results
        self.original_results: Dict[str, List[Chunk]] = {}

    def set_original_results(self, results: Dict[str, List[Chunk]]):
        """
        Set cached results from original query

        Args:
            results: Dictionary mapping queries to retrieved chunks
        """
        self.original_results = results

    def retrieve_evidence(
        self,
        claim: Claim,
        metadata: ClaimMetadata,
        num_candidates: int = 5,
        reuse_cache: bool = True,
    ) -> EvidenceSet:
        """
        Retrieve evidence for a single claim

        Args:
            claim: Claim to find evidence for
            metadata: Metadata about the claim
            num_candidates: Number of evidence chunks to retrieve (3-5)
            reuse_cache: Whether to try using cached results first

        Returns:
            EvidenceSet with retrieved evidence
        """
        evidence_chunks = []
        retrieval_scores = []
        retrieval_method = "cached"

        # Step 1: Try to use cached results if available
        if reuse_cache and self.cache_original_results and self.original_results:
            cached = self.original_results.get(claim.claim_text)
            if cached and len(cached) >= num_candidates:
                evidence_chunks = cached[:num_candidates]
                retrieval_scores = [
                    getattr(chunk, "relevance_score", 0.5) for chunk in evidence_chunks
                ]
                retrieval_method = "cached"

        # Step 2: If not cached or insufficient, perform re-query
        if not evidence_chunks and self.hybrid_retriever:
            query = self._formulate_query(claim, metadata)

            try:
                results = self.hybrid_retriever.retrieve(query, top_k=num_candidates)

                evidence_chunks = [
                    Chunk(
                        chunk_id=f"chunk_{idx}",
                        content=result.get("content", ""),
                        source=result.get("source", "unknown"),
                        relevance_score=result.get("score", 0.5),
                    )
                    for idx, result in enumerate(results)
                ]

                retrieval_scores = [chunk.relevance_score for chunk in evidence_chunks]
                retrieval_method = "requery"
            except Exception as e:
                # Fallback to empty evidence if retrieval fails
                logger.warning(f"Evidence retrieval failed: {e}")

        # Step 3: Create evidence set
        evidence_set = EvidenceSet(
            claim_id=claim.claim_id,
            evidence_chunks=evidence_chunks,
            retrieval_scores=retrieval_scores,
            retrieval_method=retrieval_method,
            num_retrieved=len(evidence_chunks),
        )

        return evidence_set

    def retrieve_evidence_batch(
        self,
        claims: List[Claim],
        metadata_list: List[ClaimMetadata],
        num_candidates: int = 5,
    ) -> Dict[str, EvidenceSet]:
        """
        Retrieve evidence for multiple claims

        Args:
            claims: List of claims
            metadata_list: List of metadata for each claim
            num_candidates: Number of candidates per claim

        Returns:
            Dictionary mapping claim_id to EvidenceSet
        """
        evidence_sets = {}

        for claim, metadata in zip(claims, metadata_list):
            evidence_set = self.retrieve_evidence(claim, metadata, num_candidates)
            evidence_sets[claim.claim_id] = evidence_set

        return evidence_sets

    def _formulate_query(self, claim: Claim, metadata: ClaimMetadata) -> str:
        """
        Formulate optimal query for evidence retrieval

        Args:
            claim: Claim to query for
            metadata: Metadata about the claim

        Returns:
            Query string optimized for retrieval
        """
        # Start with claim text
        query = claim.claim_text

        # Enhance with entities if available
        if metadata.entities:
            entity_str = " ".join(metadata.entities)
            query = f"{query} {entity_str}"

        # Add predicate if available
        if metadata.main_predicate:
            query = f"{query} {metadata.main_predicate}"

        # Limit query length
        query_words = query.split()
        if len(query_words) > 30:
            query = " ".join(query_words[:30])

        return query

    def get_statistics(self) -> dict:
        """Get retriever statistics"""
        return {
            "cache_enabled": self.cache_original_results,
            "original_results_count": len(self.original_results),
        }


class MockRetriever:
    """Mock retriever for testing"""

    def __init__(self):
        """Initialize mock retriever"""
        self.documents = {
            "health insurance": [
                {
                    "content": "Our health insurance covers medical, dental, and vision benefits for all employees.",
                    "source": "benefits.docx",
                    "score": 0.95,
                },
                {
                    "content": "Medical coverage includes preventive care and specialist visits.",
                    "source": "benefits.docx",
                    "score": 0.85,
                },
            ],
            "pto": [
                {
                    "content": "Full-time employees receive 20 days of paid time off annually.",
                    "source": "policies.docx",
                    "score": 0.92,
                },
                {
                    "content": "PTO includes vacation days, personal days, and holidays.",
                    "source": "policies.docx",
                    "score": 0.88,
                },
            ],
            "severance": [
                {
                    "content": "Employees with 5+ years of service receive 8 weeks severance upon termination.",
                    "source": "compensation.docx",
                    "score": 0.90,
                },
                {
                    "content": "Severance is based on years of employment and is paid in installments.",
                    "source": "compensation.docx",
                    "score": 0.82,
                },
            ],
        }

    def retrieve(self, query: str, top_k: int = 5) -> List[dict]:
        """Retrieve documents matching query"""
        # Find matching documents
        results = []
        query_lower = query.lower()

        for keyword, docs in self.documents.items():
            if keyword in query_lower:
                results.extend(docs)

        # Sort by score
        results.sort(key=lambda x: x["score"], reverse=True)

        return results[:top_k]


def example_usage():
    """Demonstrate evidence retriever"""

    print("=" * 70)
    print("EVIDENCE RETRIEVER EXAMPLES")
    print("=" * 70)

    retriever = EvidenceRetriever(hybrid_retriever=MockRetriever())

    # Sample claims
    claims = [
        Claim(
            claim_id="claim_001",
            claim_text="Our health insurance covers medical, dental, and vision benefits.",
            original_sentence="Our health insurance covers medical, dental, and vision benefits.",
        ),
        Claim(
            claim_id="claim_002",
            claim_text="Full-time employees receive 20 days of PTO annually.",
            original_sentence="Full-time employees receive 20 days of PTO annually.",
        ),
    ]

    # Sample metadata
    metadata_list = [
        ClaimMetadata(
            claim_id="claim_001", entities=["health insurance", "medical", "dental"]
        ),
        ClaimMetadata(claim_id="claim_002", entities=["PTO", "employees"]),
    ]

    # Retrieve evidence
    for claim, metadata in zip(claims, metadata_list):
        print(f"\nClaim: {claim.claim_text}")
        print("-" * 70)

        evidence_set = retriever.retrieve_evidence(claim, metadata, num_candidates=3)

        print(f"Evidence Found: {evidence_set.num_retrieved}")
        print(f"Retrieval Method: {evidence_set.retrieval_method}")

        for chunk in evidence_set.evidence_chunks:
            print(f"\n  [{chunk.source}] (score: {chunk.relevance_score:.2f})")
            print(f"  {chunk.content[:100]}...")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    example_usage()
