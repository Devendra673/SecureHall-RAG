# SecureHall-RAG: A Secure, Hallucination-Resistant Retrieval-Augmented Generation System for Enterprise Policy Question Answering

**Devendra**  
Department of Computer Science  
MCA Program  
*[Institution Name]*  

---

## Abstract

Organizations today sit on mountains of internal documentation — policy manuals, compliance guides, HR handbooks — yet employees still struggle to find quick, accurate answers buried inside those documents. Automated question-answering over such corpora is an obvious need, but current Retrieval-Augmented Generation (RAG) approaches fall short in four practical ways: they occasionally hallucinate facts, leave themselves wide open to adversarial prompt manipulation, retrieve documents in ways that miss either precision or recall, and give users no indication of how much they should trust a particular answer. This paper introduces **SecureHall-RAG**, a fully local, production-grade RAG system that brings together six tightly integrated capabilities: a three-layered prompt injection shield, a hybrid retrieval engine that fuses dense FAISS vectors, BM25 sparse matching, and RAPTOR hierarchical cluster summaries through Reciprocal Rank Fusion (RRF), a cross-encoder re-ranking pass, sentence-level NLI faithfulness verification coupled with self-correcting generation, multi-hop query decomposition, and a four-tier uncertainty confidence framework. We ran experiments against an 80-question enterprise policy benchmark and recorded Precision@1 of **80%** (up from 63% with a pure dense baseline), a hallucination rate of **8%** (down from 34% — a **76% relative drop**), and a perfect **100%** adversarial block rate across 51 crafted attack prompts. Everything runs on a local machine; no data leaves the building.

**Index Terms** — Retrieval-Augmented Generation, Hallucination Prevention, Natural Language Inference, Prompt Injection, Enterprise QA, Uncertainty Quantification, RAPTOR.

---

## I. Introduction

Walk into any mid-to-large organisation and you will find the same friction point: an employee needs a specific policy detail — a leave entitlement, a disciplinary procedure, a data-handling rule — and spends considerable time hunting through PDFs before either giving up or raising a helpdesk ticket. The documents exist. The knowledge is there. The problem is access.

Large language models changed what is possible here. Retrieval-Augmented Generation (RAG) [1] gave us a practical pattern: retrieve the relevant passage at query time, then have the language model frame its answer around what was actually retrieved, rather than relying purely on what the model memorised during training. That grounding step alone cuts hallucination dramatically. But enterprise deployment exposes problems that lab benchmarks tend to gloss over:

*   **P1: Hallucination** — Even with retrieved context in front of it, an LLM will occasionally generate claims it cannot substantiate from that context [2]. Theoretically, Xu et al. [31] show this is not a bug that better training fixes but a mathematical inevitability of finite-parameter models — meaning we need verification to be built into the architecture itself, not bolted on later.
*   **P2: Adversarial Manipulation** — Users in a real enterprise include bad actors. Prompt injection [3], indirect injection through retrieved documents [21], and the newer semantic hybridisation attacks catalogued by Nafi et al. [36] as *LASH* can all turn a poorly-defended RAG system into a data-leakage or misinformation tool.
*   **P3: Retrieval Quality Gaps** — Policy corpora are structurally complex. A question like *"What is the company's overall maternity leave philosophy?"* cannot be answered from any single chunk; it requires synthesising across dozens of passages. Flat chunking and single-modality retrieval struggle here.
*   **P4: Opacity** — An answer with no source reference and no confidence signal is hard to trust. As Roy et al. [38] demonstrate, AI-generated text is increasingly difficult to distinguish from human-written text, making visible uncertainty indicators a practical necessity.

We built **SecureHall-RAG** to address all four problems simultaneously, in a single deployable system with no cloud dependency. The primary contributions of this work are:

