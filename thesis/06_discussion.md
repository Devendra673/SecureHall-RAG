# CHAPTER 6: DISCUSSION

---

## 6.1 Interpretation of Results

The experimental results demonstrate that SecureHall-RAG successfully addresses all four problems identified in the problem statement.

### Addressing P1 — Hallucination

The combination of NLI faithfulness scoring and uncertainty-based abstention reduces the hallucination rate from 34% (Vanilla RAG baseline) to 8% — representing a **76% relative reduction**. This validates the core research hypothesis that post-hoc NLI verification is an effective and practical hallucination mitigation strategy for enterprise RAG systems.

The 8% residual hallucination rate is primarily attributable to cases where retrieved context is relevant but incomplete. The LLM "fills in the gaps" with plausible but unverified information. Future work using contrastive decoding or more granular claim-level verification could reduce this further.

The uncertainty tier calibration results are particularly encouraging: HIGH-tier answers are correct 93% of the time, and LOW-tier answers show only 52% correctness — demonstrating that the tier assignments are meaningful predictors of actual answer quality, not arbitrary labels. This validates the practical utility of exposing uncertainty information to end users.

### Addressing P2 — Security

The 100% block rate across all 51 adversarial test cases is a strong result. The defense-in-depth approach — where three independent layers must all be bypassed for an attack to succeed — significantly raises the difficulty of successful injection. The content filter's regex-based approach is intentionally brittle to new attack formulations, motivating the importance of regular pattern library updates as the adversarial landscape evolves.

One important limitation of the security evaluation is that the 51-attack test set, while diverse, represents a finite sample of attack space. Novel or obfuscated attack patterns not yet represented in the detection library could potentially bypass Layer 1 and test the resilience of Layers 2 and 3.

### Addressing P3 — Retrieval Gaps

The ablation study clearly demonstrates the complementarity of dense and sparse retrieval. BM25 contributes strongly on queries with precise technical terminology or policy-specific jargon, while dense FAISS retrieval handles semantic paraphrasing and conceptual questions. The combined P@1 of 0.84 represents a **33%** improvement over sparse-only retrieval and a **33%** improvement over dense-only retrieval.

RAPTOR summaries provide the largest marginal benefit for high-level queries. On comparative questions (e.g., *"What is the general philosophy of the HR department regarding employee well-being?"*), summary nodes often contain the most relevant information that would otherwise be scattered across dozens of raw chunks.

### Addressing P4 — Opacity

The inline citation system and uncertainty badges directly address the opacity problem. Users can now verify any factual claim by clicking the associated citation badge, which opens the full source passage. The color-coded confidence badge provides an immediate visual signal of answer reliability. These features transform SecureHall-RAG from a black-box oracle into a transparent, verifiable assistant — a critical distinction for enterprise deployments where accountability matters.

---

## 6.2 Strengths of the System

**1. Holistic Design**: SecureHall-RAG integrates hallucination prevention, security hardening, hierarchical retrieval, query expansion, multi-hop reasoning, and uncertainty quantification into a unified, locally-deployable pipeline — a combination not found in any single prior system.

**2. Privacy-Preserving**: The local-first architecture means sensitive policy documents never leave the organisation's infrastructure. This is a critical differentiator for regulated industries handling confidential information.

**3. Production Quality**: The system is a full-stack deployable application with JWT authentication, role-based access control, audit logging, Docker containerisation, and a premium streaming UI. It is immediately usable in real enterprise environments.

**4. Transparency and Trust**: The combination of inline citations, source panels, uncertainty badges, and audit logs provides full transparency into system behaviour. The four-tier soft redaction policy — which retains partial-support content with visual indicators rather than deleting it — ensures users receive the most useful answer the system can construct at any confidence level.

**5. Calibrated Uncertainty**: Per-query-type UQ thresholds mean that factual, procedural, comparative, and policy queries are each evaluated against confidence boundaries appropriate to their inherent ambiguity. HIGH-tier answers are correct 93% of the time, confirming that the tier assignments are meaningful predictors of answer quality.

**6. Extensibility**: The modular architecture allows easy replacement or upgrading of individual components without modifying the overall pipeline. The query expansion module degrades gracefully when the LLM is offline; the NLI cache reduces inference cost in multi-turn sessions without any configuration.

---

## 6.3 Limitations

**1. Computational Cost**: Full-pipeline query processing on local CPU-only hardware takes approximately 56 seconds on average, primarily due to LLM generation and self-correction. For high-throughput production deployments, GPU-accelerated LLM inference would be required.

**2. English-Only**: The current implementation processes only English-language documents. Multilingual enterprise environments would require multilingual embeddings and a multilingual LLM.

**3. Static Knowledge Base**: The system's knowledge is limited to ingested documents. It cannot learn from user interactions or update automatically when new policy documents are released.

**4. RAPTOR Scale**: The synchronous RAPTOR tree build could become a bottleneck for very large document corpora (>1000 documents). An asynchronous or incremental RAPTOR build would be required at production scale.

**5. Evaluation Coverage**: The 80-query test set is smaller than benchmarks used in published RAG research. A larger, independently curated evaluation set would strengthen the empirical claims.

**6. Security Evolution**: The regex-based content filter is inherently reactive — it can only detect attack patterns that have been explicitly enumerated. As adversarial techniques evolve, the pattern library (currently 27+ patterns) requires continuous maintenance.

---

## 6.4 Future Work

Several promising directions for further development are identified based on current limitations:

**1. GPU-Accelerated LLM Inference**: The primary LLM (Mistral 7B via Ollama) runs in CPU mode on most test hardware. Integrating CUDA-based inference via `llama.cpp` GPU offloading or vLLM with quantised GGUF Q4/Q8 models would reduce generation latency from ~12.5 seconds to under 0.5 seconds, making real-time query response practical.

**2. Multilingual Support**: Extending the system through language detection, multilingual embeddings, and a multilingual LLM would broaden its applicability to international enterprise environments.

**3. Online Learning from Feedback**: User feedback (thumbs up/down ratings already collected by the system) could be incorporated into an online fine-tuning loop for the embedding model, improving retrieval quality for domain-specific queries over time.

**4. Multi-level RAPTOR**: The full recursive RAPTOR algorithm with multiple summarisation levels could further improve high-level query performance for very large document corpora.

**5. Adversarial Robustness Benchmarking**: Systematic evaluation against the GAIA benchmark [28] and published prompt injection test suites would provide standardised security robustness measures beyond the current 51-prompt test set.

**6. Graph-Augmented RAG**: Building a knowledge graph from extracted entities and relations in policy documents could enable more precise multi-hop reasoning than the current LLM-based decomposition approach.

**7. Semantic Attack Detection**: Integrating SBERT-based semantic similarity against a curated attack phrase index would extend detection beyond enumerated regex patterns to novel, paraphrased attacks not yet in the pattern library.

---
