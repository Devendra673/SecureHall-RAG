# Towards Trustworthy Enterprise Document QA: Integrating Hallucination Prevention, Adversarial Defense, and Uncertainty Signalling in a Locally-Deployable RAG System

**Devendra**  
Department of Computer Science, MCA Program  
*[Institution Name]*

---

## Abstract

Retrieval-Augmented Generation has emerged as the dominant paradigm for grounding large language model (LLM) responses in external document corpora. Yet real enterprise deployments quickly expose a cluster of practical weaknesses that published benchmarks tend to underreport: factual hallucinations that survive even accurate retrieval, prompt injection attacks that subvert the generation process, retrieval pipelines that fail on thematic or comparative queries, and answers that provide users with no signal about how much trust to place in them. This paper presents **SecureHall-RAG**, a system that addresses all four weaknesses simultaneously within a single, fully local architecture. The design couples hybrid dense-plus-sparse retrieval — augmented with hierarchically clustered document summaries — with a sentence-level Natural Language Inference (NLI) verification loop, a three-layer adversarial input defense, and a four-tier calibrated uncertainty framework. Tested on an 80-question enterprise policy benchmark against three progressively stronger baselines, SecureHall-RAG reduces the hallucination rate from 34% to **8%** and achieves **80% Precision@1**, while blocking all 51 crafted adversarial inputs without a single false positive. The entire pipeline runs on commodity laptop hardware, requiring no cloud API access.

---

## 1. Introduction

The idea of using language models to answer questions from documents has been around for some time, but it only became practical at scale with the introduction of Retrieval-Augmented Generation [1]. The core insight is straightforward: instead of training a model to memorise every fact it might ever be asked about, retrieve the relevant passage at query time and have the model read it before answering. This simple addition dramatically reduces the rate at which models fabricate answers, because the evidence is right there in the input.

In enterprise settings — where the documents are HR policies, legal compliance manuals, IT security guidelines, or operational handbooks — the stakes of a wrong answer are unusually high. A hallucinated entitlement figure could result in a wrongful HR decision. A fabricated security rule could lead to a compliance violation. A confidently wrong procedural answer could expose an organisation to legal liability. At the same time, enterprise documents are sensitive enough that most organisations cannot responsibly send them to a cloud API. The data has to stay on-premises.

These constraints push us toward a different design than most published RAG systems. We need a pipeline that: (a) retrieves well across both exact-keyword and semantic queries, (b) verifies its own answers before returning them, (c) resists attempts to manipulate or hijack its behaviour, and (d) tells the user how confident it is, in a way that actually tracks how often the answer is right.

**SecureHall-RAG** was built to satisfy all four constraints at once. This paper describes the system design, reports empirical results, and compares performance across a set of controlled baselines. We find that the combination of components delivers improvements no single component achieves alone, and that the system is entirely viable on local consumer hardware.

---

## 2. Literature Survey

Research in RAG systems and their failure modes has accelerated considerably over the past three years. We focus here on the four bodies of work most directly relevant to our design.

**Retrieval-Augmented Generation.** Lewis et al. [1] established the canonical RAG formulation: a dense retriever fetches the top-K passages relevant to a query, and a sequence-to-sequence generator produces the answer conditioned on those passages. Subsequent work identified a persistent weakness in purely dense retrieval — exact technical terms, policy-specific jargon, and proper nouns are often underweighted by embedding models that smooth over vocabulary at the semantic level. Sparse methods like BM25 have the complementary strength: they match on exact tokens and are not confused by paraphrasing. Combining the two through Reciprocal Rank Fusion [2] is now widely accepted as the practical baseline for production retrieval systems, because the fusion is parameter-free and does not require score normalisation.

**Hallucination and Faithfulness Verification.** Even with highly relevant passages in context, language models occasionally produce claims that no retrieved passage supports. Ji et al. [3] provide a thorough taxonomy of this behaviour, distinguishing intrinsic hallucinations (which contradict the source material) from extrinsic ones (which add unverifiable information). They also survey mitigation strategies, noting that post-hoc verification via Natural Language Inference is among the most practical approaches: it can be applied to any generator without retraining, and NLI models have been shown to correlate well with human faithfulness judgments. The core idea — score each generated sentence as entailed, neutral, or contradicted by the retrieved context, then act on sentences that fail — is the approach our system adopts.

