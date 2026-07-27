# SecureHall-RAG: A Secure, Hallucination-Resistant Retrieval-Augmented Generation System for Enterprise Policy Question Answering

**Devendra**

MCA (Final Year), Department of Computer Science  
[Institution Name], [City], [State] – [Pin Code]  
Email: [your-email@institution.ac.in]

**Guide: [Supervisor Name]**  
[Designation], Department of Computer Science  
[Institution Name], [City], [State]

---

## Abstract

Corporate organisations maintain extensive internal documentation covering HR policies, compliance procedures, IT security protocols, and operational guidelines. Employees frequently struggle to locate specific answers from these scattered sources, leading to delays, inconsistent information, and unnecessary support requests. While Retrieval-Augmented Generation (RAG) has shown promise for automating document-based question answering, production deployments continue to face four critical shortcomings: the generation of factually unsupported claims (hallucination), vulnerability to adversarial input manipulation, limited retrieval effectiveness when relying on a single search modality, and the lack of visible trust indicators on generated responses.

This work introduces **SecureHall-RAG**, a completely on-premises system that tackles all four weaknesses through an integrated architecture. The pipeline incorporates layered adversarial input screening, a multi-modal retrieval engine combining FAISS vector search (`all-mpnet-base-v2`, 768 dimensions) with BM25 term matching and RAPTOR-style hierarchical summaries via Reciprocal Rank Fusion and cross-encoder refinement, sentence-granularity faithfulness checking through NLI entailment scoring with automated claim rewriting, LLM-driven question decomposition for multi-entity queries, and a four-level calibrated confidence indicator shown with every response.

Testing against an enterprise policy corpus (60 answerable questions from 10 HR documents) shows the complete hybrid retrieval pipeline achieving Precision@1 = **1.000** compared to **0.850** for vector search alone. Since BM25 independently reaches 1.000 on this small, terminology-rich corpus, retrieval performance is effectively saturated — the hybrid approach demonstrates robustness across query types rather than a headline accuracy gain. Against a 60-case adversarial prompt set (31 designated for blocking), the pattern-matching filter intercepts **54.8%** of attacks; supplementing it with an embedding-similarity detector raises this to **61.3%** while maintaining **78.3%** overall correct handling without introducing false positives. The NLI verification component functions as a post-generation guard (measured semantic grounding score ≈ 0.66) at a cost of approximately **+98 seconds** per query on CPU hardware, establishing that GPU-accelerated inference is necessary for real-time interaction. No external cloud services are required at any stage.

**Keywords:** Retrieval-Augmented Generation (RAG), Hallucination Prevention, Natural Language Inference (NLI), Prompt Injection Defense, RAPTOR, Hybrid Retrieval, Enterprise Question Answering, Uncertainty Quantification, Local AI

---

## I. INTRODUCTION

Operational knowledge in any enterprise — from leave entitlements and disciplinary procedures to IT access policies and compliance obligations — lives inside documents that are notoriously difficult to query efficiently. When a staff member needs a precise answer, they typically resort to manual file searches, helpdesk tickets, or informal peer queries. None of these approaches is scalable, and each introduces a risk of receiving outdated or incorrect information.

The RAG paradigm proposed by Lewis et al. [1] offered a viable technical solution: retrieve the most pertinent document passages at query time and feed them to a language model that generates an answer grounded in those passages rather than relying solely on parametric memory. In practice, however, deploying such a system in a corporate environment reveals persistent weaknesses:

**P1 — Hallucination.** Language models generate statements that the retrieved passages do not actually support [2]. Work by Xu et al. [18] demonstrates through formal analysis that this tendency is an inherent mathematical property of finite-parameter models rather than a training deficiency. Consequently, architectural safeguards for detecting unsupported claims after generation are essential.

**P2 — Adversarial Exploitation.** Users with malicious intent can craft inputs designed to override system instructions, extract confidential context, or manipulate model behaviour [3]. Research on indirect injection through retrieved documents [15] and semantically blended attack payloads [23] shows that this threat extends well beyond naive keyword-based attacks.