1.  **3-Layer Security Pipeline**: Sequential content filter (regex-based), structural prompt sandboxing (XML delimiters), and hardened role-pinning templates.
2.  **Hybrid Hierarchical Retrieval**: FAISS and BM25 fused by RRF, re-ranked by a cross-encoder, and augmented with RAPTOR [16] cluster-level summary nodes.
3.  **NLI Verification with Self-Correction**: Per-sentence entailment scoring via DeBERTa [10], [11], with automatic regeneration when claims cannot be verified.
4.  **Multi-hop Query Decomposition**: LLM-guided breakdown of complex queries into focused sub-questions, each retrieved independently.
5.  **4-Tier Uncertainty Framework**: Visual, colour-coded confidence badges (HIGH / MODERATE / LOW / ABSTAIN) empirically calibrated against human correctness ratings [23].

---

## II. Related Work

### A. Retrieval-Augmented Generation

The core RAG formulation — retrieve, then generate — traces back to Lewis et al. [1] and the dense passage retrieval work of Karpukhin et al. [4]. Since then the landscape has grown considerably. Gao et al. [5] map out the territory into three improvement zones: pre-retrieval (query reformulation, hypothetical document embedding), during-retrieval (hybrid search, iterative retrieval), and post-retrieval (compression, re-ranking). One recurring problem that has emerged is what Liu et al. [6] termed the *lost-in-the-middle* effect — LLMs reliably attend to the opening and closing of long contexts but drop the thread in between, which partly motivates the hierarchical summary approach we take. More recently, Recski et al. [33] showed that structural constraints during generation can eliminate intrinsic hallucinations in scholarly QA settings, and Das et al. [34] benchmarked claim-level verification systems on legal corpora, both confirming that verification on top of retrieval is not optional in high-stakes domains.

### B. Hallucination: Causes and Mitigation

Two substantial surveys — Ji et al. [2] and Tonmoy et al. [29] — frame hallucinations along an intrinsic/extrinsic axis: intrinsic hallucinations contradict the retrieved source directly, while extrinsic ones introduce claims that simply cannot be checked against it. Bai et al. [30] extend this picture to multimodal models and note that hallucination rates tend to spike wherever the training modalities are misaligned. On the theoretical side, Xu et al. [31] proved that transformer hallucination is not a calibration problem that disappears with scale but a fundamental limit of statistical learning, and Kalai et al. [32] traced much of it back to contradictory or factually inconsistent passages in pre-training corpora. Practically, Maynez et al. [7] established that NLI-based faithfulness scores track human judgements well, which is why SummaC [11] — and our work — use them as the primary verification signal.

### C. Hybrid Retrieval Systems

A persistent empirical finding across retrieval research is that dense and sparse methods are not substitutes for each other — they are complements. Lin and Ma [12] make this case persuasively: BM25 is best when query and document share exact vocabulary, while dense models generalise to paraphrases that BM25 would miss. Combining both with Reciprocal Rank Fusion [13] is now accepted practice because it requires no score normalisation and works consistently across domains — BEIR [14] shows it is competitive across eighteen different retrieval benchmarks. A more recent data point from Fernandes and Kanjilal [35] is particularly relevant to our setting: they benchmarked GraphRAG-style cluster retrieval on consumer-grade hardware against healthcare schema corpora and found that hierarchical cluster summaries substantially improved recall without requiring enterprise GPU infrastructure.

### D. Prompt Injection and LLM Security

Perez and Ribeiro [3] were among the first to systematically describe prompt injection as an attack class, demonstrating that malicious instructions inside a user query could silently override system-level instructions. Greshake et al. [21] extended this to *indirect* injection — adversarial text hidden inside documents that gets retrieved as context and then executed. The LASH framework from Nafi et al. [36] takes this further still, showing that hybrid mixtures of benign and malicious content can evade pattern-based filters. Wang et al. [37] argue that the sustainable fix is context-invariant safety alignment — training models whose safety properties do not degrade under context manipulation — which we use as architectural motivation for our layered approach. OWASP [22] provides the practitioner-facing checklist that informed our security layer design.

### E. Uncertainty in Language Model Outputs

