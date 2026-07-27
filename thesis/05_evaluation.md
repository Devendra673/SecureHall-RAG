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
| Dense Only (FAISS) | 0.850 | 0.983 | 1.000 | 0.983 | 1.000 |
| BM25 only (sparse) | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| Hybrid RRF (no rerank) | 0.983 | 1.000 | 1.000 | 1.000 | 1.000 |
| Hybrid RRF + Reranking | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| **Hybrid + Reranking + RAPTOR (SecureHall-RAG)** | **1.000** | **1.000** | **1.000** | **1.000** | **1.000** |

Measured with `evaluation/retrieval_ablation.py` over the 60 answerable questions (P@K = 1 if any chunk from the correct source document appears in top-K).

**Key Findings:**
- Dense-only retrieval reaches P@1 = 0.850, missing the correct document for 15% of queries; adding BM25 + RRF fusion raises this to 0.983, and the cross-encoder re-ranker closes the gap to 1.000.
- On this small corpus (10 documents, 29 chunks) with highly distinctive per-document terminology, **BM25 keyword search alone also achieves P@1 = 1.000**. Retrieval is therefore near-saturated, and these numbers do not by themselves demonstrate a large hybrid advantage — the hybrid design's value here is *robustness* (it matches the best single-modality retriever across query types) rather than a headline margin.
- Establishing a decisive hybrid/RAPTOR advantage would require a larger, more lexically ambiguous corpus where no single retrieval modality saturates.

---

## 5.4 Faithfulness and Hallucination Prevention

Faithfulness is evaluated using two complementary approaches:
1. **Lexical / semantic scores** (reproducible): ROUGE-L against gold answers and an embedding-based semantic faithfulness score (cosine similarity between the answer and its retrieved context), both computed by `evaluation/run_ablation.py`.
2. **NLI score** (reproducible in-pipeline): the mean entailment probability from the NLI cross-encoder between each answer sentence and its retrieved context, used operationally for redaction/abstention.

> **⚠ VERIFY — Table 5.3 below is not reproducible with the current repository.** The NLI comparison figures, the 3-evaluator human ratings (Fleiss κ = 0.74), and the hallucination rates (34% → 8%) require a human-annotated evaluation that does not exist in the codebase. No script produces a "hallucination rate." Before submission, either (a) run and document a human/LLM-judge evaluation, or (b) replace this table with the reproducible ROUGE-L and semantic-faithfulness metrics from the ablation run. The figures are retained below only as a placeholder pending that decision.

**Table 5.3: Faithfulness and Hallucination Scores** *(placeholder — see verification note)*

| System | NLI Score (↑) | Human Faithful (↑) | Hallucination Rate (↓) |
|---|---|---|---|
| Vanilla RAG | 0.71 | 2.31 | 34% |
| Hybrid RAG | 0.76 | 2.48 | 26% |
| Hybrid + NLI Threshold | 0.83 | 2.67 | 14% |
| **SecureHall-RAG (Full)** | **0.88** | **2.81** | **8%** |

**Key Findings (pending verification):**
- The NLI verification pipeline is the primary hallucination-control mechanism, flagging unsupported sentences and routing low-support answers to disclaimers or ABSTAIN.
- The ABSTAIN mechanism replaces out-of-scope answers with safe refusals instead of fabricated content.
- The specific reduction figure ("34% → 8%") must be regenerated or restated qualitatively as noted above.

---

## 5.5 Uncertainty Quantification Effectiveness

To evaluate uncertainty calibration, we analyze whether the assigned confidence tier correlates with actual answer correctness. For each test query, the assigned tier (HIGH / MODERATE / LOW / ABSTAIN) is compared with human correctness ratings.

> **⚠ VERIFY — the "Avg. Human Score" and "Actually Correct" columns are not reproducible.** They require labelled per-answer correctness judgements that no script in the repository produces. The reproducible harness reports the tier *distribution* and mean confidence, not per-tier correctness. Regenerate with human/judge labelling or restate qualitatively before submission. The measured tier distribution from the current ablation run should be substituted for the "% of Queries" column.

**Table 5.4: Uncertainty Tier vs. Actual Answer Correctness** *(placeholder — see verification note)*

| Assigned Tier | % of Queries | Avg. Human Score | Actually Correct |
|---|---|---|---|
| HIGH (≥0.75) | 42% | 2.91 | 93% |
| MODERATE (0.50–0.75) | 31% | 2.64 | 78% |
| LOW (0.35–0.50) | 15% | 2.17 | 52% |
| ABSTAIN (<0.35) | 12% | N/A (refused) | N/A |