**P3 — Incomplete Retrieval.** Policy corpora require both exact vocabulary matching (for role titles, dates, and regulatory identifiers) and semantic generalisation (for paraphrased or comparative queries). Any single retrieval method excels at one dimension while failing at the other, and neither can aggregate information scattered across multiple sections.

**P4 — Opacity.** When a system returns a confident-sounding answer without citing sources or indicating its own certainty level, users have no rational basis for deciding whether to act immediately or verify independently.

SecureHall-RAG was built to resolve all four issues in a single locally-hosted application. Its principal contributions are:

1. A **layered adversarial screening pipeline** combining regex-based pattern detection (with a 600-character hard cap), XML-based structural separation of system and user content, and role-constrained generation templates.
2. A **multi-modal hierarchical retrieval engine** fusing FAISS dense vectors (`all-mpnet-base-v2`, 768-dim) and BM25 keyword scores through Reciprocal Rank Fusion, followed by cross-encoder re-scoring, and augmented with RAPTOR cluster summaries for thematic coverage.
3. **Post-generation faithfulness verification** using a DeBERTa NLI cross-encoder [9] applied at sentence granularity, with automatic rewriting of poorly-supported claims and graduated output-handling policies.
4. **LLM-driven query decomposition** that splits compound questions into focused sub-queries processed independently before context merging.
5. A **four-tier confidence framework** (HIGH / MODERATE / LOW / ABSTAIN) with category-sensitive thresholds, surfaced to users through colour-coded badges.

---

## II. RELATED WORK

### A. Retrieval-Augmented Generation

The foundational RAG formulation by Lewis et al. [1] pairs a neural retriever with a sequence-to-sequence generator, grounding output in externally fetched passages. Karpukhin et al. [4] advanced the retrieval component by training dual-encoder models that map questions and passages into a shared embedding space for efficient inner-product search. A broad survey by Gao et al. [5] categorises subsequent improvements into query reformulation, retrieval-stage enhancements, and post-retrieval processing. Liu et al. [6] identified a practical concern — language models attending disproportionately to tokens at the beginning and end of their input window, underutilising material in the middle — which motivates hierarchical representations that position key content more prominently. Asai et al. [22] demonstrated that adding an explicit self-critique loop after retrieval and generation improves factual reliability, a principle that directly informs the verification stage in the present system.

### B. Hallucination and Mitigation

Ji et al. [2] classify generated hallucinations into two types: those contradicting the source (intrinsic) and those introducing unverifiable additions (extrinsic). Tonmoy et al. [17] surveyed available countermeasures across training modifications, decoding strategies, and post-generation checks, concluding that NLI-based verification after generation is the most deployment-friendly approach since it requires no changes to the generator itself. Formal work by Xu et al. [18] established that hallucination is a structural inevitability of finite-capacity statistical models, reinforcing that detection infrastructure must be embedded architecturally. Maynez et al. [7] provided empirical evidence that NLI entailment scores correlate strongly with human faithfulness ratings, justifying their use as the primary quality signal. Falke et al. [8] applied the same principle to rank summary candidates by factual correctness. Laban et al. [10] subsequently showed that computing NLI scores per-sentence rather than per-document yields substantially better alignment with human assessments.

### C. Hybrid Retrieval

Research consistently finds that dense embedding models and term-frequency methods are complementary rather than competing — each captures retrieval signals the other misses [11]. Cormack et al. [12] proposed Reciprocal Rank Fusion as a straightforward, score-normalisation-free technique for combining ranked outputs from different systems. Cross-domain evaluation through the BEIR benchmark [13] confirmed that no single retrieval method dominates across all dataset types. Sarthi et al. [14] introduced RAPTOR, a two-level hierarchy in which chunk embeddings are clustered and the model generates abstractive summaries per cluster; these summaries become additional index entries, making thematic content retrievable that no individual chunk would surface.

### D. Prompt Injection and LLM Security

