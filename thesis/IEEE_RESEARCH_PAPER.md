# SecureHall-RAG: A Secure, Hallucination-Resistant Retrieval-Augmented Generation System for Enterprise Policy Question Answering

**Devendra**  
Department of Computer Science, MCA Program  
*[Institution Name]*

---

## Abstract

Organisations manage extensive internal documentation — policy manuals, HR guidelines, compliance frameworks, IT security protocols — yet employees struggle to retrieve precise answers efficiently. Retrieval-Augmented Generation (RAG) provides a viable automation path, but production deployments persistently exhibit four weaknesses: factual claims unsupported by retrieved passages, susceptibility to adversarial prompt manipulation, retrieval pipelines that fail on certain query types, and responses that carry no indication of reliability. This paper introduces **SecureHall-RAG**, a fully local system tackling all four weaknesses through an integrated architecture. It combines a three-layer adversarial screening pipeline, a hybrid retrieval engine fusing FAISS dense search (`all-mpnet-base-v2`, 768-dim) with BM25 keyword matching through Reciprocal Rank Fusion, cross-encoder re-scoring, RAPTOR hierarchical cluster summaries, sentence-level NLI faithfulness verification with iterative self-correction, LLM-driven query decomposition, and a four-tier calibrated confidence framework. On a 10-document enterprise policy corpus (60 answerable questions), the full pipeline achieves Precision@1 = **1.000** versus **0.850** for dense-only search. Since BM25 independently saturates at 1.000 on this terminologically distinctive corpus, the hybrid design demonstrates robustness rather than a headline margin. Against a 60-case adversarial set (31 should-block), a pattern filter intercepts **54.8%** of attacks; supplementing it with an embedding-similarity semantic detector raises this to **61.3%** at **78.3%** overall correct handling with zero false positives. NLI verification guards answer faithfulness (semantic grounding ≈ 0.66) at a CPU cost of **+98 s** per query, establishing that GPU inference is necessary for interactive latency. No cloud service is required.

**Index Terms** — Retrieval-Augmented Generation, Hallucination Prevention, Natural Language Inference, Prompt Injection, Enterprise QA, Uncertainty Quantification, RAPTOR.

---

## I. Introduction

In most organisations, the knowledge employees need to do their jobs — leave entitlements, security procedures, disciplinary processes, compliance obligations — exists in written documents that are poorly accessible. Finding a specific fact requires either searching manually across file systems, asking colleagues who may or may not remember correctly, or submitting a helpdesk request and waiting.

Language models paired with retrieval infrastructure changed what is technically feasible. The RAG pattern [1] retrieves relevant passages at query time and grounds the model's response in those passages rather than in parametric memory. This reduces fabrication substantially. Enterprise deployment, however, surfaces persistent problems:

- **P1 — Hallucination.** Models generate claims their retrieved context does not support [2]. Xu et al. [31] demonstrate formally that this is a structural property of finite-parameter statistical learning, making post-generation verification architecturally necessary.
- **P2 — Adversarial Manipulation.** Prompt injection [3], indirect injection via retrieved documents [21], and semantic hybridisation attacks [36] allow malicious users to override system behaviour or exfiltrate private context.
- **P3 — Retrieval Gaps.** Policy corpora require both vocabulary-level precision and semantic generalisation. Any single retrieval modality excels at one while failing the other.
- **P4 — Opacity.** Without source citations and confidence signals, users cannot distinguish trustworthy answers from fabricated ones. Roy et al. [38] show that AI-generated text is increasingly indistinguishable from human writing, making explicit uncertainty indicators a practical necessity.

SecureHall-RAG addresses all four simultaneously in a single locally-deployable system. Its contributions:

1. **Layered Security Pipeline** — content filter (regex, 600-char cap), XML structural sandboxing, and role-constrained generation templates.
2. **Hybrid Hierarchical Retrieval** — FAISS + BM25 fused by RRF, cross-encoder re-ranking, RAPTOR [16] cluster summaries.
3. **NLI Verification with Self-Correction** — per-sentence entailment scoring (DeBERTa [10], [11]) with automated rewriting of poorly-supported claims.
4. **Multi-hop Decomposition** — LLM-driven question splitting for compound queries.
5. **Four-Tier Confidence Framework** — composite scores bucketed into HIGH / MODERATE / LOW / ABSTAIN, calibrated per query type.

---

## II. Related Work

### A. Retrieval-Augmented Generation

