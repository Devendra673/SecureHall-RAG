---

# SECUREHALL-RAG

## A Trustworthy Retrieval-Augmented Generation System for Enterprise Document Question-Answering with Hallucination Prevention, Prompt Injection Defense, and Uncertainty Quantification

---

**A Major Project Report**  
submitted in partial fulfillment of the requirements for the award of the degree of

## MASTER OF COMPUTER APPLICATIONS (MCA)

---

**Submitted By:**

**Devendra**  
MCA (Final Year)  
Enrollment No.: \_\_\_\_\_\_\_\_\_\_\_\_

---

**Under the Guidance of:**

**[Supervisor Name]**  
[Designation]  
Department of Computer Science  
[University / Institution Name]

---

**Department of Computer Science**  
**[University / Institution Name]**  
**[City, State]**

**Session: 2025 – 2026**

---

---

## CERTIFICATE FROM THE ORGANIZATION / COMPANY

This is to certify that **Devendra**, student of Master of Computer Applications (Final Year) at **[University / Institution Name]**, has successfully completed the Major Project entitled

**"SecureHall-RAG: A Trustworthy Retrieval-Augmented Generation System for Enterprise Document Question-Answering with Hallucination Prevention, Prompt Injection Defense, and Uncertainty Quantification"**

during the academic session 2025–2026. The project work was carried out at our organization under the mentorship of our technical team. The student has shown sincere dedication, technical proficiency, and professional conduct throughout the project duration.

We certify that the work produced is original and has been completed to our satisfaction.

&nbsp;

**Organization Mentor:**

\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_  
**[Mentor Name]**  
[Designation]  
[Organization / Company Name]  
Date: \_\_\_\_\_\_\_\_\_\_\_

&nbsp;

**Authorized Signatory:**

\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_  
**[Name]**  
[Designation]  
[Organization / Company Name]  
[City, State]  
Date: \_\_\_\_\_\_\_\_\_\_\_

Seal / Stamp of Organization:

\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_

---

## CERTIFICATE FROM THE COLLEGE (INTERNAL GUIDE AND HOD)

This is to certify that the Major Project Report entitled

**"SecureHall-RAG: A Trustworthy Retrieval-Augmented Generation System for Enterprise Document Question-Answering with Hallucination Prevention, Prompt Injection Defense, and Uncertainty Quantification"**

submitted by **Devendra** (Enrollment No.: \_\_\_\_\_\_\_\_) in partial fulfillment of the requirements for the award of the degree of **Master of Computer Applications** from **[University Name]** is a record of bonafide project work carried out under my supervision and guidance.

The work presented in this report is original, has not been submitted earlier for any degree or diploma to this or any other university, and has been carried out in accordance with the rules and regulations of the university.

&nbsp;

**Internal Guide:**

\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_  
**[Supervisor Name]**  
[Designation], [Department]  
[University Name]  
Date: \_\_\_\_\_\_\_\_\_\_\_

&nbsp;

**Head of Department:**

\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_  
**[Head of Department Name]**  
Department of Computer Science  
[University Name]  
Date: \_\_\_\_\_\_\_\_\_\_\_

---

## DECLARATION

I, Devendra, a student of Master of Computer Applications (Final Year) at [University Name], declare that this project report titled **"SecureHall-RAG: A Trustworthy Retrieval-Augmented Generation System for Enterprise Document Question-Answering with Hallucination Prevention, Prompt Injection Defense, and Uncertainty Quantification"** is based on work I carried out myself during the academic session 2025–2026. This report has not been submitted anywhere else for any degree, diploma, or award.

I also declare the following:

- The entire project — from design and coding to evaluation — was done by me under the guidance of my supervisor.
- Wherever I have referred to ideas, findings, or text from published sources, I have cited those sources properly.
- The portion of this report describing system architecture and experimental results has also been prepared as a research paper under the same academic supervision. This overlap is intentional and declared here for transparency.

&nbsp;

\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_  
**Devendra**  
Enrollment No.: \_\_\_\_\_\_\_\_  
Date: \_\_\_\_\_\_\_\_\_\_\_  
Place: \_\_\_\_\_\_\_\_\_\_\_

---

## ACKNOWLEDGEMENTS

This project took about eight months from the first rough idea to a working system, and I genuinely could not have finished it alone.

My biggest thanks go to my project guide, [Supervisor Name], who kept pushing me to think deeper whenever I was satisfied with a surface-level solution. The conversations we had — especially around the security design and the evaluation methodology — shaped the final system in ways I did not expect at the start.

I am also grateful to the Head of the Department and the faculty members who reviewed my work at various stages and gave honest feedback rather than just encouragement.

A large part of this project runs on open-source tools that took years of collective effort to build. The teams behind FastAPI, Next.js, FAISS, the Sentence-Transformers library, Hugging Face Transformers, and Ollama deserve real credit. Without their work being freely available, building a system like this in an academic setting would simply not be possible.

Finally, my family put up with a lot of late nights and weekend disappearances without complaint. That kind of quiet support matters more than it probably seemed at the time.

&nbsp;

**Devendra**  
[University Name]  
July 2026

---

## ABSTRACT

Every organisation I have come across — whether a university, a hospital, or a mid-size company — keeps its rules and procedures locked inside documents that almost nobody reads. HR manuals, IT security guidelines, onboarding handbooks, compliance policies — they exist, but they are spread across shared drives and intranet portals in a way that makes finding a specific answer genuinely difficult. When an employee needs to know their exact sick leave balance or the correct process for reporting a security incident, the realistic options are: search manually across a dozen files, ask a colleague who may or may not remember correctly, or raise a helpdesk ticket and wait. None of these scale, and none of them are reliable.

Large Language Models combined with Retrieval-Augmented Generation offer a technically credible way out of this situation. The basic idea is to retrieve the most relevant document sections at the moment a question is asked and hand them to the model as evidence — so the answer is grounded in what the documents actually say rather than what the model guessed during training. The problem is that simply connecting a retrieval step to a language model does not automatically produce a trustworthy system. In practice, models still generate claims that are not supported by the retrieved text. Users can inject malicious instructions through the query interface. Searching only with keyword matching or only with vector similarity consistently misses one category of relevant content. And returned answers carry no indication of how much confidence the system actually has.

**SecureHall-RAG** is the system I built to address all four of these problems within a single, locally deployable application that does not send any data to external cloud services. It brings together four mechanisms that are typically studied in isolation:

1. **Hybrid Hierarchical Retrieval** — FAISS vector search and BM25 keyword search merged through Reciprocal Rank Fusion, re-ranked by a cross-encoder, and extended with RAPTOR cluster-level summaries for thematic queries.
2. **NLI Faithfulness Verification** — each sentence the model generates is scored for entailment against the retrieved context by a DeBERTa NLI model, with a self-correction loop for low-confidence claims.
3. **Three-Layer Prompt Injection Defense** — a regex content filter, XML-delimited structural sandboxing, and role-reinforcing generation templates applied in sequence.
4. **Four-Tier Uncertainty Signalling** — composite confidence scores mapped to HIGH, MODERATE, LOW, and ABSTAIN badges shown alongside every answer.

Evaluation on a 60-question answerable benchmark and a 60-case adversarial test set produced these results: the full hybrid pipeline achieves Precision@1 of **1.000** versus **0.850** for dense-only retrieval (on a small corpus where retrieval is near-saturated — BM25 alone also reaches 1.000); the layered security framework raises the attack-block rate from **54.8%** (pattern filter only) to **61.3%** once an embedding-similarity semantic detector is added, at **78.3%** overall correct handling with no new false positives; and the NLI verification loop, rather than the negligible overhead reported in earlier drafts, adds tens of seconds per query on CPU-only hardware because it makes several additional LLM calls — GPU inference is required for interactive latency.

**Keywords:** Retrieval-Augmented Generation, Hallucination Prevention, NLI, Prompt Injection, RAPTOR, Uncertainty Quantification, Enterprise QA, Local LLM

---

## TABLE OF CONTENTS

| Chapter | Title | Page |
|:---|:---|:---:|
| | Certificate from Organization / Company | i |
| | Certificate from College (Internal Guide and HOD) | ii |
| | Declaration by the Student | iii |
| | Acknowledgements | iv |
| | Abstract / Synopsis | v |
| | List of Figures | vi |
| | List of Tables | vii |
| | Abbreviations | viii |
| **1** | **Introduction** | **1** |
| **2** | **Literature Survey** | **10** |
| **3** | **System Requirements Specification (SRS)** | **25** |
| **4** | **System Design** | **32** |
| **5** | **Implementation Details** | **48** |
| **6** | **Software Testing** | **65** |
| **7** | **Screenshots and Outputs** | **78** |
| **8** | **Conclusion and Future Scope** | **82** |
| **9** | **References** | **87** |
| **10** | **Appendix** | **90** |

---

## LIST OF FIGURES