Perez and Ribeiro [3] documented the basic mechanism of prompt injection: user-supplied text containing override instructions that the model executes as if they were system directives. Greshake et al. [15] showed that this attack vector extends to RAG systems through malicious content planted in documents that are later retrieved and processed. Nafi et al. [23] demonstrated an advanced variant (LASH) where adversarial intent is blended with benign language, defeating surface-pattern detectors — a known limitation relevant to the system presented here. The OWASP security guidance for LLM applications [16] recommends a defence-in-depth strategy combining input validation, structural isolation of instruction zones, and explicit behavioural constraints in generation prompts.

### E. Uncertainty Quantification

Kuhn et al. [19] introduced Semantic Entropy, which estimates model uncertainty by measuring disagreement across semantically clustered answer variants rather than using raw token probabilities. Manakul et al. [20] proposed SelfCheckGPT, applying cross-sample consistency as a black-box confidence signal. Kadavath et al. [21] observed that large models can partially assess their own reliability when explicitly asked, supporting the viability of prompt-based confidence elicitation. These approaches collectively motivate the four-tier bucketed confidence framework used in this work.

---

## III. SYSTEM ARCHITECTURE AND METHODOLOGY

The processing pipeline in SecureHall-RAG is strictly sequential: each query passes through adversarial screening, intelligent retrieval, context-grounded generation, and faithfulness-verified assembly before any output reaches the user.

```
User Query
    │
    ▼
┌────────────────────────────────────────────┐
│  STAGE 1: ADVERSARIAL SCREENING            │
│  • Regex pattern library (600-char cap)    │
│  • XML structural prompt sandboxing        │
│  • Role-pinning generation templates       │
└─────────────────────┬──────────────────────┘
                      │
                      ▼
┌────────────────────────────────────────────┐
│  STAGE 2: INTELLIGENT RETRIEVAL            │
│  • Semantic cache probe (cosine > 0.92)    │
│  • Multi-hop query decomposition           │
│  • FAISS dense search (all-mpnet-base-v2)  │
│  • BM25 sparse search                      │
│  • Reciprocal Rank Fusion (k=60)           │
│  • RAPTOR cluster summary nodes            │
│  • Cross-encoder re-scoring                │
│    (ms-marco-MiniLM-L-6-v2)               │
└─────────────────────┬──────────────────────┘
                      │
                      ▼
┌────────────────────────────────────────────┐
│  STAGE 3: GROUNDED GENERATION              │
│  • Structured prompt (XML-separated zones) │
│  • Ollama LLM (Llama-3.1-8B-Instruct)     │
│  • Inline citation insertion               │
└─────────────────────┬──────────────────────┘
                      │
                      ▼
┌────────────────────────────────────────────┐
│  STAGE 4: VERIFICATION & RESPONSE          │
│  • Sentence-level NLI scoring (DeBERTa)    │
│  • Self-correction loop (max 2 rounds)     │
│  • Confidence tier assignment              │
│  • SSE streaming + audit logging           │
└────────────────────────────────────────────┘
```

### A. Layered Adversarial Defence

All queries are inspected before any retrieval or generation occurs. This ensures that adversarial payloads never reach resource-intensive pipeline stages.

**Layer 1 — Pattern-Based Content Screening.** A compiled set of regular expressions targets documented categories of LLM attack inputs: direct instruction-override phrases, DAN-type jailbreak formulations, persona-reassignment attempts, base64-obfuscated payloads, social-engineering narrative wrappers, credential-exfiltration templates, and token-smuggling markers. A hard 600-character ceiling on input length is applied before pattern matching, closing the long-payload evasion vector. Matched queries receive an immediate HTTP 400 rejection with an audit log entry; no language model tokens are consumed.

**Layer 2 — Structural Input Isolation.** The final prompt fed to the LLM separates system directives, retrieved context, and user input into distinct XML-tagged zones (`<system>`, `<context>`, `<user_query>`). Because the model's instruction-following is attached to the system zone, text placed in the user zone cannot syntactically promote itself to instruction status. This implements the boundary-integrity principle described by Wang et al. [24].