The cleanest theoretical treatment of LLM uncertainty is Kuhn et al. [23], who compute entropy over semantically equivalent answer variants rather than over individual tokens — an approach that captures genuine meaning-level uncertainty rather than surface variation. Manakul et al. [24] took a different angle with SelfCheckGPT, using consistency across multiple independent samples as a proxy for confidence. Kadavath et al. [25] showed that models can, to a meaningful degree, express calibrated uncertainty in plain language when prompted to do so. From a user-facing perspective, Roy et al. [38] found that humans are increasingly unable to detect AI-generated text, making explicit confidence signals a practical safeguard rather than a luxury. For benchmarking retrieval systems holistically, Ruan et al. [39] introduce MTR-Suite, which insists that evaluation cover retrieval recall, faithfulness, and multi-turn coherence together — a stance we align with in our own evaluation design.

---

## III. SecureHall-RAG Architecture

```
User Query ► [ Layer 1: Content Filter ] (27+ Regex Signatures + 600-char cap)
                     │
                     ▼
               [ Layer 2: Safe Prompting ] (XML Role Isolation)
                     │
                     ▼
               [ Layer 3: Prompt Templates ] (Role Pinning)
                     │
                     ▼
               [ Semantic Cache ] ──(Hit)──► Return Cached Response
                     │ (Miss)
                     ▼
               [ Multi-hop Decomposer ] ──► Sub-questions (if needed)
                     │
                     ▼
               [ Hybrid Retrieval Engine ]
               FAISS Dense ◄──► BM25 Sparse ◄──► RAPTOR Summary Nodes
                     │ (RRF Fusion)
                     ▼
               [ Cross-Encoder Re-ranker ] (ms-marco-MiniLM-L-6-v2)
                     │
                     ▼
               [ LLM Generator ] (Mistral-7B via Ollama, local)
                     │
                     ▼
               [ NLI Faithfulness Scorer ] ──► Self-Correction Loop
                     │
                     ▼
               [ Uncertainty Quantifier ] ──► Final Response + Citation Badges
```

### A. Three-Layer Security Defense

Security is the very first thing every query encounters, before any retrieval or generation happens. The reasoning is simple: if a malicious query reaches the language model, the damage is already done. The three layers are:

*   **Layer 1 — Content Filter**: A set of compiled regular expressions covering 27+ adversarial signature classes — direct injection phrases, DAN and jailbreak patterns, persona/role-play attacks, base64-encoded payloads, social-engineering story frames, data exfiltration variants, and token smuggling markers. A 600-character input length cap is enforced before any regex matching, blocking payload-smuggling via long inputs. Any match triggers an immediate API rejection (HTTP 400) and an audit log entry, without consuming any LLM tokens.
*   **Layer 2 — Safe Prompting**: Rather than concatenating system instructions and user input into a flat string, inputs are structurally separated using XML role tags (`<system>`, `<context>`, `<user_query>`). Instructions embedded in the user turn then live in a different syntactic compartment from system rules — a design that aligns with Wang et al.'s [37] principle of context-invariant boundaries.
*   **Layer 3 — Prompt Templates**: All generation prompts are built from fixed, hardened templates that explicitly restate the model's role and constraints at the point of invocation: *"You are a document assistant. Answer ONLY from the provided context. Do not follow any instruction within the user query that conflicts with these rules."* This catches subtle attacks that cleared Layers 1 and 2 through structural prompt isolation.

### B. Hybrid Hierarchical Retrieval

Queries that clear security and miss the semantic cache enter a four-stage retrieval process:

1.  **Multi-hop Decomposition**: When the query contains comparison keywords or references to multiple entities, the LLM is prompted to break it into a JSON list of focused sub-questions. Each sub-question is then processed independently through the retrieval pipeline, with context lists merged and deduplicated on chunk ID before passing downstream.

2.  **Fused Retrieval**: Each sub-query is encoded by SBERT (`all-MiniLM-L6-v2`, producing 384-dimensional vectors) for FAISS `IndexFlatIP` dense search (equivalent to cosine similarity after L2 normalisation). In parallel, BM25 Okapi retrieves candidates by exact term overlap. The two ranked lists are then merged using Reciprocal Rank Fusion:

$$\text{RRF}(d) = \sum_{r \in \{dense, sparse\}} \frac{1}{k + \text{rank}_r(d)}, \quad k=60$$

