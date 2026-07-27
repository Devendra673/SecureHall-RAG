# FRONT MATTER

---

## TITLE PAGE

---

**SecureHall-RAG: A Trustworthy Retrieval-Augmented Generation System for Enterprise Document Question-Answering with Hallucination Prevention, Prompt Injection Defense, and Uncertainty Quantification**

---

A Major Project Report submitted in partial fulfillment of the requirements  
for the award of the degree of

**MASTER OF COMPUTER APPLICATIONS (MCA)**

---

Submitted by:

**Devendra**  
MCA [Year of Study]  
Enrollment No.: [Your Enrollment Number]

---

Under the guidance of:

**[Supervisor Name]**  
[Designation]  
[Department Name]  
[University/Institution Name]

---

**[Department Name]**  
**[University/Institution Name]**  
**[City, State]**

**June 2026**

---
---

## CERTIFICATE

This is to certify that the Major Project Report entitled **"SecureHall-RAG: A Trustworthy Retrieval-Augmented Generation System for Enterprise Document Question-Answering with Hallucination Prevention, Prompt Injection Defense, and Uncertainty Quantification"** submitted by **Devendra** (Enrollment No: [Enrollment No.]) in partial fulfillment of the requirements for the award of the degree of **Master of Computer Applications** from **[University Name]**, is a record of bonafide project work carried out under my supervision.

The work is original, has not been submitted earlier for any degree or diploma to this or any other university, and has been carried out in accordance with the regulations of the university.

&nbsp;

**[Supervisor Name]**  
[Designation]  
[Department, University]  
Date: ___________

&nbsp;

**Head of Department**  
[Department Name]  
[University/Institution Name]  
Date: ___________

---
---

## ACKNOWLEDGEMENTS

I express my deep and sincere gratitude to **[Supervisor Name]**, [Designation], [Department], [University], for their invaluable guidance, encouragement, and unwavering support throughout this project. Their insightful feedback and suggestions were instrumental in shaping the direction and quality of this work.

I am also thankful to the **Head of the Department**, [Department Name], and all the faculty members who provided support and resources throughout my academic journey.

I am grateful to the developers and researchers of the open-source tools and frameworks that made this project possible, including the teams behind **FastAPI**, **Next.js**, **FAISS**, **Sentence-Transformers**, **Ollama**, **Rank-BM25**, and the broader Hugging Face community.

Finally, I wish to thank my family and friends for their constant motivation and moral support, without which this work would not have been possible.

**Devendra**  
[University Name]  
June 2026

---
---

## ABSTRACT

Enterprise organizations rely heavily on internal policy documents, handbooks, and compliance manuals to govern their operations. However, manually querying these documents is time-consuming, and existing AI-powered Question-Answering (QA) systems suffer from a critical problem: **hallucination** — the generation of plausible but factually incorrect answers. This is particularly dangerous in enterprise settings where incorrect policy interpretations can lead to legal, financial, or operational consequences.

This thesis presents **SecureHall-RAG**, a full-stack, locally-deployable Retrieval-Augmented Generation (RAG) system specifically designed to address these challenges. The system makes four primary contributions:

1. **Hallucination Mitigation Architecture**: A multi-layer verification pipeline combining NLI-based faithfulness scoring using `cross-encoder/nli-deberta-v3-small`, claim-level support scoring, and a 4-tier uncertainty quantification framework (HIGH / MODERATE / LOW / ABSTAIN) that attaches confidence-calibrated disclaimers or replaces low-confidence answers with safe abstention messages. The pipeline reduces, but does not eliminate, unsupported claims.

2. **Advanced Retrieval**: A hybrid retrieval engine fusing dense FAISS vector search with sparse BM25 keyword search, cross-encoder re-ranking, semantic query caching, and RAPTOR (Recursive Abstractive Processing for Tree-Organized Retrieval) hierarchical document summarization that enables answering both granular and high-level policy questions.

3. **Multi-hop Reasoning**: A query decomposition mechanism that automatically breaks complex multi-entity questions into focused sub-queries, retrieves context for each independently, and merges results to enable comparative and multi-document reasoning.

4. **Prompt Injection Defense**: A layered security framework combining a signature/pattern content filter with an embedding-similarity semantic attack detector, together with prompt sandboxing and hardened templates. On a 60-case adversarial set it raises the attack-block rate from 54.8% (pattern only) to 61.3% (pattern + semantic) at 78.3% overall correct handling, with no new false positives — effective against known and paraphrased attacks, though not against fully novel vectors.

The system is implemented as a production-grade full-stack application: a FastAPI backend with SQLite-backed conversational memory, JWT authentication, audit logging, Server-Sent Events (SSE) streaming, and a Next.js frontend with a glassmorphism UI featuring real-time streaming, inline citations, and color-coded uncertainty badges. The system requires no cloud API dependency and runs entirely on local hardware using Ollama with Llama-3.1-8B-Instruct.