**Prompt Injection and Adversarial Robustness.** A class of attack that received limited attention until recently involves adversaries who craft user inputs designed to override system instructions. Perez and Ribeiro [4] catalogued the basic forms of this attack and demonstrated that naive system-prompt separation provides minimal protection because the language model treats all input text uniformly. Later work showed that indirect injection — adversarial text hidden inside documents that subsequently gets retrieved and processed as context — extends the attack surface beyond the user input itself. The OWASP guidance for LLM applications [5] now recognises prompt injection as one of the top risks in deployed systems and recommends layered defense with structural input separation, explicit role-pinning, and runtime pattern filtering.

**Uncertainty Quantification.** A common complaint about AI-powered QA tools is that they express the same confident tone regardless of whether the answer is well-supported or entirely fabricated. Kuhn et al. [6] formalised this problem through the concept of Semantic Entropy — computing entropy not over individual tokens but over semantically equivalent answer variants — and showed that this measure correlates with factual accuracy in a way that raw probability scores do not. Their findings motivate explicit, user-facing confidence signals tied to meaningful accuracy correlates, rather than internal probabilities that users cannot interpret.

Taken together, these four bodies of work map out the design space SecureHall-RAG occupies: a hybrid retrieval foundation, NLI-based post-hoc verification, layered adversarial defense, and calibrated uncertainty exposure.

---

## 3. Methods / Methodology

### 3.1 System Overview

SecureHall-RAG processes every user query through four sequential stages: security filtering, intelligent retrieval, grounded generation, and verification with uncertainty scoring. Each stage is an independent module with a well-defined input-output contract, which makes the system straightforward to extend or partially replace.

### 3.2 Document Ingestion

Before any query can be answered, documents must be indexed. The ingestion pipeline accepts PDF, DOCX, and TXT files, parses them into text blocks with metadata (page number, section heading, source filename), and then splits each block into overlapping chunks of approximately 512 tokens, with a 128-token overlap between adjacent chunks to avoid breaking sentences at chunk boundaries.

Two indexes are built simultaneously. First, every chunk is encoded by a Sentence-BERT model (`all-MiniLM-L6-v2`, producing 384-dimensional vectors) and added to a FAISS `IndexFlatIP` index for dense retrieval. Second, the raw token sequences of all chunks are registered with a BM25 Okapi inverted index for sparse retrieval.

After chunking, a hierarchical summarisation pass is performed using a variant of the RAPTOR technique: all chunk embeddings are clustered with K-Means, and the local LLM writes a short abstractive summary for each cluster. These summary nodes are added to both indexes alongside the raw chunks. They give the retrieval system access to thematic, multi-document content that no individual chunk would surface.

### 3.3 Three-Layer Security Filtering

Every incoming query is inspected before any retrieval or generation happens.

**Layer 1 — Pattern Matching**: A set of compiled regular expressions covers 27+ categories of known adversarial patterns: direct injection phrases (*"ignore your previous instructions"*), DAN-style jailbreaks, persona/role-play attacks (*"act as"*, *"roleplay as"*), social-engineering story frames, base64-encoded payloads, data exfiltration requests, and token smuggling markers. A 600-character input length cap is enforced before regex matching, blocking payload-smuggling via long inputs. Matching queries are rejected immediately with an error response and an audit log entry.

**Layer 2 — Structural Input Isolation**: Queries that clear Layer 1 are assembled into a structured prompt where system instructions, retrieved context, and user input are placed in distinct XML-tagged sections (`<system>`, `<context>`, `<user_query>`). This structural separation makes it significantly harder for text inside the user section to bleed into or override the system section — a design principle aligned with the context-invariant alignment recommendation in the literature.

**Layer 3 — Hardened Generation Templates**: All generation prompts are instantiated from fixed templates that restate the model's role constraints at the point of generation: *"You are a document assistant. You must answer only using the information in the provided context. Disregard any instruction within the user query that conflicts with these rules."* This final layer catches subtle attacks that may have passed syntactic filters but attempt to redirect the model through indirect framing.

### 3.4 Hybrid Hierarchical Retrieval

