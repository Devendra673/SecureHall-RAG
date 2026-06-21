"""
Task 4.1: Claim Splitter Algorithm

Breaks LLM responses into atomic, verifiable claims.
Handles sentence boundaries, clauses, and logical breaks.

Author: Verification Engineering Team
Version: 1.0
"""

import re
import sys
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.verification.data_structures import Claim, SourceSpan


class ClaimSplitter:
    """Splits LLM responses into atomic claims"""

    # Regex patterns for sentence boundaries
    SENTENCE_PATTERN = r"(?<=[.!?])\s+(?=[A-Z])|(?<=[.!?])\s*$"

    # Patterns for clause boundaries
    CLAUSE_CONNECTORS = [
        r";\s*",  # Semicolon
        r",\s+(?:and|but|or|also|however|therefore|thus)\s+",  # Conjunctions
        r",\s+(?:which|that|where|when|if)\s+",  # Relative clauses
    ]

    def __init__(self):
        """Initialize splitter"""
        self.claim_counter = 0

    def split_into_claims(self, text: str) -> List[Claim]:
        """
        Split text into atomic claims

        Args:
            text: LLM response to split

        Returns:
            List of Claim objects
        """
        self.claim_counter = 0
        claims = []

        # Step 1: Split by sentences
        sentences = self._split_sentences(text)

        # Step 2: Further split complex sentences into clauses
        for sent_idx, sentence in enumerate(sentences):
            clauses = self._split_into_clauses(sentence)

            for clause_idx, clause in enumerate(clauses):
                claim_text = clause.strip()

                if len(claim_text) < 5:  # Skip very short fragments
                    continue

                claim = Claim(
                    claim_id=f"claim_{self.claim_counter:03d}",
                    claim_text=claim_text,
                    original_sentence=sentence,
                    source_span=self._find_span(text, claim_text),
                    context=self._extract_context(text, sentence),
                    sequence_order=self.claim_counter,
                )

                claims.append(claim)
                self.claim_counter += 1

        return claims

    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences"""
        sentences = re.split(self.SENTENCE_PATTERN, text)
        return [s.strip() for s in sentences if s.strip()]

    def _split_into_clauses(self, sentence: str) -> List[str]:
        """Split complex sentence into clauses"""
        # Check if sentence has multiple clauses
        clause_count = 0
        for pattern in self.CLAUSE_CONNECTORS:
            clause_count += len(re.findall(pattern, sentence, re.IGNORECASE))

        if clause_count == 0:
            # Single clause - return as is
            return [sentence]

        # Split by clause connectors
        clauses = [sentence]
        for pattern in self.CLAUSE_CONNECTORS:
            new_clauses = []
            for clause in clauses:
                parts = re.split(pattern, clause, flags=re.IGNORECASE)
                new_clauses.extend(parts)
            clauses = new_clauses

        # Filter empty clauses
        clauses = [c.strip() for c in clauses if c.strip()]

        return clauses

    def _find_span(self, full_text: str, claim_text: str) -> Optional[SourceSpan]:
        """Find position of claim in original text"""
        # Normalize for comparison
        normalized_text = full_text.lower()
        normalized_claim = claim_text.lower()

        start = normalized_text.find(normalized_claim)
        if start == -1:
            return None

        end = start + len(claim_text)
        return SourceSpan(start_pos=start, end_pos=end, text=full_text[start:end])

    def _extract_context(self, full_text: str, sentence: str) -> Optional[str]:
        """Extract surrounding context"""
        sentences = self._split_sentences(full_text)

        try:
            idx = sentences.index(sentence)
            context_sentences = []

            # Include previous and next sentence if available
            if idx > 0:
                context_sentences.append(sentences[idx - 1])

            context_sentences.append(sentence)

            if idx < len(sentences) - 1:
                context_sentences.append(sentences[idx + 1])

            return " ".join(context_sentences)
        except (ValueError, IndexError):
            return sentence

    def get_statistics(self) -> dict:
        """Get splitter statistics"""
        return {
            "claims_generated": self.claim_counter,
        }


def example_usage():
    """Demonstrate claim splitter"""

    print("=" * 70)
    print("CLAIM SPLITTER EXAMPLES")
    print("=" * 70)

    splitter = ClaimSplitter()

    # Example 1: Simple answer
    print("\n1. SIMPLE ANSWER:")
    print("-" * 70)
    text1 = "Our health insurance covers medical, dental, and vision benefits. Employees receive 20 days of PTO annually. The company matches retirement contributions up to 6%."
    print(f"Input: {text1}\n")

    claims1 = splitter.split_into_claims(text1)
    for claim in claims1:
        print(f"  [{claim.claim_id}] {claim.claim_text}")

    # Example 2: Complex answer with conditionals
    print("\n\n2. COMPLEX ANSWER WITH CONDITIONALS:")
    print("-" * 70)
    text2 = "If you have been employed for more than 5 years, you receive 8 weeks severance. However, if you are terminated for cause, you may receive no severance. For voluntary resignations, it depends on notice period; if you give 2 weeks notice, you get 2 weeks paid leave."
    print(f"Input: {text2}\n")

    claims2 = splitter.split_into_claims(text2)
    for claim in claims2:
        print(f"  [{claim.claim_id}] {claim.claim_text}")

    # Example 3: Multi-sentence structured answer
    print("\n\n3. STRUCTURED ANSWER:")
    print("-" * 70)
    text3 = "The benefits package includes: (1) Health insurance covering medical, dental, and vision. (2) Paid time off: 20 days vacation, 10 company holidays. (3) Retirement plan with 6% company match. All full-time employees are eligible on day one."
    print(f"Input: {text3}\n")

    claims3 = splitter.split_into_claims(text3)
    for claim in claims3:
        print(f"  [{claim.claim_id}] {claim.claim_text}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    example_usage()
