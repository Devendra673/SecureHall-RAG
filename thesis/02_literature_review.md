# CHAPTER 2: LITERATURE REVIEW

---

## 2.1 Retrieval-Augmented Generation (RAG)

Retrieval-Augmented Generation (RAG) was formally introduced by Lewis et al. [1] at Facebook AI Research in 2020. The foundational insight is that language models perform significantly better on knowledge-intensive tasks when conditioned on retrieved passages from an external non-parametric memory, rather than relying solely on the knowledge encoded in their parameters during training. The original RAG framework uses a Dense Passage Retriever (DPR) [4] for retrieval and a seq2seq generator (BART) for generation, training both components end-to-end.

Since this foundational work, RAG has become the dominant paradigm for open-domain QA and document-grounded generation tasks. Subsequent work has explored variations including RAG-Sequence and RAG-Token models [1], which differ in how retrieved documents are marginalized during generation. Gao et al. [5] provide a comprehensive survey of the RAG landscape, categorizing approaches by retrieval granularity (chunk-level, document-level, sentence-level), retrieval timing (pre-retrieval, during generation, post-hoc), and augmentation method.

**Naive RAG** [5] refers to the basic pipeline of: (1) query encoding, (2) approximate nearest-neighbor retrieval, (3) context concatenation, and (4) generation. While simple, this approach suffers from retrieval noise (irrelevant passages in the context) and the "lost in the middle" problem [6], where LLMs fail to attend to information appearing in the middle of long context windows.

**Advanced RAG** techniques address these limitations through query rewriting, iterative retrieval, step-back prompting, and re-ranking. SecureHall-RAG adopts several of these advanced techniques, including cross-encoder re-ranking, hybrid retrieval, and query decomposition for multi-hop reasoning.

---

## 2.2 Hallucination in Language Models

Hallucination in language models refers to the generation of text that is fluent and grammatically correct but factually incorrect, unverifiable, or unsupported by available evidence. Ji et al. [2] and Tonmoy et al. [29] provide comprehensive surveys of hallucination types, causes, and mitigation strategies across NLP tasks. While traditional NLP focuses on textual hallucinations, recent work by Bai et al. [30] expands this taxonomy to multimodal domains, demonstrating that cross-modal representation gaps amplify hallucination rates.

Two major categories of hallucination are identified in the literature:

1. **Intrinsic Hallucination**: The generated text directly contradicts information present in the source context. This occurs when the LLM overrides retrieved facts with its parametric knowledge.

2. **Extrinsic Hallucination**: The generated text introduces claims that cannot be verified from the source context — neither confirmed nor contradicted. These are particularly dangerous as they appear plausible.

From a theoretical perspective, Xu et al. [31] prove that hallucination is mathematically inevitable for any transformer-based language model due to fundamental limits in computational complexity and dataset density, establishing the necessity of post-hoc verification frameworks like SecureHall-RAG. Empirically, Kalai et al. [32] analyze the origins of hallucination during pre-training, showing that models naturally fabricate facts when trained on datasets containing uncorrected factual errors or contradictory sources.

Maynez et al. [7] conducted a large-scale human evaluation study on faithfulness in abstractive summarization and found that over 70% of model-generated summaries contained some form of hallucination. Their work demonstrated that NLI-based automatic metrics correlate well with human faithfulness judgments, motivating the use of NLI verification in SecureHall-RAG.

In the RAG context, Shuster et al. [8] showed that grounding language models in retrieved documents substantially reduces hallucination compared to pure generative models. However, they also found that retrieval quality is a major bottleneck — poor retrieval leads to the LLM generating answers that drift from the retrieved but irrelevant passages.

---

## 2.3 Natural Language Inference for Faithfulness

Natural Language Inference (NLI) is the task of determining whether a hypothesis can be inferred (entailment), contradicted (contradiction), or neither (neutral) from a premise. NLI models have been widely adopted as automatic faithfulness metrics for summarization and QA systems.

