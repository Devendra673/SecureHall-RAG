# CHAPTER 1: INTRODUCTION

---

## 1.1 Background and Motivation

The volume of internal documentation in enterprise organizations has grown exponentially over the past decade. Policy documents, employee handbooks, compliance manuals, HR guidelines, and IT security policies collectively form the operational backbone of any modern organization. Employees frequently need to query these documents to answer questions such as: *"How many annual leave days am I entitled to?"*, *"What is the IT security policy on personal device usage?"*, or *"What are the disciplinary procedures for code-of-conduct violations?"*

Traditionally, this has been handled through manual search, keyword-based document retrieval, or dedicated helpdesk channels. These approaches are inefficient, time-consuming, and inconsistent. The emergence of Large Language Models (LLMs) and Question-Answering (QA) systems has created an opportunity to automate this process, providing employees with instant, accurate responses to policy questions.

**Retrieval-Augmented Generation (RAG)** [1] represents the state-of-the-art approach to grounded document QA. Rather than relying solely on a model's parametric knowledge, RAG systems retrieve relevant document passages at query time and condition the LLM's response on those retrieved passages. This grounds the answer in actual source material, significantly reducing hallucination compared to purely generative approaches.

However, despite this progress, existing RAG systems face several critical challenges when deployed in enterprise settings:

1. **Hallucination**: Even with retrieved context, LLMs can generate factually incorrect, misleading, or unsupported claims — a phenomenon known as hallucination [2]. In enterprise policy QA, hallucinated answers can have serious consequences including incorrect HR decisions, compliance violations, or legal liability.

2. **Security Vulnerabilities**: Enterprise RAG systems exposed to users are susceptible to adversarial inputs known as **prompt injection attacks** [3], where malicious users craft inputs designed to override system instructions, extract sensitive data, or manipulate the model's behavior.

3. **Retrieval Quality Limitations**: Standard RAG systems using either dense vector search or sparse keyword search alone miss relevant documents. Dense search struggles with exact keyword matches; sparse search fails on semantic paraphrases. Neither handles documents well at multiple levels of abstraction.

4. **Opacity**: Most existing systems provide answers without transparency into how confident the system is, which source sections the answer derives from, or whether the answer should be trusted.

5. **Cloud Dependency**: Popular commercial RAG solutions require API access to cloud LLMs (e.g., GPT-4, Claude), making them unsuitable for organizations handling sensitive, proprietary documents that must never leave the local network.

These challenges motivate the development of **SecureHall-RAG**: a comprehensive, locally-deployable RAG system that addresses each of these limitations through a multi-layer approach combining advanced retrieval, rigorous hallucination prevention, prompt injection defense, and transparent uncertainty quantification.

---

## 1.2 Problem Statement

Despite the promise of Retrieval-Augmented Generation for enterprise document QA, current systems suffer from four fundamental problems:

**P1 — Hallucination**: LLMs generating answers that are factually unsupported by the retrieved context, which existing RAG systems cannot reliably detect or prevent.

**P2 — Security**: The absence of robust defenses against prompt injection, jailbreak, and data exfiltration attacks, leaving enterprise RAG deployments vulnerable to adversarial misuse.

**P3 — Retrieval Gaps**: Single-modal retrieval (either dense or sparse) and flat document chunking fail to capture both precise keyword matches and high-level semantic relationships, particularly for multi-document or hierarchically complex queries.

**P4 — Opacity**: Systems that return answers without confidence scores, source citations, or uncertainty disclosures make it impossible for users to calibrate their trust in the system's responses.

---

## 1.3 Research Objectives

This project aims to design and implement a system that:

**O1**: Builds a hybrid retrieval pipeline combining dense vector search (FAISS) and sparse keyword search (BM25) with cross-encoder re-ranking to maximize retrieval precision and recall.

**O2**: Implements a verification pipeline using Natural Language Inference (NLI) to score the factual faithfulness of generated answers against retrieved context, preventing hallucinated claims from being returned to users.

**O3**: Constructs a hierarchical document representation using RAPTOR (Recursive Abstractive Processing for Tree-Organized Retrieval) that indexes both raw document chunks and LLM-generated cluster summaries, enabling answering of both granular and high-level queries.

**O4**: Implements multi-hop query decomposition to handle complex, multi-entity questions by breaking them into focused sub-queries and merging retrieved context.

**O5**: Designs a 3-layer prompt injection security framework that detects and blocks adversarial inputs across content filtering, prompt sandboxing, and role-pinning layers.

**O6**: Introduces a 4-tier uncertainty quantification system (HIGH / MODERATE / LOW / ABSTAIN) that communicates confidence transparently to users through visual badges and text disclaimers.

**O7**: Delivers a full-stack, locally-deployable system requiring no cloud API dependency, with a premium glassmorphism UI, real-time SSE streaming, persistent conversational memory, and administrative controls.

---

## 1.4 Research Questions

This thesis addresses the following research questions:

- **RQ1**: How can a hybrid retrieval architecture (dense + sparse + hierarchical summaries) improve document retrieval quality compared to single-modality approaches for enterprise policy QA?

- **RQ2**: To what extent does an NLI-based post-hoc verification pipeline reduce hallucinated responses in a RAG system for enterprise document QA?

- **RQ3**: How effectively can a rule-based and template-driven security framework block known categories of prompt injection and jailbreak attacks?

- **RQ4**: Does multi-hop query decomposition improve answer quality for complex, comparative, or multi-document questions compared to single-pass retrieval?

- **RQ5**: What is the impact of uncertainty quantification on user trust, system transparency, and overall answer reliability in enterprise RAG deployments?

---

## 1.5 Scope and Limitations

**Scope:**
- The system targets English-language enterprise policy documents in PDF, DOCX, and TXT formats.
- It is designed for local deployment on standard workstation hardware (no GPU required for CPU-based inference).
- The LLM backend uses Ollama with Mistral 7B or Llama 3 8B models.
- The evaluation focuses on correctness, faithfulness, retrieval precision, and security robustness.

**Limitations:**
- Multi-language support is not implemented in the current version.
- LLM response quality depends on the quality and coverage of ingested documents; questions outside the document scope trigger the web search fallback or uncertainty abstention.
- RAPTOR clustering is performed synchronously during document ingestion; for very large corpora (>10,000 chunks), this may require optimization.
- Real-time performance depends on local hardware specifications; users with limited CPU resources may experience higher latency.

---

## 1.6 Thesis Organization

The remainder of this thesis is organized as follows:

- **Chapter 2** reviews the relevant literature on RAG, hallucination in LLMs, NLI, hybrid retrieval, RAPTOR, multi-hop reasoning, prompt injection attacks, and uncertainty quantification.

- **Chapter 3** presents the system design and architecture of SecureHall-RAG, describing each component and the rationale for design decisions.

- **Chapter 4** details the implementation of each module, with code descriptions, algorithmic explanations, and implementation choices.

- **Chapter 5** presents the evaluation methodology, test dataset, experimental results, and ablation study.

- **Chapter 6** discusses the interpretation of results, strengths, limitations, and directions for future work.

- **Chapter 7** concludes the thesis with a summary of contributions and broader implications.

---