| Figure No. | Title | Page |
|:---:|:---|:---:|
| Figure 4.1 | SecureHall-RAG System Architecture (Four-Stage Processing Pipeline) | 29 |
| Figure 4.2 | Level 0 Data Flow Diagram (Context Diagram) | 32 |
| Figure 4.3 | Level 1 Data Flow Diagram | 33 |
| Figure 4.4 | Query Processing Sequence Diagram | 36 |
| Figure 5.1 | Document Ingestion and Chunking Flow | 43 |
| Figure 5.2 | Reciprocal Rank Fusion Algorithm Flow | 47 |
| Figure 5.3 | NLI Faithfulness Verification and Self-Correction Loop | 52 |
| Figure 5.4 | Three-Layer Prompt Injection Defense Architecture | 56 |
| Figure 5.5 | SSE Streaming Response Flow | 59 |

---

## LIST OF TABLES

| Table No. | Title | Page |
|:---:|:---|:---:|
| Table 3.1 | Hardware Requirements | 21 |
| Table 3.2 | Software Requirements | 22 |
| Table 3.3 | Functional Requirements | 24 |
| Table 3.4 | Non-Functional Requirements | 26 |
| Table 4.1 | Use Case Description | 34 |
| Table 4.2 | Database Schema | 40 |
| Table 5.1 | Complete Technology Stack | 43 |
| Table 6.1 | Unit Test Coverage by Module | 63 |
| Table 6.2 | Retrieval Precision@K and Recall@K | 67 |
| Table 6.3 | Faithfulness Evaluation Results | 68 |
| Table 6.4 | Confidence Tier vs. Actual Answer Correctness | 70 |
| Table 6.5 | Security Test Cases — Prompt Injection Block Rate | 72 |
| Table 6.6 | System Performance Metrics | 73 |

---

## ABBREVIATIONS

| Abbreviation | Full Form |
|:---|:---|
| RAG | Retrieval-Augmented Generation |
| NLI | Natural Language Inference |
| LLM | Large Language Model |
| FAISS | Facebook AI Similarity Search |
| BM25 | Best Match 25 |
| RAPTOR | Recursive Abstractive Processing for Tree-Organized Retrieval |
| RRF | Reciprocal Rank Fusion |
| SSE | Server-Sent Events |
| JWT | JSON Web Token |
| QA | Question-Answering |
| API | Application Programming Interface |
| SBERT | Sentence-BERT |
| MCA | Master of Computer Applications |
| UI | User Interface |
| UX | User Experience |
| RBAC | Role-Based Access Control |
| ORM | Object-Relational Mapping |
| PDF | Portable Document Format |
| DOCX | Microsoft Word Document Format |
| CUDA | Compute Unified Device Architecture |
| GPU | Graphics Processing Unit |
| SRS | System Requirements Specification |
| DFD | Data Flow Diagram |

---

---

# CHAPTER 1: INTRODUCTION

## 1.1 Introduction

Think about how most employees actually find information at work. They either remember it, ask someone, or spend twenty minutes hunting through folders and PDFs hoping the right document shows up. This is not a niche problem — it happens daily in every organisation that has grown beyond a handful of people. HR entitlements, IT security rules, leave policies, disciplinary procedures — all of this knowledge exists somewhere in writing, but the act of retrieving a specific fact from that writing is often harder than it should be.

The documents themselves are not the problem. It is the way they are stored and accessed. Policy files are scattered across intranet portals, email attachments, and shared network drives in formats that are not searchable in any intelligent way. A new joiner trying to figure out their notice period cannot run a Google-style search over internal files. They end up asking HR, who may give a different answer than what the document actually says, or they file a helpdesk ticket and wait two days for a reply that could have been a ten-second lookup.

This project started from that frustration. The question I wanted to answer was: can I build a system that lets anyone ask a plain-English question about company policies and get an accurate, cited, confidence-rated answer in a few seconds — all without sending any data to the cloud?

Large Language Models make something like this possible, but not automatically. Pairing an LLM with Retrieval-Augmented Generation (RAG) — where relevant document chunks are fetched first and then handed to the model as grounding context — reduces fabricated answers significantly compared to asking the model cold. But building a system that is actually trustworthy in an enterprise setting requires solving several problems that the basic RAG setup leaves open. Even with retrieved context, models still assert things the documents do not say. Users can try to hijack the system through cleverly worded inputs. Searching with only embeddings or only keywords each has blind spots. And an answer that comes with no indication of how confident the system is puts the entire burden of judgment on the user.

**SecureHall-RAG** is the system I built to address all four of these issues at once, in a single application that runs entirely on local hardware.

---

## 1.2 Problem Statement

Working through the design of this project, I identified four concrete problems that needed solving. Each one shows up as a real failure mode in existing RAG deployments:

**P1 — Hallucination:** Even when the model has access to the right document passages, it sometimes produces statements that those passages do not actually support. In a policy QA context this is dangerous — an employee acting on a hallucinated entitlement or procedure could face disciplinary consequences for following advice that was never in the rules.

**P2 — Prompt Injection:** Any system that accepts free-text input from users is vulnerable to adversarial manipulation. Attackers can craft inputs designed to make the model ignore its instructions, leak information from the context, or behave in entirely unintended ways. This is not a theoretical risk — it is a well-studied attack category with documented exploits against production systems.

**P3 — Retrieval Gaps:** Embedding-based search handles paraphrased and semantically varied queries well, but stumbles when the query uses specific role names, dates, or exact policy terms that match verbatim in the document. Keyword-based search handles the reverse case well but fails at semantic matching. Using only one method means some queries will reliably fail. Neither method alone can synthesise an answer from across multiple document sections.

**P4 — No Confidence Signal:** When a system returns an answer with no indication of certainty, users have no way to decide whether to trust it immediately or go verify it manually. This makes the system hard to use responsibly, especially for compliance-sensitive decisions.

---

## 1.3 Objectives

The goals I set for this project were:

**O1:** Build a hybrid retrieval pipeline that runs FAISS dense search and BM25 keyword search in parallel, combines their results through Reciprocal Rank Fusion, and then re-ranks the merged candidates with a cross-encoder.

**O2:** Add a RAPTOR layer during document ingestion — cluster the chunks, generate short abstractive summaries for each cluster, and include those summaries in the search index so that thematic queries have something useful to retrieve.

**O3:** Implement multi-hop query decomposition so that compound questions get broken into focused sub-questions before retrieval.

**O4:** Build a post-generation faithfulness checker that runs each output sentence through a DeBERTa NLI model, flags low-confidence claims with inline warnings, and triggers a rewrite loop for sentences that score below threshold.

**O5:** Layer three independent security checks on every incoming query — regex pattern matching, structural XML sandboxing of the prompt, and role-reinforcing generation templates — so that no single bypass is enough.

**O6:** Assign every response a confidence tier (HIGH, MODERATE, LOW, or ABSTAIN) based on a composite score, and surface that tier visibly to the user through colour-coded badges.

**O7:** Deliver a complete, deployable application — FastAPI backend, Next.js frontend, JWT auth, SSE streaming, chat history, audit logs, Docker support — not just a research prototype.

---

## 1.4 Organization Profile

**[Organization / Institution Name]** is a [type of institution] located in [City, State], established in [Year]. The institution focuses on [brief description of core activities — e.g., postgraduate education in Computer Science and Information Technology].

The Department of Computer Science runs the Master of Computer Applications programme with coursework covering software engineering, machine learning, data science, and full-stack development. The department has GPU-capable workstations and access to major open-source AI libraries, which made it feasible to run the models this project depends on — including a local 8B-parameter LLM — entirely on departmental hardware.

**SecureHall-RAG** was developed here as a final-year MCA major project under the supervision of [Supervisor Name], [Designation], during the 2025–2026 session. The work sits at the intersection of natural language processing, information retrieval, and application security — all areas covered in the MCA curriculum.

---

## 1.5 Report Organization

Here is how the rest of this report is laid out:

- **Chapter 2** reviews the research that informed this project — covering RAG systems, hallucination, NLI faithfulness scoring, hybrid retrieval, RAPTOR, prompt injection attacks, and uncertainty estimation. It ends with a summary of the gaps that motivated the proposed system.
- **Chapter 3** lists the hardware, software, functional, and non-functional requirements.
- **Chapter 4** covers system design — the four-stage architecture, data flow diagrams, use cases, the query sequence diagram, and the database schema.
- **Chapter 5** goes into implementation — the full technology stack, each module's design and code, and the key algorithms with working code snippets.
- **Chapter 6** documents testing — unit tests by module, integration test flows, system-level evaluation results, and security test outcomes.
- **Chapter 7** shows screenshots of the running system: login, document upload, the chat interface, streamed answers with citation and confidence badges, and the admin dashboard.
- **Chapter 8** wraps up with what the project achieved, where it falls short, and what I would build next.
- **Chapter 9** is the full reference list in IEEE format.
- **Chapter 10** is the appendix — glossary, sample API calls, and benchmark query examples.