Falke et al. [9] were among the first to repurpose NLI models for faithfulness evaluation, demonstrating that entailment scores from off-the-shelf NLI classifiers correlate with human factuality judgments in summarization.

**DeBERTa-based NLI models** have emerged as state-of-the-art for this task. The `cross-encoder/nli-deberta-v3-small` model used in SecureHall-RAG is based on the DeBERTa-v3 architecture [10], which improves upon BERT through disentangled attention and an enhanced mask decoder. The cross-encoder formulation means the premise-hypothesis pair is processed jointly, allowing richer interaction compared to bi-encoder models.

In SecureHall-RAG's implementation, each sentence of the generated answer is treated as a hypothesis and the concatenated retrieved context as the premise. The mean entailment probability across all sentences forms the overall faithfulness score. This sentence-level decomposition approach is inspired by SummaC [11], which computes document-level consistency scores by aggregating sentence-NLI scores. 

Beyond pure NLI, recent work focuses on structural constraints and fine-grained claim-level evaluation. Recski et al. [33] introduce *ACL-Verbatim*, demonstrating that integrating rule-based syntactic checking with language generation can eliminate intrinsic hallucination in scientific research QA. In the legal domain, Das et al. [34] construct a fine-grained, claim-level RAG benchmark, proving that sentence-level NLI models are highly effective at detecting subtle factual misalignments in complex, high-stakes documents, validating SecureHall-RAG's sentence-level design.

---

## 2.4 Hybrid Retrieval Systems

The dual-encoder dense retrieval approach of DPR [4] was a major advance over BM25-based sparse retrieval for semantic search, but subsequent work has shown that **hybrid systems combining dense and sparse retrieval consistently outperform either approach alone**.

Lin and Ma [12] demonstrate through extensive experiments that BM25 and dense retrieval are complementary: BM25 excels at exact keyword matching and rare-term retrieval, while dense models better handle semantic paraphrasing and conceptual similarity. They propose Reciprocal Rank Fusion (RRF) [13] as an effective, parameter-free method for combining ranked lists from both retrieval systems.

The BEIR benchmark [14] provides a comprehensive evaluation across 18 diverse retrieval tasks and shows that no single retrieval method dominates across all domains. Hybrid systems consistently achieve the best trade-off across datasets, motivating the hybrid approach in SecureHall-RAG.

**Cross-encoder re-ranking** was introduced as a second-stage refinement step by Nogueira et al. [15]. Rather than computing query and document embeddings independently (as bi-encoders do), cross-encoders process the query-document pair jointly, allowing full attention interaction between them. This yields significantly higher re-ranking accuracy at the cost of higher latency. SecureHall-RAG uses `cross-encoder/ms-marco-MiniLM-L-6-v2` for re-ranking the top-K candidates from hybrid retrieval.

---

## 2.5 Hierarchical Document Summarization — RAPTOR

RAPTOR (Recursive Abstractive Processing for Tree-Organized Retrieval) was proposed by Sarthi et al. [16] at Stanford University in 2024 and represents a significant advance in the representation of long documents for RAG systems.

The key insight of RAPTOR is that flat chunking — dividing documents into fixed-size passages — fails to capture high-level thematic relationships across documents. A question like *"What is the overall HR policy philosophy?"* requires synthesizing information from many disparate chunks, none of which individually contains a satisfactory answer.

RAPTOR builds a hierarchical tree of document representations through recursive clustering and summarization:
1. Documents are chunked and embedded.
2. Chunks are clustered using Gaussian Mixture Models (GMM) in the original paper.
3. An LLM generates abstractive summaries for each cluster.
4. Summaries are re-embedded and clustered again recursively until a single root summary is produced.
5. All nodes (raw chunks and summaries at all levels) are indexed for retrieval.

SecureHall-RAG adopts a simplified single-level RAPTOR approach using K-Means clustering (implemented from scratch using NumPy) instead of GMM, and generates one level of cluster summaries. This design choice balances the benefits of hierarchical representation against computational overhead, making it suitable for local CPU-only deployment. Experiments show that even single-level RAPTOR summaries improve recall for high-level queries.