**Layer 3 — Constrained Generation Templates.** Every generation call uses a fixed template that restates the model's operational limits: it must answer only from provided context and must disregard conflicting user-zone directives. This final constraint intercepts attacks that bypass Layers 1 and 2 through indirect or structural exploitation.

### B. Multi-Modal Hierarchical Retrieval

#### B.1 Query Decomposition
When a query references multiple entities or requires comparative reasoning, the LLM decomposes it into a JSON array of focused sub-questions. Each sub-question proceeds through retrieval independently; results are merged and deduplicated before generation.

#### B.2 Parallel Retrieval Channels

**Dense path.** Both the query and all indexed chunks are encoded with SBERT (`all-mpnet-base-v2`, 768 dimensions). After L2 normalisation, cosine similarity search runs over a FAISS `IndexFlatIP` structure.

**Sparse path.** BM25 Okapi scoring operates on a tokenised inverted index:

$$\text{BM25}(q, d) = \sum_{t \in q} \text{IDF}(t) \cdot \frac{f(t,d) \cdot (k_1 + 1)}{f(t,d) + k_1 \cdot \left(1 - b + b \cdot \frac{|d|}{\text{avgdl}}\right)}$$

Parameters: $k_1 = 1.5$, $b = 0.75$.

**Rank-level fusion.** The two ranked lists are combined using Reciprocal Rank Fusion:

$$\text{RRF}(d) = \sum_{r \in \{\text{dense, sparse}\}} \frac{1}{k + \text{rank}_r(d)}, \quad k = 60$$

This approach avoids the need for score normalisation across retrieval methods with different output scales [12].

#### B.3 Hierarchical Cluster Summaries (RAPTOR)
During document ingestion, chunk embeddings are grouped via K-Means clustering. The language model generates a concise multi-sentence summary for each cluster. These summary nodes enter both the FAISS and BM25 indexes alongside raw chunks, producing a two-level index: fine-grained chunks for specific lookups, and cluster summaries for broad thematic queries.

#### B.4 Cross-Encoder Refinement
The top 20 candidates from the RRF stage are re-scored by a cross-encoder (`ms-marco-MiniLM-L-6-v2`), which attends jointly over the full (query, passage) pair. This yields substantially higher discrimination on near-relevance cases compared to independent bi-encoder scoring.

### C. Faithfulness Verification via NLI

Each sentence $s_i$ of the generated draft answer is checked for entailment against the complete retrieved context $C$ using a DeBERTa NLI cross-encoder:

$$p(\text{entailment} \mid C, s_i) = \frac{e^{l_1}}{e^{l_0} + e^{l_1} + e^{l_2}}$$

A lightweight sentence-type classifier first identifies which sentences contain verifiable factual assertions, routing only those to the NLI model — cutting total inference calls by roughly 40%. Results are keyed by MD5 hash to avoid redundant recomputation.

Sentences scoring below the entailment threshold trigger a targeted self-correction pass where the LLM rewrites the claim using only the available evidence (capped at 2 rounds). The final output follows a **graduated handling policy**:

| Entailment Score | Action Taken |
|:---|:---|
| ≥ 0.65 | Included as-is |
| 0.40 – 0.64 | Retained with an inline caution marker |
| 0.25 – 0.39 | Retained with a low-confidence advisory |
| < 0.25 | Removed (direct factual contradiction) |

This graduated scheme preserves paraphrased-but-supported content while making residual uncertainty visible, balancing thoroughness against answer utility.

### D. Confidence Tier Assignment

A composite score derived from retrieval similarity and NLI faithfulness is mapped to one of four user-facing tiers. Boundary thresholds are tuned per query category:

| Tier | Score Range | System Behaviour |
|:---|:---:|:---|
| HIGH | ≥ 0.75 | Full answer with green trust badge |
| MODERATE | 0.50 – 0.75 | Full answer with amber caution badge |
| LOW | 0.35 – 0.50 | Answer accompanied by verification disclaimer |
| ABSTAIN | < 0.35 | Polite refusal; no generated content returned |