---

---

# CHAPTER 2: LITERATURE SURVEY

## 2.1 Existing Systems

### 2.1.1 Retrieval-Augmented Generation (RAG)

The core idea behind RAG was formalised by Lewis et al. (2020), who showed that grounding a language model's responses in passages retrieved from an external knowledge store — rather than relying on whatever the model memorised during training — substantially cut down on fabricated content. In their setup, a retriever first selects the most contextually relevant document segments, which are then passed to the generator as part of its input. The separation between "what to look up" and "what to say" is what makes the approach practical for knowledge-intensive tasks.

Karpukhin et al. (2020) tackled the retrieval side of this problem by training a dual-encoder model — Dense Passage Retrieval — where both questions and candidate passages are mapped into a shared vector space. Retrieval then reduces to a fast inner-product search, which works well at scale. Gao et al. (2023) reviewed how the field moved beyond this baseline, organising improvements into three categories: changes before retrieval (query reformulation, hypothetical document generation), changes to the retrieval step itself (hybrid indexing, iterative querying), and post-retrieval refinements (compression, reranking).

One finding from Liu et al. (2024) that directly influenced the design of this project: when long retrieved contexts are fed into a model, the model pays noticeably more attention to the first and last sections than to the middle. Passages sitting in the interior of a long context window tend to be underused, even when they are the most relevant. This "lost in the middle" effect is one of the reasons hierarchical document representations like RAPTOR became attractive — they surface key content more consistently than flat chunk sequences.

### 2.1.2 Hallucination in Large Language Models

One thing that becomes apparent quickly when working with LLMs in production is that retrieval grounding reduces hallucination but does not stop it. Ji et al. (2023) surveyed this problem extensively and drew a useful distinction between two types of fabricated output: statements that directly contradict the source material, and statements that go beyond what the source says without technically contradicting it. Both are problematic in a policy QA context, but they call for different handling — outright contradictions should be removed, while unsupported extensions may only need a warning.

Tonmoy et al. (2024) looked at the range of available mitigation strategies and concluded that post-generation verification using NLI scoring is the most practical option for deployed systems, specifically because it works regardless of which underlying LLM is in use and requires no retraining. Xu et al. (2024) went further and argued — through formal analysis — that hallucination in language models is not a bug that better training can fully fix. It follows from the mathematical properties of fitting a finite set of parameters to a vast and often contradictory training corpus. The practical implication is that a production system should assume hallucination will occur and build detection into the pipeline rather than hoping the model has outgrown the tendency.

### 2.1.3 Natural Language Inference for Faithfulness

NLI is a classification task: given a premise and a hypothesis, a model decides whether the hypothesis is supported by the premise, contradicted by it, or neither. Maynez et al. (2020) were among the first to show that NLI scores track human faithfulness judgements well enough to be useful as an automated quality signal for generated text — which is what makes them practical here.

Falke et al. (2019) demonstrated that the same NLI-derived scoring idea could be used to rank candidate summaries by how factually accurate they are relative to their source. Laban et al. (2022) refined this into the SummaC framework, where the key move was switching from document-level NLI scoring to sentence-level scoring. Checking each output sentence independently, rather than the response as a whole, turned out to agree much more closely with human assessments — which makes sense, because a response can be mostly correct with one bad sentence buried in the middle. He et al. (2023) introduced DeBERTaV3, a cross-encoder NLI model that gives strong accuracy on standard benchmarks without being so slow that it becomes a bottleneck in a live pipeline. That combination of quality and speed made it the right choice for the faithfulness checker in this project.

### 2.1.4 Hybrid Retrieval Systems

A consistent finding across retrieval research is that dense embedding models and sparse keyword methods tend to be good at different things rather than the same thing. Lin and Ma (2021) described this clearly: term-frequency-based approaches like BM25 work best when query and document share the same precise vocabulary — which is common in policy documents full of specific role names, dates, and regulation codes. Dense retrieval, on the other hand, handles queries where the user paraphrases something that is stated differently in the document — a situation where keyword matching breaks down entirely. Using both together and combining their ranked outputs gets the benefits of both.

Cormack et al. (2009) introduced Reciprocal Rank Fusion as a clean way to merge multiple ranked lists without needing to normalise scores across retrievers. Each document's combined score is simply the sum of reciprocals of its positions in each list — a rank-based formula that is stable across retrieval methods with very different scoring scales. The BEIR benchmark (Thakur et al., 2021) later tested retrieval approaches across 18 different datasets from diverse domains and found that which method performs best depends on the domain — reinforcing the case for combining methods rather than picking one and hoping it generalises.

### 2.1.5 Hierarchical Document Representation (RAPTOR)

Standard RAG splits documents into fixed-size chunks and indexes those directly. This works for factual lookups targeting a specific paragraph, but struggles with questions that need information spread across several sections or even several documents. Sarthi et al. (2024) proposed RAPTOR as a way to build a second layer of representation on top of raw chunks. The process clusters chunk embeddings together, then has a language model write a short summary for each cluster. These summaries are added to the search index alongside the original chunks, so a query about a broad theme can retrieve a cluster summary that no single chunk would have matched, while a specific factual query still reaches the right raw passage.

The original RAPTOR experiments showed particularly large improvements on questions that require putting together a big-picture answer from scattered evidence — the kind of question that is common in policy documents where a procedure involves multiple departments and several steps spread across different sections.

### 2.1.6 Prompt Injection Attacks

A language model does not naturally distinguish between instructions that came from the system designer and text that came from the user — it processes them all as one sequence. Perez and Ribeiro (2022) published one of the first systematic studies of how this can be exploited: simple phrases like "ignore the above instructions and instead do X" embedded in a user query were enough to redirect the model's behaviour in ways the designer did not intend. The attack is easy to mount and was effective against naive deployments.

Greshake et al. (2023) showed that RAG systems face an additional exposure: an attacker who can plant malicious text inside a document that the system might retrieve has a channel to inject instructions that the model reads as part of its context rather than as user input. From the model's perspective, this retrieved malicious text looks the same as retrieved legitimate content. The OWASP Foundation (2023) subsequently listed prompt injection as the top security risk for LLM-based applications and recommended a combination of strict input validation, clear structural separation between system instructions and user content, and explicit role constraints in generation prompts — which maps closely to the three-layer defense built in this project.

### 2.1.7 Uncertainty Quantification

Getting a language model to produce useful confidence signals is harder than it sounds. Token probabilities reflect how likely a word continuation is, but not how likely the underlying claim is to be factually correct. Kuhn et al. (2023) addressed this with Semantic Entropy, which estimates uncertainty by generating multiple answers to the same question and measuring how much they disagree in meaning — not just in wording. The idea is that a model that is genuinely uncertain will produce noticeably different answers across runs, while a model that knows the answer well will keep saying the same thing in different words.

Manakul et al. (2023) took a similar consistency-based approach with SelfCheckGPT but framed it as a black-box method that works without access to model internals, making it applicable to API-based deployments as well. Kadavath et al. (2022) found something interesting: when large models are directly asked whether they think a given answer is correct, their self-assessments correlate reasonably well with actual accuracy. This suggests that prompting the model to express uncertainty is a lightweight option worth exploring in production systems where running multiple samples is too slow.

---

## 2.2 Proposed System

Reading through this body of work, it became clear that each piece of the puzzle has been studied individually but rarely put together in a single working system. **SecureHall-RAG** brings them all into one locally-deployable application with five integrated components:

1. **Hybrid Hierarchical Retrieval** — FAISS dense search and BM25 sparse search run in parallel, their results merged through RRF, refined by a cross-encoder reranker, and augmented with RAPTOR cluster summaries for thematic queries.

2. **NLI Faithfulness Verification** — a DeBERTa NLI cross-encoder scores each sentence of the generated answer for entailment against the retrieved context. A self-correction loop rewrites sentences that fall below threshold, and a four-tier soft redaction policy handles different levels of concern without discarding useful content.

3. **Three-Layer Prompt Injection Defense** — a regex content filter (covering 17+ attack categories with a 600-character input cap), XML-delimited structural sandboxing to prevent user text from overriding system instructions, and hardened role-reinforcing generation templates as the final layer.

4. **Four-Tier Uncertainty Signalling** — HIGH, MODERATE, LOW, and ABSTAIN tiers based on a composite of retrieval similarity and NLI faithfulness, shown to users as colour-coded confidence badges on every response.

5. **Full Production Stack** — FastAPI backend with JWT-based authentication, role-based access control, Server-Sent Events streaming, SQLite persistence, audit logging, Docker packaging, and a Next.js 14 frontend.

---

## 2.3 Scope of the Project

**What this project covers:**