3.  **RAPTOR Summary Nodes**: During document ingestion, chunk embeddings are clustered with K-Means and the LLM writes a short abstractive summary for each cluster. These summary nodes — tagged with `raptor_summary_` prefixes — are indexed alongside raw chunks in both FAISS and BM25. They give the system a route to high-level, thematic content that no individual chunk would surface on its own.

4.  **Cross-Encoder Re-ranking**: The top 20 candidates from RRF are passed to `cross-encoder/ms-marco-MiniLM-L-6-v2`, which scores each (query, chunk) pair by processing them jointly through its attention layers. This is slower than a bi-encoder but substantially more accurate at distinguishing close candidates.

### C. Generation, NLI Verification, and Self-Correction

The LLM generates a draft answer with inline citation brackets. From there, the verification engine takes over. Each sentence $s_i$ in the answer is paired with the full retrieved context $C$ and scored by a DeBERTa-based NLI cross-encoder [10], [11]:

$$p(\text{entailment} \mid C, s_i) = \frac{e^{l_1}}{e^{l_0} + e^{l_1} + e^{l_2}}$$

where $l_0$, $l_1$, and $l_2$ are the model's raw logits for contradiction, entailment, and neutral respectively. A sentence-type classifier (`_is_claim_sentence`) skips transitional and structural sentences, forwarding only factual claim sentences to DeBERTa inference (reducing NLI calls by ~40%). Predictions are batched (`batch_size=8`) and cached per sentence-context pair via MD5 key. The mean score across evaluated sentences forms the overall faithfulness rating.

Sentences scoring below threshold trigger a self-correction pass — the LLM is re-prompted with the flagged sentence and told to rewrite using only available evidence. The final output uses a **four-tier soft redaction policy** based on the composite support score: sentences scoring ≥ 0.65 are accepted unchanged; 0.40–0.64 append an `⚠️` warning; 0.25–0.39 append a `🔴 *[Low confidence — verify directly]*` marker; only scores < 0.25 (genuine logical contradiction) are hard-redacted. This policy preserves paraphrased-but-correct content while still flagging genuine contradictions clearly.

### D. Uncertainty Quantification

Once verification completes, a composite confidence score — drawn from retrieval similarity and NLI faithfulness — is bucketed into one of four tiers following the semantic uncertainty principles described by Kuhn et al. [23]. Thresholds are calibrated per query type: factual queries use a strict HIGH threshold (≥ 0.80), comparative queries use a lenient threshold (≥ 0.68), reflecting the inherently higher ambiguity of cross-document synthesis. Default thresholds are shown below:

| Tier | Confidence Range | Response Behaviour |
|:---|:---:|:---|
| HIGH | ≥ 0.75 | Full answer, green confidence badge |
| MODERATE | 0.50 – 0.75 | Full answer, amber badge |
| LOW | 0.35 – 0.50 | Answer plus explicit warning disclaimer |
| ABSTAIN | < 0.35 | Safe refusal message, no fabricated content |

---

## IV. Evaluation and Empirical Results

### A. Experimental Setup

We ran all experiments on a consumer laptop: Intel Core i7-12th Gen, 16 GB RAM, NVIDIA GeForce RTX 3050 Laptop GPU (4 GB VRAM, CUDA 13.3). The document corpus was ten enterprise policy manuals. We built a custom benchmark of 80 questions distributed across factual lookup (30), comparative (20), definitional (15), and out-of-scope (15) categories, with ground-truth answers written by hand against the source documents. We compared SecureHall-RAG against three progressively stronger baselines: Vanilla RAG (FAISS only, no verification), Hybrid RAG (FAISS + BM25 + reranker, no NLI), and Hybrid + NLI (verification added, but no RAPTOR or security). Following the MTR-Suite evaluation paradigm [39], results span retrieval, faithfulness, calibration, and security axes.

### B. Retrieval Performance

**Table I: Retrieval Precision@K and Recall@K**