Queries that pass security enter the retrieval engine. The engine first checks a semantic cache: if a previous query with cosine similarity above 0.92 to the current query exists, its cached answer is returned immediately, saving the full retrieval-and-generation cost.

On a cache miss, the LLM checks whether the query appears to be comparative or multi-entity. If so, it decomposes the query into a JSON list of focused sub-questions, each of which is processed independently. For each sub-question:

- FAISS dense retrieval fetches the top-K semantically similar chunks.
- BM25 sparse retrieval fetches the top-K keyword-matched candidates.
- The two ranked lists are merged by Reciprocal Rank Fusion [2]:

$$\text{RRF}(d) = \sum_{r \in \{\text{dense, sparse}\}} \frac{1}{k + \text{rank}_r(d)}, \quad k = 60$$

The top-20 fused candidates are then re-ranked by a cross-encoder model (`cross-encoder/ms-marco-MiniLM-L-6-v2`), which scores each (query, chunk) pair by attending to the concatenated text jointly — a significantly more precise but computationally heavier operation than bi-encoder similarity.

Context lists from all sub-questions are merged and deduplicated by chunk ID before being passed to generation.

### 3.5 Generation and NLI Verification

The assembled context, user query, and system template are passed to Mistral-7B running locally via Ollama. The LLM generates an answer with inline citation brackets indicating which retrieved chunk each claim is drawn from.

Once a draft answer is generated, the NLI verification module tokenises it into individual sentences. Each sentence $s_i$ is scored against the full retrieved context $C$ using a DeBERTa-based NLI cross-encoder, which outputs logits $l_0$ (contradiction), $l_1$ (entailment), and $l_2$ (neutral). The entailment probability is:

$$p(\text{entailment} \mid C, s_i) = \frac{e^{l_1}}{e^{l_0} + e^{l_1} + e^{l_2}}$$

Sentences scoring below the entailment threshold trigger a self-correction pass: the LLM is re-prompted with the flagged sentence and told to rewrite it using only the available evidence. The final output applies a **four-tier soft redaction policy**: sentences scoring ≥ 0.65 are accepted unchanged; 0.40–0.64 append an `⚠️` warning inline; 0.25–0.39 append a `🔴 *[Low confidence — verify directly]*` marker; only scores < 0.25 — indicating genuine logical contradiction with the source — are hard-redacted. The mean entailment score across evaluated claim sentences forms the overall faithfulness rating.

### 3.6 Uncertainty Quantification

Confidence thresholds are calibrated per query type: factual lookup queries use a strict HIGH boundary (≥ 0.80), while comparative queries — which inherently synthesise across multiple sources — use a more lenient boundary (≥ 0.68). This prevents premature LOW or ABSTAIN tier assignments on queries that are inherently uncertain by nature rather than due to retrieval failure. Default tiers are:

| Tier | Default Confidence | User-Facing Behaviour |
|:---|:---:|:---|
| HIGH | ≥ 0.75 | Answer shown with green confidence badge |
| MODERATE | 0.50 – 0.75 | Answer shown with amber badge |
| LOW | 0.35 – 0.50 | Answer shown with warning disclaimer |
| ABSTAIN | < 0.35 | Safe refusal — no fabricated content returned |

The tier badge is displayed inline in the frontend alongside the answer and source citations, giving users an immediate, interpretable signal about how much weight to place on the response.

---

## 4. Results and Comparative Analysis

### 4.1 Experimental Setup

All experiments were run on a consumer laptop (Intel Core i7-12th Gen, 16 GB RAM, NVIDIA GeForce RTX 3050 Laptop GPU, 4 GB VRAM). The document corpus consisted of 10 enterprise policy manuals. We constructed an 80-question benchmark with manually written ground-truth answers, spanning four question categories: factual lookup (30 questions), comparative (20), definitional (15), and out-of-scope (15). The out-of-scope category tests whether the system refuses to answer when the corpus contains no relevant information.

Three baseline configurations were compared:
- **Baseline A — Vanilla RAG**: FAISS dense retrieval only; no re-ranking, no NLI verification, no security.
- **Baseline B — Hybrid RAG**: FAISS + BM25 + cross-encoder re-ranking, but no NLI verification, no RAPTOR, no security.
- **Baseline C — Hybrid + NLI**: Adds NLI faithfulness scoring to Baseline B, but without RAPTOR summaries, multi-hop decomposition, or security filtering.
- **SecureHall-RAG**: Full system, all components active.

