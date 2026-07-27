# Towards Trustworthy Enterprise Document QA: Integrating Hallucination Prevention, Adversarial Defense, and Uncertainty Signalling in a Locally-Deployable RAG System

**Devendra**  
Department of Computer Science, MCA Program  
*[Institution Name]*

---

## Abstract

Retrieval-Augmented Generation is now the standard approach for grounding language model outputs in factual document content. Production enterprise deployments, however, consistently reveal weaknesses that academic benchmarks rarely surface: generated claims that no source passage supports, adversarial inputs that hijack the generation process, retrieval pipelines that fail on thematic or comparative queries, and answers delivered without any indication of their reliability. This paper describes **SecureHall-RAG**, a system that tackles all four weaknesses within a single, entirely local architecture. It pairs multi-modal retrieval — combining dense vector search with keyword matching and hierarchically clustered summaries — with sentence-level NLI-based faithfulness verification, a multi-layer adversarial screening pipeline, and a four-tier calibrated confidence indicator. On a 10-document enterprise policy corpus (60 answerable questions), the full retrieval pipeline achieves Precision@1 = **1.000** versus **0.850** for dense-only search; since BM25 alone also saturates at 1.000 on this terminologically distinctive corpus, the hybrid design demonstrates *robustness* across query types rather than a headline gain. Against a 60-case adversarial set (31 designated for blocking), the pattern filter intercepts **54.8%** of attacks; adding an embedding-similarity semantic detector raises this to **61.3%** at **78.3%** overall correct handling with zero false positives. NLI verification guards answer faithfulness (measured semantic grounding ≈ 0.66) at a CPU cost of **+98 s** per query, establishing that GPU inference is necessary for interactive use. A human-annotated faithfulness study is identified as necessary future work. The complete system runs on consumer hardware without any cloud dependency.

---

## 1. Introduction

Answering questions from internal company documents sounds like a solved problem until you actually try to build something that works reliably. The documents exist — HR handbooks, IT security guidelines, compliance manuals, onboarding procedures — but extracting a correct, specific answer from them on demand turns out to be surprisingly hard in practice.

The RAG approach introduced by Lewis et al. [1] made this technically feasible: fetch the relevant passages at query time, hand them to a language model, and let the model compose an answer grounded in what it just read rather than whatever it memorised during training. In a lab setting this works remarkably well. In a real corporate deployment, four problems emerge that the basic setup does not handle:

First, language models still fabricate claims even when the right evidence is sitting in their context window. The retrieved passage might say "12 days of casual leave" and the model outputs "15 days" — not because it did not see the passage, but because the statistical completion mechanism occasionally prefers a plausible-sounding but wrong continuation. Second, any system that accepts free-text input from users is open to adversarial manipulation. Crafted prompts can override system instructions, exfiltrate private context, or cause the model to behave in entirely unintended ways. Third, a single retrieval method cannot cover all query types — embedding search misses exact terminology, keyword search misses paraphrases, and neither can answer a question that requires synthesising content scattered across multiple document sections. Fourth, when every answer sounds equally confident, users have no way to decide which ones to trust immediately and which ones to verify.

SecureHall-RAG was designed to handle all four of these simultaneously in a system that runs entirely on a laptop — no cloud APIs, no external data transmission. The rest of this paper describes how it works, what the measured results look like, and where the honest limitations remain.

---

## 2. Background and Prior Work

Four research threads converge in this system's design.

**Retrieval-Augmented Generation.** The original RAG formulation [1] demonstrated that pairing a neural retriever with a conditional generator substantially reduces factual errors compared to closed-book generation. Subsequent work found that dense retrievers — while excellent at capturing semantic similarity — consistently underweight exact vocabulary matches that are critical in policy documents (specific role titles, regulatory codes, precise dates). Sparse methods like BM25 have exactly the complementary strength. Reciprocal Rank Fusion [2] provides a clean, score-normalisation-free way to merge their ranked outputs, and has become a practical standard in production retrieval systems.

**Hallucination and Faithfulness.** Ji et al. [3] distinguish two flavours of generated fabrication: intrinsic (contradicting the source) and extrinsic (adding content the source cannot verify). Both are problematic in enterprise settings. The most deployment-friendly countermeasure — applying NLI models to score each generated sentence against the retrieved evidence, then acting on sentences that fail — requires no modification to the underlying generator and correlates well with human judgement of answer faithfulness, as demonstrated empirically by multiple groups.