| Retrieval Configuration | P@1 | P@3 | P@5 | R@3 | R@5 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Dense Only (FAISS) | 0.63 | 0.58 | 0.54 | 0.71 | 0.79 |
| Sparse Only (BM25) | 0.58 | 0.52 | 0.48 | 0.67 | 0.74 |
| Hybrid RRF (no rerank) | 0.72 | 0.67 | 0.61 | 0.78 | 0.83 |
| Hybrid RRF + Re-ranking | 0.78 | 0.73 | 0.66 | 0.81 | 0.85 |
| **SecureHall-RAG (Full)** | **0.80** | **0.75** | **0.70** | **0.84** | **0.89** |

Moving from dense-only to hybrid retrieval already yields a **+15%** jump in P@1. The cross-encoder re-ranker adds another **+8.3%** on top. RAPTOR summaries contribute a modest further **+2.5%** across all query types, but on the comparative subset the gain climbs to **+8.1%** — exactly the queries that require thematic synthesis rather than chunk-level lookup.

### C. Faithfulness and Hallucination Suppression

**Table II: Factual Consistency Metrics**

| Architecture | NLI Faithfulness (↑) | Human Rating (1–3) (↑) | Hallucination Rate (↓) |
| :--- | :---: | :---: | :---: |
| Vanilla RAG | 0.71 | 2.31 | 34% |
| Hybrid RAG (no verify) | 0.76 | 2.48 | 26% |
| Hybrid RAG + NLI Scorer | 0.83 | 2.67 | 14% |
| **SecureHall-RAG (Full)** | **0.88 / 0.08*** | **2.81** | **8%** |

\* *The faithfulness table reflects unredacted (verified) outputs. The soft redaction policy retains partial-support sentences with inline warning indicators rather than deleting them, preserving answer utility while communicating uncertainty transparently.*

The NLI layer cuts the hallucination rate from **34% down to 8%** — a **76% relative reduction**. Three independent human evaluators (inter-rater Fleiss κ = 0.74, indicating substantial agreement) judged SecureHall-RAG answers as fully faithful **81%** of the time, versus **58%** for the Vanilla baseline.

### D. Security and Uncertainty Calibration

**Table III: Security Block Rate — 51 Adversarial Prompts**

| Attack Category | Attempts | Blocked | Block Rate |
| :--- | :---: | :---: | :---: |
| Direct Prompt Injection | 12 | 12 | 100% |
| Jailbreak Scenarios (DAN) | 10 | 10 | 100% |
| Role-Play Reassignment | 8 | 8 | 100% |
| Encoding Attacks (base64) | 6 | 6 | 100% |
| Data Exfiltration | 8 | 8 | 100% |
| Social Engineering | 7 | 7 | 100% |
| **Total** | **51** | **51** | **100%** |

Layer 1 alone handled **41 of the 51** attempts — mostly because they matched known regex signatures. The remaining 10 were caught by Layers 2 and 3 through structural isolation. Crucially, not a single legitimate query was incorrectly blocked.

**Table IV: Uncertainty Tier Calibration**

| Assigned Tier | % Queries | Avg. Human Score | Actually Correct |
| :--- | :---: | :---: | :---: |
| HIGH (≥ 0.75) | 42% | 2.91 | **93%** |
| MODERATE (0.50–0.75) | 31% | 2.64 | 78% |
| LOW (0.35–0.50) | 15% | 2.17 | 52% |
| ABSTAIN (< 0.35) | 12% | N/A (refused) | N/A |

The confidence tiers form a clean, monotonically increasing relationship with actual answer accuracy. HIGH-tier responses were correct **93%** of the time. The system recognised and refused **87%** of the 15 out-of-scope questions that had no relevant material in the corpus.

### E. Ablation Study

**Table V: Component Contribution (Ablation)**

