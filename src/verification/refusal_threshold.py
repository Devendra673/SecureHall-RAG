"""
Task 4.5: Refusal Threshold Logic

Determines when to refuse or abstain from claims based on support scores.
Implements configurable thresholds for accept/partial/refuse decisions.

Author: Verification Engineering Team
Version: 1.0
"""

import sys
from pathlib import Path
from typing import List

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.verification.data_structures import (
    SupportScore,
    ThresholdConfig,
    SupportLevel,
    VerificationDecision,
)


class RefusalThresholdEngine:
    """Determines verification decisions based on thresholds"""

    def __init__(self, config: ThresholdConfig = None):
        """
        Initialize threshold engine

        Args:
            config: Threshold configuration (uses defaults if None)
        """
        self.config = config or ThresholdConfig()

    def make_decision(self, score: SupportScore) -> tuple:
        """
        Make verification decision for a score

        Args:
            score: Support score for a claim

        Returns:
            (support_level: SupportLevel, decision: VerificationDecision)
        """
        # Adjust score for conflicts
        final_score = score.final_support
        if score.conflict_detected:
            final_score *= 1 - self.config.conflict_weight

        # Determine support level
        if final_score >= self.config.high_threshold:
            support_level = SupportLevel.SUPPORTED
        elif final_score >= self.config.medium_threshold:
            support_level = SupportLevel.PARTIALLY_SUPPORTED
        elif final_score >= self.config.low_threshold:
            support_level = SupportLevel.UNSUPPORTED
        else:
            support_level = SupportLevel.UNSUPPORTED

        # Handle conflicts
        if score.conflict_detected:
            support_level = SupportLevel.CONFLICTING

        # Make decision
        if support_level == SupportLevel.SUPPORTED:
            decision = VerificationDecision.ACCEPT
        elif support_level == SupportLevel.PARTIALLY_SUPPORTED:
            if self.config.allow_partial:
                decision = VerificationDecision.PARTIAL_ACCEPT
            else:
                decision = VerificationDecision.REFUSE
        else:
            decision = VerificationDecision.REFUSE

        return support_level, decision

    def make_decisions_batch(
        self,
        scores: List[SupportScore],
    ) -> List[tuple]:
        """
        Make decisions for multiple scores

        Args:
            scores: List of support scores

        Returns:
            List of (support_level, decision) tuples
        """
        return [self.make_decision(score) for score in scores]

    def get_recommendation(self) -> str:
        """Get recommendation for threshold configuration"""
        if self.config.high_threshold >= 0.8:
            return "Conservative: High bar for acceptance, few false positives"
        elif self.config.high_threshold >= 0.7:
            return "Balanced: Middle ground between acceptance and caution"
        else:
            return "Permissive: Low bar for acceptance, more false positives likely"


class ThresholdConfigurations:
    """Pre-defined threshold configurations"""

    # Conservative: Avoid false positives, accept only strong claims
    CONSERVATIVE = ThresholdConfig(
        high_threshold=0.85,
        medium_threshold=0.65,
        low_threshold=0.4,
        conflict_weight=0.8,
        allow_partial=False,
    )

    # Balanced: Middle ground
    BALANCED = ThresholdConfig(
        high_threshold=0.75,
        medium_threshold=0.5,
        low_threshold=0.3,
        conflict_weight=0.5,
        allow_partial=True,
    )

    # Permissive: Accept more claims, higher false positive rate
    PERMISSIVE = ThresholdConfig(
        high_threshold=0.6,
        medium_threshold=0.4,
        low_threshold=0.2,
        conflict_weight=0.3,
        allow_partial=True,
    )

    # High Recall: Accept as many correct claims as possible
    HIGH_RECALL = ThresholdConfig(
        high_threshold=0.5,
        medium_threshold=0.3,
        low_threshold=0.1,
        conflict_weight=0.2,
        allow_partial=True,
    )

    @staticmethod
    def get_all() -> dict:
        """Get all configurations"""
        return {
            "conservative": ThresholdConfigurations.CONSERVATIVE,
            "balanced": ThresholdConfigurations.BALANCED,
            "permissive": ThresholdConfigurations.PERMISSIVE,
            "high_recall": ThresholdConfigurations.HIGH_RECALL,
        }


def example_usage():
    """Demonstrate refusal threshold logic"""

    print("=" * 70)
    print("REFUSAL THRESHOLD ENGINE EXAMPLES")
    print("=" * 70)

    # Create sample scores
    scores = [
        SupportScore(
            claim_id="claim_1",
            overlap_score=0.95,
            semantic_score=0.92,
            nli_score=0.90,
            conflict_detected=False,
            final_support=0.92,
            reasoning="Strong support",
        ),
        SupportScore(
            claim_id="claim_2",
            overlap_score=0.65,
            semantic_score=0.60,
            nli_score=0.62,
            conflict_detected=False,
            final_support=0.62,
            reasoning="Partial support",
        ),
        SupportScore(
            claim_id="claim_3",
            overlap_score=0.25,
            semantic_score=0.20,
            nli_score=0.15,
            conflict_detected=False,
            final_support=0.20,
            reasoning="Minimal support",
        ),
    ]

    # Test different threshold configurations
    configs = ThresholdConfigurations.get_all()

    for config_name, config in configs.items():
        print(f"\n{config_name.upper()} CONFIGURATION")
        print("-" * 70)
        print(f"High Threshold:    {config.high_threshold}")
        print(f"Medium Threshold:  {config.medium_threshold}")
        print(f"Low Threshold:     {config.low_threshold}")
        print(f"Allow Partial:     {config.allow_partial}")

        engine = RefusalThresholdEngine(config)
        print(f"Recommendation:    {engine.get_recommendation()}")

        print("\nDecisions:")
        for score in scores:
            support_level, decision = engine.make_decision(score)
            print(
                f"  {score.claim_id}: {support_level.value} → {decision.value} (score: {score.final_support:.2f})"
            )

    print("\n" + "=" * 70)


if __name__ == "__main__":
    example_usage()
