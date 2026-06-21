"""
Task 4.7: Abstain/Refusal Message Generator

Generates clear, helpful refusal messages when claims cannot be verified.
Explains why claims were rejected and suggests next steps.

Author: Verification Engineering Team
Version: 1.0
"""

import sys
from pathlib import Path
from typing import List, Optional
from enum import Enum

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.verification.data_structures import (
    VerifiedClaim,
    VerificationDecision,
    SupportLevel,
)


class RefusalReason(Enum):
    """Reasons for refusing claims"""

    INSUFFICIENT_EVIDENCE = "Insufficient evidence in knowledge base"
    CONFLICTING_EVIDENCE = "Evidence conflicts with claim"
    UNCERTAIN = "Claim has too much uncertainty"
    OUT_OF_SCOPE = "Claim appears to be outside scope of documents"
    MULTIPLE_INTERPRETATIONS = "Claim has multiple possible interpretations"


class RefusalMessage:
    """Generated refusal message with reasoning"""

    def __init__(
        self,
        claim_text: str,
        reason: RefusalReason,
        confidence: float,
        suggestion: Optional[str] = None,
    ):
        """
        Initialize refusal message

        Args:
            claim_text: The claim being refused
            reason: Reason for refusal
            confidence: Confidence in refusal decision (0-1)
            suggestion: Optional suggestion for how to verify claim
        """
        self.claim_text = claim_text
        self.reason = reason
        self.confidence = confidence
        self.suggestion = suggestion


class RefusalMessageGenerator:
    """Generates refusal messages for unverified claims"""

    def __init__(self):
        """Initialize generator"""
        pass

    def generate_refusal_message(
        self,
        claim: VerifiedClaim,
    ) -> RefusalMessage:
        """
        Generate refusal message for a claim

        Args:
            claim: Claim that was refused

        Returns:
            RefusalMessage with explanation and suggestions
        """
        # Determine refusal reason
        reason = self._determine_reason(claim)

        # Generate suggestion
        suggestion = self._generate_suggestion(claim, reason)

        # Calculate confidence
        confidence = (
            1.0 - claim.support_score
        )  # Higher confidence in refusal if low score

        return RefusalMessage(
            claim_text=claim.claim_text,
            reason=reason,
            confidence=confidence,
            suggestion=suggestion,
        )

    def generate_refusal_messages_batch(
        self,
        claims: List[VerifiedClaim],
    ) -> List[RefusalMessage]:
        """
        Generate refusal messages for multiple claims

        Args:
            claims: List of refused claims

        Returns:
            List of RefusalMessage objects
        """
        return [self.generate_refusal_message(claim) for claim in claims]

    def format_refusal_message_text(
        self,
        message: RefusalMessage,
    ) -> str:
        """
        Format message into human-readable text

        Args:
            message: RefusalMessage to format

        Returns:
            Formatted message string
        """
        lines = []

        lines.append(f'❌ Cannot verify: "{message.claim_text}"')
        lines.append("")
        lines.append(f"Reason: {message.reason.value}")
        lines.append(f"Confidence: {message.confidence:.0%}")
        lines.append("")

        if message.suggestion:
            lines.append(f"💡 Suggestion: {message.suggestion}")
        else:
            lines.append(
                "💡 Suggestion: Verify this claim independently or consult primary sources."
            )

        return "\n".join(lines)

    def format_batch_refusal_text(
        self,
        messages: List[RefusalMessage],
    ) -> str:
        """
        Format multiple refusal messages

        Args:
            messages: List of RefusalMessage objects

        Returns:
            Combined formatted text
        """
        if not messages:
            return "All claims verified successfully."

        lines = []
        lines.append(f"Unable to verify {len(messages)} claim(s):\n")

        for msg in messages:
            lines.append(self.format_refusal_message_text(msg))
            lines.append("")

        return "\n".join(lines)

    def _determine_reason(self, claim: VerifiedClaim) -> RefusalReason:
        """Determine reason for refusal"""
        # Check for conflicting evidence
        if "Conflict" in claim.reasoning or "conflicting" in claim.reasoning.lower():
            return RefusalReason.CONFLICTING_EVIDENCE

        # Check support level
        if claim.support_score < 0.1:
            return RefusalReason.OUT_OF_SCOPE
        elif claim.support_score < 0.3:
            return RefusalReason.INSUFFICIENT_EVIDENCE
        else:
            return RefusalReason.UNCERTAIN

    def _generate_suggestion(
        self,
        claim: VerifiedClaim,
        reason: RefusalReason,
    ) -> str:
        """Generate suggestion for verification"""
        suggestions = {
            RefusalReason.INSUFFICIENT_EVIDENCE: f"Try searching for more specific documentation about '{self._extract_key_terms(claim.claim_text)}'",
            RefusalReason.CONFLICTING_EVIDENCE: f"Review conflicting sources to resolve the contradiction about '{self._extract_key_terms(claim.claim_text)}'",
            RefusalReason.UNCERTAIN: f"Request clarification or additional context for: {claim.claim_text}",
            RefusalReason.OUT_OF_SCOPE: f"This information may not be covered in the available documents. Consider external sources.",
            RefusalReason.MULTIPLE_INTERPRETATIONS: f"The claim '{claim.claim_text}' can be interpreted multiple ways. Please rephrase for clarity.",
        }

        return suggestions.get(reason, "Consult primary sources for verification.")

    def _extract_key_terms(self, text: str) -> str:
        """Extract key terms from claim"""
        # Get important nouns/entities
        important_words = [w for w in text.split() if len(w) > 4]
        return " ".join(important_words[:3])


class AbstainMessage:
    """Message indicating system cannot make a determination"""

    def __init__(self, reason: str, confidence: float):
        """
        Initialize abstain message

        Args:
            reason: Reason for abstaining
            confidence: How confident we are in this abstention
        """
        self.reason = reason
        self.confidence = confidence

    def to_text(self) -> str:
        """Convert to text"""
        return f"⚠️ Cannot determine: {self.reason} (Confidence: {self.confidence:.0%})"


class AbstainMessageGenerator:
    """Generates abstention messages"""

    def __init__(self):
        """Initialize generator"""
        pass

    def generate_abstain_message(
        self,
        issue: str,
        confidence: float = 0.5,
    ) -> AbstainMessage:
        """Generate abstention message"""
        return AbstainMessage(issue, confidence)


def example_usage():
    """Demonstrate refusal message generator"""

    print("=" * 70)
    print("REFUSAL MESSAGE GENERATOR EXAMPLES")
    print("=" * 70)

    generator = RefusalMessageGenerator()

    # Sample refused claims
    claims = [
        VerifiedClaim(
            claim_id="claim_1",
            claim_text="The company offers free gym membership",
            support_score=0.15,
            support_level=SupportLevel.UNSUPPORTED,
            decision=VerificationDecision.REFUSE,
        ),
        VerifiedClaim(
            claim_id="claim_2",
            claim_text="Remote work is allowed after 2 years with company",
            support_score=0.45,
            support_level=SupportLevel.PARTIALLY_SUPPORTED,
            decision=VerificationDecision.REFUSE,
        ),
    ]

    messages = generator.generate_refusal_messages_batch(claims)

    print("\nIndividual Refusal Messages:")
    print("-" * 70)

    for msg in messages:
        formatted = generator.format_refusal_message_text(msg)
        print(formatted)
        print()

    print("\nBatch Refusal Summary:")
    print("-" * 70)
    batch_text = generator.format_batch_refusal_text(messages)
    print(batch_text)

    print("\n" + "=" * 70)


if __name__ == "__main__":
    example_usage()