This hierarchical, local-first paradigm is aligned with recent developments in GraphRAG. Fernandes and Kanjilal [35] benchmarked GraphRAG implementations on consumer hardware, demonstrating that structural relationship extraction and cluster summarization significantly improve local LLM recall on specialized healthcare schemas, validating the efficacy of running lightweight hierarchical indices locally rather than relying on massive cloud databases.

---

## 2.6 Multi-hop Reasoning in Question Answering

Multi-hop reasoning requires synthesizing information from multiple, disparate sources to answer questions that cannot be resolved by a single retrieved passage. Yang et al. [17] introduced the HotpotQA benchmark specifically to evaluate multi-hop reasoning, demonstrating that simple retrieval-and-read models fail on questions requiring the traversal of multiple evidence chains.

Several approaches to multi-hop QA have been proposed:

- **Iterative Retrieval**: Retrieve-read-retrieve cycles where each retrieval step is informed by the previous answer [18].
- **Query Decomposition**: Breaking the original question into simpler sub-questions that can be answered independently [19].
- **Graph-based Approaches**: Building knowledge graphs from documents and traversing them for multi-hop inference [20].

SecureHall-RAG adopts a **query decomposition** approach inspired by Perez et al. [19]. The LLM is prompted to analyze the input query and output a JSON list of focused sub-questions. For each sub-question, the hybrid retrieval pipeline is executed independently, and the retrieved context lists are merged and deduplicated by chunk ID before being passed to the generation step. This approach is particularly effective for comparative questions (e.g., *"Compare the leave policies of the HR and IT departments"*) and multi-entity questions.

---

## 2.7 Prompt Injection Attacks and Defenses

Prompt injection attacks represent a novel category of adversarial attack unique to LLM-based applications. Perez and Ribeiro [3] were among the first to systematically study prompt injection, demonstrating that malicious instructions embedded in user inputs can override system prompts, cause the model to ignore its constraints, and leak sensitive information.

Greshake et al. [21] expanded this work to study **indirect prompt injection** in RAG systems, where malicious instructions are embedded within documents retrieved from external sources. In this attack vector, the adversary plants adversarial instructions in a document that, when retrieved as context, causes the LLM to execute the attacker's commands.

Adversarial methods have become increasingly sophisticated. Nafi et al. [36] introduced *LASH*, an adaptive semantic hybridization technique that constructs black-box jailbreaks by blending benign and malicious contexts, demonstrating that standard filters can easily be bypassed by hybrid semantic distributions. To counter this, Wang et al. [37] advocate for *context-invariant safety alignment*, modifying model behaviors so that safety guidelines remain active regardless of adversarial modifications in the input context.

Categories of attacks studied in the literature include:

- **Direct Injection**: Malicious instructions directly in user queries ("Ignore previous instructions and...")
- **Jailbreaking**: Prompts designed to bypass safety training ("Pretend you are DAN, an AI without restrictions...")
- **Role-play Attacks**: Framing attacks as hypothetical scenarios ("In a story where you are a different AI...")
- **Encoding Attacks**: Base64 or other encoding to bypass content filters
- **Context Overflow**: Flooding the context to push system instructions out of the model's attention window
- **Data Exfiltration**: Prompts designed to extract training data or context information

SecureHall-RAG addresses these attacks through a 3-layer defense:
1. **Content Filter** (`content_filter.py`): Rule-based pattern matching using regex against 17+ injection signatures.
2. **Safe Prompting** (`safe_prompting.py`): Structural prompt sandboxing using XML-tagged roles and instruction pinning.
3. **Prompt Templates** (`prompt_templates.py`): Template-based separation of system context from user input to prevent context contamination.

This defense-in-depth approach is consistent with recommendations from the OWASP Top 10 for LLM Applications [22] and incorporates context-invariant boundaries to resist hybrid semantic attacks like LASH [36].

---

## 2.8 Uncertainty Quantification in NLP

