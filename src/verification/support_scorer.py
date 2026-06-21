"""
Task 4.4: Support Scorer

Quantifies how much evidence supports each claim.
Uses BM25 overlap, semantic similarity, and NLI scoring.

Author: Verification Engineering Team
Version: 1.0
"""

import sys
import re
import logging
from pathlib import Path
from typing import List
from collections import Counter

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.verification.data_structures import Claim, EvidenceSet, SupportScore, Chunk

logger = logging.getLogger(__name__)


class SupportScorer:
    """Scores support level for claims based on evidence"""

    def __init__(self, use_nli: bool = True, llm=None):
        """
        Initialize scorer

        Args:
            use_nli: Whether to use NLI model (requires transformers)
            llm: Optional LLMInference instance for fallback robust scoring
        """
        self.use_nli = use_nli
        self.nli_model = None
        self.llm = llm

        if use_nli:
            try:
                from transformers import pipeline

                self.nli_model = pipeline("zero-shot-classification")
            except ImportError:
                logger.warning("transformers not available, local NLI disabled")
                self.use_nli = False

    def score_support(self, claim: Claim, evidence_set: EvidenceSet) -> SupportScore:
        """
        Score how much evidence supports the claim

        Args:
            claim: Claim to score
            evidence_set: Evidence retrieved for the claim

        Returns:
            SupportScore with detailed scoring breakdown
        """
        overlap_score = 0.0
        semantic_score = 0.0
        nli_score = 0.0
        conflict_detected = False
        conflict_evidence = None

        # Calculate overlap score
        if evidence_set.evidence_chunks:
            overlap_scores = [
                self._bm25_overlap(claim.claim_text, chunk.content)
                for chunk in evidence_set.evidence_chunks
            ]
            overlap_score = (
                max(overlap_scores) if overlap_scores else 0.0
            )

        # Calculate semantic similarity score
        if evidence_set.evidence_chunks:
            semantic_scores = [
                self._semantic_similarity(claim.claim_text, chunk.content)
                for chunk in evidence_set.evidence_chunks
            ]
            semantic_score = (
                max(semantic_scores) if semantic_scores else 0.0
            )

        # Calculate NLI score (Hybrid approach: fast local model + robust LLM fallback)
        if evidence_set.evidence_chunks:
            nli_scores = []
            for idx, chunk in enumerate(evidence_set.evidence_chunks):
                score = 0.0
                if self.use_nli and self.nli_model:
                    score = self._nli_entailment(claim.claim_text, chunk.content)
                
                # OPTIMIZATION: Only run slow LLM fallback on the absolute best chunk
                # and only if the fast NLI model isn't completely confident.
                if idx == 0 and self.llm and self.llm.is_loaded and (not self.use_nli or (0.3 < score < 0.7)):
                    score = self._llm_entailment(claim.claim_text, chunk.content)
                    
                nli_scores.append(score)
                
            nli_score = max(nli_scores) if nli_scores else 0.0

        # Check for conflicts
        conflict_detected, conflict_evidence = self._detect_conflict(
            claim.claim_text, evidence_set.evidence_chunks
        )

        # Aggregate into final support score
        if evidence_set.evidence_chunks:
            # Weighted average of scores (we always try to have an NLI score now via LLM fallback)
            final_support = (overlap_score * 0.2 + semantic_score * 0.3 + nli_score * 0.5)

            # Penalize conflicts
            if conflict_detected:
                final_support *= 0.5
        else:
            final_support = 0.0

        # Generate reasoning
        reasoning = self._generate_reasoning(
            overlap_score,
            semantic_score,
            nli_score,
            conflict_detected,
            len(evidence_set.evidence_chunks),
        )

        return SupportScore(
            claim_id=claim.claim_id,
            overlap_score=overlap_score,
            semantic_score=semantic_score,
            nli_score=nli_score,
            conflict_detected=conflict_detected,
            conflict_evidence=conflict_evidence,
            final_support=final_support,
            reasoning=reasoning,
        )

    def score_support_batch(
        self,
        claims: List[Claim],
        evidence_sets: List[EvidenceSet],
    ) -> List[SupportScore]:
        """
        Score multiple claims

        Args:
            claims: List of claims
            evidence_sets: List of evidence sets (parallel to claims)

        Returns:
            List of support scores
        """
        return [
            self.score_support(claim, evidence_set)
            for claim, evidence_set in zip(claims, evidence_sets)
        ]

    def _bm25_overlap(self, claim: str, evidence: str) -> float:
        """
        Calculate BM25-style keyword overlap

        Args:
            claim: Claim text
            evidence: Evidence text

        Returns:
            Overlap score 0-1
        """
        # Tokenize
        claim_tokens = set(self._tokenize(claim))
        evidence_tokens = set(self._tokenize(evidence))

        # Calculate overlap
        if not claim_tokens:
            return 0.0

        overlap = len(claim_tokens & evidence_tokens)
        coverage = overlap / len(claim_tokens)

        return min(1.0, coverage)

    def _semantic_similarity(self, claim: str, evidence: str) -> float:
        """
        Calculate semantic similarity (simple version)

        Args:
            claim: Claim text
            evidence: Evidence text

        Returns:
            Similarity score 0-1
        """
        # Simple heuristic: check for key phrase overlap
        claim_lower = claim.lower()
        evidence_lower = evidence.lower()

        # Get bigrams and trigrams
        claim_phrases = self._extract_phrases(claim)
        evidence_phrases = self._extract_phrases(evidence)

        if not claim_phrases:
            return 0.0

        # Calculate phrase overlap
        phrase_overlap = len(set(claim_phrases) & set(evidence_phrases))
        phrase_coverage = phrase_overlap / len(claim_phrases)

        return min(1.0, phrase_coverage)

    def _nli_entailment(self, claim: str, evidence: str) -> float:
        """
        Calculate entailment probability using NLI model

        Args:
            claim: Claim to verify
            evidence: Supporting evidence

        Returns:
            Entailment probability 0-1
        """
        if not self.nli_model:
            return 0.5  # Default confidence

        try:
            result = self.nli_model(
                evidence,
                [claim, "opposite of claim", "unrelated to claim"],
                multi_class=True,
            )

            # Get entailment score (assuming first position is entailment)
            scores = result.get("scores", [0.33, 0.33, 0.33])
            entailment_score = scores[0]

            return entailment_score
        except Exception:
            return 0.5  # Default on error

    def _llm_entailment(self, claim: str, evidence: str) -> float:
        """
        Calculate entailment probability using the LLM.
        """
        prompt = f"""You are an NLI (Natural Language Inference) engine.
Determine if the given Evidence supports the Claim.
Evidence: "{evidence}"
Claim: "{claim}"

Respond with EXACTLY ONE WORD from the following options:
SUPPORTED (if the evidence fully proves the claim)
CONTRADICTED (if the evidence disproves the claim)
NEUTRAL (if the evidence is unrelated or insufficient)
"""
        try:
            result = self.llm.generate(prompt, max_tokens=10).strip().upper()
            if "SUPPORTED" in result:
                return 0.95
            elif "CONTRADICTED" in result:
                return 0.05
            return 0.5
        except Exception as e:
            logger.warning(f"LLM entailment failed: {e}")
            return 0.5

    def _detect_conflict(self, claim: str, chunks: List[Chunk]) -> tuple:
        """
        Detect if evidence conflicts with claim

        Args:
            claim: Claim text
            chunks: Evidence chunks

        Returns:
            (conflict_detected: bool, conflicting_chunk: Optional[Chunk])
        """
        conflict_keywords = ["not", "never", "no", "exclude", "except", "cannot"]

        claim_has_negation = any(kw in claim.lower() for kw in conflict_keywords)

        for chunk in chunks:
            chunk_has_negation = any(
                kw in chunk.content.lower() for kw in conflict_keywords
            )

            # Conflict if one has negation and other doesn't, but same topic
            if claim_has_negation != chunk_has_negation:
                # Check topic overlap
                if self._bm25_overlap(claim, chunk.content) > 0.5:
                    return True, chunk

        return False, None

    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization"""
        # Remove punctuation and split
        text = re.sub(r"[^\w\s]", "", text.lower())
        tokens = text.split()

        # Remove stopwords
        stopwords = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
        }
        return [t for t in tokens if t and t not in stopwords and len(t) > 2]

    def _extract_phrases(self, text: str) -> List[str]:
        """Extract bigrams and trigrams"""
        tokens = self._tokenize(text)
        phrases = []

        # Bigrams
        for i in range(len(tokens) - 1):
            phrases.append(f"{tokens[i]} {tokens[i+1]}")

        # Trigrams
        for i in range(len(tokens) - 2):
            phrases.append(f"{tokens[i]} {tokens[i+1]} {tokens[i+2]}")

        return phrases

    def _generate_reasoning(
        self,
        overlap: float,
        semantic: float,
        nli: float,
        conflict: bool,
        num_evidence: int,
    ) -> str:
        """Generate human-readable reasoning"""
        parts = []

        if num_evidence == 0:
            return "No evidence found for this claim."

        parts.append(f"Based on {num_evidence} evidence chunk(s):")
        parts.append(f"- Keyword overlap: {overlap:.1%}")
        parts.append(f"- Semantic similarity: {semantic:.1%}")

        if nli > 0:
            parts.append(f"- Entailment: {nli:.1%}")

        if conflict:
            parts.append("- WARNING: Conflicting evidence detected")

        return " ".join(parts)


def example_usage():
    """Demonstrate support scorer"""

    print("=" * 70)
    print("SUPPORT SCORER EXAMPLES")
    print("=" * 70)

    scorer = SupportScorer(use_nli=False)

    # Sample claim and evidence
    claim = Claim(
        claim_id="claim_001",
        claim_text="Health insurance covers dental benefits",
        original_sentence="Health insurance covers dental benefits",
    )

    evidence_chunks = [
        Chunk(
            chunk_id="chunk_1",
            content="Our health insurance covers medical, dental, and vision benefits for all employees.",
            source="benefits.docx",
            relevance_score=0.95,
        ),
        Chunk(
            chunk_id="chunk_2",
            content="Dental coverage includes cleanings, fillings, and root canals.",
            source="benefits.docx",
            relevance_score=0.88,
        ),
    ]

    evidence_set = EvidenceSet(
        claim_id="claim_001",
        evidence_chunks=evidence_chunks,
        retrieval_scores=[0.95, 0.88],
        retrieval_method="test",
        num_retrieved=2,
    )

    print(f"\nClaim: {claim.claim_text}")
    print(f"Evidence: {evidence_set.num_retrieved} chunks found")
    print("-" * 70)

    score = scorer.score_support(claim, evidence_set)

    print(f"Overlap Score:     {score.overlap_score:.3f}")
    print(f"Semantic Score:    {score.semantic_score:.3f}")
    print(f"Final Support:     {score.final_support:.3f}")
    print(f"Conflict Detected: {score.conflict_detected}")
    print(f"Reasoning:         {score.reasoning}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    example_usage()