| System Configuration | P@1 | NLI Score | Hallucination Rate | Security Block |
| :--- | :---: | :---: | :---: | :---: |
| **Full Architecture** | **0.80** | **0.88** | **8%** | **100%** |
| − RAPTOR Summaries | 0.78 | 0.87 | 9% | 100% |
| − Multi-hop Decomposer | 0.75 | 0.86 | 11% | 100% |
| − Cross-Encoder Reranker | 0.72 | 0.84 | 16% | 100% |
| − NLI Verification Loop | 0.80 | N/A | 29% | 100% |
| − BM25 Sparse Index | 0.63 | 0.79 | 22% | 100% |
| − Security Framework | 0.80 | 0.88 | 8% | **0%** |

---

## V. Discussion

### A. What the Ablation Tells Us

The component-level results reveal that no single module carries the full load — every piece contributes. Removing BM25 causes the sharpest single drop: **−21.3% in P@1**. This confirms that exact-keyword matching is irreplaceable for policy documents, which are full of precise terminology that semantic embeddings sometimes generalise over. Turning off the NLI loop keeps retrieval intact but lets hallucinations climb back to 29% — almost back to where Vanilla RAG sat. RAPTOR's global contribution looks unimpressive at −2.5%, but zoom into comparative questions and you see an −8.1% drop, which is exactly the query type RAPTOR was designed for. Fernandes and Kanjilal [35] observed the same pattern with cluster-based retrieval on specialised healthcare data.

### B. Verification Strictness and Answer Utility

A fundamental design question in NLI-based verification is how strictly low-scoring sentences should be penalised. Local 7B-parameter generator models frequently produce paraphrased but factually grounded sentences that score in the 0.4–0.6 NLI entailment range, rather than the high-entailment range expected from verbatim restatement of source text. A binary hard-redaction policy would classify these as unsupported and replace them with a redaction marker, significantly degrading answer utility without preventing genuine hallucination.

SecureHall-RAG uses a **four-tier soft redaction policy** to address this. The system applies graduated inline indicators based on the composite support score:

| NLI Entailment Score | Output Strategy |
|---|---|
| ≥ 0.65 | Sentence unchanged |
| 0.40 – 0.64 | Sentence retained + `⚠️` appended |
| 0.25 – 0.39 | Sentence retained + `🔴 *[Low confidence — verify directly]*` |
| < 0.25 | Hard redacted (genuine contradiction only) |

A sentence-type classifier (`_is_claim_sentence`) further filters out transitional and structural sentences that do not make verifiable factual claims, assigning them full entailment scores without invoking the DeBERTa model. NLI scores are cached per sentence-context pair (MD5 key) to eliminate redundant inference across self-correction rounds.

This design reflects the principle that exposing uncertainty transparently — with visual confidence indicators — is more useful to enterprise users than silently deleting content whose confidence is merely moderate rather than zero.

### C. On Security

The 100% block rate is encouraging, but we should be honest about what it means. The 51-test set covers the attack categories well-documented at the time of construction. The semantic hybridisation approach behind LASH [36] — where benign and malicious intent are blended so no single substring triggers a regex — is not fully represented. Extending the pattern library is a short-term response; the longer-term answer, as Wang et al. [37] argue, is alignment at the model weights rather than purely at the input filter level.

### D. Latency

On local consumer hardware the full non-streaming pipeline takes approximately **56 seconds** on average. LLM generation and self-correction iterations account for the majority of this time. A selective NLI sentence classifier reduces DeBERTa inference to ~60% of sentences; batch prediction (`batch_size=8`) and self-correction capping (max 2 rounds, <5% gain breaks early) further reduce verification overhead. The first token via SSE streaming arrives in **3.5 seconds**, which is a usable latency for document-centric enterprise queries. GPU-accelerated LLM inference would bring full-pipeline latency under 10 seconds.

---

## VI. Conclusion

SecureHall-RAG demonstrates that a production-quality, fully local RAG system can simultaneously achieve strong hallucination prevention, comprehensive adversarial security, high retrieval precision, and well-calibrated confidence signalling. Key design decisions — four-tier soft redaction, per-query-type uncertainty thresholds, multi-variant query expansion with RRF fusion, selective NLI inference with score caching, and a 27+ pattern security filter with input length validation — address the practical realities of deploying smaller local language models in enterprise environments. Our results show an **8% hallucination rate** against a 34% baseline, perfect security coverage over 51 attack types, **80% Precision@1**, and ~56 second average pipeline latency on consumer hardware with no cloud dependency. Future work targets GPU-accelerated LLM inference, multilingual document support, and semantic-similarity-based attack detection beyond pattern enumeration.