Evaluation on a 60-question answerable benchmark and a 60-case adversarial set shows the full hybrid pipeline reaching Precision@1 = 1.000 (versus 0.850 dense-only, on a small corpus where retrieval is near-saturated), the verification pipeline routing low-support answers to disclaimers or abstention, and the layered security framework blocking 61.3% of attacks (up from 54.8% with pattern matching alone) at 78.3% overall correct handling. The results are reported honestly, including the limitations of the small evaluation corpus and the residual attack surface.

**Keywords:** Retrieval-Augmented Generation, Hallucination Prevention, Prompt Injection Defense, Natural Language Inference, RAPTOR, Multi-hop Reasoning, Uncertainty Quantification, Enterprise Document QA, Local LLM, FAISS, BM25.

---
---

## TABLE OF CONTENTS

1. Introduction
   - 1.1 Background and Motivation
   - 1.2 Problem Statement
   - 1.3 Research Objectives
   - 1.4 Research Questions
   - 1.5 Scope and Limitations
   - 1.6 Thesis Organization

2. Literature Review
   - 2.1 Retrieval-Augmented Generation (RAG)
   - 2.2 Hallucination in Language Models
   - 2.3 Natural Language Inference for Faithfulness
   - 2.4 Hybrid Retrieval Systems
   - 2.5 Hierarchical Document Summarization (RAPTOR)
   - 2.6 Multi-hop Reasoning in QA
   - 2.7 Prompt Injection Attacks and Defenses
   - 2.8 Uncertainty Quantification in NLP
   - 2.9 Summary and Research Gaps

3. System Design and Architecture
   - 3.1 System Overview
   - 3.2 Document Ingestion Pipeline
   - 3.3 Hybrid Retrieval Engine
   - 3.4 Verification Pipeline
   - 3.5 Security Framework
   - 3.6 API and Frontend Architecture
   - 3.7 Data Models and Storage

4. Implementation
   - 4.1 Technology Stack
   - 4.2 Document Parsing and Chunking
   - 4.3 Dense and Sparse Retrieval
   - 4.4 Cross-Encoder Re-ranking
   - 4.5 RAPTOR Hierarchical Summarization
   - 4.6 Multi-hop Query Decomposition
   - 4.7 NLI Faithfulness Scoring
   - 4.8 Uncertainty Quantification
   - 4.9 Prompt Injection Defense
   - 4.10 Semantic Caching
   - 4.11 Backend API
   - 4.12 Frontend Interface

5. Evaluation and Results
   - 5.1 Evaluation Methodology
   - 5.2 Test Dataset
   - 5.3 Retrieval Performance
   - 5.4 Faithfulness and Hallucination Prevention
   - 5.5 Uncertainty Quantification Effectiveness
   - 5.6 Security Evaluation
   - 5.7 System Performance
   - 5.8 Ablation Study

6. Discussion
   - 6.1 Interpretation of Results
   - 6.2 Strengths of the System
   - 6.3 Limitations
   - 6.4 Future Work

7. Conclusion

References

---
---

## LIST OF FIGURES

| Figure | Caption |
|---|---|
| Fig. 3.1 | End-to-end system architecture of SecureHall-RAG |
| Fig. 3.2 | Document ingestion and chunking pipeline |
| Fig. 3.3 | Hybrid retrieval engine with RAPTOR integration |
| Fig. 3.4 | Multi-layer verification pipeline |
| Fig. 3.5 | 3-layer prompt injection security framework |
| Fig. 4.1 | RAPTOR clustering and summarization workflow |
| Fig. 4.2 | Multi-hop query decomposition flow |
| Fig. 4.3 | NLI faithfulness scoring pipeline |
| Fig. 4.4 | Uncertainty tier assignment logic |
| Fig. 5.1 | Precision@K comparison: Baseline vs. SecureHall-RAG |
| Fig. 5.2 | Faithfulness score distribution across test queries |
| Fig. 5.3 | Uncertainty tier distribution on test dataset |
| Fig. 5.4 | Ablation study: Impact of each component |

---

## LIST OF TABLES

| Table | Caption |
|---|---|
| Table 2.1 | Comparison of related RAG systems |
| Table 4.1 | Technology stack summary |
| Table 5.1 | Test dataset composition |
| Table 5.2 | Retrieval performance metrics |
| Table 5.3 | Faithfulness scores: Baseline vs. SecureHall-RAG |
| Table 5.4 | Prompt injection defense test results |
| Table 5.5 | Ablation study results |

---

## ABBREVIATIONS

| Abbreviation | Full Form |
|---|---|
| RAG | Retrieval-Augmented Generation |
| NLI | Natural Language Inference |
| LLM | Large Language Model |
| FAISS | Facebook AI Similarity Search |
| BM25 | Best Match 25 (probabilistic retrieval function) |
| RAPTOR | Recursive Abstractive Processing for Tree-Organized Retrieval |
| SSE | Server-Sent Events |
| JWT | JSON Web Token |
| QA | Question-Answering |
| API | Application Programming Interface |
| SBERT | Sentence-BERT |
| MCA | Master of Computer Applications |
| UI | User Interface |
| UX | User Experience |
