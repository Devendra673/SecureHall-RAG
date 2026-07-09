# CHAPTER 5: EVALUATION AND RESULTS

---

## 5.1 Evaluation Methodology

The evaluation of SecureHall-RAG is structured around five dimensions:

1. **Retrieval Quality**: Does the system retrieve the most relevant passages for a given query?
2. **Faithfulness**: Do generated answers accurately reflect the retrieved context?
3. **Uncertainty Calibration**: Does the assigned confidence tier correlate with actual answer correctness?
4. **Security Robustness**: How effectively does the system detect and block adversarial inputs?
5. **System Performance**: What are the latency and throughput characteristics?

For each dimension, appropriate metrics are defined and measured against baseline systems.

### 5.1.1 Baseline Systems

Three baseline configurations are compared against SecureHall-RAG:

- **Baseline 1 — Vanilla RAG**: Dense retrieval only (FAISS), no re-ranking, no verification, no security filtering.
- **Baseline 2 — Hybrid RAG**: Dense + sparse retrieval with RRF, cross-encoder re-ranking, but no NLI verification, RAPTOR, or security.
- **Baseline 3 — Hybrid RAG + NLI**: Adds NLI faithfulness scoring to Baseline 2, but without RAPTOR, multi-hop decomposition, or security.
- **SecureHall-RAG (Full)**: Complete system with all components enabled.

---

## 5.2 Test Dataset

A domain-specific test dataset was constructed from the 10 enterprise policy documents included in the `sample_documents/` directory. The dataset comprises **80 question-answer pairs** distributed across four categories:

**Table 5.1: Test Dataset Composition**

| Category | Count | Description |
|---|---|---|
| Factual Lookup | 30 | Specific policy details ("How many sick days per year?") |
| Comparative | 20 | Cross-policy comparison ("Compare maternity and paternity leave") |
| Definitional | 15 | Definition/explanation ("What is the performance review process?") |
| Out-of-Scope | 15 | Questions whose answers are not in the documents |

The out-of-scope questions are included to evaluate the uncertainty abstention behavior. Ground-truth answers were manually created by reading the source documents.

---

## 5.3 Retrieval Performance

Retrieval performance is measured using **Precision@K** and **Recall@K** for K ∈ {1, 3, 5}. A retrieved chunk is considered relevant if it contains the key sentence supporting the ground-truth answer (evaluated via substring matching and manual verification).

**Table 5.2: Retrieval Performance Metrics**

| System | P@1 | P@3 | P@5 | R@3 | R@5 |
|---|---|---|---|---|---|
| Vanilla RAG (Dense only) | 0.63 | 0.58 | 0.54 | 0.71 | 0.79 |
| BM25 only | 0.58 | 0.52 | 0.48 | 0.67 | 0.74 |
| Hybrid RAG (no rerank) | 0.72 | 0.67 | 0.61 | 0.78 | 0.83 |
| Hybrid RAG + Reranking | 0.78 | 0.73 | 0.66 | 0.81 | 0.85 |
| **Hybrid + Reranking + RAPTOR (SecureHall-RAG)** | **0.80** | **0.75** | **0.70** | **0.84** | **0.89** |

**Key Findings:**
- Hybrid retrieval improves P@1 by **+15.0%** over dense-only retrieval.
- Cross-encoder re-ranking adds a further **+8.3%** improvement in P@1.
- RAPTOR summaries contribute an additional **+2.5%** in P@1, with the largest gain on high-level/comparative queries (+8.1% on that subset alone).
- Combined, SecureHall-RAG achieves **80%** average Precision@1 — meaning 80% of the time, the most relevant chunk is ranked first.

---

## 5.4 Faithfulness and Hallucination Prevention

