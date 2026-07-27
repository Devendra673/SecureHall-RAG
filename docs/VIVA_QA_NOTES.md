# SecureHall-RAG: Viva & Defense Q&A Notes

This document contains anticipated questions from your defense committee and the optimal technical answers to defend your architecture decisions.

---

## 1. Retrieval & Search Mechanisms

**Q: Why did you use Hybrid Search instead of just standard vector embeddings (FAISS/Chroma)?**
**Answer:** Dense embeddings (like `all-MiniLM-L6-v2`) map text to semantic meanings in a vector space. While excellent for understanding intent, they often fail at exact keyword matching (e.g., specific acronyms, names, or ID numbers). BM25 is a sparse retrieval algorithm that excels at keyword matching. By combining both (Hybrid Retrieval), the system captures both the semantic meaning of the question and any exact lexical matches, significantly boosting recall.

**Q: You mentioned using a Cross-Encoder for re-ranking. Why is this necessary if you already have FAISS?**
**Answer:** FAISS uses a Bi-Encoder, meaning it embeds the query and the document separately and calculates the cosine distance between them. This is very fast but misses fine-grained interactions between the query words and document words. A Cross-Encoder feeds both the query and the document into the transformer simultaneously, allowing the self-attention mechanism to compare every word in the query to every word in the document. It is computationally expensive, so we only use it to re-rank the top 15 results retrieved by the much faster FAISS/BM25 layer.

---

## 2. Hallucination Control

**Q: How exactly does your system detect a hallucination?**
**Answer:** Our Verification Pipeline works post-generation. Once the LLM generates a response, we use a Claim Splitter to break the paragraph into atomic sentences. For each sentence, we calculate a "Support Score" by comparing it against the retrieved evidence using semantic entailment logic. If the support score for any specific claim falls below a strict threshold (e.g., 0.5), the system flags it as a hallucination, strips it from the final output, and issues a Refusal Message.

**Q: Why do this post-generation instead of just writing a better system prompt?**
**Answer:** LLMs are probabilistic models; they are inherently designed to guess the next most likely token. A system prompt saying "Do not hallucinate" relies entirely on the LLM's own internal logic, which is flawed. Our post-generation pipeline acts as an objective, external judge. It treats the LLM's output as an untrusted draft until it mathematically verifies that the facts exist in the source text.

---

## 3. Prompt Injection Security

**Q: How does your 3-Layer Defense stop prompt injections?**
**Answer:** Prompt injections happen when malicious instructions are embedded in the data (like a resume).
1. **Layer 1 (Content Filter):** Pre-processes the retrieved data to catch known jailbreak strings or encoded text (like Base64).
2. **Layer 2 (Safe Prompting):** We wrap the retrieved data in strict XML delimiters `<context>...</context>` so the LLM knows what is instructions vs. what is data.
3. **Layer 3 (Instruction Hierarchy):** We place the user's actual question at the very end of the prompt. LLMs suffer from "recency bias"—by putting the core instructions last, it overwrites any conflicting instructions that were injected in the middle of the context window.

**Q: Did you evaluate this against real-world attacks?**
**Answer:** Yes, we built an adversarial corpus containing 17 different attack patterns across 6 categories (SQL injection, System overrides, Roleplay jailbreaks, etc.). An undefended RAG system failed 100% of the time, while our 3-Layer defense blocked 100% of the attacks with less than a 10ms processing overhead.

---

## 4. Architecture & Scalability

**Q: You built this using SQLite and FAISS. Is this scalable for a large enterprise?**
**Answer:** The current architecture is a highly optimized proof-of-concept. However, the system is completely modular. For enterprise scale, the architecture plan dictates migrating the SQLite database and FAISS index into a unified PostgreSQL cluster using the `pgvector` extension, and offloading document chunking/embedding to background Celery workers using Redis. The core Python/FastAPI logic would remain identical.

**Q: Why run the LLM locally (Ollama) instead of using the OpenAI API?**
**Answer:** Privacy and Data Sovereignty. This system is designed for querying highly confidential enterprise documents (HR complaints, proprietary code, financial records). Sending this data to a third-party API introduces massive compliance and data-leak risks. By running models like Mistral 7B locally, we achieve "Zero-Trust" privacy.