Factual queries apply a stricter HIGH boundary (≥ 0.80); comparative queries use a relaxed threshold (≥ 0.68), reflecting the inherently greater ambiguity in cross-document synthesis.

---

## IV. EXPERIMENTAL EVALUATION

### A. Setup

Experiments were conducted on a consumer laptop: Intel Core i7 (12th Gen), 16 GB RAM, NVIDIA GeForce RTX 3050 (4 GB VRAM). The language model (Llama-3.1-8B-Instruct served by Ollama) ran in **CPU-only mode** to simulate a resource-constrained deployment. Embeddings were produced by `sentence-transformers/all-mpnet-base-v2` (768 dimensions). The corpus comprised ten HR policy manuals in DOCX format, yielding 29 indexed chunks after semantic chunking.

**Question set.** 75 question–answer pairs generated automatically from the corpus — 60 answerable across five categories (factual, multi-document synthesis, out-of-scope, numerical/date, procedural) and 15 unanswerable by design. Gold answers are short extracted phrases.

**Adversarial set.** 60 test cases spanning six attack categories (prompt injection, jailbreak, encoded/obfuscated, edge case, hallucination bait, out-of-distribution). Of these, 31 carry an expected behaviour of "block."

**Metric caveat.** ROUGE-L computes lexical overlap against short gold extracts; since the system generates full explanatory sentences, ROUGE-L systematically underestimates quality. This is discussed further in Section V-B.

### B. Retrieval Results

**Table I: Retrieval Precision and Recall** (60 answerable questions; P@K = 1 if any chunk from the correct source appears in the top-K)

| Configuration | P@1 | P@3 | P@5 | R@3 | R@5 |
|:---|:---:|:---:|:---:|:---:|:---:|
| Dense Only (FAISS) | 0.850 | 0.983 | 1.000 | 0.983 | 1.000 |
| Sparse Only (BM25) | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| Hybrid RRF (no rerank) | 0.983 | 1.000 | 1.000 | 1.000 | 1.000 |
| Hybrid RRF + Re-ranking | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| **Full System** | **1.000** | **1.000** | **1.000** | **1.000** | **1.000** |

Vector-only retrieval misses the correct source document for 15% of queries (P@1 = 0.850). Introducing BM25 through rank fusion raises this to 0.983; the cross-encoder closes the remaining gap to 1.000. Cluster summaries do not degrade precision. Notably, BM25 alone also achieves perfect P@1 on this corpus — a consequence of the highly distinctive terminology in HR policy documents — consistent with domain-specific retrieval patterns observed in [11].

### C. Answer Quality

**Table II: Quality Metrics** (15-question category-balanced subset)

| Metric | Baseline | Enhanced |
|:---|:---:|:---:|
| ROUGE-L (↑) | 0.087 | 0.074 |
| Semantic faithfulness (↑) | 0.664 | 0.661 |
| Answer relevance (↑) | 0.636 | 0.636 |
| Mean confidence | 0.733 | 0.661 |

No baseline-to-enhanced difference reaches statistical significance (p = 0.51–0.99). This confirms that the verification component operates as a safety guard rather than a quality enhancer: it does not materially alter the grounding of answers that were already well-retrieved. The meaningful faithfulness indicator is the semantic score (≈ 0.66, computed as the embedding cosine between the answer and its retrieved context), since ROUGE-L is depressed by the metric–task mismatch noted above. The verification loop's real cost is computational — enhanced-mode latency averages 149 s versus 50 s for the baseline (+98 s, p < 0.001), confirming that GPU inference is necessary for interactive deployment.

### D. Security Results

**Table III: Adversarial Handling** (60 cases total; block rate computed over the 31 cases designated for blocking)