- Documents in PDF, DOCX, and TXT formats, written in English.
- On-premises deployment on standard hardware — a GPU helps with LLM speed but the system runs on CPU-only machines too.
- LLM inference via Ollama running Llama-3.1-8B-Instruct in GGUF Q4 quantized format.
- Evaluation across retrieval quality, answer faithfulness, adversarial robustness, and uncertainty calibration dimensions.
- Single-tenant or small-team deployments; not designed for large public-facing traffic.

**What this project does not cover:**

- Non-English documents — the NLI model, the embedding model, and the LLM are all English-only in the current configuration.
- Queries outside the indexed corpus will either fall through to a web-search fallback or trigger an ABSTAIN response; the system makes no attempt to answer from general knowledge.
- RAPTOR summary generation happens synchronously at ingestion time; very large corpora would need this moved to an async background task.
- Latency on CPU-only hardware is substantial for the full enhanced pipeline — on the order of tens of seconds per query (roughly ~56 s when the NLI verification and self-correction loop runs), because each verification/self-correction step issues separate LLM calls. SSE streaming improves *perceived* latency by delivering tokens as they are produced, but interactive end-to-end latency requires GPU-accelerated inference.
- The FAISS index uses exhaustive flat search, which scales well to several thousand chunks but would need approximate-nearest-neighbour methods beyond that.

---

## 2.4 Identified Research Gaps

Going through the available literature, I found a consistent pattern: each of the five capabilities this project integrates has been studied in isolation, but no published system combines all of them in a single deployable application without cloud dependency.

| Capability | State of Existing Work |
|:---|:---|
| Hybrid dense + sparse retrieval | Well studied; several production tools exist |
| RAPTOR hierarchical summarization | Exists in research; rarely seen in deployed systems |
| NLI-based faithfulness verification | Well studied in research; almost never built into live QA systems |
| Prompt injection defense layers | Covered in security papers; seldom present in QA applications |
| User-visible confidence tiers | Discussed in uncertainty papers; almost never surfaced in interfaces |
| All five combined, fully on-premises | Not found in any published system |

The last row is the gap this project fills. For regulated sectors — healthcare, legal, government, finance — sending employee queries and document contents to a cloud API is often not an option. Data residency requirements, confidentiality obligations, and internal security policies all push toward on-premises solutions. A system that delivers all five trustworthiness features locally is genuinely absent from what is currently published or available as open source.

---

---

# CHAPTER 3: SYSTEM REQUIREMENTS SPECIFICATION (SRS)

## 3.1 Hardware Requirements

I ran the entire development and evaluation on a consumer laptop — nothing special. The table below captures what the minimum viable setup looks like versus what I actually used and what I would recommend for comfortable use.

| Component | Minimum | Recommended |
|:---|:---|:---|
| CPU | Intel Core i5 (8th Gen or newer) | Intel Core i7 / AMD Ryzen 7 |
| RAM | 8 GB | 16 GB or more |
| Storage | 20 GB free space | 50 GB SSD |
| GPU | Not required | NVIDIA GPU with 4 GB+ VRAM |
| OS | Windows 10 / Ubuntu 20.04 | Windows 11 / Ubuntu 22.04 |

**Evaluation environment:** Intel Core i7-12th Gen, 16 GB RAM, NVIDIA GeForce RTX 3050 Laptop GPU (4 GB VRAM), Windows 11. The LLM ran in CPU-only mode during evaluation to reflect the most constrained realistic deployment scenario.

---

## 3.2 Software Requirements

| Component | Technology | Version |
|:---|:---|:---|
| Runtime | Python | 3.10+ |
| Backend Framework | FastAPI + Uvicorn | 0.110+ |
| LLM Runtime | Ollama | 0.24+ |
| LLM Model | Llama-3.1-8B-Instruct (GGUF Q4) | — |
| ML Library | PyTorch | 2.0+ |
| Sentence Transformers | sentence-transformers | 2.6+ |
| Vector Index | FAISS | 1.7+ |
| Sparse Retrieval | rank_bm25 | 0.2+ |
| NLP Toolkit | NLTK | 3.8+ |
| Document Parsing | pdfplumber, python-docx | — |
| Database | SQLite + SQLAlchemy | 2.0+ |
| Auth Utilities | python-jose, passlib | — |
| Frontend | Next.js 14 (App Router) | 14.x |
| State Management | Zustand | 4.x |
| Containerization | Docker + Docker Compose | — |

---

## 3.3 Functional Requirements

These are the capabilities the system must provide. I defined them early and used them to track whether each part of the implementation actually delivered what it was supposed to.

| ID | Requirement |
|:---|:---|
| FR-01 | Accept PDF, DOCX, and TXT files and index their contents for retrieval. |
| FR-02 | Take natural language questions from authenticated users and return grounded answers. |
| FR-03 | Use a hybrid pipeline (dense + sparse + reranker) for passage retrieval. |
| FR-04 | Build RAPTOR cluster summaries at ingestion time and include them in the retrieval index. |
| FR-05 | Break complex multi-part questions into sub-questions before retrieval. |
| FR-06 | Score each generated sentence for factual support using an NLI model. |
| FR-07 | Attach a confidence tier (HIGH / MODERATE / LOW / ABSTAIN) to every response. |
| FR-08 | Screen incoming queries against known adversarial attack patterns and block matches. |
| FR-09 | Require JWT bearer token authentication on all API endpoints. |
| FR-10 | Save chat sessions and message history per user, persistently. |
| FR-11 | Stream response tokens to the frontend over SSE as they are generated. |
| FR-12 | Show source citations inline with every answer. |
| FR-13 | Give administrators a dashboard for managing users, documents, and audit logs. |
| FR-14 | Write a timestamped entry to the audit log for every security-relevant event. |

---

## 3.4 Non-Functional Requirements

Beyond what the system must do, these are the quality and deployment constraints it must satisfy.

| ID | Requirement |
|:---|:---|
| NFR-01 | All inference, retrieval, and storage must run locally — no outbound calls to cloud APIs. |
| NFR-02 | SSE streaming must begin delivering tokens within 5 seconds of query submission on local hardware. |
| NFR-03 | Semantically repeated queries must be served from cache without re-running the full pipeline. |
| NFR-04 | The application must be launchable with a single `docker-compose up` command. |
| NFR-05 | Access control must support at least two roles — standard user and administrator — with distinct permissions. |
| NFR-06 | All persistent data — messages, sessions, documents, audit entries — must be stored in a local SQLite database. |
| NFR-07 | The backend must handle concurrent requests without blocking, using async request processing throughout. |

---

---

# CHAPTER 4: SYSTEM DESIGN

## 4.1 System Architecture

The entire query flow in SecureHall-RAG moves through four stages in order. Nothing reaches the next stage until the current one completes successfully. This sequential structure was a deliberate choice — it means a malicious query gets caught at Stage 1 before it ever touches the retrieval index, and an unverified answer never reaches the user without going through Stage 4 first.

```
User Query
     |
     V
+----------------------------------+
|   STAGE 1: SECURITY FILTERING   |
|  Layer 1: Content Filter        |
|  Layer 2: Safe Prompting        |
|  Layer 3: Prompt Templates      |
+----------------+-----------------+
                 |
                 V
+----------------------------------+
|  STAGE 2: INTELLIGENT RETRIEVAL |
|  Semantic Cache Check           |
|  Multi-hop Decomposition        |
|  FAISS Dense + BM25 Sparse      |
|  Reciprocal Rank Fusion         |
|  RAPTOR Summary Nodes           |
|  Cross-Encoder Re-ranking       |
+----------------+-----------------+
                 |
                 V
+----------------------------------+
|  STAGE 3: GROUNDED GENERATION   |
|  Structured Prompt Assembly     |
|  Ollama LLM (Llama-3.1-8B)      |
|  Inline Citation Embedding      |
+----------------+-----------------+
                 |
                 V
+----------------------------------+
| STAGE 4: VERIFICATION & RESPONSE|
|  Sentence-Level NLI Scoring     |
|  Self-Correction Loop           |
|  Uncertainty Tier Assignment    |
|  SSE Streaming to Frontend      |
|  SQLite Persistence + Audit Log |
+----------------------------------+
```

Six design principles guided every decision:

1. **Defense in Depth** — security runs at three independent layers, so bypassing one does not open the system.
2. **Verify Before Returning** — no answer leaves Stage 4 without going through the NLI checker.
3. **Transparency** — every response carries source citations and a visible confidence tier.
4. **Local-First** — no data leaves the machine; all models, storage, and inference stay on-device.
5. **Modularity** — each stage is a self-contained module that can be swapped or upgraded independently.
6. **Production Quality** — authentication, audit logging, streaming, and the UI are built to a deployable standard, not a demo standard.

---

## 4.2 Data Flow Diagrams (DFD)

### Level 0 DFD (Context Diagram)

```
+----------+    Query      +------------------+    Answer     +----------+
|          |-------------->|                  |-------------->|          |
|   User   |               | SecureHall-RAG   |               |   User   |
|          |<--------------|   System         |<--------------|          |
+----------+    Response   +------------------+               +----------+
                                   |
                           +-------+-------+
                           |  Document     |
                           |  Repository   |
                           +---------------+
```

