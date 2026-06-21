"""
End-to-End RAG Pipeline
Phase 2, Task 2.11

Implements complete Retrieval-Augmented Generation pipeline with document
ingestion, semantic search, and LLM-based answer generation.
"""

from typing import Dict, List, Tuple, Optional
import time
import logging
from pathlib import Path
import sys

# ── Core pipeline imports (always required) ──────────────────────────────────
try:
    # Package usage (e.g. called from FastAPI)
    from .ingestion.document_parser import DocumentParser
    from .ingestion.chunker import SemanticChunker
    from .ingestion.metadata_tracker import MetadataStore, ChunkMetadata
    from .retrieval.hybrid_retriever import HybridRetriever, SearchResult
    from .retrieval.reranker import CrossEncoderReRanker
    from .llm.inference import LLMInference
except ImportError:
    # Standalone / script usage
    sys.path.insert(0, str(Path(__file__).parent))
    from ingestion.document_parser import DocumentParser
    from ingestion.chunker import SemanticChunker
    from ingestion.metadata_tracker import MetadataStore, ChunkMetadata
    from retrieval.hybrid_retriever import HybridRetriever, SearchResult
    from retrieval.reranker import CrossEncoderReRanker
    from llm.inference import LLMInference

# ── Verification pipeline (optional — gracefully skipped if unavailable) ──────
try:
    from .verification.llm_claim_splitter import LLMClaimSplitter
    from .verification.support_scorer import SupportScorer
    from .verification.refusal_threshold import (
        RefusalThresholdEngine,
        ThresholdConfigurations,
    )
    from .verification.answer_assembler import AnswerAssembler
    from .verification.evidence_retriever import EvidenceRetriever
    from .verification.data_structures import Claim, EvidenceSet, Chunk as VerifChunk

    _VERIFICATION_AVAILABLE = True