Lewis et al. [1] paired a neural retriever with a conditional generator to ground outputs in external passages. Karpukhin et al. [4] formalised dense passage retrieval via dual-encoder training. Gao et al. [5] survey subsequent improvements across pre-retrieval, retrieval, and post-retrieval stages. Liu et al. [6] identified that models underutilise content positioned in the middle of long contexts, motivating hierarchical representations. Recski et al. [33] and Das et al. [34] confirm in scholarly and legal QA settings that post-retrieval verification is necessary in high-stakes domains.

### B. Hallucination

Ji et al. [2] and Tonmoy et al. [29] distinguish intrinsic hallucinations (contradicting the source) from extrinsic ones (adding unverifiable content). Xu et al. [31] proved this is structurally inevitable in finite-capacity models. Kalai et al. [32] traced much of it to contradictory pre-training data. Maynez et al. [7] established that NLI-based faithfulness scores track human judgements, which is why SummaC [11] and this work use them as the primary verification signal.

### C. Hybrid Retrieval

Dense and sparse retrieval address complementary needs [12]: BM25 matches exact vocabulary while dense models generalise to paraphrases. Cormack et al. [13] introduced RRF for score-normalisation-free fusion; BEIR [14] validated its cross-domain competitiveness. Fernandes and Kanjilal [35] confirmed that hierarchical cluster retrieval improves recall on consumer hardware, supporting our use of RAPTOR [16].

### D. LLM Security

Perez and Ribeiro [3] characterised prompt injection. Greshake et al. [21] extended it to indirect injection via retrieved documents. Nafi et al. [36] (LASH) demonstrated that blended benign/malicious payloads evade pattern filters — a limitation of our current system. Wang et al. [37] argue the sustainable path is alignment-level safety, which we treat as the long-term direction while using layered filtering pragmatically.

### E. Uncertainty

Kuhn et al. [23] compute entropy over meaning-equivalent answer clusters rather than tokens. Manakul et al. [24] use cross-sample consistency. Kadavath et al. [25] showed prompted self-assessment is a viable lightweight confidence strategy. These inform our four-tier framework.

---

## III. System Architecture

The pipeline processes each query through four stages sequentially: adversarial screening → intelligent retrieval → grounded generation → faithfulness-verified assembly.

### A. Three-Layer Security

- **Layer 1 — Content Filter.** Compiled regex patterns covering 27+ attack categories, preceded by a 600-character hard cap. Matched queries are rejected with an audit entry; no LLM tokens consumed.
- **Layer 2 — Structural Sandboxing.** System directives, retrieved context, and user text occupy distinct XML zones, preventing user-zone content from overriding system-zone instructions [37].
- **Layer 3 — Role-Pinning Templates.** Fixed generation templates restate model constraints at invocation, catching indirect attacks that cleared earlier layers.

### B. Hybrid Hierarchical Retrieval

1. **Multi-hop Decomposition.** Compound queries are split by the LLM into focused sub-questions.
2. **Fused Search.** FAISS dense (all-mpnet-base-v2, 768-dim) and BM25 sparse run in parallel. Outputs merged by RRF ($k=60$).
3. **RAPTOR Summaries.** Chunk embeddings clustered via K-Means; LLM-generated abstractive summaries indexed alongside raw chunks.
4. **Cross-Encoder Re-ranking.** Top-20 RRF candidates re-scored by `ms-marco-MiniLM-L-6-v2` using joint attention.

### C. NLI Verification

Each sentence $s_i$ scored for entailment against context $C$ via DeBERTa:

$$p(\text{entailment} \mid C, s_i) = \frac{e^{l_1}}{e^{l_0} + e^{l_1} + e^{l_2}}$$

Sentence-type classifier skips non-factual sentences (~40% reduction). Cached by MD5. Sentences below threshold trigger self-correction (max 2 rounds). Graduated output policy: ≥0.65 unchanged; 0.40–0.64 + warning; 0.25–0.39 + low-confidence advisory; <0.25 removed.

### D. Uncertainty Framework

Composite score (retrieval + NLI) bucketed per query type. Factual: HIGH ≥ 0.80; comparative: HIGH ≥ 0.68.

| Tier | Range | Behaviour |
|:---|:---:|:---|
| HIGH | ≥ 0.75 | Green badge, full answer |
| MODERATE | 0.50–0.75 | Amber badge |
| LOW | 0.35–0.50 | Verification disclaimer |
| ABSTAIN | < 0.35 | Safe refusal |

---

## IV. Evaluation

### A. Setup

Consumer laptop (i7-12th, 16GB, RTX 3050 4GB). Llama-3.1-8B via Ollama in CPU-only mode. Corpus: 10 HR manuals, 29 chunks. Benchmark: 75 questions (60 answerable), auto-generated gold answers. Adversarial: 60 cases (31 should-block). Quality on 15-question subset.

### B. Retrieval