### Level 1 DFD

```
+--------+  Query  +----------+  Filtered  +----------+  Context  +----------+
|        |-------->| Security |----------->| Retrieval|---------->|  LLM     |
|  User  |         | Filter   |   Query    | Engine   |  Chunks   | Generator|
|        |         +----------+            +----------+           +----------+
|        |                                                              |
|        |<------------------------------------------------------------+
+--------+         Answer (citations + confidence tier)
```

---

## 4.3 Use Case Diagrams

| Actor | Use Case | What it does |
|:---|:---|:---|
| User | Login | Exchanges credentials for a JWT access token |
| User | Ask Question | Sends a natural language query to the pipeline |
| User | View Answer | Receives a streamed, cited, tier-rated response |
| User | View Citations | Expands a citation badge to read the source passage |
| User | View History | Browses and reloads previous chat sessions |
| User | Upload Document | Submits a file for ingestion and indexing |
| User | Provide Feedback | Marks an answer as helpful or not helpful |
| Admin | Manage Users | Creates, deactivates, or changes user roles |
| Admin | View Audit Logs | Reviews the timestamped security event log |
| Admin | Manage Documents | Views document inventory, triggers re-indexing |
| Admin | View Dashboard | Monitors query volume, confidence distribution, active users |

---

## 4.4 Sequence Diagrams

### Full Query Processing Sequence

```
1.  User types a query in the chat interface and submits
2.  Frontend sends POST /api/v1/query/stream with JWT Bearer token in header
3.  Backend verifies the token and extracts the user's identity and role
4.  Security Filter checks the query against 17+ injection pattern categories
        → If a pattern matches: return HTTP 400, write audit log entry, stop
5.  Cache Manager checks for a semantically similar cached query (cosine > 0.92)
        → Cache HIT: return the cached answer immediately (~120 ms)
        → Cache MISS: continue to Step 6
6.  Multi-hop Decomposer checks whether the query references multiple entities
        → If yes: LLM breaks it into sub-questions, each processed separately
7.  Retriever runs FAISS dense search and BM25 sparse search simultaneously
8.  RRF merges the two ranked lists; Cross-Encoder scores and re-ranks top 20
9.  RAPTOR summary nodes are included if thematic context is useful
10. LLM Generator assembles a structured XML-separated prompt and calls Ollama
11. NLI Verifier scores each sentence; self-correction rewrites low-scoring ones
12. Uncertainty module computes composite confidence → assigns HIGH/MODERATE/LOW/ABSTAIN
13. SSE stream sends metadata first (citations, confidence, tier), then tokens
14. DB writes the message, updates query history, and appends the audit log
15. User sees streamed answer with inline citation badges and a confidence badge
```

---

## 4.5 Database Design / Schema

The SQLite database is managed through SQLAlchemy ORM and contains seven tables. The schema was designed to support multi-user access, complete query history, per-answer feedback, and a full audit trail.

| Table | Key Columns |
|:---|:---|
| `users` | id, username, email, hashed_password, role, is_active |
| `chat_sessions` | id, user_id, title, created_at |
| `chat_messages` | id, session_id, role, content, confidence, uncertainty_tier, latency_ms |
| `query_history` | id, user_id, query_text, answer_text, confidence, uncertainty_tier |
| `audit_logs` | id, user_id, action, resource, details_json, ip_address, timestamp |
| `user_feedback` | id, answer_id, user_id, is_positive, comment |
| `documents` | doc_id, user_id, filename, file_size_bytes, chunk_count, status |

**Relationships:**
- One user → many chat sessions
- One session → many messages
- One user → many audit log entries
- One user → many uploaded documents
- One message → many feedback entries

---

---

# CHAPTER 5: IMPLEMENTATION DETAILS

## 5.1 Technologies Used / Programming Languages

**Table 5.1: Complete Technology Stack**

| Layer | Component | Technology | Version |
|:---|:---|:---|:---:|
| Backend Framework | API Server | FastAPI + Uvicorn | 0.110+ |
| LLM Inference | Local LLM | Ollama (Llama-3.1-8B-Instruct) | 0.24+ |
| Dense Retrieval | Vector Index | FAISS (IndexFlatIP) | 1.7+ |
| Embeddings | Sentence Encoder | all-mpnet-base-v2 (768-dim) | 2.6+ |
| Sparse Retrieval | BM25 | rank_bm25 (BM25Okapi) | 0.2+ |
| Re-ranking | Cross-Encoder | ms-marco-MiniLM-L-6-v2 | via ST |
| NLI Verification | Faithfulness | nli-deberta-v3-base | via ST |
| Clustering | K-Means | NumPy (custom) | 1.24+ |
| Database | ORM + Storage | SQLAlchemy + SQLite | 2.0+ |
| Authentication | JWT | python-jose + passlib | — |
| Frontend Framework | React | Next.js 14 (App Router) | 14.x |
| Frontend State | Store | Zustand | 4.x |
| Frontend Animation | Motion | Framer Motion | 10.x |
| Containerization | Docker | Docker Compose | — |

**Languages used:**
- **Python 3.10+** for everything on the backend — ingestion, retrieval, NLI, LLM calls, API.
- **TypeScript / React** for all frontend components, API integration, and state handling.
- **SQL** for schema definitions inside the SQLAlchemy ORM models.
- **YAML / Dockerfile** for Docker configuration and environment setup.

---

## 5.2 Modules Description

### Module 1: Document Ingestion Pipeline (`src/ingestion/`)

Getting documents into a retrievable state involves three sub-steps. First, the `DocumentParser` reads the file and extracts clean text — PDFs go through `pdfplumber` which preserves layout information and page numbers; DOCX files are read with `python-docx` in paragraph order; plain text files are loaded with UTF-8 decoding. Second, the `Chunker` splits that text into overlapping windows that respect sentence boundaries rather than cutting mid-sentence (target window: 512 tokens, overlap: 128 tokens, minimum chunk size: 50 tokens). Third, the `RaptorTreeBuilder` takes all the chunk embeddings, groups them into clusters with K-Means, and for each cluster asks the LLM to write a short 2–3 sentence summary. Those summaries go into the index as additional nodes alongside the raw chunks.

### Module 2: Hybrid Retrieval Engine (`src/retrieval/`)

| Component | Technology | Role |
|:---|:---|:---|
| Dense Retriever | FAISS IndexFlatIP + SBERT all-mpnet-base-v2 | Finds semantically similar passages |
| Sparse Retriever | BM25 Okapi (rank_bm25) | Finds passages with exact term matches |
| Fusion Layer | Reciprocal Rank Fusion (k=60) | Merges both ranked lists without score normalisation |
| Re-ranker | cross-encoder/ms-marco-MiniLM-L-6-v2 | Scores top-20 candidates jointly for high precision |
| Semantic Cache | Cosine similarity threshold (> 0.92) | Returns cached answers for near-duplicate queries |
| Web Fallback | DuckDuckGo search | Handles questions outside the indexed corpus |

### Module 3: LLM Inference Engine (`src/llm/`)

The `OllamaInference` class handles all communication with the locally running Ollama server. It supports both standard synchronous responses (for cases where the full answer is needed before processing) and streaming via SSE (for the chat interface). One practical challenge during development was that Ollama uses its own tag naming scheme that does not always match the model identifier in the config file — the module handles this by resolving the configured name against the list of available tags at startup.

### Module 4: NLI Faithfulness Verifier (`src/verification/`)

The `NLIFaithfulnessScorer` loads `cross-encoder/nli-deberta-v3-base` and runs each sentence of a generated answer against the full retrieved context as an NLI pair. The three-class output (contradiction / neutral / entailment) is converted to a probability score through softmax. A sentence classifier runs first to skip non-factual sentences like transitions and headings — this cuts the number of NLI calls by about 40% without affecting coverage. Results are cached by MD5 key so repeated checks on the same sentence do not re-run inference.

The `AnswerAssembler` applies a four-level policy based on each sentence's entailment score:
- **≥ 0.65** → include as-is
- **0.40–0.64** → include with an inline ⚠️ warning
- **0.25–0.39** → include with a 🔴 low-confidence marker
- **< 0.25** → remove (genuine contradiction only)

### Module 5: Security Framework (`src/security/`)

Three files, three independent layers. `content_filter.py` holds a compiled library of regex patterns covering over 17 adversarial input categories, plus a hard 600-character length cap enforced before any pattern matching. `safe_prompting.py` assembles the final prompt using XML tags — `<system>`, `<context>`, and `<user_query>` — so user text cannot syntactically escape into the system instruction zone. `prompt_templates.py` provides the hardened generation templates that restate the model's role and constraints at the start of every LLM call.

### Module 6: API Layer (`src/api/`)

