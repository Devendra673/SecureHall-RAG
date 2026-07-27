# Citation Format Specification

This document specifies the canonical citation format used by the verification pipeline and web UI.

## Goals
- Provide compact, human-readable inline citations for answers
- Provide richer block citations for evidence viewers
- Ensure machine-readable JSON serialization for APIs
- Support multiple citation types (direct quote, paraphrase, inferred)

## Data Model (JSON)

A `Citation` object follows this JSON shape:

```json
{
  "claim_id": "claim-001",
  "evidence_chunk_id": "chunk-12",
  "evidence_text": "Employees are eligible for 15 days paid leave per year.",
  "source": "HR_Policy.pdf",
  "relevance_score": 0.92
}
```

- `claim_id` (string): Identifier of the claim this citation supports.
- `evidence_chunk_id` (string): Identifier of the retrieved chunk.
- `evidence_text` (string): Short text snippet from the chunk (ideally <= 300 chars).
- `source` (string): Document name or source id.
- `relevance_score` (float): 0-1 relevance returned by retriever/scorer.

## Human-Readable Formats

- Inline citation: `(HR_Policy.pdf, chunk: chunk-12, relevance=0.92)`
- Block citation: `Source: HR_Policy.pdf — chunk: chunk-12 — relevance: 0.92\n"Employees are eligible for 15 days paid leave per year."`

## Citation Types
- `direct_quote`: evidence_text is verbatim from source
- `paraphrase`: evidence_text is paraphrased but accurately reflects source
- `inferred`: evidence_text is an inferred summary (use sparingly)

## Best Practices
- Keep `evidence_text` short (<= 300 chars).
- Include multiple citations per claim when available and relevant.
- Use `relevance_score` to order citations in the UI.
- Use `SourceSpan` offsets for precise highlighting when available.

## Serialization Utilities
See `src/verification/citation_utils.py` for convenience functions:
- `citation_to_dict`, `citation_to_json`, `citation_from_dict`
- `format_inline_citation`, `format_block_citation`

## Examples
- Single inline citation in answer: "Employees receive paid leave (HR_Policy.pdf, chunk: chunk-12, relevance=0.92)."
- Evidence viewer entry:
```
Source: HR_Policy.pdf — chunk: chunk-12 — relevance: 0.92
"Employees are eligible for 15 days paid leave per year."
```

## Versioning
- Version: 1.0
- Date: 2026-05-28
- Author: Verification/UI Team