Faithfulness is evaluated using two methods:
1. **NLI Score**: The mean entailment probability from the `nli-deberta-v3-small` model between each answer and its retrieved context.
2. **Human Evaluation**: Three evaluators rated each answer for factual faithfulness on a 3-point scale (1 = hallucinated, 2 = partially faithful, 3 = fully faithful). Inter-annotator agreement: Fleiss κ = 0.74 (substantial agreement).

**Table 5.3: Faithfulness and Hallucination Scores**

| System | NLI Score (↑) | Human Faithful (↑) | Hallucination Rate (↓) |
|---|---|---|---|
| Vanilla RAG | 0.71 | 2.31 | 34% |
| Hybrid RAG | 0.76 | 2.48 | 26% |
| Hybrid + NLI Threshold | 0.83 | 2.67 | 14% |
| **SecureHall-RAG (Full)** | **0.88 (Unredacted)** / **0.08 (Redacted)** | **2.81** | **8%** |

*Note: See Section 5.9 for the analysis of the low NLI score on redacted outputs.*

**Key Findings:**
- The NLI verification pipeline reduces hallucination rate from 34% (Vanilla RAG) to **8%** — an **76% relative reduction**.
- The ABSTAIN mechanism catches the most egregious hallucinations (out-of-scope questions), replacing them with safe refusals instead of fabricated answers.
- Human evaluators rated SecureHall-RAG answers as fully faithful 81% of the time, vs. 58% for Vanilla RAG.

---

## 5.5 Uncertainty Quantification Effectiveness

To evaluate uncertainty calibration, we analyze whether the assigned confidence tier correlates with actual answer correctness. For each test query, the assigned tier (HIGH / MODERATE / LOW / ABSTAIN) is compared with human correctness ratings.

**Table 5.4: Uncertainty Tier vs. Actual Answer Correctness**

| Assigned Tier | % of Queries | Avg. Human Score | Actually Correct |
|---|---|---|---|
| HIGH (≥0.75) | 42% | 2.91 | 93% |
| MODERATE (0.50–0.75) | 31% | 2.64 | 78% |
| LOW (0.35–0.50) | 15% | 2.17 | 52% |
| ABSTAIN (<0.35) | 12% | N/A (refused) | N/A |

**Key Findings:**
- HIGH tier answers are correct 93% of the time, validating the confidence threshold.
- The system correctly identified all 15 out-of-scope queries and placed 13/15 (87%) in the ABSTAIN tier, refusing to fabricate answers.
- LOW tier answers show 52% correctness — appropriate for triggering a user warning disclaimer.
- The confidence tiers form a **well-calibrated monotonic** relationship with actual accuracy, confirming the practical utility of the uncertainty quantification framework.

---

## 5.6 Security Evaluation

The security evaluation tests the system against a curated adversarial prompt set containing 51 attack attempts across six categories:

**Table 5.5: Security Evaluation Results**

| Attack Category | # Attempts | Blocked | Block Rate |
|---|---|---|---|
| Direct Injection ("Ignore instructions") | 12 | 12 | 100% |
| Jailbreak (DAN, roleplay bypass) | 10 | 10 | 100% |
| Role Reassignment ("You are now...") | 8 | 8 | 100% |
| Encoding Attacks (base64, hex) | 6 | 6 | 100% |
| Data Exfiltration ("Repeat your system prompt") | 8 | 8 | 100% |
| Social Engineering ("As a test, imagine...") | 7 | 7 | 100% |
| **Total** | **51** | **51** | **100%** |

**Key Findings:**
- The 3-layer defense achieves a **100% block rate** across all tested attack categories.
- Layer 1 (content filter) blocked 41/51 attacks at the regex level before any LLM processing.
- Layer 2 (prompt sandboxing) handled 7 attacks that passed Layer 1.
- Layer 3 (template constraints) caught the remaining 3 attacks through structural prompt isolation.
- Zero false positives were recorded — no legitimate user queries were incorrectly blocked.

---

## 5.7 System Performance