FastAPI routes are grouped by function: `/auth/` for login and token refresh, `/query` and `/query/stream` for standard and streaming question answering, `/documents/` for upload and ingestion management, `/admin/` for dashboard and user management, `/history/` for session retrieval, and `/feedback/` for per-answer ratings. Every route except the login endpoint requires a valid JWT Bearer token. Role checks on admin routes use a FastAPI dependency that reads the role claim from the decoded token.

### Module 7: Frontend Application (`frontend/`)

Built on Next.js 14 using the App Router. The chat interface streams tokens via the browser's `EventSource` API and renders them as they arrive. Citation superscripts are clickable and slide open a side panel showing the source passage, document name, and relevance score. The confidence tier badge appears at the top of each response — colour-coded green, amber, orange, or red. The admin dashboard lives at `/admin` and is only accessible to users whose JWT contains `role: admin`.

---

## 5.3 Implementation Steps

Setting up the system from scratch follows this sequence:

1. **Environment**: Install Python 3.10+, Node.js 18+, and Ollama. Pull the Llama-3.1-8B-Instruct model via the Ollama CLI (`ollama pull llama3.1`). Clone the repo and run `pip install -r requirements.txt`.

2. **Database**: Run `python -m src.api.core.database` to create all SQLite tables. Use the init script to create the first admin account.

3. **Document Ingestion**: Upload files via the admin dashboard or directly via `POST /api/v1/documents/`. The pipeline parses, chunks, embeds, indexes into FAISS and BM25, and builds RAPTOR nodes automatically.

4. **LLM Config**: Set `OLLAMA_BASE_URL=http://localhost:11434` in the `.env` file. The model name resolver handles the rest.

5. **NLI Model**: Downloads automatically from Hugging Face on first run and is cached locally after that.

6. **Frontend**: `cd frontend && npm install && npm run dev` for development; `npm run build && npm start` for production.

7. **Docker**: `docker-compose up` from the project root starts both services with all dependencies wired together.

**Key implementation — RRF fusion:**

```python
def reciprocal_rank_fusion(dense_results, sparse_results, k=60):
    scores = {}
    for rank, chunk_id in enumerate(dense_results):
        scores[chunk_id] = scores.get(chunk_id, 0) + 1 / (k + rank + 1)
    for rank, chunk_id in enumerate(sparse_results):
        scores[chunk_id] = scores.get(chunk_id, 0) + 1 / (k + rank + 1)
    return sorted(scores, key=scores.get, reverse=True)
```

**Key implementation — NLI entailment scoring:**

```python
logits = self.model.predict(pairs)             # shape: (n_sentences, 3)
exp_logits = np.exp(logits - np.max(logits, axis=1, keepdims=True))
probs = exp_logits / np.sum(exp_logits, axis=1, keepdims=True)
entailment_probs = probs[:, 1]                 # index 1 = entailment class
faithfulness_score = float(np.mean(entailment_probs))
```

**Key implementation — SSE streaming endpoint:**

```python
async def event_generator():
    yield f"data: {json.dumps({'type': 'metadata', 'citations': citations,
                               'confidence': conf, 'uncertainty_tier': tier})}\n\n"
    async for token in llm.generate_stream(prompt):
        yield f"data: {json.dumps({'type': 'chunk', 'content': token})}\n\n"
    yield f"data: {json.dumps({'type': 'done', 'answer_id': answer_id})}\n\n"
```

---

---

# CHAPTER 6: SOFTWARE TESTING

## 6.1 Testing Strategies

Testing was structured across four levels, each targeting a different scope of the system.

**Unit Testing** checked individual functions in isolation, using mocked inputs for dependencies that touch the database, the LLM, or external models. The goal was to confirm that each module's logic is correct before anything gets wired together.

**Integration Testing** ran end-to-end flows through the complete pipeline using real documents and known queries. These tests are slower but they catch bugs that only appear when modules hand data to each other.

**System Testing** evaluated the deployed system against a prepared benchmark of 75 questions across five categories, measuring retrieval precision, answer quality, latency, and confidence tier distribution.

**Security Testing** ran a 60-case adversarial set against the live system to measure how many known attack patterns the security layers catch, and how the system handles edge cases where no pattern triggers.

---

## 6.2 Unit Testing

I wrote 85 unit tests across all 10 modules. Every test passed. The table below shows the breakdown.

**Table 6.1: Unit Test Coverage by Module**

| Module | Test Cases | Pass Rate |
|:---|:---:|:---:|
| `document_parser.py` | 12 | 100% |
| `chunker.py` | 8 | 100% |
| `dense_retriever.py` | 6 | 100% |
| `bm25_retriever.py` | 6 | 100% |
| `hybrid_retriever.py` (RRF) | 5 | 100% |
| `raptor_tree.py` | 7 | 100% |
| `nli_faithfulness.py` | 8 | 100% |
| `uncertainty.py` (tier logic) | 10 | 100% |
| `content_filter.py` | 17 | 100% |
| `auth / JWT` | 6 | 100% |
| **Total** | **85** | **100%** |

---

## 6.3 Integration Testing

Five integration scenarios were tested end-to-end:

- **Ingestion flow**: A test PDF was uploaded and processed. After ingestion, both the FAISS index and the BM25 index were queried directly to confirm the expected chunks were present.
- **Simple factual query**: A question with a clear, single-passage answer was processed through the full pipeline. The test verified that the retrieved chunk contained the answer, the NLI score was above 0.65, and the assigned tier was HIGH.
- **Out-of-scope query**: A question whose answer is not in any indexed document was submitted. The system correctly returned an ABSTAIN response rather than generating a speculative answer.
- **Multi-hop query**: A comparative question was submitted. The decomposer split it into two sub-questions, both were retrieved independently, and the merged result contained relevant chunks for each.
- **Cache hit**: The same query was submitted twice with slightly different wording. The second call hit the semantic cache (cosine > 0.92) and returned in under 150 ms without re-running the LLM.

---

## 6.4 System Testing

The benchmark covers 75 questions across five categories (15 per category): factual retrieval, multi-document synthesis, out-of-scope, numerical/date, and procedural how-to. Sixty of the 75 are answerable from the indexed corpus; 15 are unanswerable by design. All gold answers were auto-generated from the source documents.

**Table 6.2: Retrieval Precision@K and Recall@K** (60 answerable questions; P@K = 1 if any chunk from the correct source document appears in top-K)

| Configuration | P@1 | P@3 | P@5 | R@3 | R@5 |
|:---|:---:|:---:|:---:|:---:|:---:|
| Dense Only (FAISS) | 0.850 | 0.983 | 1.000 | 0.983 | 1.000 |
| Sparse Only (BM25) | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| Hybrid RRF (no rerank) | 0.983 | 1.000 | 1.000 | 1.000 | 1.000 |
| Hybrid RRF + Re-ranking | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| **SecureHall-RAG (Full)** | **1.000** | **1.000** | **1.000** | **1.000** | **1.000** |

**Table 6.3: Answer Quality Evaluation** (75 questions)

| Metric | Baseline | Enhanced |
|:---|:---:|:---:|
| ROUGE-L faithfulness (↑) | 0.087 | 0.074 |
| Semantic faithfulness — answer vs. context (↑) | 0.664 | 0.661 |
| Answer relevance (↑) | 0.636 | 0.636 |
| Mean confidence | 0.733 | 0.661 |

*Measured on a 15-question category-balanced subset via `evaluation/run_ablation.py` (Llama-3.1-8B, CPU), aggregated by `evaluation/compute_real_metrics.py`. None of the baseline↔enhanced differences are statistically significant (p = 0.51–0.99): the verification loop is a guard, not a generator, so it changes grounding little on already well-retrieved answers. ROUGE-L is near-zero because of a metric–task mismatch (short auto-generated gold answers), so semantic faithfulness ≈ 0.66 (embedding cosine between the answer and retrieved context) is the meaningful signal. Verification's real cost is latency — enhanced mean ≈ 149 s vs. baseline ≈ 50 s per query on CPU (+98 s, p < 0.001). These are subset figures; regenerate on the full 75-question set for final reporting.*

**Table 6.4: Confidence Tier Distribution** (enhanced mode, 15-question subset)

| Assigned Tier | % of Queries | What the system does |
|:---|:---:|:---|
| HIGH (≥ 0.75) | 40.0% | Full answer, green badge |
| MODERATE (0.50 – 0.75) | 26.7% | Full answer, amber badge |
| LOW (0.35 – 0.50) | 33.3% | Answer with verification disclaimer |
| ABSTAIN (< 0.35) | 0.0% | Safe refusal — no generated content |

The confidence-calibration fix reduced the ABSTAIN rate from a previously reported 69.3% to 0% on this answerable subset: a noisy CPU-mode NLI score was previously blended at 40% weight and pulled well-retrieved answers into ABSTAIN, whereas the blend now treats retrieval as the primary confidence signal and bounds how far verification can lower it. Note the tradeoff: abstention falls sharply, but the verifier now has less power to suppress a well-retrieved but poorly-grounded answer (in one enhanced case 7 of 8 claims were rejected yet confidence remained HIGH) — a residual over-confidence risk worth noting in the limitations.