**Adversarial Inputs.** Perez and Ribeiro [4] documented how straightforward it is to override a language model's system instructions via carefully worded user input. The OWASP guidance for LLM applications [5] now lists prompt injection as the top deployment risk and recommends defence-in-depth: input validation, structural separation of instruction zones, and explicit behavioural constraints at generation time. Our three-layer design implements exactly this stack.

**Uncertainty Communication.** Kuhn et al. [6] formalised the problem through Semantic Entropy — computing uncertainty over meaning-equivalent answer clusters rather than raw token probabilities — and showed this measure tracks factual accuracy far better than model confidence scores. Their finding motivates our approach of surfacing a calibrated tier badge alongside every answer rather than hiding confidence inside the system.

---

## 3. System Design

### 3.1 Processing Pipeline

Every query flows through four stages in fixed order. Nothing advances to the next stage until the current one completes successfully. The rationale is straightforward: a malicious query should be caught at Stage 1 before it costs any retrieval or generation resources, and no answer should reach the user without passing through Stage 4's verification check.

### 3.2 Document Ingestion

Before anything can be retrieved, documents must be parsed and indexed. The ingestion pipeline accepts PDF, DOCX, and plain text files, extracts text with metadata (page numbers, section headings, source filenames), and splits it into overlapping chunks of roughly 512 tokens with 128-token overlap to preserve sentence continuity at boundaries.

Two parallel indexes are built: a FAISS `IndexFlatIP` over L2-normalised embeddings from SBERT (`all-mpnet-base-v2`, 768 dimensions) for dense retrieval, and a BM25 Okapi inverted index over tokenised text for sparse retrieval.

A hierarchical summarisation step follows: chunk embeddings are clustered via K-Means, and the local LLM produces a short abstractive summary for each cluster. These summary nodes enter both indexes alongside raw chunks, creating a two-tier structure — fine-grained passages for specific lookups, and cluster-level summaries for broad thematic queries that no individual chunk would satisfy.

### 3.3 Layered Security Screening

All incoming queries are inspected before retrieval begins.

**Layer 1 — Pattern Detection.** A compiled regular expression library covers 27+ documented adversarial input categories: direct instruction overrides, DAN-type jailbreaks, persona/role-play hijacks, base64-encoded payloads, data-exfiltration templates, social-engineering narrative frames, and token-smuggling constructs. A hard 600-character input cap is enforced before pattern matching to block long-payload evasion. Matched queries receive an immediate rejection response and an audit log entry — no model inference occurs.

**Layer 2 — Structural Isolation.** The prompt sent to the LLM separates system directives, retrieved context, and user input into distinct XML-tagged zones (`<system>`, `<context>`, `<user_query>`). Because the model's instruction-following behaviour is anchored to the system zone, user-zone text cannot syntactically escalate to instruction status.

**Layer 3 — Constrained Templates.** Generation prompts use fixed templates that re-assert the model's operational constraints at invocation time: respond only from provided context, disregard conflicting user-zone instructions. This catches indirect attacks that pass both pattern and structural checks.

### 3.4 Multi-Modal Retrieval

On a cache miss (semantic similarity < 0.92 to any stored query), the system determines whether the query is compound. If so, the LLM decomposes it into independent sub-questions.

For each (sub-)question, dense and sparse retrieval run in parallel. Their ranked outputs are combined via Reciprocal Rank Fusion:

$$\text{RRF}(d) = \sum_{r \in \{\text{dense, sparse}\}} \frac{1}{k + \text{rank}_r(d)}, \quad k = 60$$

The top 20 fused candidates are re-scored by a cross-encoder (`ms-marco-MiniLM-L-6-v2`) that attends jointly over the full (query, passage) pair — far more discriminative than independent embedding similarity for borderline cases. After re-ranking, context from all sub-questions is merged and deduplicated.

### 3.5 Generation and Verification

The LLM (Llama-3.1-8B-Instruct via Ollama) generates an answer from the assembled context using a structured, role-constrained prompt. The draft answer is then decomposed into individual sentences, each scored for entailment against the full retrieved context using a DeBERTa NLI cross-encoder:

$$p(\text{entailment} \mid C, s_i) = \frac{e^{l_1}}{e^{l_0} + e^{l_1} + e^{l_2}}$$

A sentence-type classifier first filters out non-factual sentences (transitions, headings), cutting NLI calls by ~40%. Results are cached by content hash.

