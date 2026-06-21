"""
Claim Verification & Hallucination Control - Core Data Structures (Phase 4)

Defines all data classes used throughout the verification pipeline.

Author: Verification Engineering Team
Version: 1.0
"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
from enum import Enum
import json


class ClaimType(Enum):
    """Classification of claim types"""

    FACTUAL = "factual"  # Statement of fact
    PROCEDURAL = "procedural"  # How to do something
    CONDITIONAL = "conditional"  # If/then statements
    POLICY_REF = "policy_ref"  # Reference to specific policy
    UNKNOWN = "unknown"


class SupportLevel(Enum):
    """Support level for claims"""

    SUPPORTED = "supported"  # High confidence evidence
    PARTIALLY_SUPPORTED = "partially_supported"  # Some evidence
    UNSUPPORTED = "unsupported"  # Little or no evidence
    CONFLICTING = "conflicting"  # Evidence contradicts claim


class VerificationDecision(Enum):
    """Final decision for claim"""

    ACCEPT = "accept"  # Include in final answer
    PARTIAL_ACCEPT = "partial_accept"  # Include with caveats
    REFUSE = "refuse"  # Exclude from final answer


@dataclass
class SourceSpan:
    """Location reference in original text"""

    start_pos: int
    end_pos: int
    text: str
    source_id: Optional[str] = None


@dataclass
class Claim:
    """Represents a single claim from LLM response"""

    claim_id: str
    claim_text: str
    original_sentence: str
    source_span: Optional[SourceSpan] = None
    context: Optional[str] = None
    sequence_order: int = 0

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "claim_id": self.claim_id,
            "claim_text": self.claim_text,
            "original_sentence": self.original_sentence,
            "context": self.context,
            "sequence_order": self.sequence_order,
        }


@dataclass
class ClaimMetadata:
    """Metadata extracted from a claim"""

    claim_id: str
    entities: List[str] = field(default_factory=list)
    claim_type: ClaimType = ClaimType.UNKNOWN
    main_predicate: Optional[str] = None
    temporal_markers: List[str] = field(default_factory=list)
    complexity_score: float = 0.5  # 0-1, higher = more complex
    llm_confidence: float = 0.5  # LLM's self-assessed confidence

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "claim_id": self.claim_id,
            "entities": self.entities,
            "claim_type": self.claim_type.value,
            "main_predicate": self.main_predicate,
            "temporal_markers": self.temporal_markers,
            "complexity_score": self.complexity_score,
            "llm_confidence": self.llm_confidence,
        }


@dataclass
class Chunk:
    """Retrieved evidence chunk"""

    chunk_id: str
    content: str
    source: str  # Document name
    relevance_score: float  # 0-1


@dataclass
class EvidenceSet:
    """All evidence for a single claim"""

    claim_id: str
    evidence_chunks: List[Chunk] = field(default_factory=list)
    retrieval_scores: List[float] = field(default_factory=list)
    retrieval_method: str = "dense"  # dense, sparse, hybrid
    num_retrieved: int = 0

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "claim_id": self.claim_id,
            "num_retrieved": self.num_retrieved,
            "retrieval_method": self.retrieval_method,
            "retrieval_scores": self.retrieval_scores,
        }


@dataclass
class SupportScore:
    """Support scoring for a claim"""

    claim_id: str
    overlap_score: float  # BM25-based
    semantic_score: float  # Embedding-based
    nli_score: float  # Natural Language Inference
    conflict_detected: bool = False
    conflict_evidence: Optional[Chunk] = None
    final_support: float = 0.5  # Aggregated
    reasoning: str = ""

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "claim_id": self.claim_id,
            "overlap_score": self.overlap_score,
            "semantic_score": self.semantic_score,
            "nli_score": self.nli_score,
            "conflict_detected": self.conflict_detected,
            "final_support": self.final_support,
            "reasoning": self.reasoning,
        }


@dataclass
class ThresholdConfig:
    """Configuration for verification thresholds"""

    high_threshold: float = 0.8  # SUPPORTED
    medium_threshold: float = 0.5  # PARTIALLY_SUPPORTED
    low_threshold: float = 0.3  # UNSUPPORTED
    conflict_weight: float = 0.5  # How much to penalize conflicts
    allow_partial: bool = True  # Allow partial acceptance


@dataclass
class Citation:
    """Citation reference for a claim"""

    claim_id: str
    evidence_chunk_id: str
    evidence_text: str
    source: str
    relevance_score: float
    span_start: Optional[int] = None
    span_end: Optional[int] = None

    def to_dict(self) -> Dict:
        return {
            "claim_id": self.claim_id,
            "evidence_chunk_id": self.evidence_chunk_id,
            "evidence_text": self.evidence_text,
            "source": self.source,
            "relevance_score": self.relevance_score,
            "span_start": self.span_start,
            "span_end": self.span_end,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Citation":
        return cls(
            claim_id=data.get("claim_id"),
            evidence_chunk_id=data.get("evidence_chunk_id"),
            evidence_text=data.get("evidence_text"),
            source=data.get("source"),
            relevance_score=float(data.get("relevance_score", 0.0)),
            span_start=data.get("span_start"),
            span_end=data.get("span_end"),
        )


@dataclass
class VerifiedClaim:
    """Claim after verification"""

    claim_id: str
    claim_text: str
    original_sentence: str
    support_score: float
    support_level: SupportLevel
    decision: VerificationDecision
    evidence_citations: List[Citation] = field(default_factory=list)
    reasoning: str = ""

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "claim_id": self.claim_id,
            "claim_text": self.claim_text,
            "support_score": self.support_score,
            "support_level": self.support_level.value,
            "decision": self.decision.value,
            "num_citations": len(self.evidence_citations),
        }


@dataclass
class VerifiedAnswer:
    """Final verified answer"""

    original_answer: str
    verified_answer: str
    claims_breakdown: List[VerifiedClaim] = field(default_factory=list)
    total_support_score: float = 0.0  # Average
    accepted_count: int = 0
    rejected_count: int = 0
    partial_count: int = 0
    evidence_citations: Dict[str, List[Citation]] = field(default_factory=dict)
    processing_time_ms: float = 0.0

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "original_answer_length": len(self.original_answer),
            "verified_answer_length": len(self.verified_answer),
            "total_support_score": self.total_support_score,
            "accepted_count": self.accepted_count,
            "rejected_count": self.rejected_count,
            "partial_count": self.partial_count,
            "total_claims": len(self.claims_breakdown),
            "processing_time_ms": self.processing_time_ms,
        }


@dataclass
class RefusalMessage:
    """Refusal message for unsupported claims"""

    message: str
    reason: str  # Why refusal occurred
    available_partial: Optional[str] = None  # What IS supported
    suggestions: List[str] = field(default_factory=list)  # Suggestions for user
    support_score: float = 0.0

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "message": self.message,
            "reason": self.reason,
            "has_partial": self.available_partial is not None,
            "num_suggestions": len(self.suggestions),
            "support_score": self.support_score,
        }


@dataclass
class PrecisionRecallAnalysis:
    """Precision/recall analysis results"""

    threshold_configs: List[float] = field(default_factory=list)
    precision_scores: List[float] = field(default_factory=list)
    recall_scores: List[float] = field(default_factory=list)
    f1_scores: List[float] = field(default_factory=list)
    recommended_threshold: float = 0.75
    test_cases_count: int = 0

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "threshold_configs": self.threshold_configs,
            "precision_scores": self.precision_scores,
            "recall_scores": self.recall_scores,
            "f1_scores": self.f1_scores,
            "recommended_threshold": self.recommended_threshold,
            "test_cases_count": self.test_cases_count,
        }


@dataclass
class VerificationMetrics:
    """Overall verification metrics"""

    hallucination_rate: float  # False positives
    precision: float  # Correct accepts / all accepts
    recall: float  # Correct accepts / should accept
    f1_score: float  # Harmonic mean
    accuracy: float  # Overall accuracy
    latency_ms: float  # Average latency
    memory_mb: float  # Memory usage

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class VerificationResponse:
    """Standardized verification API response model."""

    answer_text: str
    claims: List[Dict]
    citations: List[Dict]
    evidence_snippets: Dict[str, str]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "answer_text": self.answer_text,
            "claims": self.claims,
            "citations": self.citations,
            "evidence_snippets": self.evidence_snippets,
            "metadata": self.metadata,
        }