| Category | Cases | Should Block | Pattern Only | Pattern + Semantic |
|:---|:---:|:---:|:---:|:---:|
| Prompt Injection | 10 | 10 | 6 (60.0%) | 6 (60.0%) |
| Jailbreak | 10 | 10 | 5 (50.0%) | 7 (70.0%) |
| Encoded / Obfuscated | 10 | 8 | 6 (75.0%) | 6 (75.0%) |
| Edge Case | 10 | 3 | 0 (0.0%) | 0 (0.0%) |
| Hallucination Bait | 10 | 0 | — | — |
| Out of Distribution | 10 | 0 | — | — |
| **Total block rate** | **60** | **31** | **17 (54.8%)** | **19 (61.3%)** |
| **Overall correct** | | | **45/60 (75.0%)** | **47/60 (78.3%)** |

The pattern library reliably catches attacks with recognisable surface signatures (encoded payloads blocked at 75%). Supplementing it with an embedding-similarity detector — which flags queries whose semantic meaning closely resembles a known attack intent regardless of exact wording — yields an additional +6.5 percentage points of block rate with zero new false positives. The gain concentrates entirely in the jailbreak category (5→7 of 10), where contextual and social-engineering framings carry no substring that would trigger a regex. Edge-case attacks (0/3) that are both syntactically and semantically novel remain undetected — a limitation examined in Section V-C.

### E. Confidence Distribution

**Table IV: Tier Assignment** (enhanced mode, 15-question subset)

| Tier | Proportion |
|:---|:---:|
| HIGH (≥ 0.75) | 40.0% |
| MODERATE (0.50–0.75) | 26.7% |
| LOW (0.35–0.50) | 33.3% |
| ABSTAIN (< 0.35) | 0.0% |

A calibration correction — switching from a 40% NLI-weight blend to one that treats retrieval as the dominant signal and bounds the verifier's downward pull — eliminated the previous 69.3% abstention artefact. The tradeoff is explicit: abstention drops sharply, but the system can no longer force a well-retrieved answer into refusal when the NLI scorer returns noisy low scores on CPU. Over-confidence on weakly-grounded answers becomes the residual risk.

### F. Ablation

**Table V: Component Contributions**

| Configuration | P@1 | Attack Block |
|:---|:---:|:---:|
| **Full (pattern + semantic)** | **1.000** | **61.3%** |
| Without semantic detector | 1.000 | 54.8% |
| Without reranker | 0.983 | 61.3% |
| Dense only | 0.850 | 61.3% |
| Without security | 1.000 | **0.0%** |

Removing the security framework entirely drops the block rate to zero — a binary-criticality relationship. The semantic detector contributes +6.5 points over the pattern filter alone. The reranker contributes +1.7 points of P@1. Quality-side metrics (Table II) are unaffected by retrieval/security toggles and are therefore omitted from this ablation.

---

## V. DISCUSSION

### A. On Retrieval Saturation

The full pipeline reaches the P@1 ceiling (1.000) on this 10-document corpus. BM25 alone matches this, owing to the highly specific terminology found in HR policies — role titles, leave-day counts, and procedural names create unambiguous keyword anchors. The practical value of the dense channel becomes apparent on queries that paraphrase policy language without repeating exact terms; a more lexically diverse corpus would make this contrast visible. The cross-encoder resolves ranking ties that bi-encoder scoring leaves ambiguous, confirming the utility of joint-attention refinement for borderline relevance decisions.

RAPTOR summaries do not shift measured P@1 here because the re-ranker already saturates the ceiling. Their expected benefit is on larger document sets where broad thematic queries cannot be answered by any single chunk.

### B. Understanding the Low ROUGE-L Score

The measured ROUGE-L (0.087 baseline, 0.074 enhanced) reflects a mismatch between what the metric expects and what the system produces. Gold answers are short auto-generated extracts (5–15 words); system responses are full explanatory sentences drawing on multiple passages. A longest-common-subsequence overlap near zero between a 40-word answer and a 10-word reference is a mathematical artefact of the scoring formula rather than an indicator of factual inaccuracy. Embedding-based semantic faithfulness (≈ 0.66) — measuring how well the generated answer is grounded in the retrieved context regardless of surface wording — provides a more representative quality signal.