except ImportError as _ve:
    _VERIFICATION_AVAILABLE = False
    logging.getLogger(__name__).warning(
        f"Verification pipeline unavailable (import error): {_ve}. "
        "Answers will not be claim-verified."
    )


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RAGPipeline:
    """
    Complete Retrieval-Augmented Generation pipeline.

    Flow: Document Upload → Parse → Chunk → Embed → Retrieve → Generate → Answer with Citations

    Acceptance Criteria (Task 2.11):
    - ✅ End-to-end query answering with retrieved context
    - ✅ Document retrieval with hybrid search (dense + sparse)
    - ✅ LLM-based answer generation with system prompts
    - ✅ Return (answer, citations, confidence) tuples
    - ✅ Performance target: <10s end-to-end (retrieval <150ms + LLM <5000ms + overhead)

    Performance Targets:
    - Ingestion: ~1-5 minutes for typical corporate policies
    - Retrieval: <150ms per query (hybrid search)
    - Generation: <5s per query with context
    - Total: <10s end-to-end per query
    """

    def __init__(
        self,
        llm_model: str = "mistral",
        dense_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        chunk_size_tokens: int = 300,
        retrieval_top_k: int = 5,
        temperature: float = 0.3,
        reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        enable_reranking: bool = True,
    ):
        """
        Initialize RAG pipeline components.

        Args:
            llm_model: LLM model identifier for Ollama
            dense_model: Dense embedding model identifier
            chunk_size_tokens: Chunk size in tokens (default 300)
            retrieval_top_k: Number of chunks to retrieve (default 5)
            temperature: LLM sampling temperature (default 0.3 for deterministic)
        """
        self.parser = DocumentParser()
        self.chunker = SemanticChunker(chunk_size_tokens=chunk_size_tokens)
        self.metadata_store = MetadataStore()
        self.retriever = HybridRetriever(dense_model=dense_model)

        self.enable_reranking = enable_reranking
        if self.enable_reranking:
            self.reranker = CrossEncoderReRanker(model_name=reranker_model)
        else:
            self.reranker = None

        self.llm = LLMInference(model_name=llm_model, temperature=temperature)
        self.retrieval_top_k = retrieval_top_k

        self.index_built = False
        self.total_chunks = 0
        self.last_latency = 0
        self.chunk_id_to_text = {}  # Map chunk_id → text for citations

        # Persistent corpus — accumulates across multiple ingest_documents() calls
        # so that uploading doc B does NOT erase doc A from the index.
        self._corpus_texts: List[str] = []
        self._corpus_chunk_ids: List[str] = []

        logger.info(
            f"RAGPipeline initialized: llm={llm_model}, "
            f"dense={dense_model}, chunk_size={chunk_size_tokens}, "
            f"top_k={retrieval_top_k}"
        )

    def ingest_documents(self, file_paths: List[str]) -> int:
        """
        Parse, chunk, and index documents.

        Args:
            file_paths: List of DOCX/PDF file paths

        Returns:
            Total number of chunks created

        Raises:
            ValueError: If no valid files provided
            RuntimeError: If indexing fails

        Implementation:
        - Parse each document with DocumentParser
        - Chunk with SemanticChunker preserving metadata
        - Build both dense and sparse indices with HybridRetriever
        - Store chunk texts for citation generation
        """
        logger.info(f"Ingesting {len(file_paths)} documents...")

        if not file_paths:
            raise ValueError("No files provided for ingestion")

        start_time = time.time()

        # Work on NEW chunks only; existing corpus is preserved in self._corpus_*
        new_texts: List[str] = []
        new_chunk_ids: List[str] = []
        chunk_count = 0

        try:
            for file_path in file_paths:
                file_path = Path(file_path)

                if not file_path.exists():
                    logger.warning(f"File not found: {file_path}")
                    continue

                logger.info(f"Processing: {file_path.name}")

                # Parse document → list of (text, DocumentMetadata) tuples
                parsed_tuples = self.parser.parse(str(file_path))

                if not parsed_tuples:
                    logger.warning(f"No content extracted from {file_path.name}")
                    continue

                # Flatten all paragraphs/pages into a single text while tracking
                # per-paragraph metadata for richer chunk metadata downstream.
                full_text = "\n\n".join(text for text, _ in parsed_tuples)

                # Chunk the combined text
                chunks = self.chunker.chunk(
                    full_text,
                    source_file=file_path.name,
                    chunk_id_prefix=file_path.stem,
                )
                logger.info(f"Created {len(chunks)} chunks from {file_path.name}")

                # Store chunks and metadata
                for chunk_idx, chunk in enumerate(chunks):
                    chunk_id = f"{file_path.stem}_{chunk_idx:04d}"

                    # Store text for citations
                    self.chunk_id_to_text[chunk_id] = chunk.text

                    # Add to THIS ingestion's lists
                    new_texts.append(chunk.text)
                    new_chunk_ids.append(chunk_id)

                    # Add metadata
                    chunk_metadata = ChunkMetadata(
                        chunk_id=chunk_id,
                        source_doc=str(file_path),
                        section=getattr(chunk, "section", "Default"),
                        page_num=getattr(chunk, "page", 1),
                        start_char=getattr(chunk, "start_pos", 0),
                        end_char=getattr(chunk, "end_pos", 0),
                        chunk_text_length=len(chunk.text),
                    )
                    self.metadata_store.add_chunk(chunk_metadata)
                    chunk_count += 1

            if chunk_count == 0:
                raise RuntimeError("No valid chunks created from documents")

            # Merge new chunks into the persistent corpus
            self._corpus_texts.extend(new_texts)
            self._corpus_chunk_ids.extend(new_chunk_ids)

            # Rebuild index over the FULL corpus (all uploaded docs combined)
            total_corpus = len(self._corpus_texts)
            logger.info(
                f"Building retriever indices: {chunk_count} new chunks + "
                f"{total_corpus - chunk_count} existing = {total_corpus} total"
            )
            self.retriever.build_index(self._corpus_texts, self._corpus_chunk_ids)

            # Mark index as ready IMMEDIATELY after retrieval index is built.
            self.index_built = True
            self.total_chunks = total_corpus  # cumulative count across all uploads

            elapsed = time.time() - start_time
            logger.info(
                f"Ingestion complete: {chunk_count} new chunks ({total_corpus} total) in {elapsed:.2f}s"
            )

            # Lazy LLM init — fire-and-forget so ingestion doesn't block
            try:
                if not self.llm.is_loaded:
                    self.llm.load_model()
                    logger.info("LLM model ready.")
            except Exception as e:
                logger.warning(
                    f"LLM not available after ingestion ({e}). "
                    "Pipeline will answer in retrieval-only mode until Ollama is reachable."
                )

            return chunk_count

        except Exception as e:
            logger.error(f"Ingestion failed: {str(e)}")
            raise RuntimeError(f"Document ingestion failed: {str(e)}")

    def query(
        self,
        question: str,
        allowed_doc_ids: Optional[List[str]] = None,
        include_context: bool = True,
    ) -> Dict:
        """
        Answer question using RAG pipeline.

        Args:
            question: User question
            include_context: Whether to include context in answer (default True)

        Returns:
            Dict with keys:
            - 'answer': Generated response
            - 'citations': List of (chunk_id, source, text) tuples
            - 'confidence': Confidence score [0, 1]
            - 'latency_ms': Total pipeline latency
            - 'retrieval_latency_ms': Retrieval time
            - 'generation_latency_ms': Generation time
            - 'sources': Unique source files used

        Pipeline Flow:
        1. Retrieve top-k relevant chunks (hybrid search)
        2. Format chunks as context
        3. Create prompt with context + question
        4. Generate answer with LLM (if available)
        5. Extract citations from retrieved chunks
        6. Return structured response

        Performance: <10s end-to-end typical
        """
        if not question or not question.strip():
            raise ValueError("Question cannot be empty")

        if not self.index_built:
            logger.info("Pipeline index not built (no documents uploaded). Proceeding to conversational fallback.")

        start_time = time.time()
        logger.info(f"Processing query: {question[:50]}...")

        try:
            # Retrieve relevant chunks (get 3x more if re-ranking is enabled)
            retrieval_start = time.time()
            if self.index_built:
                fetch_k = (
                    self.retrieval_top_k * 3
                    if self.enable_reranking and self.reranker and self.reranker.is_loaded
                    else self.retrieval_top_k
                )
                search_results = self.retriever.search(
                    question, top_k=fetch_k, allowed_doc_ids=allowed_doc_ids
                )
            else:
                search_results = []

            # Re-rank results
            if (
                self.enable_reranking
                and self.reranker
                and self.reranker.is_loaded
                and search_results
            ):
                search_results = self.reranker.rerank(
                    query=question,
                    results=search_results,
                    chunk_texts=self.chunk_id_to_text,
                    top_k=self.retrieval_top_k,
                )

            retrieval_time = (time.time() - retrieval_start) * 1000

            # Extract citations and build context
            citations = []
            context_chunks = []
            sources_set = set()

            if not search_results:
                logger.info("No relevant chunks found — falling back to conversational mode")
                context = ""
            else:
                for result in search_results:
                    chunk_id = result.chunk_id
                    chunk_text = self.chunk_id_to_text.get(chunk_id, "")

                    # Get metadata
                    chunk_metadata = self.metadata_store.get_chunk(chunk_id)
                    source_file = chunk_metadata.source_doc if chunk_metadata else "Unknown"

                    citations.append((chunk_id, source_file, chunk_text))
                    context_chunks.append((chunk_text, result.hybrid_score))
                    sources_set.add(Path(source_file).name)

            # Format context
            context = self.format_context(context_chunks)

            # Generate answer
            generation_start = time.time()

            # Lazy LLM init — if Ollama wasn't reachable during ingestion,
            # try again now. This lets the first question trigger the connection.
            if not self.llm.is_loaded:
                logger.info("LLM not yet loaded — attempting lazy init now...")
                try:
                    self.llm.load_model()
                    logger.info("Mistral model connected successfully.")
                except Exception as e:
                    logger.warning(
                        f"LLM lazy init failed ({e}) — using retrieval-only mode."
                    )

            if self.llm.is_loaded:
                try:
                    if context:
                        # Create RAG prompt — explicitly ask for multi-source synthesis, but allow conversational greetings
                        rag_prompt = f"""You are a helpful assistant answering questions based on the provided documents.

Instructions:
- Synthesize information from ALL relevant sections of the context below.
- Give a comprehensive, detailed answer covering all relevant points found.
- If information comes from multiple documents, combine it into a single coherent answer.
- Cite the source document name when referencing specific facts (e.g. "According to [filename]...").
- If the user is simply greeting you (e.g. "hi", "hello") or making general conversation, respond CONCISELY and politely without referencing the documents. Keep greetings to 1-2 sentences max.
- Otherwise, if the answer to the user's specific question is not in the context, say: "The information is not available in the uploaded documents."
- Do NOT stop after finding the first relevant sentence — check all context sections.

Context (from {len(search_results)} retrieved sections across uploaded documents):
{context}

Question: {question}

Comprehensive Answer:"""
                    else:
                        # Conversational fallback prompt (no context available)
                        rag_prompt = f"""You are a helpful, polite, and intelligent AI assistant. 
The user is talking to you directly. Respond naturally to their greeting, pleasantry, or general question. 
Keep your response CONCISE (1-2 sentences). Do not ramble or over-explain.
If they ask about documents, remind them they haven't uploaded any or that no relevant documents were found.

User: {question}

Assistant:"""

                    answer = self.llm.generate(rag_prompt, max_tokens=1024)
                    if not answer or not answer.strip():
                        raise ValueError("LLM returned empty response")
                except Exception as e:
                    logger.warning(f"LLM generation failed: {e}")
                    # Fall through to retrieval-only mode below
                    answer = None
            else:
                answer = None

            # Retrieval-only fallback — synthesize a clean answer from the top chunks
            if not answer:
                logger.info(
                    "Using retrieval-only mode — building answer from retrieved chunks"
                )
                top_chunks = [text for text, _ in context_chunks[:3]]
                if top_chunks:
                    # Present the most relevant passage(s) cleanly
                    answer = (
                        f"Based on the uploaded documents, here is the most relevant information:\n\n"
                        + "\n\n".join(
                            f"• {chunk.strip()[:500]}" for chunk in top_chunks
                        )
                    )
                else:
                    # Generic response when offline and no chunks
                    lower_q = question.lower().strip()
                    if lower_q in ["hi", "hello", "hey", "how are you", "who are you"]:
                        answer = "Hello! I am SecureHall-RAG. I can help you answer questions about your documents."
                    else:
                        answer = "No relevant information found in the knowledge base."

            generation_time = (time.time() - generation_start) * 1000

            # ── Verification pipeline ──────────────────────────────────────────
            # Run claim-level verification when LLM produced a real answer
            # (skip in retrieval-only mode where answer IS the raw context)
            verified_confidence = None
            if _VERIFICATION_AVAILABLE and self.llm.is_loaded:
                try:
                    verif_start = time.time()

                    # Build Chunk objects from search results for the verifier
                    verif_chunks = [
                        VerifChunk(
                            chunk_id=r.chunk_id,
                            content=self.chunk_id_to_text.get(r.chunk_id, ""),
                            source=Path(
                                self.metadata_store.get_chunk(r.chunk_id).source_doc
                                if self.metadata_store.get_chunk(r.chunk_id)
                                else "unknown"
                            ).name,
                            relevance_score=r.hybrid_score,
                        )
                        for r in search_results
                    ]

                    # Split answer into individual claim sentences using LLM
                    splitter = LLMClaimSplitter(llm=self.llm)
                    raw_claims = splitter.split_into_claims(answer)

                    if raw_claims:
                        # raw_claims is already List[Claim] from ClaimSplitter
                        claim_objs = raw_claims

                        # Build evidence sets from already-retrieved chunks
                        evidence_sets = {
                            claim.claim_id: EvidenceSet(
                                claim_id=claim.claim_id,
                                evidence_chunks=verif_chunks,
                                retrieval_scores=[
                                    ch.relevance_score for ch in verif_chunks
                                ],
                                retrieval_method="hybrid",
                                num_retrieved=len(verif_chunks),
                            )
                            for claim in claim_objs
                        }

                        # Score support — use_nli=False avoids loading a large
                        # zero-shot-classification model at query time which
                        # can OOM/crash the server. LLM fallback handles robust
                        # entailment checks for the top evidence chunk instead.
                        scorer = SupportScorer(use_nli=False, llm=self.llm)
                        scores = scorer.score_support_batch(
                            claim_objs, list(evidence_sets.values())
                        )

                        # Make accept/refuse decisions
                        threshold_engine = RefusalThresholdEngine(
                            ThresholdConfigurations.BALANCED
                        )
                        decisions = threshold_engine.make_decisions_batch(scores)

                        # Assemble verified answer
                        assembler = AnswerAssembler()
                        verified = assembler.assemble_answer(
                            answer, claim_objs, scores, decisions, evidence_sets
                        )

                        answer = verified.verified_answer
                        verified_confidence = verified.total_support_score

                        verif_time = (time.time() - verif_start) * 1000
                        logger.info(
                            f"Verification complete in {verif_time:.0f}ms — "
                            f"{verified.accepted_count} accepted, "
                            f"{verified.rejected_count} rejected, "
                            f"confidence={verified_confidence:.2f}"
                        )
                except Exception as e:
                    logger.warning(f"Verification pipeline failed (non-fatal): {e}")
            # ── End verification ───────────────────────────────────────────────

            # ── Confidence score ──────────────────────────────────────────────
            # Use the raw cosine similarity from FAISS (absolute range ~0.3–0.9)
            # rather than the normalized hybrid rank score (always relative 0–1,
            # bottoms out to 0 when only 1 chunk exists in the corpus).
            # Use the raw cosine similarity from FAISS or the CrossEncoder logit
            # to compute confidence.
            if (
                self.enable_reranking
                and self.reranker
                and self.reranker.is_loaded
                and search_results
            ):
                # MS-MARCO CrossEncoder outputs logits where > 0 is good, > 5 is very good.
                raw_score = search_results[0].hybrid_score
                # Calibrate: 0 -> 50%, 5 -> 100%, -5 -> 0%
                calibrated = max(0.0, min(1.0, (raw_score + 5.0) / 10.0))
            else:
                raw_cos_sim = (
                    float(getattr(search_results[0], "raw_dense_score", 0.0))
                    if search_results
                    else 0.0
                )
                calibrated = max(0.0, (raw_cos_sim - 0.25) / 0.65)

            if verified_confidence is not None and verified_confidence > 0:
                # Blend calibrated retrieval (60%) + verification (40%)
                confidence = 0.6 * calibrated + 0.4 * float(verified_confidence)
            else:
                confidence = calibrated

            # Clamp to [0, 1]
            confidence = max(0.0, min(1.0, confidence))

            total_latency = (time.time() - start_time) * 1000

            result = {
                "answer": answer.strip(),
                "citations": citations,
                "confidence": float(confidence),
                "latency_ms": total_latency,
                "retrieval_latency_ms": retrieval_time,
                "generation_latency_ms": generation_time,
                "sources": sorted(list(sources_set)),
            }

            logger.info(
                f"Query processed in {total_latency:.2f}ms "
                f"(retrieval: {retrieval_time:.2f}ms, "
                f"generation: {generation_time:.2f}ms)"
            )

            return result

        except Exception as e:
            logger.error(f"Query failed: {str(e)}")
            raise RuntimeError(f"Query processing failed: {str(e)}")

    def format_context(self, chunks: List[Tuple[str, float]]) -> str:
        """
        Format retrieved chunks into context for LLM.

        Args:
            chunks: List of (chunk_text, relevance_score) tuples

        Returns:
            Formatted context string with citations and scores

        Implementation:
        - Create numbered context blocks
        - Include relevance scores
        - Format for clarity

        Example output:
        ```
        [1] (Relevance: 0.92)
        All employees must follow the Code of Conduct...

        [2] (Relevance: 0.87)
        Leave requests must be submitted 30 days in advance...
        ```
        """
        if not chunks:
            return "No relevant context available."

        context_lines = []
        for i, (text, score) in enumerate(chunks, 1):
            # Truncate very long texts
            display_text = text[:300] + "..." if len(text) > 300 else text
            context_lines.append(f"[{i}] (Relevance: {score:.2f})\n{display_text}\n")

        return "\n".join(context_lines)

    def get_statistics(self) -> Dict:
        """Get pipeline statistics"""
        return {
            "total_chunks": self.total_chunks,
            "index_built": self.index_built,
            "llm_loaded": self.llm.is_loaded,
            "metadata_chunks": (
                len(self.metadata_store.chunk_metadata)
                if hasattr(self.metadata_store, "chunk_metadata")
                else 0
            ),
            "retriever_stats": self.retriever.get_statistics(),
            "llm_stats": self.llm.get_model_info(),
        }


