# Verification Response Schema

This document defines the JSON schema for the `VerificationResponse` produced by the system.

Top-level keys:
- `answer_text` (string): The assembled, verified answer text (markdown/annotated).
- `claims` (array): List of claims with verification metadata. Each item:
  - `claim_id` (string)
  - `claim_text` (string)
  - `decision` (string) - one of `accept`, `partial_accept`, `refuse`
  - `support_score` (float)
  - `support_level` (string)
  - `reasoning` (string)
  - `citations` (array) - list of citation objects
- `citations` (array): Flattened list of citation objects. Each citation:
  - `claim_id`, `evidence_chunk_id`, `evidence_text`, `source`, `relevance_score`, `span_start`, `span_end`
- `evidence_snippets` (object): Mapping from `evidence_chunk_id` -> snippet text (used for UI highlighting)
- `metadata` (object): runtime metadata such as `processing_time_ms`, `total_support_score`, `accepted_count`, etc.

Example usage: the UI consumes `evidence_snippets` and `citations` to display highlighted evidence and citation lists.