Uncertainty quantification (UQ) in NLP addresses the critical question of *how confident is the model in its predictions?* Kuhn et al. [23] introduced Semantic Entropy as a principled measure of LLM uncertainty, computing entropy over semantically equivalent answer clusters rather than individual tokens. This approach captures uncertainty at the meaning level rather than the surface-form level.

For practical RAG deployments, retrieval-based confidence scores offer a simpler proxy for uncertainty. The intuition is that when retrieved context has low relevance to the query (as measured by similarity scores), the LLM is being asked to answer without sufficient grounding, leading to a higher probability of hallucination.

Manakul et al. [24] proposed SelfCheckGPT, which estimates consistency across multiple LLM samples as an uncertainty measure. Kadavath et al. [25] showed that LLMs can be prompted to express their own uncertainty through calibrated verbalized confidence estimates.

Evaluating these systems requires robust benchmarking frameworks. Roy et al. [38] present findings from the *Counter Turing Test*, illustrating the challenges in detecting AI-generated text as model generation quality improves, which underscores the need for clear uncertainty indicators (like confidence badges) so users can distinguish verified facts from plausible machine-written text. To standardize RAG benchmarking, Ruan et al. [39] introduce the *MTR-Suite*, a unified framework for evaluating and synthesizing conversational retrieval datasets, demonstrating that robust evaluation must encompass retrieval recall, answer faithfulness, and multi-turn consistency.

SecureHall-RAG adopts a retrieval-score-based uncertainty quantification scheme, mapping the normalized confidence score (derived from retrieval similarity scores and NLI faithfulness scores) to four discrete tiers (HIGH, MODERATE, LOW, ABSTAIN). This design is practical, computationally efficient, and interpretable for end users, directly addressing the opacity problem identified in the literature and aligned with MTR-Suite's multidimensional evaluation paradigm [39].

---

## 2.9 Comparison of Related Systems

Table 2.1 summarizes the key features of related enterprise RAG systems and compares them against SecureHall-RAG:

**Table 2.1: Comparison of Related RAG Systems**

| System | Hybrid Retrieval | NLI Verification | RAPTOR | Multi-hop | Injection Defense | Uncertainty QT | Local Deploy |
|---|---|---|---|---|---|---|---|
| Naive RAG [1] | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| Advanced RAG [5] | Partial | ❌ | ❌ | Partial | ❌ | ❌ | ✅ |
| RAPTOR [16] | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ✅ |
| SelfRAG [26] | ❌ | Partial | ❌ | ❌ | ❌ | Partial | ✅ |
| LlamaIndex RAG | ✅ | ❌ | ❌ | Partial | ❌ | ❌ | ✅ |
| **SecureHall-RAG** | **✅** | **✅** | **✅** | **✅** | **✅** | **✅** | **✅** |

---

## 2.10 Summary and Research Gaps

The literature review reveals the following key insights:

1. RAG significantly reduces hallucination over purely generative approaches but does not eliminate it. Post-hoc NLI verification is a promising and practical mitigation strategy.

2. Hybrid retrieval consistently outperforms single-modality approaches. The combination of BM25 (sparse) and FAISS (dense) with cross-encoder re-ranking is the current best practice.

3. RAPTOR hierarchical summarization addresses a fundamental limitation of flat chunking for high-level queries but has not been widely applied to enterprise policy document QA.

4. Multi-hop query decomposition improves answer quality for comparative and multi-entity questions, yet most enterprise RAG systems use single-pass retrieval.

5. Prompt injection is a serious and underaddressed vulnerability in enterprise LLM deployments. Defense-in-depth approaches combining content filtering, structural prompt isolation, and role pinning are recommended.

6. Uncertainty quantification in RAG is underexplored, particularly for practical, locally-deployable systems. Most existing work focuses on probabilistic measures that require multiple LLM samples, which is computationally expensive.

**Research Gap**: No existing system combines all six capabilities — hybrid retrieval with RAPTOR, NLI faithfulness verification, multi-hop decomposition, prompt injection defense, and practical uncertainty quantification — in a single, locally-deployable, enterprise-grade application. SecureHall-RAG addresses this gap.

---