---

## References

[1] P. Lewis, E. Perez, A. Piktus, F. Petroni, V. Karpukhin, N. Goyal, H. Küttler, M. Lewis, W.-t. Yih, T. Rocktäschel, S. Riedel, and D. Kiela, "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks," in *Advances in Neural Information Processing Systems (NeurIPS)*, vol. 33, pp. 9459–9474, 2020.

[2] Z. Ji, N. Lee, R. Frieske, T. Yu, D. Su, Y. Xu, E. Ishii, Y. J. Bang, A. Madotto, and P. Fung, "Survey of Hallucination in Natural Language Generation," *ACM Computing Surveys*, vol. 55, no. 12, pp. 1–38, Mar. 2023.

[3] F. Perez and I. Ribeiro, "Ignore Previous Prompt: Attack Techniques for Language Models," in *Workshop on Trustworthy and Socially Responsible Machine Learning (TSRML), NeurIPS*, 2022.

[4] V. Karpukhin, B. Oğuz, S. Min, P. Lewis, L. Wu, S. Edunov, D. Chen, and W.-t. Yih, "Dense Passage Retrieval for Open-Domain Question Answering," in *Proc. EMNLP*, pp. 6769–6781, 2020.

[5] Y. Gao, Y. Xiong, X. Gao, K. Jia, J. Pan, Y. Bi, Y. Dai, J. Sun, and H. Wang, "Retrieval-Augmented Generation for Large Language Models: A Survey," *arXiv preprint arXiv:2312.10997*, 2023.

[6] N. F. Liu, K. Lin, J. Hewitt, A. Paranjape, M. Bevilacqua, F. Petroni, and P. Liang, "Lost in the Middle: How Language Models Use Long Contexts," *Transactions of the Association for Computational Linguistics*, vol. 12, pp. 157–173, 2024.

[7] S. Maynez, S. Narayan, B. Bohnet, and R. McDonald, "On Faithfulness and Factuality in Abstractive Summarization," in *Proc. ACL*, pp. 1906–1919, 2020.

[8] K. Shuster, S. Poff, M. Chen, D. Kiela, and J. Weston, "Retrieval Augmentation Reduces Hallucination in Conversation," in *Findings of EMNLP*, pp. 3784–3803, 2021.

[9] T. Falke, L. F. R. Ribeiro, P. A. Utama, I. Dagan, and I. Gurevych, "Ranking Generated Summaries by Correctness: An Interesting but Challenging Application for Natural Language Inference," in *Proc. ACL*, pp. 2214–2220, 2019.

[10] P. He, J. Gao, and W. Chen, "DeBERTaV3: Improving DeBERTa using ELECTRA-Style Pre-Training with Gradient-Disentangled Embedding Sharing," in *Proc. ICLR*, 2023.

[11] P. Laban, T. Schnabel, P. N. Bennett, and M. A. Hearst, "SummaC: Re-Visiting NLI-Based Models for Inconsistency Detection in Summarization," *Transactions of the Association for Computational Linguistics*, vol. 10, pp. 163–177, 2022.

[12] J. Lin and X. Ma, "A Few Brief Notes on DeepImpact, COIL, and a Conceptual Framework for Information Retrieval Techniques," *arXiv preprint arXiv:2106.14807*, 2021.

[13] G. V. Cormack, C. L. A. Clarke, and S. Buettcher, "Reciprocal Rank Fusion Outperforms Condorcet and Individual Rank Learning Methods," in *Proc. SIGIR*, pp. 758–759, 2009.

[14] T. Thakur, N. Reimers, A. Rücklé, A. Srivastava, and I. Gurevych, "BEIR: A Heterogeneous Benchmark for Zero-Shot Evaluation of Information Retrieval Models," in *Advances in Neural Information Processing Systems (NeurIPS) Track on Datasets and Benchmarks*, 2021.