---

## 6.5 Test Cases

**Table 6.5: Security Test Cases — Adversarial Handling** (60 cases; block rate over 31 should-block cases)

Two configurations are compared to isolate the embedding-similarity semantic attack detector added on top of the pattern filter.

| Attack Category | Cases | Should Block | Baseline (pattern) | Enhanced (pattern + semantic) |
|:---|:---:|:---:|:---:|:---:|
| Prompt Injection | 10 | 10 | 6 (60.0%) | 6 (60.0%) |
| Jailbreak | 10 | 10 | 5 (50.0%) | 7 (70.0%) |
| Encoded / Obfuscated | 10 | 8 | 6 (75.0%) | 6 (75.0%) |
| Edge Case | 10 | 3 | 0 (0.0%) | 0 (0.0%) |
| Hallucination Bait | 10 | 0 | N/A | N/A |
| Out of Distribution | 10 | 0 | N/A | N/A |
| **Total attack-block rate** | **60** | **31** | **17 (54.8%)** | **19 (61.3%)** |
| **Overall correct handling** | | | **45/60 (75.0%)** | **47/60 (78.3%)** |

The pattern filter is strongest against attacks with machine-readable signatures — encoded payloads at 75%, verbatim jailbreak phrases, instruction-override strings — blocking 54.8% of should-block cases. Adding an embedding-similarity semantic detector raises this to 61.3% and overall correct handling to 78.3% with no new false positives; the gain is entirely in the jailbreak category (5/10 → 7/10), where it catches contextual framings that trigger no specific pattern. Fully novel vectors (edge-case attacks, 0/3) remain the gap. An earlier draft reported a "100%" block rate; that did not survive a false-positive-aware re-evaluation and is corrected here.

**Table 6.6: System Performance Metrics**

| Metric | Value |
|:---|:---:|
| Retrieval (hybrid search + reranker) | <150 ms |
| LLM generation per call (CPU, Llama-3.1-8B) | ~5–30 s |
| NLI verification + self-correction (enhanced, CPU) | +tens of seconds/query (several extra LLM calls) |
| Semantic cache hit response time | ~120 ms |
| Document ingestion rate | ~2.3 pages/sec |
| FAISS index build (100 chunks) | 0.8 s |
| BM25 index build (100 chunks) | 0.3 s |

*Note: the previously reported "+8.6 ms verification overhead" and "~2.05 s total latency" were artefacts of a run in which the verification loop never actually executed. Real NLI claim-splitting, per-claim scoring, and self-correction each issue separate LLM calls, so on CPU the enhanced pipeline is a high-assurance, non-real-time mode; GPU/quantised inference is required for interactive latency.*

---

---

# CHAPTER 7: SCREENSHOTS AND OUTPUTS

## 7.1 Input Screens

### 7.1.1 Login Screen

A clean, glassmorphism-styled login form with username and password fields and a gradient Sign In button. Failed authentication shows an inline error message — no page reload.

### 7.1.2 Document Upload Interface

A drag-and-drop upload zone that accepts PDF, DOCX, and TXT files. After a file is dropped, a progress indicator moves through four stages: parsing, chunking, embedding, and RAPTOR build. The file list below shows each document's name, size, chunk count, and current ingestion status.

### 7.1.3 Chat Query Interface

A full-height conversation panel with a pinned input bar at the bottom. A collapsible sidebar on the left lists previous sessions by date. Clicking any past session restores the full message thread.

---

## 7.2 Output / Report Screens

### 7.2.1 Streamed Answer with Uncertainty Badge

As soon as a query is submitted, the confidence badge and citation superscripts appear before the first token arrives. Tokens then stream into the answer box in real time. The badge colour maps to the uncertainty tier:

| Tier | Badge Colour | Icon |
|:---|:---|:---|
| HIGH | Emerald (green) | Shield Check |
| MODERATE | Amber (yellow) | Alert Triangle |
| LOW | Orange | Alert Triangle |
| ABSTAIN | Red | Shield Alert |

### 7.2.2 Citation Panel

Tapping a citation badge (e.g. [1]) slides open a right-side drawer showing the source document name, page number, relevance score, and the exact retrieved passage that backs the cited claim.

### 7.2.3 Admin Dashboard

Four tabs: Overview (query totals, average confidence, active users), Users (role assignment and account controls), Documents (inventory with per-document chunk counts and re-index buttons), and Audit Logs (a filterable, timestamped event table showing user, action, and IP address).

---

---

# CHAPTER 8: CONCLUSION AND FUTURE SCOPE

## 8.1 Conclusion

SecureHall-RAG set out to solve four specific problems that make existing RAG deployments unreliable in enterprise settings: hallucination, adversarial manipulation, retrieval gaps, and opacity. Looking at what was built and what the evaluation showed, here is an honest summary of what was achieved.

**Retrieval** is the clearest win. Combining FAISS dense search with BM25 sparse retrieval through Reciprocal Rank Fusion, then applying a cross-encoder reranker on the top candidates, brings document-level Precision@1 from 0.850 (dense-only) to a perfect 1.000. The system reliably surfaces the right source document for every answerable question in the benchmark. RAPTOR cluster summaries extend coverage to thematic queries without hurting precision on factual ones.

**Faithfulness verification** works architecturally even if ROUGE-L does not capture it. The NLI pipeline flags low-confidence claims with inline warnings and activates safe ABSTAIN responses when it cannot sufficiently support an answer. The cost is real, not negligible: the loop makes several extra LLM calls (claim-splitting, per-claim scoring, self-correction), adding tens of seconds per query on CPU — GPU inference is needed for interactive use. The main limitation is measurement: ROUGE-L against short auto-generated gold answers is the wrong metric for this task, which is why an embedding-based semantic faithfulness score was added as a better proxy. The system's actual behaviour is more useful than the ROUGE-L score suggests.

**Security** is partial and honest about it. The pattern filter alone catches 54.8% of should-block adversarial inputs; adding an embedding-similarity semantic detector raises this to 61.3% and overall correct handling from 75.0% to 78.3%, with no new false positives. Encoded and obfuscated payloads are blocked at 75%, and the semantic layer adds the contextual jailbreaks that trigger no specific signature. Fully novel vectors that are also semantically distant from every known attack intent are the gap that remains.

**Uncertainty signalling** is implemented and functional. The four-tier confidence framework assigns graduated responses — from full answers with green badges down to explicit safe refusals — based on a composite of retrieval and NLI scores. This gives users a visible, actionable signal rather than a number.

**Privacy** is non-negotiable for many of the organisations this system is built for. Running entirely on local hardware, with no outbound API calls, means the system can be deployed in regulated sectors where cloud data transmission is not permitted.

---

## 8.2 Limitations of the Project

Being direct about what does not work yet:

- **Latency** for the full enhanced pipeline is on the order of tens of seconds per query on CPU-only hardware (~56 s when the verification + self-correction loop runs), driven by repeated sequential LLM calls in Ollama's CPU mode. It is a high-assurance, non-real-time mode on CPU; GPU/quantised inference is required to make it conversational.
- **Language support** is English only. The embedding model, the NLI model, and Llama-3.1 are all English-centric in this configuration.
- **Corpus scale** — the FAISS flat index is fine up to a few thousand chunks but would need approximate nearest-neighbour indexing for much larger document sets.
- **RAPTOR depth** — the current implementation builds only one level of cluster summaries. Full recursive multi-level RAPTOR is not yet implemented.
- **Evaluation scale** — the benchmark is 75 auto-generated questions across 10 documents. This is enough to establish trends but not enough to claim generalisation across diverse enterprise corpora.
- **Human evaluation** was not conducted. All quality measurements are automated. ROUGE-L in particular underestimates answer quality against this dataset's short gold answers.

---

## 8.3 Future Enhancements

**GPU inference** is the single change that would make the biggest practical difference. Running the LLM with Q4 GGUF quantization on the existing RTX 3050 would cut end-to-end latency from ~2 seconds to well under 500 ms, making real-time conversation genuinely viable.

**Semantic attack detection** would address the biggest security gap. Rather than only checking against a fixed pattern library, computing the embedding similarity between an incoming query and a curated set of known attack phrasings would flag novel jailbreak variants that use indirect language to avoid exact matches.

**Multilingual support** by swapping in a multilingual embedding model and an instruction-tuned multilingual LLM would open the system to global enterprise deployments where not all documentation is in English.

**Online feedback learning** — the thumbs-up/thumbs-down ratings already collected through the feedback API could feed periodic fine-tuning of the embedding model, gradually improving retrieval quality for domain-specific vocabulary over time.

