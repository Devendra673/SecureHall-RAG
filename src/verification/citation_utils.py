"""
Citation utilities for serialization, formatting, and examples.
"""

from typing import Dict, Any, Optional
from .data_structures import Citation
import json


def citation_to_dict(c: Citation) -> Dict[str, Any]:
    return {
        "claim_id": c.claim_id,
        "evidence_chunk_id": c.evidence_chunk_id,
        "evidence_text": c.evidence_text,
        "source": c.source,
        "relevance_score": c.relevance_score,
    }


def citation_to_json(c: Citation) -> str:
    return json.dumps(citation_to_dict(c), ensure_ascii=False)


def citation_from_dict(d: Dict[str, Any]) -> Citation:
    return Citation(
        claim_id=d.get("claim_id", ""),
        evidence_chunk_id=d.get("evidence_chunk_id", ""),
        evidence_text=d.get("evidence_text", ""),
        source=d.get("source", ""),
        relevance_score=float(d.get("relevance_score", 0.0)),
    )


def format_inline_citation(c: Citation) -> str:
    """Return an inline human-readable citation string.

    Examples:
    - (CompanyPolicy: HR_Policy.pdf, chunk 12, relevance=0.87)
    - [HR Policy — Section 2.1] (relevance=0.87)
    """
    src = c.source if c.source else "unknown source"
    return f"({src}, chunk: {c.evidence_chunk_id}, relevance={c.relevance_score:.2f})"


def format_block_citation(c: Citation) -> str:
    """Return a block citation useful for UI displays with snippet."""
    header = f"Source: {c.source} — chunk: {c.evidence_chunk_id} — relevance: {c.relevance_score:.2f}"
    snippet = c.evidence_text
    return f'{header}\n"{snippet}"'


# Example usage helper
def example_citation() -> str:
    c = Citation(
        claim_id="claim-001",
        evidence_chunk_id="chunk-12",
        evidence_text="Employees are eligible for 15 days paid leave per year.",
        source="HR_Policy.pdf",
        relevance_score=0.92,
    )
    return format_block_citation(c)