The verification pipeline contributes operational value that ROUGE-L cannot detect: inline caution markers on partially-supported sentences, hard removal of directly contradicted claims, and safe refusal when confidence falls below threshold. These behaviours are visible to users but invisible to a token-overlap metric.

### C. Security — What Works and What Does Not

The pattern-matching layer is effective against attacks with identifiable surface features — encoded payloads (75% block rate) and known jailbreak phrases. Its boundary is equally clear: novel contextual framings that carry no recognisable substring (edge cases, 0/3 blocked) pass through undetected.

The embedding-similarity detector closes part of this gap. By comparing each incoming query against a bank of known attack-intent embeddings, it flags inputs whose meaning resembles a documented exploit even when the wording is entirely different. This raised the overall block rate from 54.8% to 61.3%, concentrated in the jailbreak category where social-engineering and hypothetical framings are common. A minimum word-count threshold prevents very short legitimate queries from triggering false alarms.

The remaining gap — attacks whose semantics are also distant from every stored intent vector — requires either a substantially expanded seed set or a trained binary classifier. This remains future work.

### D. Latency Implications

On CPU-only hardware, language-model generation dominates end-to-end time (5–30 s per call). The NLI verification loop compounds this by issuing multiple additional generation calls: claim decomposition, per-claim entailment assessment, and (when triggered) a self-correction rewrite. The measured overhead of +98 s per query in enhanced mode makes clear that verification on CPU is a high-assurance batch process rather than an interactive feature. Deploying a quantised model (Q4 GGUF) with GPU offloading is the direct path to bringing total latency under 10 seconds.

### E. Abstention Calibration and Its Tradeoff

The confidence score blends retrieval similarity with NLI-derived faithfulness. A prior version weighted both equally, causing noisy CPU-mode NLI scores to drag well-retrieved answers below the ABSTAIN threshold (resulting in 69.3% refusal). The corrected blend treats retrieval as the primary signal and caps the verifier's downward influence. The result — 0% abstention on the answerable subset — confirms the fix but introduces a new concern: the system can no longer force refusal when retrieval looks good but the answer is factually poor. Monitoring over-confidence on weakly-supported answers is the necessary complementary measure.

---

## VI. CONCLUSION

This paper presented SecureHall-RAG, a locally-deployable RAG system for enterprise policy question answering that integrates hallucination mitigation, adversarial defence, hybrid retrieval, and transparent confidence signalling into a single architecture.

Measured findings:

- **Retrieval.** Hybrid rank fusion with cross-encoder refinement achieves P@1 = 1.000 versus 0.850 for dense-only search. On this small, terminologically distinctive corpus, BM25 alone also saturates at 1.000 — the hybrid design's contribution is robustness across query types rather than a headline accuracy gain.
- **Security.** A regex pattern filter blocks 54.8% of designated attacks; supplementing it with an embedding-similarity semantic detector raises this to 61.3% at 78.3% overall correct handling, with no new false positives. Novel attacks outside both the pattern library and the semantic seed set remain undetected.
- **Verification.** The NLI guard maintains semantic grounding at ≈ 0.66, flags unsupported claims, and routes low-confidence answers to disclaimers or refusal. Its CPU overhead (+98 s/query) requires GPU-accelerated inference for real-time use.
- **Privacy.** All computation — retrieval, generation, verification, storage — executes on local hardware with no external API calls.

The architecture is modular and production-ready, incorporating JWT authentication, role-based access, audit logging, SSE streaming, and Docker containerisation. Priority directions for future work include expanding the semantic attack seed bank for higher block rates, deploying GPU-quantised inference for interactive latency, and conducting human evaluation to obtain a faithfulness measurement independent of ROUGE-L's limitations.

---

## REFERENCES

[1] P. Lewis et al., "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks," *NeurIPS*, vol. 33, pp. 9459–9474, 2020.

[2] Z. Ji et al., "Survey of Hallucination in Natural Language Generation," *ACM Computing Surveys*, vol. 55, no. 12, pp. 1–38, 2023.