**Table I** (60 answerable; P@K=1 if correct document in top-K)

| Config | P@1 | P@3 | P@5 | R@3 | R@5 |
|:---|:---:|:---:|:---:|:---:|:---:|
| Dense Only | 0.850 | 0.983 | 1.000 | 0.983 | 1.000 |
| BM25 Only | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| Hybrid (no rerank) | 0.983 | 1.000 | 1.000 | 1.000 | 1.000 |
| **Full System** | **1.000** | **1.000** | **1.000** | **1.000** | **1.000** |

Dense-only misses 15% of queries. BM25 fusion raises P@1 to 0.983; cross-encoder closes the gap. BM25 alone also saturates — corpus-specific lexical distinctiveness. Hybrid design proves robustness, not a headline gain.

### C. Answer Quality

**Table II** (15-question subset)

| Metric | Baseline | Enhanced |
|:---|:---:|:---:|
| ROUGE-L (↑) | 0.087 | 0.074 |
| Semantic faithfulness (↑) | 0.664 | 0.661 |
| Answer relevance (↑) | 0.636 | 0.636 |
| Confidence | 0.733 | 0.661 |

Differences not significant (p=0.51–0.99). Verification is a guard, not a generator. Semantic faithfulness (≈0.66) is the meaningful signal; ROUGE-L depressed by metric mismatch. Verification cost: +98 s/query on CPU.

### D. Security

**Table III** (60 cases, 31 should-block)

| Category | Should Block | Pattern | + Semantic |
|:---|:---:|:---:|:---:|
| Prompt Injection | 10 | 6 (60%) | 6 (60%) |
| Jailbreak | 10 | 5 (50%) | 7 (70%) |
| Encoded | 8 | 6 (75%) | 6 (75%) |
| Edge Case | 3 | 0 (0%) | 0 (0%) |
| **Total** | **31** | **17 (54.8%)** | **19 (61.3%)** |
| **Overall correct** | | **75.0%** | **78.3%** |

Semantic detector adds +6.5 points (jailbreak category), no false positives. Novel vectors outside pattern library and seed set remain undetected [36].

### E. Confidence Tiers

**Table IV** (enhanced, 15-question subset)

| Tier | % |
|:---|:---:|
| HIGH | 40.0% |
| MODERATE | 26.7% |
| LOW | 33.3% |
| ABSTAIN | 0.0% |

Calibration fix cut ABSTAIN from 69.3% to 0%. Tradeoff: reduced verifier power over well-retrieved but weakly-grounded answers.

### F. Ablation

**Table V**

| Config | P@1 | Block Rate |
|:---|:---:|:---:|
| **Full** | **1.000** | **61.3%** |
| − Semantic | 1.000 | 54.8% |
| − Reranker | 0.983 | 61.3% |
| Dense only | 0.850 | 61.3% |
| − Security | 1.000 | **0%** |

Security removal: total failure. Semantic detector: +6.5 points. Reranker: +1.7 P@1 points.

---

## V. Discussion

### A. Retrieval Saturation

The full pipeline saturates P@1 on this 10-document corpus. BM25 alone matches this ceiling, owing to highly specific policy terminology — role titles, numerical entitlements, procedural keywords create unambiguous anchors. Dense retrieval's value emerges on paraphrased queries lacking exact term overlap; a larger, more lexically diverse corpus would make this visible. The cross-encoder resolves ranking ties that bi-encoder scoring leaves ambiguous.

RAPTOR summaries add no measurable P@1 here since the reranker already hits the ceiling. Their contribution is expected on larger corpora with broad thematic queries no single chunk satisfies.

### B. Quality Metric Limitations

ROUGE-L (0.087/0.074) reflects a metric–task mismatch: short gold extracts versus full system sentences. Embedding-based semantic faithfulness (≈0.66) — measuring how well the answer is grounded in context regardless of surface wording — is the more representative signal. BERTScore or human evaluation would provide the most meaningful faithfulness measurement.

The verification pipeline's operational value — inline warnings on partially-supported claims, hard redaction of contradictions, and ABSTAIN responses for low-confidence queries — is real but invisible to a token-overlap metric.

### C. Security Boundaries

Pattern matching handles attacks with detectable surface features (encoded payloads 75%, known jailbreak phrases, override strings) at 54.8%. The semantic detector extends this to contextual framings by comparing query embeddings against stored attack intents — raising coverage to 61.3% with no false positives, concentrated in the jailbreak category. Attacks semantically distant from every seed intent (edge cases, 0/3) remain the gap.

The path forward is broader seed coverage or a trained classifier in the near term, and alignment-level safety [37] as the long-term direction.

### D. Latency