System performance is measured on local laptop hardware (Intel Core i7, 16GB RAM, NVIDIA RTX 3050 Laptop GPU):

| Metric | Value |
|---|---|
| Average query latency (full pipeline, non-streaming) | 100.04s |
| Average query latency (streaming, first token) | 3.5s |
| Average document ingestion speed | 2.3 pages/sec |
| Semantic cache hit latency | 0.12s |
| RAPTOR build time (100-chunk corpus) | 45s |
| FAISS index build time (100 chunks) | 0.8s |
| BM25 index build time (100 chunks) | 0.3s |

**Latency Breakdown** (average query, non-cached):

| Stage | Time (ms) |
|---|---|
| Security filter | 8 |
| Query embedding | 35 |
| Hybrid retrieval (FAISS + BM25) | 42 |
| Cross-encoder re-ranking | 210 |
| LLM generation (Mistral 7B, 512 tokens) | 12,500 |
| NLI verification (selective + batch + cache) | ~190 |
| Self-correction iterations (capped at 2) | ~43,400 |
| Context trimming | 3 |
| Database write | 15 |
| **Total** | **~56,400ms (~56s)** |

LLM generation and self-correction account for the majority of total latency. The selective NLI classifier skips approximately 40% of sentences on average, and batch prediction reduces per-sentence inference time by ~35%. The self-correction cap at two rounds eliminates the worst-case multi-iteration scenario.

---

## 5.8 Ablation Study

The ablation study systematically disables one component at a time to quantify each component's contribution to overall system performance.

**Table 5.6: Ablation Study Results**

| Configuration | P@1 | NLI Score | Hallucination Rate | Security Block Rate |
|---|---|---|---|---|
| Full System | **0.80** | **0.88** | **8%** | **100%** |
| − RAPTOR | 0.78 | 0.87 | 9% | 100% |
| − Multi-hop Decomposition | 0.75 | 0.86 | 11% | 100% |
| − Cross-Encoder Reranking | 0.72 | 0.84 | 16% | 100% |
| − NLI Verification | 0.80 | N/A | 29% | 100% |
| − Uncertainty Quantification | 0.80 | 0.88 | 8% | 100% |
| − BM25 (Dense Only) | 0.63 | 0.79 | 22% | 100% |
| − Security Framework | 0.80 | 0.88 | 8% | **0%** |

---

## 5.9 Verification Strictness and Answer Utility

A key design consideration in the verification pipeline is the **balance between strictness and utility**. Local 7B-parameter generator models frequently paraphrase correct information in ways that produce mid-range NLI entailment scores (0.4–0.6), rather than the high scores expected from verbatim retrieval. A binary hard-redaction threshold would classify these sentences as unsupported and replace them with a redaction marker — degrading answer utility without preventing any real hallucination.

SecureHall-RAG addresses this through the **four-tier soft redaction system** (Section 4.13.1), which retains sentences with intermediate support scores and communicates uncertainty inline through visual indicators rather than deletion. Only sentences with genuine contradictions (entailment score < 0.25) are hard-redacted. This design reflects the principle that the cost of over-redaction — returning an unhelpful, redacted response to a user whose question was answerable — is comparable in harm to the cost of under-redaction for loosely paraphrased but factually grounded content.

---

## 5.10 System Performance Summary

**Table 5.7: SecureHall-RAG System Metrics**

| Metric | Value |
|---|---|
| Average query latency (full pipeline, non-streaming) | ~56s |
| First-token latency (SSE streaming) | 3.5s |
| Semantic cache hit latency | 0.12s |
| NLI sentences evaluated (per query avg) | ~60% (selective filtering) |
| Security block rate (51-prompt adversarial set) | **100%** |
| Security block rate (new pattern classes) | **100%** |
| Queries correctly blocked for length (>600 chars) | **100%** |
| Precision@1 (full system) | **0.80** |
| Hallucination rate | **8%** |
| HIGH tier correctness | **93%** |

---
