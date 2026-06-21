"""
Task 4.2: Claim Extraction Module

Extracts NLP features and metadata from claims.
Identifies entities, claim types, predicates, temporal markers.

Author: Verification Engineering Team
Version: 1.0
"""

import sys
import re
from pathlib import Path
from typing import List, Optional, Dict
from dataclasses import dataclass

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.verification.data_structures import Claim, ClaimMetadata, ClaimType


class ClaimExtractor:
    """Extracts metadata from claims"""

    # Temporal markers
    TEMPORAL_MARKERS = [
        "when",
        "after",
        "before",
        "during",
        "while",
        "since",
        "until",
        "if",
        "once",
        "as soon as",
        "whenever",
        "immediately",
        "annually",
        "daily",
        "weekly",
        "monthly",
        "yearly",
        "at",
        "on",
        "in",
    ]

    # Claim type indicators
    PROCEDURAL_KEYWORDS = [
        "to",
        "how to",
        "process",
        "procedure",
        "step",
        "instructions",
        "instructions",
        "must",
        "should",
        "required",
        "need to",
    ]

    CONDITIONAL_KEYWORDS = [
        "if",
        "unless",
        "provided",
        "assuming",
        "in case",
        "in the event",
    ]

    POLICY_KEYWORDS = [
        "policy",
        "company",
        "employee",
        "benefits",
        "plan",
        "rule",
        "guideline",
        "requirement",
        "provision",
        "covered",
    ]

    def __init__(self):
        """Initialize extractor"""
        pass

    def extract_metadata(self, claim: Claim) -> ClaimMetadata:
        """
        Extract metadata from a claim

        Args:
            claim: Claim to extract from

        Returns:
            ClaimMetadata with extracted features
        """
        claim_text = claim.claim_text.lower()

        # Extract entities (basic NER)
        entities = self._extract_entities(claim.claim_text)

        # Determine claim type
        claim_type = self._classify_claim_type(claim_text)

        # Extract main predicate (verb/action)
        predicate = self._extract_predicate(claim.claim_text)

        # Extract temporal markers
        temporal_markers = self._extract_temporal_markers(claim_text)

        # Calculate complexity score
        complexity = self._calculate_complexity(claim.claim_text, claim_type)

        # Estimate LLM confidence (heuristic)
        llm_confidence = self._estimate_confidence(claim_text)

        return ClaimMetadata(
            claim_id=claim.claim_id,
            entities=entities,
            claim_type=claim_type,
            main_predicate=predicate,
            temporal_markers=temporal_markers,
            complexity_score=complexity,
            llm_confidence=llm_confidence,
        )

    def _extract_entities(self, text: str) -> List[str]:
        """Extract named entities (basic)"""
        entities = []

        # Capitalized words (basic NER)
        words = text.split()
        for word in words:
            # Remove punctuation
            clean_word = re.sub(r"[^\w]", "", word)

            # Check if capitalized (likely entity)
            if clean_word and clean_word[0].isupper() and len(clean_word) > 2:
                if clean_word not in entities:
                    entities.append(clean_word)

        # Known entities
        known_entities = [
            "health insurance",
            "pto",
            "dental",
            "vision",
            "retirement",
            "company",
            "employee",
            "benefits",
            "leave",
            "pay",
            "401k",
            "severance",
            "vacation",
            "holiday",
        ]

        text_lower = text.lower()
        for entity in known_entities:
            if entity in text_lower and entity not in entities:
                entities.append(entity)

        return entities[:10]  # Limit to 10 most important

    def _classify_claim_type(self, text: str) -> ClaimType:
        """Classify the type of claim"""

        # Check for procedural keywords
        for keyword in self.PROCEDURAL_KEYWORDS:
            if keyword in text:
                return ClaimType.PROCEDURAL

        # Check for conditional keywords
        for keyword in self.CONDITIONAL_KEYWORDS:
            if keyword in text:
                return ClaimType.CONDITIONAL

        # Check for policy references
        for keyword in self.POLICY_KEYWORDS:
            if keyword in text:
                return ClaimType.POLICY_REF

        # Default to factual
        return ClaimType.FACTUAL

    def _extract_predicate(self, text: str) -> Optional[str]:
        """Extract main predicate (verb/action)"""
        # Common verbs in policy documents
        verbs = [
            "provides",
            "offers",
            "covers",
            "includes",
            "requires",
            "allows",
            "grants",
            "gives",
            "receives",
            "gets",
            "must",
            "should",
            "may",
            "cannot",
            "can",
            "does",
            "is",
            "are",
            "will",
            "have",
            "has",
        ]

        text_lower = text.lower()
        for verb in verbs:
            if verb in text_lower:
                return verb

        return None

    def _extract_temporal_markers(self, text: str) -> List[str]:
        """Extract temporal markers"""
        markers = []

        for marker in self.TEMPORAL_MARKERS:
            if marker in text:
                if marker not in markers:
                    markers.append(marker)

        return markers

    def _calculate_complexity(self, text: str, claim_type: ClaimType) -> float:
        """Calculate complexity score (0-1)"""
        complexity = 0.5  # Start at medium

        # Length factor
        word_count = len(text.split())
        if word_count < 10:
            complexity -= 0.2
        elif word_count > 30:
            complexity += 0.2

        # Conditional adds complexity
        if claim_type == ClaimType.CONDITIONAL:
            complexity += 0.2

        # Multiple conjunctions add complexity
        conjunctions = len(re.findall(r"\b(and|or|but)\b", text, re.IGNORECASE))
        complexity += min(conjunctions * 0.1, 0.2)

        # Clamp to 0-1
        return max(0.0, min(1.0, complexity))

    def _estimate_confidence(self, text: str) -> float:
        """Estimate LLM confidence (heuristic) - Deprecated in Phase 3
        Confidence is now calculated accurately using NLI evaluation in AnswerAssembler.
        """
        return 1.0


def example_usage():
    """Demonstrate claim extractor"""

    print("=" * 70)
    print("CLAIM EXTRACTOR EXAMPLES")
    print("=" * 70)

    extractor = ClaimExtractor()

    # Create sample claims
    claims = [
        Claim(
            claim_id="claim_001",
            claim_text="Our health insurance covers medical, dental, and vision benefits.",
            original_sentence="Our health insurance covers medical, dental, and vision benefits.",
        ),
        Claim(
            claim_id="claim_002",
            claim_text="If you work for 5 years, you receive 8 weeks severance.",
            original_sentence="If you work for 5 years, you receive 8 weeks severance.",
        ),
        Claim(
            claim_id="claim_003",
            claim_text="To request PTO, you must submit a form 2 weeks before the date.",
            original_sentence="To request PTO, you must submit a form 2 weeks before the date.",
        ),
    ]

    for claim in claims:
        print(f"\nClaim: {claim.claim_text}")
        print("-" * 70)

        metadata = extractor.extract_metadata(claim)

        print(f"Entities:          {', '.join(metadata.entities)}")
        print(f"Type:              {metadata.claim_type.value}")
        print(f"Predicate:         {metadata.main_predicate}")
        print(
            f"Temporal Markers:  {', '.join(metadata.temporal_markers) if metadata.temporal_markers else 'None'}"
        )
        print(f"Complexity:        {metadata.complexity_score:.2f}")
        print(f"LLM Confidence:    {metadata.llm_confidence:.2f}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    example_usage()