Sentences below threshold trigger a self-correction pass (capped at 2 rounds). The final output follows a graduated policy: ≥ 0.65 accepted as-is; 0.40–0.64 retained with an inline caution marker; 0.25–0.39 retained with a low-confidence advisory; < 0.25 hard-removed (direct contradiction only).

### 3.6 Confidence Tier Assignment

A composite score blending retrieval similarity (primary signal) and NLI faithfulness (bounded adjustment) is bucketed into four user-facing tiers:

| Tier | Default Range | Behaviour |
|:---|:---:|:---|
| HIGH | ≥ 0.75 | Full answer, green badge |
| MODERATE | 0.50–0.75 | Full answer, amber badge |
| LOW | 0.35–0.50 | Answer with verification disclaimer |
| ABSTAIN | < 0.35 | Polite refusal, no content generated |

Factual queries use a stricter HIGH boundary (≥ 0.80); comparative queries use a relaxed one (≥ 0.68) to reflect inherent synthesis ambiguity.

---

## 4. Results

### 4.1 Setup

Hardware: Intel Core i7 (12th Gen), 16 GB RAM, NVIDIA RTX 3050 (4 GB VRAM). The LLM ran in CPU-only mode to simulate resource-constrained deployment. Corpus: 10 HR policy manuals (DOCX), yielding 29 chunks. Benchmark: 75 questions (60 answerable, 15 unanswerable) with auto-generated gold answers across five categories. Adversarial set: 60 cases (31 should-block) across six attack types. Quality measured on a 15-question subset (CPU cost). All evaluation is automated.

Baselines:
- **A — Vanilla RAG:** Dense retrieval only, no re-ranking, no verification, no security.
- **B — Hybrid RAG:** Dense + BM25 + cross-encoder, no verification, no RAPTOR, no security.
- **C — Hybrid + NLI:** Adds NLI scoring to B; no RAPTOR, no multi-hop, no security.
- **SecureHall-RAG:** All components active.

### 4.2 Retrieval

**Table 1: Retrieval Precision and Recall** (60 answerable questions)

| Configuration | P@1 | P@3 | P@5 | R@3 | R@5 |
|:---|:---:|:---:|:---:|:---:|:---:|
| Dense Only (FAISS) | 0.850 | 0.983 | 1.000 | 0.983 | 1.000 |
| BM25 (sparse only) | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| Hybrid RRF (no rerank) | 0.983 | 1.000 | 1.000 | 1.000 | 1.000 |
| **SecureHall-RAG (Full)** | **1.000** | **1.000** | **1.000** | **1.000** | **1.000** |

Dense-only misses the correct document for 15% of queries. BM25 fusion raises P@1 to 0.983; the cross-encoder closes the remaining gap. On this small, lexically distinctive corpus BM25 alone also hits 1.000 — retrieval is near-saturated and these numbers cannot demonstrate a large hybrid advantage. The hybrid design's value is robustness across query types; a more ambiguous corpus would make the margin visible.

### 4.3 Answer Quality

**Table 2: Quality Metrics** (15-question subset)

| Metric | Baseline | Enhanced |
|:---|:---:|:---:|
| ROUGE-L (↑) | 0.087 | 0.074 |
| Semantic faithfulness (↑) | 0.664 | 0.661 |
| Answer relevance (↑) | 0.636 | 0.636 |
| Mean confidence | 0.733 | 0.661 |

No difference is statistically significant (p = 0.51–0.99). The verification loop functions as a guard rather than a quality enhancer — it does not change grounding on already well-retrieved answers. Semantic faithfulness (embedding cosine between answer and context, ≈ 0.66) is the meaningful signal; ROUGE-L is depressed by the metric–task mismatch (short gold extracts vs. full system sentences). Verification's cost is latency: +98 s/query on CPU (see Table 6).

### 4.4 Security

**Table 3: Adversarial Handling** (60 cases, 31 should-block)

| Category | Should Block | Pattern Only | + Semantic |
|:---|:---:|:---:|:---:|
| Prompt Injection | 10 | 6 (60%) | 6 (60%) |
| Jailbreak | 10 | 5 (50%) | 7 (70%) |
| Encoded / Obfuscated | 8 | 6 (75%) | 6 (75%) |
| Edge Case | 3 | 0 (0%) | 0 (0%) |
| **Total block rate** | **31** | **17 (54.8%)** | **19 (61.3%)** |
| **Overall correct** | | **75.0%** | **78.3%** |