LLM generation dominates (5–30 s/call on CPU). The verification loop compounds this with multiple additional calls (claim decomposition, per-claim scoring, self-correction) — measured total overhead +98 s/query. On CPU, enhanced mode is high-assurance batch processing. GPU + GGUF Q4 quantisation is the path to interactive latency.

---

## VI. Conclusion

SecureHall-RAG demonstrates that production-quality, fully local enterprise document QA can simultaneously achieve strong retrieval, layered adversarial defence, post-generation verification, and calibrated confidence signalling.

- **Retrieval:** P@1 = 1.000 (hybrid + reranker) vs. 0.850 (dense-only). Near-saturated corpus; value is robustness.
- **Security:** 54.8% → 61.3% attack-block (pattern + semantic), 78.3% correct, no false positives.
- **Verification:** Semantic faithfulness ≈ 0.66; +98 s/query on CPU. GPU required for interactive use.
- **Privacy:** Zero cloud dependency.

Future directions: expanded attack-seed coverage, GPU-quantised inference, human faithfulness evaluation, larger evaluation corpus.

---

## References

[1] P. Lewis et al., "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks," *NeurIPS*, vol. 33, pp. 9459–9474, 2020.
[2] Z. Ji et al., "Survey of Hallucination in Natural Language Generation," *ACM Computing Surveys*, vol. 55, no. 12, 2023.
[3] F. Perez and I. Ribeiro, "Ignore Previous Prompt: Attack Techniques for Language Models," *NeurIPS Workshop*, 2022.
[4] V. Karpukhin et al., "Dense Passage Retrieval for Open-Domain QA," *EMNLP*, pp. 6769–6781, 2020.
[5] Y. Gao et al., "RAG for LLMs: A Survey," *arXiv:2312.10997*, 2023.
[6] N. F. Liu et al., "Lost in the Middle," *Trans. ACL*, vol. 12, pp. 157–173, 2024.
[7] S. Maynez et al., "On Faithfulness and Factuality in Abstractive Summarization," *ACL*, pp. 1906–1919, 2020.
[8] K. Shuster et al., "Retrieval Augmentation Reduces Hallucination," *Findings of EMNLP*, pp. 3784–3803, 2021.
[9] T. Falke et al., "Ranking Generated Summaries by Correctness," *ACL*, pp. 2214–2220, 2019.
[10] P. He et al., "DeBERTaV3," *ICLR*, 2023.
[11] P. Laban et al., "SummaC," *Trans. ACL*, vol. 10, pp. 163–177, 2022.
[12] J. Lin and X. Ma, "DeepImpact, COIL, and IR Techniques," *arXiv:2106.14807*, 2021.
[13] G. V. Cormack et al., "Reciprocal Rank Fusion," *SIGIR*, pp. 758–759, 2009.
[14] T. Thakur et al., "BEIR," *NeurIPS Datasets*, 2021.
[16] P. Sarthi et al., "RAPTOR," *ICLR*, 2024.
[21] K. Greshake et al., "Indirect Prompt Injection," *AISec/CCS*, 2023.
[22] OWASP, "Top 10 for LLM Applications," 2023.
[23] L. Kuhn et al., "Semantic Uncertainty," *ICLR*, 2023.
[24] P. Manakul et al., "SelfCheckGPT," *EMNLP*, pp. 9745–9765, 2023.
[25] S. Kadavath et al., "Language Models Know What They Know," *arXiv:2207.05221*, 2022.
[26] A. Asai et al., "Self-RAG," *ICLR*, 2024.
[29] S. M. Tonmoy et al., "Hallucination Mitigation Survey," *arXiv:2401.01313*, 2024.
[31] Z. Xu et al., "Hallucination is Inevitable," *arXiv:2401.11817*, 2024.
[32] A. T. Kalai et al., "Why Language Models Hallucinate," *arXiv:2509.04664*, 2025.
[33] G. Recski et al., "ACL-Verbatim," *arXiv:2605.21102*, 2026.
[34] S. Das et al., "Fine-Grained Claim-Level RAG for Law," *arXiv:2605.21071*, 2026.
[35] P. Fernandes and R. Kanjilal, "GraphRAG on Consumer Hardware," *arXiv:2605.20815*, 2026.
[36] A. A. N. Nafi et al., "LASH," *arXiv:2605.21362*, 2026.
[37] Y. Wang et al., "Context-Invariant Safety Alignment," *arXiv:2605.20994*, 2026.
[38] R. Roy et al., "Counter Turing Test," *arXiv:2605.20761*, 2026.
[39] J. Ruan et al., "MTR-Suite," *arXiv:2605.20729*, 2026.