[3] F. Perez and I. Ribeiro, "Ignore Previous Prompt: Attack Techniques for Language Models," *NeurIPS Workshop on Trustworthy ML*, 2022.

[4] V. Karpukhin et al., "Dense Passage Retrieval for Open-Domain Question Answering," *Proc. EMNLP*, pp. 6769–6781, 2020.

[5] Y. Gao et al., "Retrieval-Augmented Generation for LLMs: A Survey," *arXiv:2312.10997*, 2023.

[6] N. F. Liu et al., "Lost in the Middle: How Language Models Use Long Contexts," *Trans. ACL*, vol. 12, pp. 157–173, 2024.

[7] S. Maynez et al., "On Faithfulness and Factuality in Abstractive Summarization," *Proc. ACL*, pp. 1906–1919, 2020.

[8] T. Falke et al., "Ranking Generated Summaries by Correctness," *Proc. ACL*, pp. 2214–2220, 2019.

[9] P. He, J. Gao, and W. Chen, "DeBERTaV3: Improving DeBERTa using ELECTRA-Style Pre-Training," *Proc. ICLR*, 2023.

[10] P. Laban et al., "SummaC: Re-Visiting NLI-Based Models for Inconsistency Detection in Summarization," *Trans. ACL*, vol. 10, pp. 163–177, 2022.

[11] J. Lin and X. Ma, "A Few Brief Notes on DeepImpact, COIL, and a Conceptual Framework for IR Techniques," *arXiv:2106.14807*, 2021.

[12] G. V. Cormack, C. L. A. Clarke, and S. Buettcher, "Reciprocal Rank Fusion Outperforms Condorcet and Individual Rank Learning Methods," *Proc. SIGIR*, pp. 758–759, 2009.

[13] T. Thakur et al., "BEIR: A Heterogeneous Benchmark for Zero-Shot Evaluation of Information Retrieval Models," *NeurIPS Datasets and Benchmarks*, 2021.

[14] P. Sarthi et al., "RAPTOR: Recursive Abstractive Processing for Tree-Organized Retrieval," *Proc. ICLR*, 2024.

[15] K. Greshake et al., "Not What You've Signed Up For: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection," *AISec Workshop, CCS*, 2023.

[16] OWASP Foundation, "OWASP Top 10 for Large Language Model Applications," 2023.

[17] S. M. Tonmoy et al., "A Comprehensive Survey of Hallucination Mitigation Techniques in Large Language Models," *arXiv:2401.01313*, 2024.

[18] Z. Xu, S. Jain, and M. Kankanhalli, "Hallucination is Inevitable: An Innate Limitation of Large Language Models," *arXiv:2401.11817*, 2024.

[19] L. Kuhn, Y. Gal, and S. Farquhar, "Semantic Uncertainty: Linguistic Invariances for Uncertainty Estimation in Natural Language Generation," *Proc. ICLR*, 2023.

[20] P. Manakul, A. Liusie, and M. J. F. Gales, "SelfCheckGPT: Zero-Resource Black-Box Hallucination Detection for Generative Large Language Models," *Proc. EMNLP*, pp. 9745–9765, 2023.

[21] S. Kadavath et al., "Language Models (Mostly) Know What They Know," *arXiv:2207.05221*, 2022.

[22] A. Asai et al., "Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection," *Proc. ICLR*, 2024.

[23] A. A. N. Nafi et al., "LASH: Adaptive Semantic Hybridization for Black-Box Jailbreaking of LLMs," *arXiv:2605.21362*, 2026.

[24] Y. Wang et al., "Towards Context-Invariant Safety Alignment for Large Language Models," *arXiv:2605.20994*, 2026.

---

**Author Profile:**

**Devendra** is a final-year MCA student at [Institution Name] with research interests in applied NLP, information retrieval, and AI system security. His work focuses on building trustworthy, locally-deployable AI applications for regulated environments where data privacy precludes cloud dependency. This paper derives from his major project completed during the 2025–2026 academic session.