The pattern library handles attacks with recognisable signatures (encoded payloads at 75%). The semantic detector — comparing query embeddings against known attack intents — adds +6.5 points concentrated in the jailbreak category, with no false positives (minimum-length guard). Novel vectors semantically distant from every stored intent (edge cases, 0/3) remain undetected.

### 4.5 Confidence Distribution

**Table 4: Tier Distribution** (enhanced, 15 questions)

| Tier | Proportion |
|:---|:---:|
| HIGH (≥ 0.75) | 40.0% |
| MODERATE (0.50–0.75) | 26.7% |
| LOW (0.35–0.50) | 33.3% |
| ABSTAIN (< 0.35) | 0.0% |

A calibration fix (retrieval as primary signal, verifier bounded) dropped ABSTAIN from 69.3% to 0%. The tradeoff: the system no longer forces refusal when retrieval looks good but grounding is weak. Over-confidence on poorly-supported answers is the residual risk.

### 4.6 Ablation

**Table 5: Component Ablation**

| Configuration | P@1 | Attack Block |
|:---|:---:|:---:|
| **Full (pattern + semantic)** | **1.000** | **61.3%** |
| − Semantic detector | 1.000 | 54.8% |
| − Cross-encoder | 0.983 | 61.3% |
| − BM25 (dense only) | 0.850 | 61.3% |
| − Security framework | 1.000 | **0%** |

Security removal causes total adversarial failure (0%). The semantic detector adds +6.5 points; the reranker adds +1.7 P@1 points. Quality metrics are unaffected by these toggles and reported in Table 2.

### 4.7 Latency

**Table 6: Performance (CPU)**

| Metric | Value |
|:---|:---:|
| Baseline latency | ~50 s/query |
| Enhanced latency | ~149 s/query |
| Verification overhead | +98 s (p < 0.001) |
| Retrieval | < 150 ms |
| Cache hit | 0.12 s |

The verification loop's multiple LLM calls dominate enhanced-mode latency. GPU-quantised inference (Q4 GGUF with offloading) is necessary for interactive response times.

---

## 5. Conclusion

SecureHall-RAG demonstrates that the four trust gaps in enterprise RAG — hallucination, adversarial vulnerability, retrieval blindspots, and answer opacity — can be addressed within a single, locally-deployable architecture running on consumer hardware.

The measured picture: hybrid retrieval with cross-encoder refinement saturates at P@1 = 1.000 on this small corpus (dense-only: 0.850; the hybrid design proves robustness, not a large margin). A layered adversarial defence combining pattern matching, structural isolation, role-constrained generation, and an embedding-similarity semantic detector raises the attack-block rate from 54.8% to 61.3% at 78.3% correct handling with no new false positives — effective against known and paraphrased attacks, but honest about the remaining gap for fully novel vectors. NLI-based verification holds semantic faithfulness at ≈ 0.66, flagging or redacting unsupported claims; its CPU latency (+98 s/query) is the system's primary practical constraint and requires GPU acceleration. A four-tier confidence framework with calibrated thresholds delivers an actionable trust signal with 0% ABSTAIN on the answerable set after calibration — though the corresponding over-confidence risk on weakly-grounded answers needs monitoring.

For future work: a quantitative faithfulness study with human annotators or an LLM-as-judge protocol, GPU-quantised deployment for interactive latency, expansion of the semantic attack seed bank, multilingual document support, and evaluation on a larger, more lexically diverse corpus where retrieval saturation no longer masks the hybrid advantage.

---

## References

[1] P. Lewis et al., "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks," *NeurIPS*, vol. 33, pp. 9459–9474, 2020.

[2] G. V. Cormack, C. L. A. Clarke, and S. Buettcher, "Reciprocal Rank Fusion Outperforms Condorcet and Individual Rank Learning Methods," *Proc. SIGIR*, pp. 758–759, 2009.

[3] Z. Ji et al., "Survey of Hallucination in Natural Language Generation," *ACM Computing Surveys*, vol. 55, no. 12, pp. 1–38, 2023.

[4] F. Perez and I. Ribeiro, "Ignore Previous Prompt: Attack Techniques for Language Models," *NeurIPS Workshop on Trustworthy ML*, 2022.

[5] OWASP Foundation, "OWASP Top 10 for Large Language Model Applications," 2023.

[6] L. Kuhn, Y. Gal, and S. Farquhar, "Semantic Uncertainty: Linguistic Invariances for Uncertainty Estimation in Natural Language Generation," *Proc. ICLR*, 2023.