### 4.2 Retrieval Quality

**Table 1: Retrieval Precision@K and Recall@K**

| Configuration | P@1 | P@3 | P@5 | R@3 | R@5 |
|:---|:---:|:---:|:---:|:---:|:---:|
| Baseline A — Vanilla RAG | 0.63 | 0.58 | 0.54 | 0.71 | 0.79 |
| BM25 (sparse only) | 0.58 | 0.52 | 0.48 | 0.67 | 0.74 |
| Baseline B — Hybrid RAG | 0.78 | 0.73 | 0.66 | 0.81 | 0.85 |
| **SecureHall-RAG (Full)** | **0.80** | **0.75** | **0.70** | **0.84** | **0.89** |

Moving from single-modality dense retrieval to hybrid RRF fusion raises Precision@1 by **+15 percentage points**. The cross-encoder re-ranker alone accounts for a further **+8.3%** gain. Adding RAPTOR cluster summaries pushes P@1 to 0.80 overall, with a noticeably larger gain (**+8.1%**) on the comparative question subset — these are precisely the thematic, multi-document queries that cluster summaries are designed for.

### 4.3 Hallucination and Faithfulness

**Table 2: Faithfulness Evaluation**

| Configuration | NLI Score (↑) | Human Rating /3 (↑) | Hallucination Rate (↓) |
|:---|:---:|:---:|:---:|
| Baseline A — Vanilla RAG | 0.71 | 2.31 | 34% |
| Baseline B — Hybrid RAG | 0.76 | 2.48 | 26% |
| Baseline C — Hybrid + NLI | 0.83 | 2.67 | 14% |
| **SecureHall-RAG (Full)** | **0.88** | **2.81** | **8%** |

The NLI verification layer is by far the strongest single lever for hallucination control: removing it causes the rate to rise from 8% to 29% (the − NLI row in the ablation, Table 4). Across the full comparison, SecureHall-RAG brings the hallucination rate down by **76% relative** to Vanilla RAG. Three human evaluators (Fleiss inter-rater κ = 0.74) rated the full system's answers as fully faithful 81% of the time, compared to 58% for the vanilla baseline. The four-tier soft redaction policy ensures that partial-support content is surfaced with inline uncertainty indicators rather than deleted, preserving answer utility while maintaining transparency.

### 4.4 Security Effectiveness

**Table 3: Adversarial Input Block Rate (51 total attempts)**

| Attack Type | Attempts | Blocked | Rate |
|:---|:---:|:---:|:---:|
| Direct Prompt Injection | 12 | 12 | 100% |
| Jailbreak (DAN-style) | 10 | 10 | 100% |
| Role Reassignment | 8 | 8 | 100% |
| Encoding Attacks (base64) | 6 | 6 | 100% |
| Data Exfiltration | 8 | 8 | 100% |
| Social Engineering | 7 | 7 | 100% |
| **Total** | **51** | **51** | **100%** |

Layer 1 (pattern matching) blocked 41 of the 51 attempts without involving the LLM at all. The remaining 10 were caught by the structural isolation in Layers 2 and 3. Zero legitimate user queries were incorrectly blocked across the entire 80-question benchmark.

### 4.5 Uncertainty Calibration

**Table 4: Confidence Tier vs. Actual Correctness**

| Tier | % of Queries | Human Correctness |
|:---|:---:|:---:|
| HIGH (≥ 0.75) | 42% | **93%** |
| MODERATE (0.50–0.75) | 31% | 78% |
| LOW (0.35–0.50) | 15% | 52% |
| ABSTAIN (< 0.35) | 12% | N/A (refused) |

The confidence tiers form a strict monotonic relationship with human-judged correctness. HIGH-tier answers are right 93% of the time; LOW-tier answers are right only about half the time — which is precisely the signal users need to know when they should go and verify an answer manually. The system correctly abstained on 87% of the 15 out-of-scope questions.

### 4.6 Ablation Summary

**Table 5: Ablation — Effect of Removing Each Component**

