# Citation Specification

This document specifies the standardized `Citation` format used across the verification pipeline and UI.

## Data Model

- `claim_id` (string): Identifier of the claim this citation supports.
- `evidence_chunk_id` (string): Identifier of the retrieved chunk/document segment.
- `evidence_text` (string): Short text snippet used as the evidence excerpt.
- `source` (string): Human-readable source name (filename or doc id).
- `relevance_score` (float): [0.0-1.0] score indicating retrieval/relevance strength.
- `span_start` (int, optional): Character offset where the snippet starts in original chunk.
- `span_end` (int, optional): Character offset where the snippet ends in original chunk.

Example JSON:

```json
{
  "claim_id": "claim-001",
  "evidence_chunk_id": "chunk-12",
  "evidence_text": "Employees are eligible for 15 days paid leave per year.",
  "source": "HR_Policy.pdf",
  "relevance_score": 0.92,
  "span_start": 102,
  "span_end": 142
}
```

## Serialization
- Use `Citation.to_dict()` and `Citation.from_dict()` for stable conversion.
- Use `src.verification.citation_utils.citation_to_json` and `citation_from_dict` for JSON IO.

## UI Rendering
- Inline: `({source}, chunk: {id}, relevance={score:.2f})`
- Block: `Source: {source} — chunk: {id} — relevance: {score:.2f}\n"{evidence_text}"`
- Highlight using `span_start`/`span_end` when available; fallback to text search for paraphrases.

## Best Practices
- Keep `evidence_text` short (<= 256 chars) and representative of the chunk.
- Provide `span_start`/`span_end` when exact match exists to enable highlighting.
- Include multiple citations per claim when evidence is multi-hop or fragmented.

## Backwards Compatibility
- New fields must be optional with reasonable defaults.
- Consumers should ignore unknown fields.

## Versioning
- This spec is version 1.0. If fields change, bump spec version and update `docs/CITATION_SPEC.md`.