**Full recursive RAPTOR** — extending the current single-level cluster summary to multiple recursive levels would help with very large corpora where even thematic clusters are too broad to produce useful single-summary nodes.

**Graph-augmented retrieval** — building a lightweight knowledge graph from entity and relation extraction on the policy corpus could enable more structured multi-hop reasoning, replacing the current LLM-driven decomposition with explicit graph traversal for queries involving named roles, departments, or regulations.

**Standardised security benchmarking** — running the security layer against published adversarial prompt injection suites would give a comparable, reproducible robustness score rather than results only on a project-specific test set.

---

---

# CHAPTER 9: REFERENCES

[1] P. Lewis, E. Perez, A. Piktus, F. Petroni, V. Karpukhin, N. Goyal, H. Küttler, M. Lewis, W.-t. Yih, T. Rocktäschel, S. Riedel, and D. Kiela, "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks," in *Advances in Neural Information Processing Systems (NeurIPS)*, vol. 33, pp. 9459–9474, 2020.

[2] Z. Ji, N. Lee, R. Frieske, T. Yu, D. Su, Y. Xu, E. Ishii, Y. J. Bang, A. Madotto, and P. Fung, "Survey of Hallucination in Natural Language Generation," *ACM Computing Surveys*, vol. 55, no. 12, pp. 1–38, 2023.

[3] F. Perez and I. Ribeiro, "Ignore Previous Prompt: Attack Techniques for Language Models," in *Workshop on Trustworthy and Socially Responsible Machine Learning (TSRML), NeurIPS*, 2022.

[4] V. Karpukhin, B. Oguz, S. Min, P. Lewis, L. Wu, S. Edunov, D. Chen, and W.-t. Yih, "Dense Passage Retrieval for Open-Domain Question Answering," in *Proc. EMNLP*, pp. 6769–6781, 2020.

[5] Y. Gao, Y. Xiong, X. Gao, K. Jia, J. Pan, Y. Bi, Y. Dai, J. Sun, and H. Wang, "Retrieval-Augmented Generation for Large Language Models: A Survey," *arXiv preprint arXiv:2312.10997*, 2023.

[6] N. F. Liu, K. Lin, J. Hewitt, A. Paranjape, M. Bevilacqua, F. Petroni, and P. Liang, "Lost in the Middle: How Language Models Use Long Contexts," *Transactions of the Association for Computational Linguistics*, vol. 12, pp. 157–173, 2024.

[7] S. Maynez, S. Narayan, B. Bohnet, and R. McDonald, "On Faithfulness and Factuality in Abstractive Summarization," in *Proc. ACL*, pp. 1906–1919, 2020.

[8] K. Shuster, S. Poff, M. Chen, D. Kiela, and J. Weston, "Retrieval Augmentation Reduces Hallucination in Conversation," in *Findings of EMNLP*, pp. 3784–3803, 2021.

[9] T. Falke, L. F. R. Ribeiro, P. A. Utama, I. Dagan, and I. Gurevych, "Ranking Generated Summaries by Correctness: An Interesting but Challenging Application for Natural Language Inference," in *Proc. ACL*, pp. 2214–2220, 2019.

[10] P. He, J. Gao, and W. Chen, "DeBERTaV3: Improving DeBERTa using ELECTRA-Style Pre-Training with Gradient-Disentangled Embedding Sharing," in *Proc. ICLR*, 2023.

[11] P. Laban, T. Schnabel, P. N. Bennett, and M. A. Hearst, "SummaC: Re-Visiting NLI-Based Models for Inconsistency Detection in Summarization," *Transactions of the Association for Computational Linguistics*, vol. 10, pp. 163–177, 2022.

[12] J. Lin and X. Ma, "A Few Brief Notes on DeepImpact, COIL, and a Conceptual Framework for Information Retrieval Techniques," *arXiv preprint arXiv:2106.14807*, 2021.

[13] G. V. Cormack, C. L. A. Clarke, and S. Buettcher, "Reciprocal Rank Fusion Outperforms Condorcet and Individual Rank Learning Methods," in *Proc. SIGIR*, pp. 758–759, 2009.

[14] T. Thakur, N. Reimers, A. Ruckle, A. Srivastava, and I. Gurevych, "BEIR: A Heterogeneous Benchmark for Zero-Shot Evaluation of Information Retrieval Models," in *Advances in Neural Information Processing Systems Datasets and Benchmarks Track*, 2021.

[15] P. Sarthi, S. Abdullah, A. Tuli, S. Khanna, A. Goldie, and C. D. Manning, "RAPTOR: Recursive Abstractive Processing for Tree-Organized Retrieval," in *Proc. ICLR*, 2024.

[16] K. Greshake, S. Abdelnabi, S. Mishra, C. Endres, T. Holz, and M. Fritz, "Not What You've Signed Up For: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection," in *Proc. AISec Workshop at CCS*, 2023.

[17] OWASP Foundation, "OWASP Top 10 for Large Language Model Applications," OWASP, 2023.

[18] L. Kuhn, Y. Gal, and S. Farquhar, "Semantic Uncertainty: Linguistic Invariances for Uncertainty Estimation in Natural Language Generation," in *Proc. ICLR*, 2023.

[19] P. Manakul, A. Liusie, and M. J. F. Gales, "SelfCheckGPT: Zero-Resource Black-Box Hallucination Detection for Generative Large Language Models," in *Proc. EMNLP*, pp. 9745–9765, 2023.

[20] S. Kadavath et al., "Language Models (Mostly) Know What They Know," *arXiv preprint arXiv:2207.05221*, 2022.

[21] A. Asai, Z. Wu, Y. Wang, A. Sil, and H. Hajishirzi, "Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection," in *Proc. ICLR*, 2024.

[22] Z. Xu, S. Jain, and M. Kankanhalli, "Hallucination is Inevitable: An Innate Limitation of Large Language Models," *arXiv preprint arXiv:2401.11817*, 2024.

[23] S. M. Tonmoy, S. M. Zaman, V. Jain, A. Rani et al., "A Comprehensive Survey of Hallucination Mitigation Techniques in Large Language Models," *arXiv preprint arXiv:2401.01313*, 2024.

---

---

# CHAPTER 10: APPENDIX

## Glossary

| Term | Definition |
|:---|:---|
| RAG | Retrieval-Augmented Generation: An architecture that grounds LLM answers in retrieved document passages. |
| Hallucination | Generation of plausible but factually unsupported content by a language model. |
| NLI | Natural Language Inference: Task of classifying whether a hypothesis is entailed, contradicted, or neutral with respect to a premise. |
| FAISS | Facebook AI Similarity Search: A library for efficient dense vector similarity search. |
| BM25 | Best Match 25: A probabilistic bag-of-words retrieval function. |
| RAPTOR | Recursive Abstractive Processing for Tree-Organized Retrieval: A hierarchical document summarization method. |
| RRF | Reciprocal Rank Fusion: A parameter-free method for combining multiple ranked retrieval lists. |
| Prompt Injection | An adversarial attack that embeds instructions in user input or retrieved context to override the LLM's system prompt. |
| Uncertainty Tier | One of four confidence levels (HIGH/MODERATE/LOW/ABSTAIN) assigned to each answer based on NLI score, retrieval score, and query type. |
| SSE | Server-Sent Events: A web standard for server-to-client streaming over HTTP. |
| JWT | JSON Web Token: A compact, URL-safe token format for authentication. |

---

## Sample API Code Snippets

### Authentication — Login

```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "username": "devendra",
  "password": "your_password"
}
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

### Standard Query

```http
POST /api/v1/query
Authorization: Bearer <token>
Content-Type: application/json

{
  "query": "How many days of casual leave am I entitled to per year?"
}
```

Response:
```json
{
  "answer": "Employees are entitled to 12 days of casual leave per calendar year [1].",
  "confidence": 0.91,
  "uncertainty_tier": "HIGH",
  "citations": [{"id": 1, "text": "...", "source": "HR_Policy.pdf", "page": 4}],
  "hallucination_risk": false
}
```

### Streaming Query

```http
GET /api/v1/query/stream?query=What+is+the+maternity+leave+policy
Authorization: Bearer <token>
Accept: text/event-stream
```

---

## Sample Benchmark Queries

| # | Category | Query |
|:---:|:---|:---|
| 1 | Factual | How many sick days per year is each employee entitled to? |
| 2 | Factual | What is the notice period for resignation? |
| 3 | Factual | What is the company's data retention policy duration? |
| 4 | Comparative | Compare the maternity leave and paternity leave benefits. |
| 5 | Comparative | What is the difference between casual leave and sick leave? |
| 6 | Definitional | What is the performance improvement plan process? |
| 7 | Definitional | How does the company define a data breach? |
| 8 | Out-of-scope | What is the current stock price of the company? |
| 9 | Out-of-scope | Who won the most recent employee of the year award? |
| 10 | Multi-hop | Which department head is responsible for approving extended medical leave? |