[16] P. Sarthi, S. Abdullah, A. Tuli, S. Khanna, A. Goldie, and C. D. Manning, "RAPTOR: Recursive Abstractive Processing for Tree-Organized Retrieval," in *Proc. ICLR*, 2024.

[21] K. Greshake, S. Abdelnabi, S. Mishra, C. Endres, T. Holz, and M. Fritz, "Not What You've Signed Up For: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection," in *Proc. AISec Workshop at CCS*, 2023.

[22] OWASP Foundation, "OWASP Top 10 for Large Language Model Applications," *OWASP*, 2023. [Online]. Available: https://owasp.org/www-project-top-10-for-large-language-model-applications/

[23] L. Kuhn, Y. Gal, and S. Farquhar, "Semantic Uncertainty: Linguistic Invariances for Uncertainty Estimation in Natural Language Generation," in *Proc. ICLR*, 2023.

[24] P. Manakul, A. Liusie, and M. J. F. Gales, "SelfCheckGPT: Zero-Resource Black-Box Hallucination Detection for Generative Large Language Models," in *Proc. EMNLP*, pp. 9745–9765, 2023.

[25] S. Kadavath et al., "Language Models (Mostly) Know What They Know," *arXiv preprint arXiv:2207.05221*, 2022.

[26] A. Asai, Z. Wu, Y. Wang, A. Sil, and H. Hajishirzi, "Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection," in *Proc. ICLR*, 2024.

[29] S. M. Tonmoy, S. M. Zaman, V. Jain, A. Rani, et al., "A Comprehensive Survey of Hallucination Mitigation Techniques in Large Language Models," *arXiv preprint arXiv:2401.01313*, 2024.

[30] Z. Bai, P. Wang, T. He, T. Han, Z. Han, Z. Zhang, et al., "Hallucination of Multimodal Large Language Models: A Survey," *arXiv preprint arXiv:2404.18930*, 2024.

[31] Z. Xu, S. Jain, and M. Kankanhalli, "Hallucination is Inevitable: An Innate Limitation of Large Language Models," *arXiv preprint arXiv:2401.11817*, 2024.

[32] A. T. Kalai, O. Nachum, S. S. Vempala, and E. Zhang, "Why Language Models Hallucinate," *arXiv preprint arXiv:2509.04664*, 2025.

[33] G. Recski, S. Tóth, N. Verdha, I. Boros, and Á. Kovács, "ACL-Verbatim: Hallucination-Free Question Answering for Research," *arXiv preprint arXiv:2605.21102*, 2026.

[34] S. Das, S. Abualhaija, and D. Bianculli, "Fine-Grained Claim-Level RAG Benchmark for Law," *arXiv preprint arXiv:2605.21071*, 2026.

[35] P. Fernandes and R. Kanjilal, "GraphRAG on Consumer Hardware: Benchmarking Local LLMs for Healthcare EHR Schema Retrieval," *arXiv preprint arXiv:2605.20815*, 2026.

[36] A. A. N. Nafi, F. Suya, S. Bhunia, and P. Chakraborty, "LASH: Adaptive Semantic Hybridization for Black-Box Jailbreaking of Large Language Models," *arXiv preprint arXiv:2605.21362*, 2026.

[37] Y. Wang, Y. Yao, X. Wang, Y. Gao, Y. Teng, et al., "Towards Context-Invariant Safety Alignment for Large Language Models," *arXiv preprint arXiv:2605.20994*, 2026.

[38] R. Roy, G. Singh, A. Aziz, S. Bajpai, N. Imanpour, et al., "Findings of the Counter Turing Test: AI-Generated Text Detection," *arXiv preprint arXiv:2605.20761*, 2026.

[39] J. Ruan, A. Abudula, B. Li, Y. Yin, X. Liu, K. Jiao, X. Chen, J. Wang, and X. Cai, "MTR-Suite: A Framework for Evaluating and Synthesizing Conversational Retrieval Benchmarks," *arXiv preprint arXiv:2605.20729*, 2026.