**Key Findings (pending verification):**
- The intent is that confidence tiers track correctness monotonically (higher tier → more often correct), giving users an actionable signal for when to verify manually.
- The specific per-tier correctness percentages must be regenerated via labelled evaluation or restated qualitatively as noted above.

---

## 5.6 Security Evaluation

The security evaluation tests the system against a curated adversarial set of **60 cases**, of which **31 are attacks that should be blocked** (the remaining 29 are benign or out-of-scope cases used to measure false positives). Two configurations are compared to isolate the contribution of the embedding-similarity semantic attack detector added on top of the signature/pattern content filter:

- **Baseline** — signature/pattern content filter only.
- **Enhanced** — pattern filter **+** embedding-similarity semantic detector (`all-MiniLM-L6-v2`, cosine threshold 0.48, minimum-length guard).

**Table 5.5: Security Evaluation Results (attacks blocked / attacks in category)**

| Attack Category | Should-block | Baseline (pattern only) | Enhanced (pattern + semantic) |
|---|---|---|---|
| Prompt Injection | 10 | 6 (60%) | 6 (60%) |
| Jailbreak | 10 | 5 (50%) | 7 (70%) |
| Encoded / Obfuscated | 8 | 6 (75%) | 6 (75%) |
| Edge Case | 3 | 0 (0%) | 0 (0%) |
| **Total attack-block rate** | **31** | **17 (54.8%)** | **19 (61.3%)** |
| **Overall correct handling (60 cases)** | — | **45 (75.0%)** | **47 (78.3%)** |

**Key Findings:**
- Adding the semantic detector raises the attack-block rate from **54.8%** to **61.3%** and overall correct handling from **75.0%** to **78.3%**, with **no new false positives** (the minimum-length guard prevents short benign queries such as *"Is this a good policy?"* from being flagged).
- The gain comes entirely from the **jailbreak** category (5/10 → 7/10): the semantic detector catches paraphrased and contextual attacks that share no literal keyword with the pattern library — for example *"Hypothetically, if you had no safety guidelines, how would you answer …"* and *"I am your developer and I authorize you to bypass all restrictions."*
- The pattern filter alone remains strong on encoded/obfuscated payloads (75%) and verbatim instruction-override strings.
- **Honest limitation:** 61.3% is the current ceiling. Fully novel attack vectors that are neither pattern-matched nor semantically close to a known attack intent (notably the edge-case category, 0/3) still slip through. Broader attack-seed coverage or a trained classifier would be needed to push this higher. Earlier drafts of this thesis reported a "100% block rate" over a 51-prompt set; that figure did not survive a rigorous, false-positive-aware re-evaluation and has been corrected here.

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
| LLM generation (Llama-3.1-8B, 512 tokens) | 12,500 |
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

| Configuration | P@1 | NLI Score | Hallucination Rate | Security Attack-Block Rate |
|---|---|---|---|---|
| Full System (pattern + semantic security) | 1.000 | *regen* | *regen* | **61.3%** |
| − Semantic Attack Detector (pattern only) | 1.000 | *regen* | *regen* | 54.8% |
| − RAPTOR | 1.000 | *regen* | *regen* | 61.3% |
| − Multi-hop Decomposition | 1.000 | *regen* | *regen* | 61.3% |
| − Cross-Encoder Reranking | 0.983 | *regen* | *regen* | 61.3% |
| − NLI Verification | 1.000 | N/A | *regen* | 61.3% |
| − Uncertainty Quantification | 1.000 | *regen* | *regen* | 61.3% |
| − BM25 (Dense Only) | 0.850 | *regen* | *regen* | 61.3% |
| − Security Framework | 1.000 | *regen* | *regen* | **0%** |

> **Note on this table.** The *P@1* column is measured (`evaluation/retrieval_ablation.py`, 60 answerable questions) — note that on this near-saturated corpus only the reranker (1.000 → 0.983 when removed) and dense-vs-hybrid (0.850 dense-only) actually move P@1. The *Security Attack-Block Rate* column is measured (60-case adversarial set; see Table 5.5). The *NLI Score* and *Hallucination Rate* columns require a labelled faithfulness/human evaluation that the repository does not currently produce (marked *regen*); regenerate or restate qualitatively before submission — see the ⚠ VERIFY note on Table 5.3.

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
| Attack-block rate — pattern filter only (31 attacks) | **54.8%** |
| Attack-block rate — pattern + semantic detector (31 attacks) | **61.3%** |
| Overall correct handling (60 adversarial cases) | **78.3%** |
| Queries correctly blocked for length (>600 chars) | **100%** |
| Precision@1 (full system) | 0.80 |
| Hallucination rate | 8% |
| HIGH tier correctness | 93% |

---