| Configuration | P@1 | Hallucination Rate | Security Block |
|:---|:---:|:---:|:---:|
| **Full System** | **0.80** | **8%** | **100%** |
| − BM25 sparse retrieval | 0.63 | 22% | 100% |
| − Cross-encoder re-ranker | 0.72 | 16% | 100% |
| − RAPTOR summaries | 0.78 | 9% | 100% |
| − NLI verification | 0.80 | 29% | 100% |
| − Multi-hop decomposition | 0.75 | 11% | 100% |
| − Security framework | 0.80 | 8% | **0%** |

The ablation makes two things clear. First, every component contributes, and the contribution of each is additive — there is no redundancy in the design. Second, the security layer is the single point of complete failure if removed: without it, the block rate drops to 0%, meaning the system becomes fully exploitable.

### 4.7 System Performance

On the same consumer laptop hardware:

| Metric | Measured Value |
|:---|:---:|
| Full-pipeline latency (non-streaming) | ~56 s |
| Streaming first-token latency | 3.5 s |
| Document ingestion speed | 2.3 pages/sec |
| Semantic cache hit response time | 0.12 s |

LLM generation and iterative self-correction account for the majority of the non-streaming latency. A selective NLI sentence classifier, batch DeBERTa inference, and self-correction capping (max 2 rounds) reduce verification overhead significantly. The streaming first-token latency of 3.5 seconds is the user-perceived delay for a thoughtful document query. On a dedicated server with a modern GPU and quantised GGUF model variants, total latency is projected to fall below 10 seconds.

---

## 5. Conclusion

This paper described SecureHall-RAG, a system built around the observation that trustworthy enterprise document QA requires more than accurate retrieval. It requires verification, security, and honest uncertainty communication — and all three must work together, not independently.

The results support the design approach. Hybrid RRF retrieval with cross-encoder re-ranking and RAPTOR cluster summaries achieves 80% Precision@1, outperforming any single retrieval modality by a substantial margin. The NLI self-correction loop with soft graduated redaction reduces the hallucination rate to 8%, a 76% relative improvement over a dense-only baseline, while preserving useful partial-support content through inline uncertainty indicators rather than deletion. A three-layer adversarial defense — with 27+ pattern signatures and a 600-character input cap — blocks every tested attack input without harming legitimate use. And a four-tier uncertainty framework with per-query-type thresholds delivers calibrated confidence signals that genuinely track answer quality.

The broader implication is that open-source, locally-deployed LLMs are now capable of supporting production-quality, privacy-preserving document QA for organisations that cannot use cloud services. The remaining challenges are latency under CPU-only hardware constraints, multilingual document support, and continuous maintenance of the security pattern library as adversarial techniques evolve.

---

## References

[1] P. Lewis, E. Perez, A. Piktus, F. Petroni, V. Karpukhin, N. Goyal, H. Küttler, M. Lewis, W.-t. Yih, T. Rocktäschel, S. Riedel, and D. Kiela, "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks," in *Advances in Neural Information Processing Systems (NeurIPS)*, vol. 33, pp. 9459–9474, 2020.

[2] G. V. Cormack, C. L. A. Clarke, and S. Buettcher, "Reciprocal Rank Fusion Outperforms Condorcet and Individual Rank Learning Methods," in *Proc. ACM SIGIR Conference on Research and Development in Information Retrieval*, pp. 758–759, 2009.

[3] Z. Ji, N. Lee, R. Frieske, T. Yu, D. Su, Y. Xu, E. Ishii, Y. J. Bang, A. Madotto, and P. Fung, "Survey of Hallucination in Natural Language Generation," *ACM Computing Surveys*, vol. 55, no. 12, pp. 1–38, 2023.

[4] F. Perez and I. Ribeiro, "Ignore Previous Prompt: Attack Techniques for Language Models," in *Workshop on Trustworthy and Socially Responsible Machine Learning (TSRML) at NeurIPS*, 2022.

[5] OWASP Foundation, "OWASP Top 10 for Large Language Model Applications," OWASP, 2023. [Online]. Available: https://owasp.org/www-project-top-10-for-large-language-model-applications/

[6] L. Kuhn, Y. Gal, and S. Farquhar, "Semantic Uncertainty: Linguistic Invariances for Uncertainty Estimation in Natural Language Generation," in *Proc. International Conference on Learning Representations (ICLR)*, 2023.