if __name__ == "__main__":
    print("=" * 70)
    print("RAGPipeline Test (Retrieval-Only Mode)")
    print("=" * 70)

    # Create pipeline
    pipeline = RAGPipeline(
        llm_model="mistral",
        chunk_size_tokens=300,
        retrieval_top_k=5,
        enable_reranking=True,
    )
    print("[OK] Pipeline initialized")

    # Create sample documents (simulated)
    print("\n" + "=" * 70)
    print("Creating Sample Documents")
    print("=" * 70)

    sample_texts = [
        "Employee handbook provides comprehensive information about company policies and procedures. All employees must follow company policies.",
        "Benefits package includes health insurance dental and vision coverage for all employees.",
        "Health insurance covers preventive care visits and emergency services for employees.",
        "Vacation policy allows employees to take up to three weeks paid time off per year.",
        "Remote work program permits eligible employees to work from home.",
        "Professional development budget available for courses and certifications.",
        "Retirement plan offers 401k matching up to six percent of salary.",
        "Compliance training is mandatory for all employees annually.",
        "Diversity and inclusion initiatives promote equal opportunity in the workplace.",
        "Performance reviews conducted quarterly with feedback from managers.",
    ]

    # Build index manually (without file ingestion)
    print("\nBuilding index from sample texts...")
    chunk_ids = [f"sample_{i:04d}" for i in range(len(sample_texts))]

    for chunk_id, text in zip(chunk_ids, sample_texts):
        pipeline.chunk_id_to_text[chunk_id] = text
        metadata = ChunkMetadata(
            chunk_id=chunk_id,
            source_doc="sample.txt",
            section="Sample",
            page_num=1,
            start_char=0,
            end_char=len(text),
            chunk_text_length=len(text),
        )
        pipeline.metadata_store.add_chunk(metadata)

    pipeline.retriever.build_index(sample_texts, chunk_ids)
    pipeline.index_built = True
    pipeline.total_chunks = len(sample_texts)

    print(f"[OK] Created index with {len(sample_texts)} chunks")

    # Query examples
    print("\n" + "=" * 70)
    print("Query Examples (Retrieval-Only)")
    print("=" * 70)

    queries = [
        "What benefits does the company offer?",
        "What is the vacation policy?",
        "Tell me about remote work options",
    ]

    for query in queries:
        print(f"\nQuery: '{query}'")
        try:
            result = pipeline.query(query)
            print(f"[OK] Answer retrieved")
            print(f"  Confidence: {result['confidence']:.2f}")
            print(f"  Sources: {', '.join(result['sources'])}")
            print(f"  Latency: {result['latency_ms']:.2f}ms")
            if result["citations"]:
                print(f"  Citations: {len(result['citations'])} chunks")
        except Exception as e:
            print(f"[ERR] Error: {str(e)}")

    # Statistics
    print("\n" + "=" * 70)
    print("Pipeline Statistics")
    print("=" * 70)

    stats = pipeline.get_statistics()
    print(f"\nPipeline Statistics:")
    print(f"  Total chunks: {stats['total_chunks']}")
    print(f"  Index built: {stats['index_built']}")
    print(f"  LLM loaded: {stats['llm_loaded']}")
    print(f"  Metadata chunks: {stats['metadata_chunks']}")
