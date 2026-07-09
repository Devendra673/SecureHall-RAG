"""
Task 4.6: Answer Assembler

Builds final verified answers from accepted claims with citations.
Preserves original structure where possible.

Author: Verification Engineering Team
Version: 1.0
"""

import sys
import time
from pathlib import Path
from typing import List, Dict, Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.verification.data_structures import (
    Claim,
    SupportScore,
    VerificationDecision,
    SupportLevel,
    Citation,
    VerifiedClaim,
    VerifiedAnswer,
    EvidenceSet,
)


class AnswerAssembler:
    """Assembles verified answers from claims and scores"""

    def __init__(self):
        """Initialize assembler"""
        pass

    def assemble_answer(
        self,
        original_answer: str,
        claims: List[Claim],
        scores: List[SupportScore],
        decisions: List[tuple],  # List of (support_level, decision) tuples
        evidence_sets: Dict[str, EvidenceSet],
    ) -> VerifiedAnswer:
        """
        Assemble verified answer from components

        Args:
            original_answer: Original LLM response
            claims: List of claims extracted from answer
            scores: List of support scores for each claim
            decisions: List of verification decisions
            evidence_sets: Evidence sets for each claim

        Returns:
            VerifiedAnswer with verified claims and citations
        """
        start_time = time.time()

        verified_claims = []
        accepted_count = 0
        rejected_count = 0
        partial_count = 0
        all_citations: Dict[str, List[Citation]] = {}

        # Build verified claims
        for claim, score, (support_level, decision), evidence_set in zip(
            claims, scores, decisions, evidence_sets.values()
        ):
            # Generate citations
            citations = self._generate_citations(claim, evidence_set, score)
            all_citations[claim.claim_id] = citations

            # Create verified claim
            verified_claim = VerifiedClaim(
                claim_id=claim.claim_id,
                claim_text=claim.claim_text,
                original_sentence=claim.original_sentence,
                support_score=score.final_support,
                support_level=support_level,
                decision=decision,
                evidence_citations=citations,
                reasoning=score.reasoning,
            )

            verified_claims.append(verified_claim)

            # Count decisions
            if decision == VerificationDecision.ACCEPT:
                accepted_count += 1
            elif decision == VerificationDecision.PARTIAL_ACCEPT:
                partial_count += 1
            else:
                rejected_count += 1

        # Assemble verified answer
        verified_answer_text = self._build_verified_answer_text(
            original_answer, verified_claims
        )

        # Calculate metrics: True Confidence Metric (Phase 3)
        # Calculate confidence based on the ratio of supported claims to total claims
        total_support = (
            (accepted_count + 0.5 * partial_count) / len(scores)
            if scores
            else 0.0
        )

        processing_time = (time.time() - start_time) * 1000  # Convert to ms

        return VerifiedAnswer(
            original_answer=original_answer,
            verified_answer=verified_answer_text,
            claims_breakdown=verified_claims,
            total_support_score=total_support,
            accepted_count=accepted_count,
            rejected_count=rejected_count,
            partial_count=partial_count,
            evidence_citations=all_citations,
            processing_time_ms=processing_time,
        )

    def _generate_citations(
        self,
        claim: Claim,
        evidence_set: EvidenceSet,
        score: SupportScore,
    ) -> List[Citation]:
        """Generate citations for a claim"""
        citations = []

        for idx, chunk in enumerate(evidence_set.evidence_chunks):
            # Attempt to find an exact span for the claim in the chunk for highlighting
            content_lower = chunk.content.lower()
            claim_lower = claim.claim_text.lower()
            span_start = None
            span_end = None
            if claim_lower in content_lower:
                span_start = content_lower.index(claim_lower)
                span_end = span_start + len(claim_lower)

            # Extract surrounding context for UI (approx 200 chars)
            snippet = self._extract_surrounding_context(
                chunk.content, span_start, span_end
            )

            # Per-citation confidence combines chunk relevance and overall claim support
            citation_confidence = float(chunk.relevance_score) * float(
                score.final_support
            )

            citation = Citation(
                claim_id=claim.claim_id,
                evidence_chunk_id=chunk.chunk_id,
                evidence_text=snippet,
                source=chunk.source,
                relevance_score=chunk.relevance_score,
                span_start=span_start,
                span_end=span_end,
            )
            # attach computed confidence in reasoning field if available
            citation_confidence = round(citation_confidence, 4)
            citations.append(citation)

        return citations

    def _build_verified_answer_text(
        self,
        original_answer: str,
        verified_claims: List[VerifiedClaim],
    ) -> str:
        """
        Build the final answer.

        Strategy: Redact claims that are explicitly rejected to mitigate hallucination.
        Append a compact verification note for any partial support.
        """
        total = len(verified_claims)
        answer = original_answer.strip()

        # Hallucination Mitigation: Redact or warn depending on score
        redacted_count = 0
        warned_count = 0
        flagged_count = 0

        for c in verified_claims:
            if c.decision == VerificationDecision.ACCEPT:
                continue

            score = c.support_score

            if score >= 0.65:
                continue
            elif score >= 0.40:
                replacement = c.original_sentence.strip() + " ⚠️"
                warned_count += 1
            elif score >= 0.25:
                replacement = c.original_sentence.strip() + " 🔴 *[Low confidence — verify directly]*"
                flagged_count += 1
            else:
                replacement = "[REDACTED: Unsupported/Contradicted Claim]"
                redacted_count += 1

            if c.original_sentence and c.original_sentence in answer:
                answer = answer.replace(c.original_sentence, replacement)
            elif c.claim_text and c.claim_text in answer:
                answer = answer.replace(c.claim_text, replacement)

        # Append a small note only when there are unverified, low confidence, or redacted claims
        notes = []
        if warned_count:
            notes.append(f"⚠️ {warned_count} claim(s) only partially supported by the documents.")
        if flagged_count:
            notes.append(f"🔴 {flagged_count} claim(s) verified with low confidence.")
        if redacted_count:
            notes.append(f"🚨 {redacted_count} unsupported claim(s) redacted to prevent hallucination.")

        if notes:
            answer = answer + "\n\n" + "  \n".join(notes)

        return answer

    def _format_citations(self, claim: VerifiedClaim) -> str:
        """Format citations for display"""
        if not claim.evidence_citations:
            return ""

        sources = [f"{c.source}" for c in claim.evidence_citations[:2]]
        if len(claim.evidence_citations) > 2:
            sources.append(f"+{len(claim.evidence_citations) - 2} more")

        return f" [Sources: {', '.join(sources)}]"

    def _extract_surrounding_context(
        self, text: str, start: Optional[int], end: Optional[int], window: int = 200
    ) -> str:
        """Return a snippet around the span (or start of text) trimmed to window size."""
        if start is None or end is None:
            snippet = text[:window]
            return snippet if len(text) <= window else snippet + "..."

        # Bound the window around the span
        text_len = len(text)
        left = max(0, start - window // 2)
        right = min(text_len, end + window // 2)

        snippet = text[left:right]
        if left > 0:
            snippet = "..." + snippet
        if right < text_len:
            snippet = snippet + "..."
        return snippet

    def get_statistics(self) -> dict:
        """Get assembler statistics"""
        return {
            "assembler_version": "1.0",
        }


def example_usage():
    """Demonstrate answer assembler"""

    print("=" * 70)
    print("ANSWER ASSEMBLER EXAMPLES")
    print("=" * 70)

    assembler = AnswerAssembler()

    # Sample verified answer
    from src.verification.data_structures import Chunk

    original = "Health insurance covers dental. We provide 20 days PTO. All employees get matching 401k."

    claims = [
        Claim(
            claim_id="claim_1",
            claim_text="Health insurance covers dental",
            original_sentence="Health insurance covers dental.",
        ),
        Claim(
            claim_id="claim_2",
            claim_text="20 days PTO provided",
            original_sentence="We provide 20 days PTO.",
        ),
    ]

    scores = [
        SupportScore(
            claim_id="claim_1",
            overlap_score=0.95,
            semantic_score=0.92,
            nli_score=0.90,
            final_support=0.92,
        ),
        SupportScore(
            claim_id="claim_2",
            overlap_score=0.85,
            semantic_score=0.80,
            nli_score=0.82,
            final_support=0.82,
        ),
    ]

    decisions = [
        (SupportLevel.SUPPORTED, VerificationDecision.ACCEPT),
        (SupportLevel.SUPPORTED, VerificationDecision.ACCEPT),
    ]

    evidence_sets = {
        "claim_1": EvidenceSet(
            claim_id="claim_1",
            evidence_chunks=[
                Chunk(
                    chunk_id="e1",
                    content="Health insurance covers medical, dental, and vision",
                    source="benefits.docx",
                    relevance_score=0.95,
                )
            ],
        ),
        "claim_2": EvidenceSet(
            claim_id="claim_2",
            evidence_chunks=[
                Chunk(
                    chunk_id="e2",
                    content="Full-time employees receive 20 days PTO annually",
                    source="policies.docx",
                    relevance_score=0.85,
                )
            ],
        ),
    }

    verified = assembler.assemble_answer(
        original, claims, scores, decisions, evidence_sets
    )

    print(f"Original Answer:\n{verified.original_answer}\n")
    print(f"Verified Answer:\n{verified.verified_answer}\n")
    print(f"Accepted: {verified.accepted_count}")
    print(f"Rejected: {verified.rejected_count}")
    print(f"Processing Time: {verified.processing_time_ms:.1f}ms")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    example_usage()
