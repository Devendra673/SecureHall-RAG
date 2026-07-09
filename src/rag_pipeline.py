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
    from .ingestion.metadata_tracker import MetadataStore, ChunkMetadata, DocumentMetadata
    from .retrieval.hybrid_retriever import HybridRetriever, SearchResult
    from .retrieval.reranker import CrossEncoderReRanker
    from .llm.inference import LLMInference
    from .retrieval.web_search import WebSearchService
    from .retrieval.query_expander import QueryExpander
except ImportError:
    # Standalone / script usage
    sys.path.insert(0, str(Path(__file__).parent))
    from ingestion.document_parser import DocumentParser
    from ingestion.chunker import SemanticChunker
    from ingestion.metadata_tracker import MetadataStore, ChunkMetadata, DocumentMetadata
    from retrieval.hybrid_retriever import HybridRetriever, SearchResult
    from retrieval.reranker import CrossEncoderReRanker
    from llm.inference import LLMInference
    from retrieval.web_search import WebSearchService
    from retrieval.query_expander import QueryExpander

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
    from .verification.data_structures import Claim, EvidenceSet, Chunk as VerifChunk, SupportLevel, VerificationDecision

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
        enable_hyde: bool = True,
        enable_cache: bool = True,
        data_dir: Optional[str] = None,
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
        self.web_search_service = WebSearchService()

        self.enable_reranking = enable_reranking
        if self.enable_reranking:
            self.reranker = CrossEncoderReRanker(model_name=reranker_model, device="cpu")
        else:
            self.reranker = None

        self.llm = LLMInference(model_name=llm_model, temperature=temperature)
        self.retrieval_top_k = retrieval_top_k
        self.enable_hyde = enable_hyde
        self.enable_cache = enable_cache
        self.enable_raptor = True

        self.cache = None
        if self.enable_cache:
            try:
                from .retrieval.semantic_cache import SemanticCache
                self.cache = SemanticCache(embedding_model=dense_model)
            except Exception as cache_err:
                logger.warning(f"Failed to load semantic cache: {cache_err}")

        self.index_built = False
        self.total_chunks = 0
        self.last_latency = 0
        self.chunk_id_to_text = {}  # Map chunk_id → text for citations

        # Persistent corpus — accumulates across multiple ingest_documents() calls
        # so that uploading doc B does NOT erase doc A from the index.
        self._corpus_texts: List[str] = []
        self._corpus_chunk_ids: List[str] = []

        # Persistence directory
        self.data_dir = data_dir

        logger.info(
            f"RAGPipeline initialized: llm={llm_model}, "
            f"dense={dense_model}, chunk_size={chunk_size_tokens}, "
            f"top_k={retrieval_top_k}, data_dir={data_dir}"
        )

        # Attempt to load previously persisted indices from disk
        if self.data_dir:
            self._load_persisted_state()

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

                # Remove any existing chunks for this file to prevent duplicates
                prefix = f"{file_path.stem}_"
                filtered_corpus = [
                    (cid, txt) for cid, txt in zip(self._corpus_chunk_ids, self._corpus_texts)
                    if not cid.startswith(prefix)
                ]
                if len(filtered_corpus) < len(self._corpus_chunk_ids):
                    logger.info(f"Removing old chunks for document {file_path.name} from corpus to avoid duplicates.")
                    self._corpus_chunk_ids = [item[0] for item in filtered_corpus]
                    self._corpus_texts = [item[1] for item in filtered_corpus]
                    
                # Clean in-memory chunk map
                for cid in list(self.chunk_id_to_text.keys()):
                    if cid.startswith(prefix):
                        del self.chunk_id_to_text[cid]
                        
                # Clean in-memory metadata store
                for cid in list(self.metadata_store.chunk_metadata.keys()):
                    if cid.startswith(prefix):
                        del self.metadata_store.chunk_metadata[cid]
                        
                for doc_key in list(self.metadata_store.document_metadata.keys()):
                    if doc_key == file_path.name or doc_key == str(file_path) or Path(doc_key).stem == file_path.stem:
                        del self.metadata_store.document_metadata[doc_key]
                        
                # Clean SQLite DB tables (if persistent)
                if self.metadata_store.db_path:
                    import sqlite3
                    try:
                        conn = sqlite3.connect(str(self.metadata_store.db_path))
                        cursor = conn.cursor()
                        cursor.execute("DELETE FROM chunks WHERE chunk_id LIKE ?", (f"{prefix}%",))
                        cursor.execute("DELETE FROM documents WHERE source_doc = ? OR source_doc = ? OR source_doc LIKE ?", 
                                       (file_path.name, str(file_path), f"%{file_path.stem}%"))
                        conn.commit()
                        conn.close()
                    except Exception as db_err:
                        logger.warning(f"Failed to delete old metadata from database: {db_err}")

                # Parse document → list of (text, DocumentMetadata) tuples
                parsed_tuples = self.parser.parse(str(file_path))

                if not parsed_tuples:
                    logger.warning(f"No content extracted from {file_path.name}")
                    continue

                # Flatten all paragraphs/pages into a single text while tracking
                # per-paragraph metadata for richer chunk metadata downstream.
                full_text = "\n\n".join(text for text, _ in parsed_tuples)

                # Chunk the combined text with parent-child chunking
                chunks, child_to_parent = self.chunker.chunk_with_parents(
                    full_text,
                    source_file=file_path.name,
                    chunk_id_prefix=file_path.stem,
                )
                logger.info(f"Created {len(chunks)} chunks from {file_path.name}")

                # Store chunks and metadata
                for chunk in chunks:
                    chunk_id = chunk.chunk_id

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
                        page_num=getattr(chunk, "page_number", 1),
                        start_char=getattr(chunk, "start_pos", 0),
                        end_char=getattr(chunk, "end_pos", 0),
                        chunk_text_length=len(chunk.text),
                        parent_chunk_id=chunk.parent_chunk_id,
                    )
                    self.metadata_store.add_chunk(chunk_metadata)
                    
                    if chunk.parent_chunk_id and chunk.parent_text:
                        self.metadata_store.store_parent_text(chunk.parent_chunk_id, chunk.parent_text)

                    chunk_count += 1

                # Register document in metadata store
                doc_meta = DocumentMetadata(
                    source_doc=file_path.name,
                    file_path=str(file_path),
                    total_chunks=len(chunks),
                    total_characters=len(full_text),
                    file_size_bytes=file_path.stat().st_size if file_path.exists() else len(full_text),
                )
                self.metadata_store.register_document(doc_meta)

            if chunk_count == 0:
                raise RuntimeError("No valid chunks created from documents")

            # Build RAPTOR Hierarchical Summary Tree
            if getattr(self, "enable_raptor", True) and self.llm.is_loaded:
                try:
                    from .ingestion.raptor_tree import RaptorTreeBuilder
                    raptor_builder = RaptorTreeBuilder(self.llm, self.retriever.dense_retriever)
                    summary_texts, summary_ids, summary_metadata = raptor_builder.build_summaries(new_texts, new_chunk_ids)
                    
                    if summary_texts:
                        logger.info(f"RAPTOR: Adding {len(summary_texts)} summary chunks to corpus...")
                        for s_text, s_id, s_meta in zip(summary_texts, summary_ids, summary_metadata):
                            # Add to core mappings
                            self.chunk_id_to_text[s_id] = s_text
                            new_texts.append(s_text)
                            new_chunk_ids.append(s_id)
                            
                            # Add to metadata store so that parent/source tracing doesn't crash
                            chunk_metadata = ChunkMetadata(
                                chunk_id=s_id,
                                source_doc="Hierarchical Summary",
                                section="RAPTOR Summary Node",
                                page_num=1,
                                start_char=0,
                                end_char=len(s_text),
                                chunk_text_length=len(s_text),
                                parent_chunk_id=None,
                            )
                            self.metadata_store.add_chunk(chunk_metadata)
                except Exception as raptor_err:
                    logger.warning(f"Failed to build RAPTOR summary: {raptor_err}")

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

    def _is_summary_query(self, question: str) -> bool:
        """
        Detect if the query is asking for a document-level summary or overview.
        These queries have no matching text in any document chunk, so retrieval
        similarity is inherently low — they must NOT trigger the web search fallback.
        """
        q = question.lower().strip().rstrip("?.!")
        summary_phrases = [
            "summarize", "summary", "summarise", "overview", "give me an overview",
            "what are the documents about", "what is in the documents",
            "brief overview", "key points", "main points", "highlights",
            "what documents do you have", "list the documents", "what files",
            "give me a summary", "can you summarize", "please summarize",
            "explain the documents", "what topics", "what does the document cover",
            "what is covered", "tell me about the documents", "describe the documents",
        ]
        return any(phrase in q for phrase in summary_phrases)

    def _is_conversational_query(self, question: str) -> bool:
        """Check if the question is a greeting or general pleasantry that doesn't need RAG context."""
        q = question.lower().strip().rstrip("?.!")
        greetings = {
            "hi", "hello", "hey", "greetings", "good morning", "good afternoon", "good evening",
            "how's it going", "how are you", "yo", "sup", "whats up", "what's up", "who are you",
            "what is your name", "what do you do", "what can you do", "help", "who created you",
            "thank you", "thanks", "bye", "goodbye"
        }
        if q in greetings:
            return True

        # Check for time/date queries (e.g. "what is the time", "current date", "what date is today")
        time_keywords = {"time", "date", "today", "now", "clock"}
        if any(tk in q for tk in time_keywords) and len(q.split()) <= 6:
            rag_keywords = {"policy", "document", "file", "leave", "pdf", "docx", "upload", "admission", "requirements"}
            if not any(rk in q for rk in rag_keywords): # avoid matches
                return True

        # If it's very short and matches greeting words without RAG keywords
        words = q.split()
        if len(words) <= 3 and any(w in greetings for w in words):
            rag_keywords = {"policy", "document", "file", "leave", "pdf", "docx", "upload", "admission", "requirements"}
            if not any(w in rag_keywords for w in words):
                return True
        return False

    def use_finetuned_embeddings(self, model_path: str) -> bool:
        """
        Load fine-tuned embeddings model and re-index corpus (Domain Adaptation).
        """
        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading fine-tuned embeddings from: {model_path}")
            
            # Load new model to dense retriever
            self.retriever.dense_retriever.model = SentenceTransformer(model_path)
            
            # If we have corpus texts, rebuild index with the new model
            if self._corpus_texts:
                logger.info(f"Re-indexing {len(self._corpus_texts)} chunks using fine-tuned model...")
                self.retriever.build_index(self._corpus_texts, self._corpus_chunk_ids)
                
            logger.info("Successfully switched to fine-tuned embedding model!")
            return True
        except Exception as e:
            logger.error(f"Failed to load fine-tuned embedding model: {e}")
            return False

    def _attempt_self_correction(
        self,
        original_answer: str,
        context: str,
        question: str,
        verification_report: List[dict],
        verif_chunks: list,
        is_web_search: bool,
        max_retries: int = 1,
        prev_confidence: float = 0.0,
    ) -> Tuple[str, float, bool]:
        """
        Attempt to rewrite answer using LLM based on critique of unsupported claims.
        """
        if not verification_report:
            return original_answer, 1.0, True

        unsupported_list = "\n".join(
            f"{idx + 1}. Claim: \"{item['claim']}\" (Level: {item['support_level']}) - Reason: {item['reason']}"
            for idx, item in enumerate(verification_report)
        )

        critique_prompt = f"""Your previous answer draft:
---
{original_answer}
---

The following claims in your answer were found to be UNSUPPORTED by the source documents:
{unsupported_list}

Using ONLY the following verified context, rewrite your answer to remove or correct the unsupported claims.
If you cannot write a factually supported answer, respond with: "I apologize, but I cannot find sufficient verified evidence to answer this question."

Context:
{context}

Question: {question}"""

        logger.info(f"Self-correction prompt generated with {len(verification_report)} unsupported claims. Attempting generate...")

        try:
            corrected_answer = self.llm.generate(prompt=critique_prompt, max_tokens=1024)
            if not corrected_answer or not corrected_answer.strip():
                return original_answer, 0.0, False

            if "apologize" in corrected_answer.lower() or "cannot find sufficient" in corrected_answer.lower():
                return corrected_answer, 0.0, False

            # Verify corrected answer
            splitter = LLMClaimSplitter(llm=self.llm)
            claims = splitter.split_into_claims(corrected_answer)
            if not claims:
                return corrected_answer, 1.0, True

            evidence_sets = {
                claim.claim_id: EvidenceSet(
                    claim_id=claim.claim_id,
                    evidence_chunks=verif_chunks,
                    retrieval_scores=[ch.relevance_score for ch in verif_chunks],
                    retrieval_method="web_search" if is_web_search else "hybrid",
                    num_retrieved=len(verif_chunks),
                )
                for claim in claims
            }

            scorer = SupportScorer(use_nli=False, llm=self.llm)
            scores = scorer.score_support_batch(claims, list(evidence_sets.values()))

            threshold_engine = RefusalThresholdEngine(ThresholdConfigurations.BALANCED)
            decisions = threshold_engine.make_decisions_batch(scores)

            assembler = AnswerAssembler()
            verified = assembler.assemble_answer(
                corrected_answer, claims, scores, decisions, evidence_sets
            )

            new_confidence = verified.total_support_score

            if new_confidence >= 0.80:
                return verified.verified_answer, new_confidence, True

            # If improvement is negligible, stop early
            if new_confidence - prev_confidence < 0.05:
                logger.info(f"Self-correction improvement ({new_confidence - prev_confidence:.2f}) < 5% - stopping early.")
                return verified.verified_answer, new_confidence, False

            if max_retries > 0:
                # Recurse
                new_verification_report = []
                for c in verified.claims_breakdown:
                    if c.support_level in [SupportLevel.UNSUPPORTED, SupportLevel.CONFLICTING] or c.decision == VerificationDecision.REFUSE:
                        new_verification_report.append({
                            "claim": c.claim_text,
                            "support_level": c.support_level.value,
                            "reason": c.reasoning or "No clear evidence found in sources."
                        })
                return self._attempt_self_correction(
                    original_answer=corrected_answer,
                    context=context,
                    question=question,
                    verification_report=new_verification_report,
                    verif_chunks=verif_chunks,
                    is_web_search=is_web_search,
                    max_retries=max_retries - 1,
                    prev_confidence=new_confidence,
                )
            else:
                return verified.verified_answer, new_confidence, False

        except Exception as e:
            logger.error(f"Error during self-correction attempt: {e}")
            return original_answer, 0.0, False

    def _rrf_merge(self, result_lists: List[List], top_k: int = 5, k: int = 60) -> List:
        """
        Reciprocal Rank Fusion across multiple ranked lists.
        result_lists: list of lists, each list is [SearchResult, ...]
        """
        from collections import defaultdict
        scores = defaultdict(float)
        chunk_map = {}

        for result_list in result_lists:
            for rank, res in enumerate(result_list):
                chunk_id = res.chunk_id
                scores[chunk_id] += 1.0 / (k + rank + 1)
                chunk_map[chunk_id] = res

        sorted_ids = sorted(scores, key=lambda x: scores[x], reverse=True)
        
        merged = []
        for cid in sorted_ids[:top_k]:
            res = chunk_map[cid]
            res.hybrid_score = scores[cid]
            merged.append(res)
        return merged

    def _trim_context_chunks(self, chunks: List[Tuple], max_tokens: int = 1500) -> List[Tuple]:
        trimmed = []
        total_tokens = 0
        for chunk in chunks:
            text = chunk[0]
            tokens = len(text) // 4
            if total_tokens + tokens > max_tokens:
                if not trimmed:
                    trimmed.append(chunk)
                break
            trimmed.append(chunk)
            total_tokens += tokens
        return trimmed

    def query(
        self,
        question: str,
        allowed_doc_ids: Optional[List[str]] = None,
        include_context: bool = True,
        history: Optional[List[dict]] = None,
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

        is_conversational = self._is_conversational_query(question)

        # Semantic Caching check
        if self.enable_cache and self.cache and not is_conversational:
            cached = self.cache.get(question)
            if cached:
                logger.info("SemanticCache: returning cached result")
                # update latency
                cached["latency_ms"] = (time.time() - start_time) * 1000
                cached["cache_hit"] = True
                return cached

        # Lazy LLM init for query rewriting if needed
        if history and not is_conversational and not self.llm.is_loaded:
            try:
                self.llm.load_model()
            except Exception as e:
                logger.warning(f"LLM lazy init during query rewriting failed ({e})")

        search_query = question
        if history and self.llm.is_loaded and not is_conversational:
            try:
                search_query = self.llm.rewrite_query(question, history)
            except Exception as e:
                logger.error(f"Error during query rewriting: {e}")
                search_query = question

        # HyDE Query Expansion
        if self.enable_hyde and self.llm.is_loaded and not is_conversational:
            try:
                hyde_doc = self.llm.generate_hypothetical_document(search_query)
                if hyde_doc and hyde_doc != search_query:
                    search_query = hyde_doc
                    logger.info("HyDE: using hypothetical document for retrieval")
            except Exception as e:
                logger.warning(f"HyDE generation failed: {e}")

        try:
            # Retrieve relevant chunks (get 3x more if re-ranking is enabled)
            retrieval_start = time.time()
            
            # Detect multi-hop query
            is_multihop = False
            sub_questions = [search_query]
            multihop_keywords = {"compare", "difference", "both", "and also", "as well as", "relation", "compare and contrast"}
            has_keywords = any(k in search_query.lower() for k in multihop_keywords) or (" and " in search_query.lower() and len(search_query.split()) > 6)
            
            if self.llm.is_loaded and not is_conversational and has_keywords:
                try:
                    decomposed = self.llm.decompose_query(search_query)
                    if len(decomposed) > 1:
                        is_multihop = True
                        sub_questions = decomposed
                        logger.info(f"Multi-hop routing activated. Sub-questions: {sub_questions}")
                except Exception as e:
                    logger.warning(f"Decomposition failed: {e}")

            if self.index_built and not is_conversational:
                if is_multihop:
                    combined_results = []
                    seen_chunk_ids = set()
                    fetch_k = (
                        self.retrieval_top_k * 3
                        if self.enable_reranking and self.reranker and self.reranker.is_loaded
                        else self.retrieval_top_k
                    )
                    for sub_q in sub_questions:
                        sub_results = self.retriever.search(
                            sub_q, top_k=fetch_k, allowed_doc_ids=allowed_doc_ids
                        )
                        # Re-rank sub-results
                        if (
                            self.enable_reranking
                            and self.reranker
                            and self.reranker.is_loaded
                            and sub_results
                        ):
                            sub_results = self.reranker.rerank(
                                query=sub_q,
                                results=sub_results,
                                chunk_texts=self.chunk_id_to_text,
                                top_k=self.retrieval_top_k,
                            )
                        for res in sub_results:
                            if res.chunk_id not in seen_chunk_ids:
                                seen_chunk_ids.add(res.chunk_id)
                                combined_results.append(res)
                    
                    # Sort combined results by score descending
                    combined_results.sort(key=lambda r: getattr(r, "hybrid_score", 0.0) or getattr(r, "raw_dense_score", 0.0), reverse=True)
                    search_results = combined_results[:self.retrieval_top_k]
                else:
                    fetch_k = (
                        self.retrieval_top_k * 3
                        if self.enable_reranking and self.reranker and self.reranker.is_loaded
                        else self.retrieval_top_k
                    )
                    # Query Expansion (Phase 3)
                    expander = QueryExpander(self.llm)
                    query_variants = expander.expand(search_query, n=2)
                    
                    if len(query_variants) > 1:
                        all_variant_results = []
                        for variant in query_variants:
                            variant_results = self.retriever.search(
                                variant, top_k=fetch_k, allowed_doc_ids=allowed_doc_ids
                            )
                            all_variant_results.append(variant_results)
                        search_results = self._rrf_merge(all_variant_results, top_k=fetch_k)
                    else:
                        search_results = self.retriever.search(
                            search_query, top_k=fetch_k, allowed_doc_ids=allowed_doc_ids
                        )
            else:
                search_results = []

            # Re-rank results (for non-multihop)
            if (
                not is_multihop
                and self.enable_reranking
                and self.reranker
                and self.reranker.is_loaded
                and search_results
            ):
                search_results = self.reranker.rerank(
                    query=search_query,
                    results=search_results,
                    chunk_texts=self.chunk_id_to_text,
                    top_k=self.retrieval_top_k,
                )

            retrieval_time = (time.time() - retrieval_start) * 1000

            # Calculate calibrated retrieval score
            if is_conversational:
                calibrated = 1.0
            else:
                if (
                    self.enable_reranking
                    and self.reranker
                    and self.reranker.is_loaded
                    and search_results
                ):
                    raw_score = search_results[0].hybrid_score
                    calibrated = max(0.0, min(1.0, (raw_score + 5.0) / 10.0))
                else:
                    raw_cos_sim = (
                        float(getattr(search_results[0], "raw_dense_score", 0.0))
                        if search_results
                        else 0.0
                    )
                    calibrated = max(0.0, (raw_cos_sim - 0.25) / 0.65)

            # Web search fallback check
            is_web_search = False
            citations = []
            context_chunks = []
            sources_set = set()

            is_summary = self._is_summary_query(question)

            if not is_conversational and is_summary and self._corpus_texts:
                # Summary queries: use all RAPTOR summary nodes if available,
                # otherwise fall back to the first N chunks from the full corpus.
                logger.info("Summary query detected — bypassing web fallback, using corpus overview.")
                raptor_ids = [cid for cid in self._corpus_chunk_ids if cid.startswith("raptor_summary_")]
                if raptor_ids:
                    # Use RAPTOR summaries as the context
                    for cid in raptor_ids[:self.retrieval_top_k]:
                        text = self.chunk_id_to_text.get(cid, "")
                        if text:
                            citations.append((cid, "RAPTOR Cluster Summary", text))
                            context_chunks.append((text, 1.0, "RAPTOR Cluster Summary"))
                            sources_set.add("RAPTOR Cluster Summary")
                    calibrated = 0.8  # high confidence — we're using our own summaries
                elif self._corpus_texts:
                    # No RAPTOR nodes built yet — use first N raw chunks as fallback overview
                    for idx, (cid, text) in enumerate(zip(self._corpus_chunk_ids, self._corpus_texts)):
                        if idx >= self.retrieval_top_k:
                            break
                        citations.append((cid, "Document Overview", text))
                        context_chunks.append((text, 0.7, "Document Overview"))
                        sources_set.add("Document Overview")
                    calibrated = 0.7

            elif not is_conversational and not is_summary and (not search_results or calibrated < 0.35):
                logger.info(f"Low confidence ({calibrated:.2f}) or empty results. Triggering web search fallback...")
                web_results = self.web_search_service.search(search_query, num_results=3)
                if web_results:
                    is_web_search = True
                    calibrated = 0.5 # Web search default confidence
                    for idx, res in enumerate(web_results, 1):
                        chunk_id = f"web_{idx:04d}"
                        link = res.get("link", "")
                        title = res.get("title", "Web Page")
                        snippet = res.get("snippet", "")
                        chunk_text = f"Title: {title}\nSnippet: {snippet}"
                        citations.append((chunk_id, link, chunk_text))
                        context_chunks.append((chunk_text, 0.5, link))
                        sources_set.add(link)

            # If not web search and we have local search results, populate citations from local
            if not is_web_search and search_results:
                seen_parents = set()
                parent_context_chunks = []
                for result in search_results:
                    chunk_id = result.chunk_id
                    chunk_text = self.chunk_id_to_text.get(chunk_id, "")

                    # Get metadata
                    chunk_metadata = self.metadata_store.get_chunk(chunk_id)
                    source_file = "Unknown"
                    parent_id = ""
                    if chunk_metadata:
                        if chunk_metadata.source_doc:
                            source_file = chunk_metadata.source_doc
                        parent_id = getattr(chunk_metadata, "parent_chunk_id", "")
                    else:
                        parts = chunk_id.rsplit("_", 1)
                        if parts:
                            file_stem = parts[0]
                            upload_dir = Path("uploaded_documents")
                            if upload_dir.exists():
                                for f in upload_dir.iterdir():
                                    if f.is_file() and f.stem == file_stem:
                                        source_file = str(f)
                                        break

                    citations.append((chunk_id, source_file, chunk_text))
                    sources_set.add(Path(source_file).name)

                    if parent_id:
                        if parent_id not in seen_parents:
                            seen_parents.add(parent_id)
                            parent_text = self.metadata_store.get_parent_text(parent_id)
                            if parent_text:
                                parent_context_chunks.append((parent_text, result.hybrid_score, source_file))
                            else:
                                parent_context_chunks.append((chunk_text, result.hybrid_score, source_file))
                    else:
                        parent_context_chunks.append((chunk_text, result.hybrid_score, source_file))
                context_chunks = parent_context_chunks

            # Trim context to 1500 tokens (Phase 6.2)
            context_chunks = self._trim_context_chunks(context_chunks, max_tokens=1500)

            # Format context
            context = self.format_context(context_chunks)

            # Early ABSTAIN logic (Phase 2.3)
            if not is_conversational and not is_web_search and calibrated < 0.25 and not is_summary:
                logger.info(f"Retrieval confidence {calibrated:.2f} is below 0.25. Skipping LLM generation and abstaining early.")
                from .verification.uncertainty import UncertaintyQuantifier
                answer, uncertainty_tier = UncertaintyQuantifier.process_response("", calibrated, query=question)
                return {
                    "answer": answer,
                    "citations": [],
                    "confidence": float(calibrated),
                    "uncertainty_tier": uncertainty_tier,
                    "latency_ms": (time.time() - start_time) * 1000,
                    "retrieval_latency_ms": retrieval_time,
                    "generation_latency_ms": 0.0,
                    "sources": [],
                }

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
                    # Format history if available (limit to last 5 turns to save context window)
                    history_text = ""
                    if history:
                        recent_history = history[-5:]
                        history_text = "Previous Conversation:\n" + "\n".join(
                            f"{msg.get('role', 'unknown').capitalize()}: {msg.get('content', '')}"
                            for msg in recent_history
                        ) + "\n\n"

                    if context:
                        if is_web_search:
                            rag_prompt = f"""You are a helpful assistant answering questions based on the web search results below.

Instructions:
- Synthesize information from ALL relevant search results.
- Give a comprehensive, detailed answer.
- Cite the corresponding web search result using bracket numbers like [1] or [2] at the end of the sentence or clause containing the fact. The bracket number must correspond to the section index (e.g. use [1] for the first section, [2] for the second).
- If the user is simply greeting you (e.g. "hi", "hello") or making general conversation, respond CONCISELY and politely without referencing search results. Keep greetings to 1-2 sentences max.
- Otherwise, if the answer to the user's specific question is not in the context, say: "The information is not available in the search results."

{history_text}Web Search Context:
{context}

Question: {question}

Comprehensive Answer:"""
                        else:
                            # Create RAG prompt — explicitly ask for multi-source synthesis, but allow conversational greetings
                            rag_prompt = f"""You are a helpful assistant answering questions based on the provided documents.

Instructions:
- Synthesize information from ALL relevant sections of the context below.
- Give a comprehensive, detailed answer covering all relevant points found.
- If information comes from multiple documents, combine it into a single coherent answer.
- Cite the corresponding context section using bracket numbers like [1] or [2] at the end of the sentence or clause containing the fact. The bracket number must correspond to the section index (e.g. use [1] for the first section, [2] for the second). Do not create citations for section numbers that do not exist.
- If the user is simply greeting you (e.g. "hi", "hello") or making general conversation, respond CONCISELY and politely without referencing the documents. Keep greetings to 1-2 sentences max.
- Otherwise, if the answer to the user's specific question is not in the context, say: "The information is not available in the uploaded documents."
- Do NOT stop after finding the first relevant sentence — check all context sections.

{history_text}Context (from {len(search_results)} retrieved sections across uploaded documents):
{context}

Question: {question}

Comprehensive Answer:"""
                    else:
                        # Conversational fallback prompt (no context available)
                        from datetime import datetime
                        current_dt = datetime.now().strftime("%Y-%m-%d %I:%M %p")
                        rag_prompt = f"""You are a helpful, polite, and intelligent AI assistant. 
The user is talking to you directly. Respond naturally to their greeting, pleasantry, or general question. 
Keep your response CONCISE (1-2 sentences). Do not ramble or over-explain.
The current system local date and time is: {current_dt}. If the user asks about the time or date, answer them directly and correctly based on this system date/time.
If they ask about documents, remind them they haven't uploaded any or that no relevant documents were found.

{history_text}User: {question}

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
                seen_chunks = set()
                top_chunks = []
                for chunk in context_chunks:
                    text = chunk[0]
                    trimmed = text.strip()
                    if trimmed not in seen_chunks:
                        seen_chunks.add(trimmed)
                        top_chunks.append(trimmed)
                top_chunks = top_chunks[:3]

                if top_chunks:
                    # Present the most relevant passage(s) cleanly
                    answer = (
                        f"Based on the {'web search' if is_web_search else 'uploaded documents'}, here is the most relevant information:\n\n"
                        + "\n\n".join(
                            f"• {chunk[:500]}" for chunk in top_chunks
                        )
                    )
                else:
                    lower_q = question.lower().strip()
                    time_keywords = {"time", "date", "today", "now", "clock"}
                    if any(tk in lower_q for tk in time_keywords) and len(lower_q.split()) <= 6:
                        from datetime import datetime
                        answer = f"The current system date and time is {datetime.now().strftime('%A, %B %d, %Y, %I:%M %p')}."
                    elif any(g in lower_q for g in ["hi", "hello", "hey", "how are you", "who are you"]):
                        answer = "Hello! I am SecureHall-RAG. I can help you answer questions about your documents."
                    else:
                        answer = "No relevant information found in the knowledge base."

            generation_time = (time.time() - generation_start) * 1000

            # ── Verification pipeline ──────────────────────────────────────────
            # Run claim-level verification when LLM produced a real answer
            # (skip in retrieval-only mode where answer IS the raw context)
            verified_confidence = None
            if _VERIFICATION_AVAILABLE and self.llm.is_loaded and not is_conversational:
                try:
                    verif_start = time.time()

                    # Build Chunk objects from search results/web search for the verifier
                    if is_web_search:
                        verif_chunks = [
                            VerifChunk(
                                chunk_id=cit[0],
                                content=cit[2],
                                source=cit[1],
                                relevance_score=0.5,
                            )
                            for cit in citations
                        ]
                    else:
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
                                retrieval_method="web_search" if is_web_search else "hybrid",
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

                        # --- ACTIVE CRITIQUE & SELF-CORRECTION LOOP ---
                        if verified_confidence < 0.80 and not is_web_search:
                            logger.info(f"Answer confidence {verified_confidence:.2f} below threshold (0.80). Attempting self-correction...")
                            unsupported_claims = []
                            for c in verified.claims_breakdown:
                                if c.support_level in [SupportLevel.UNSUPPORTED, SupportLevel.CONFLICTING] or c.decision == VerificationDecision.REFUSE:
                                    unsupported_claims.append({
                                        "claim": c.claim_text,
                                        "support_level": c.support_level.value,
                                        "reason": c.reasoning or "No clear evidence found in sources."
                                    })
                            if unsupported_claims:
                                corrected_ans, new_conf, success = self._attempt_self_correction(
                                    original_answer=answer,
                                    context=context,
                                    question=question,
                                    verification_report=unsupported_claims,
                                    verif_chunks=verif_chunks,
                                    is_web_search=is_web_search,
                                    max_retries=1
                                )
                                if success:
                                    answer = corrected_ans
                                    verified_confidence = new_conf
                                    logger.info(f"Self-correction succeeded. New confidence: {new_conf:.2f}")
                                else:
                                    logger.info("Self-correction failed or abstained. Keeping original verified response.")
                except Exception as e:
                    logger.warning(f"Verification pipeline failed (non-fatal): {e}")
            # ── End verification ───────────────────────────────────────────────

            # ── Confidence score ──────────────────────────────────────────────
            if is_conversational:
                confidence = 1.0
            else:
                if verified_confidence is not None and verified_confidence > 0:
                    # Blend calibrated retrieval (60%) + verification (40%)
                    confidence = 0.6 * calibrated + 0.4 * float(verified_confidence)
                else:
                    confidence = calibrated

                # Clamp to [0, 1]
                confidence = max(0.0, min(1.0, confidence))

            # Apply Uncertainty Quantification
            from .verification.uncertainty import UncertaintyQuantifier
            answer, uncertainty_tier = UncertaintyQuantifier.process_response(answer or "", confidence, query=question)

            total_latency = (time.time() - start_time) * 1000

            result = {
                "answer": answer.strip(),
                "citations": citations,
                "confidence": float(confidence),
                "uncertainty_tier": uncertainty_tier,
                "latency_ms": total_latency,
                "retrieval_latency_ms": retrieval_time,
                "generation_latency_ms": generation_time,
                "sources": sorted(list(sources_set)),
            }

            # Store in semantic cache
            if self.enable_cache and self.cache and not is_conversational and answer:
                self.cache.set(question, result)

            return result

        except Exception as e:
            logger.error(f"Query failed: {str(e)}")
            raise RuntimeError(f"Pipeline query failed: {str(e)}")
    def query_stream(
        self,
        question: str,
        allowed_doc_ids: Optional[List[str]] = None,
        include_context: bool = True,
        history: Optional[List[dict]] = None,
    ):
        """
        Stream answer using RAG pipeline.
        Yields dictionaries with different event types:
        - {"type": "metadata", "citations": [...], "sources": [...], "confidence": ...}
        - {"type": "chunk", "content": "..."}
        - {"type": "done", "latency_ms": ...}
        """
        import json
        
        if not question or not question.strip():
            raise ValueError("Question cannot be empty")

        if not self.index_built:
            logger.info("Pipeline index not built (no documents uploaded). Proceeding to conversational fallback.")

        start_time = time.time()
        logger.info(f"Processing query stream: {question[:50]}...")

        is_conversational = self._is_conversational_query(question)

        # Semantic Caching check
        if self.enable_cache and self.cache and not is_conversational:
            cached = self.cache.get(question)
            if cached:
                logger.info("SemanticCache: returning cached result via stream")
                yield {
                    "type": "metadata",
                    "citations": cached["citations"],
                    "sources": cached["sources"],
                    "confidence": cached["confidence"],
                    "cache_hit": True
                }
                yield {"type": "chunk", "content": cached["answer"]}
                yield {
                    "type": "done",
                    "latency_ms": (time.time() - start_time) * 1000,
                    "generation_latency_ms": 0.0
                }
                return

        # Lazy LLM init for query rewriting if needed
        if history and not is_conversational and not self.llm.is_loaded:
            try:
                self.llm.load_model()
            except Exception as e:
                logger.warning(f"LLM lazy init during query rewriting failed ({e})")

        search_query = question
        if history and self.llm.is_loaded and not is_conversational:
            try:
                search_query = self.llm.rewrite_query(question, history)
            except Exception as e:
                logger.error(f"Error during query rewriting: {e}")
                search_query = question

        # HyDE Query Expansion
        if self.enable_hyde and self.llm.is_loaded and not is_conversational:
            try:
                hyde_doc = self.llm.generate_hypothetical_document(search_query)
                if hyde_doc and hyde_doc != search_query:
                    search_query = hyde_doc
                    logger.info("HyDE: using hypothetical document for retrieval in stream")
            except Exception as e:
                logger.warning(f"HyDE generation failed in stream: {e}")

        try:
            # 1. Retrieve & Rerank (Synchronous)
            retrieval_start = time.time()
            
            # Detect multi-hop query
            is_multihop = False
            sub_questions = [search_query]
            multihop_keywords = {"compare", "difference", "both", "and also", "as well as", "relation", "compare and contrast"}
            has_keywords = any(k in search_query.lower() for k in multihop_keywords) or (" and " in search_query.lower() and len(search_query.split()) > 6)
            
            if self.llm.is_loaded and not is_conversational and has_keywords:
                try:
                    decomposed = self.llm.decompose_query(search_query)
                    if len(decomposed) > 1:
                        is_multihop = True
                        sub_questions = decomposed
                        logger.info(f"Multi-hop routing activated in stream. Sub-questions: {sub_questions}")
                except Exception as e:
                    logger.warning(f"Decomposition failed in stream: {e}")

            if self.index_built and not is_conversational:
                if is_multihop:
                    combined_results = []
                    seen_chunk_ids = set()
                    fetch_k = (
                        self.retrieval_top_k * 3
                        if self.enable_reranking and self.reranker and self.reranker.is_loaded
                        else self.retrieval_top_k
                    )
                    for sub_q in sub_questions:
                        sub_results = self.retriever.search(
                            sub_q, top_k=fetch_k, allowed_doc_ids=allowed_doc_ids
                        )
                        # Re-rank sub-results
                        if (
                            self.enable_reranking
                            and self.reranker
                            and self.reranker.is_loaded
                            and sub_results
                        ):
                            sub_results = self.reranker.rerank(
                                query=sub_q,
                                results=sub_results,
                                chunk_texts=self.chunk_id_to_text,
                                top_k=self.retrieval_top_k,
                            )
                        for res in sub_results:
                            if res.chunk_id not in seen_chunk_ids:
                                seen_chunk_ids.add(res.chunk_id)
                                combined_results.append(res)
                    
                    # Sort combined results by score descending
                    combined_results.sort(key=lambda r: getattr(r, "hybrid_score", 0.0) or getattr(r, "raw_dense_score", 0.0), reverse=True)
                    search_results = combined_results[:self.retrieval_top_k]
                else:
                    fetch_k = (
                        self.retrieval_top_k * 3
                        if self.enable_reranking and self.reranker and self.reranker.is_loaded
                        else self.retrieval_top_k
                    )
                    # Query Expansion (Phase 3)
                    expander = QueryExpander(self.llm)
                    query_variants = expander.expand(search_query, n=2)
                    
                    if len(query_variants) > 1:
                        all_variant_results = []
                        for variant in query_variants:
                            variant_results = self.retriever.search(
                                variant, top_k=fetch_k, allowed_doc_ids=allowed_doc_ids
                            )
                            all_variant_results.append(variant_results)
                        search_results = self._rrf_merge(all_variant_results, top_k=fetch_k)
                    else:
                        search_results = self.retriever.search(
                            search_query, top_k=fetch_k, allowed_doc_ids=allowed_doc_ids
                        )
            else:
                search_results = []

            if (
                not is_multihop
                and self.enable_reranking
                and self.reranker
                and self.reranker.is_loaded
                and search_results
            ):
                search_results = self.reranker.rerank(
                    query=search_query,
                    results=search_results,
                    chunk_texts=self.chunk_id_to_text,
                    top_k=self.retrieval_top_k,
                )

            retrieval_time = (time.time() - retrieval_start) * 1000

            # Calculate calibrated confidence score
            if is_conversational:
                confidence_score = 1.0
            else:
                if (
                    self.enable_reranking
                    and self.reranker
                    and self.reranker.is_loaded
                    and search_results
                ):
                    raw_score = search_results[0].hybrid_score
                    confidence_score = max(0.0, min(1.0, (raw_score + 5.0) / 10.0))
                else:
                    raw_cos_sim = (
                        float(getattr(search_results[0], "raw_dense_score", 0.0))
                        if search_results
                        else 0.0
                    )
                    confidence_score = max(0.0, min(1.0, (raw_cos_sim - 0.25) / 0.65))

            # Web search fallback check
            is_web_search = False
            citations = []
            context_chunks = []
            sources_set = set()

            if not is_conversational and (not search_results or confidence_score < 0.35):
                logger.info(f"Low confidence ({confidence_score:.2f}) or empty results. Triggering web search fallback...")
                web_results = self.web_search_service.search(search_query, num_results=3)
                if web_results:
                    is_web_search = True
                    confidence_score = 0.5 # Web search default confidence
                    for idx, res in enumerate(web_results, 1):
                        chunk_id = f"web_{idx:04d}"
                        link = res.get("link", "")
                        title = res.get("title", "Web Page")
                        snippet = res.get("snippet", "")
                        chunk_text = f"Title: {title}\nSnippet: {snippet}"
                        citations.append((chunk_id, link, chunk_text))
                        context_chunks.append((chunk_text, 0.5, link))
                        sources_set.add(link)

            # If not web search and we have local search results, populate citations from local
            if not is_web_search and search_results:
                seen_parents = set()
                parent_context_chunks = []
                for result in search_results:
                    chunk_id = result.chunk_id
                    chunk_text = self.chunk_id_to_text.get(chunk_id, "")

                    # Get metadata
                    chunk_metadata = self.metadata_store.get_chunk(chunk_id)
                    source_file = "Unknown"
                    parent_id = ""
                    if chunk_metadata:
                        if chunk_metadata.source_doc:
                            source_file = chunk_metadata.source_doc
                        parent_id = getattr(chunk_metadata, "parent_chunk_id", "")
                    else:
                        parts = chunk_id.rsplit("_", 1)
                        if parts:
                            file_stem = parts[0]
                            upload_dir = Path("uploaded_documents")
                            if upload_dir.exists():
                                for f in upload_dir.iterdir():
                                    if f.is_file() and f.stem == file_stem:
                                        source_file = str(f)
                                        break

                    citations.append((chunk_id, source_file, chunk_text))
                    sources_set.add(Path(source_file).name)

                    if parent_id:
                        if parent_id not in seen_parents:
                            seen_parents.add(parent_id)
                            parent_text = self.metadata_store.get_parent_text(parent_id)
                            if parent_text:
                                parent_context_chunks.append((parent_text, result.hybrid_score, source_file))
                            else:
                                parent_context_chunks.append((chunk_text, result.hybrid_score, source_file))
                    else:
                        parent_context_chunks.append((chunk_text, result.hybrid_score, source_file))
                context_chunks = parent_context_chunks

            # Trim context to 1500 tokens (Phase 6.2)
            context_chunks = self._trim_context_chunks(context_chunks, max_tokens=1500)

            context = self.format_context(context_chunks)

            # Apply Uncertainty Quantification (Phase 5)
            from .verification.uncertainty import UncertaintyQuantifier
            uncertainty_tier = UncertaintyQuantifier.get_tier(confidence_score, query=question)

            # Early ABSTAIN check when confidence is below 0.25 (Phase 2.3)
            if not is_conversational and not is_web_search and confidence_score < 0.25:
                uncertainty_tier = UncertaintyQuantifier.ABSTAIN

            # Yield metadata event immediately before generation starts
            yield {
                "type": "metadata",
                "citations": citations,
                "sources": list(sources_set),
                "confidence": confidence_score,
                "uncertainty_tier": uncertainty_tier,
                "retrieval_latency_ms": retrieval_time
            }

            if uncertainty_tier == UncertaintyQuantifier.ABSTAIN:
                abstain_msg = "I apologize, but I cannot find sufficient reliable evidence in the provided documents to answer your question with confidence."
                yield {"type": "chunk", "content": abstain_msg}
                yield {
                    "type": "done",
                    "latency_ms": (time.time() - start_time) * 1000,
                    "generation_latency_ms": 0.0
                }
                return

            # 2. Format Prompt & Stream Generation
            generation_start = time.time()

            if not self.llm.is_loaded:
                try:
                    self.llm.load_model()
                except Exception:
                    pass

            # Format history
            history_text = ""
            if history:
                recent_history = history[-5:]
                history_text = "Previous Conversation:\n" + "\n".join(
                    f"{msg.get('role', 'unknown').capitalize()}: {msg.get('content', '')}"
                    for msg in recent_history
                ) + "\n\n"

            answer = ""
            if self.llm.is_loaded:
                try:
                    if context:
                        if is_web_search:
                            rag_prompt = f"""You are a helpful assistant answering questions based on the web search results below.

Instructions:
- Synthesize information from ALL relevant search results.
- Give a comprehensive, detailed answer.
- Cite the corresponding web search result using bracket numbers like [1] or [2] at the end of the sentence or clause containing the fact. The bracket number must correspond to the section index (e.g. use [1] for the first section, [2] for the second).
- If the user is simply greeting you (e.g. "hi", "hello") or making general conversation, respond CONCISELY and politely without referencing search results. Keep greetings to 1-2 sentences max.
- Otherwise, if the answer to the user's specific question is not in the context, say: "The information is not available in the search results."

{history_text}Web Search Context:
{context}

Question: {question}

Comprehensive Answer:"""
                        else:
                            rag_prompt = f"""You are a helpful assistant answering questions based on the provided documents.

Instructions:
- Synthesize information from ALL relevant sections of the context below.
- Give a comprehensive, detailed answer covering all relevant points found.
- If information comes from multiple documents, combine it into a single coherent answer.
- Cite the corresponding context section using bracket numbers like [1] or [2] at the end of the sentence or clause containing the fact. The bracket number must correspond to the section index (e.g. use [1] for the first section, [2] for the second). Do not create citations for section numbers that do not exist.
- If the user is simply greeting you (e.g. "hi", "hello") or making general conversation, respond CONCISELY and politely without referencing the documents. Keep greetings to 1-2 sentences max.
- Otherwise, if the answer to the user's specific question is not in the context, say: "The information is not available in the uploaded documents."

{history_text}Context (from {len(search_results)} retrieved sections across uploaded documents):
{context}

Question: {question}

Comprehensive Answer:"""
                    else:
                        from datetime import datetime
                        current_dt = datetime.now().strftime("%Y-%m-%d %I:%M %p")
                        rag_prompt = f"""You are a helpful, polite, and intelligent AI assistant. 
The user is talking to you directly. Respond naturally to their greeting, pleasantry, or general question. 
Keep your response CONCISE (1-2 sentences). Do not ramble or over-explain.
The current system local date and time is: {current_dt}. If the user asks about the time or date, answer them directly and correctly based on this system date/time.
If they ask about documents, remind them they haven't uploaded any or that no relevant documents were found.

{history_text}User: {question}

Assistant:"""

                    # Stream LLM tokens
                    for chunk in self.llm.generate_stream(rag_prompt, max_tokens=1024):
                        answer += chunk
                        yield {"type": "chunk", "content": chunk}
                        
                except Exception as e:
                    logger.warning(f"LLM streaming failed: {e}")
                    yield {"type": "error", "content": f"LLM streaming failed: {e}"}
            
            # If answer is still empty (LLM offline or failed)
            if not answer:
                seen_chunks = set()
                top_chunks = []
                for chunk in context_chunks:
                    text = chunk[0]
                    trimmed = text.strip()
                    if trimmed not in seen_chunks:
                        seen_chunks.add(trimmed)
                        top_chunks.append(trimmed)
                top_chunks = top_chunks[:3]

                if top_chunks:
                    fallback = (
                        f"Based on the {'web search' if is_web_search else 'uploaded documents'}, here is the most relevant information:\n\n"
                        + "\n\n".join(f"• {chunk[:500]}" for chunk in top_chunks)
                    )
                else:
                    lower_q = question.lower().strip()
                    time_keywords = {"time", "date", "today", "now", "clock"}
                    if any(tk in lower_q for tk in time_keywords) and len(lower_q.split()) <= 6:
                        from datetime import datetime
                        fallback = f"The current system date and time is {datetime.now().strftime('%A, %B %d, %Y, %I:%M %p')}."
                    elif any(g in lower_q for g in ["hi", "hello", "hey", "how are you", "who are you"]):
                        fallback = "Hello! I am SecureHall-RAG. I can help you answer questions about your documents."
                    else:
                        fallback = "No relevant information found in the knowledge base."
                yield {"type": "chunk", "content": fallback}

            # If uncertainty tier is LOW, append disclaimer to response
            if answer and uncertainty_tier == UncertaintyQuantifier.LOW:
                disclaimer = "\n\n*Note: This answer was generated with low confidence from the source documents. Please verify with official channels.*"
                if not answer.endswith(disclaimer):
                    answer += disclaimer
                    yield {"type": "chunk", "content": disclaimer}

            generation_time = (time.time() - generation_start) * 1000

            # Yield done event
            yield {
                "type": "done",
                "latency_ms": (time.time() - start_time) * 1000,
                "generation_latency_ms": generation_time
            }

        except Exception as e:
            logger.error(f"Stream query failed: {str(e)}")
            yield {"type": "error", "content": f"Stream failed: {str(e)}"}

    def format_context(self, chunks: List[Tuple]) -> str:
        """
        Format retrieved chunks into context for LLM.

        Args:
            chunks: List of (chunk_text, relevance_score) or (chunk_text, relevance_score, source) tuples

        Returns:
            Formatted context string with citations and scores
        """
        if not chunks:
            return "No relevant context available."

        context_lines = []
        for i, chunk in enumerate(chunks, 1):
            if len(chunk) == 3:
                text, score, source = chunk
                source_display = f"Source: {Path(source).name if not (source.startswith('http://') or source.startswith('https://')) else source}, "
            else:
                text, score = chunk[0], chunk[1]
                source_display = ""
            # Truncate very long texts
            display_text = text[:800] + "..." if len(text) > 800 else text
            context_lines.append(f"[{i}] ({source_display}Relevance Score: {score:.2f})\n{display_text}\n")

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

    def persist(self) -> None:
        """
        Save the current index state to disk so documents survive server restarts.

        Saves:
        - FAISS dense embeddings + metadata
        - BM25 sparse index
        - chunk_id_to_text mapping (needed for citation generation)
        - corpus texts and chunk_ids
        - metadata store
        """
        if not self.data_dir:
            logger.warning("No data_dir configured — skipping persistence.")
            return

        if not self.index_built:
            logger.warning("Index not built yet — nothing to persist.")
            return

        import json

        data_path = Path(self.data_dir)
        data_path.mkdir(parents=True, exist_ok=True)

        # Save retriever indices (FAISS + BM25)
        self.retriever.save_indices(str(data_path / "indices"))

        # Save chunk_id_to_text mapping (needed for citations on reload)
        with open(data_path / "chunk_id_to_text.json", "w", encoding="utf-8") as f:
            json.dump(self.chunk_id_to_text, f, ensure_ascii=False, indent=2)

        # Save parent_texts mapping if present
        if hasattr(self.metadata_store, "parent_texts") and self.metadata_store.parent_texts:
            with open(data_path / "parent_texts.json", "w", encoding="utf-8") as f:
                json.dump(self.metadata_store.parent_texts, f, ensure_ascii=False, indent=2)

        # Save metadata store
        self.metadata_store.export_metadata(str(data_path / "metadata_store.json"))

        # Save corpus state
        corpus_state = {
            "corpus_texts": self._corpus_texts,
            "corpus_chunk_ids": self._corpus_chunk_ids,
            "total_chunks": self.total_chunks,
        }
        with open(data_path / "corpus_state.json", "w", encoding="utf-8") as f:
            json.dump(corpus_state, f, ensure_ascii=False, indent=2)

        logger.info(
            f"✅ Persisted pipeline state to {data_path} "
            f"({self.total_chunks} chunks)"
        )

    def _load_persisted_state(self) -> None:
        """
        Attempt to load previously saved indices and corpus state from disk.
        Called automatically during __init__ when data_dir is set.
        """
        import json

        data_path = Path(self.data_dir)
        indices_path = data_path / "indices"
        chunk_map_path = data_path / "chunk_id_to_text.json"
        corpus_state_path = data_path / "corpus_state.json"
        metadata_store_path = data_path / "metadata_store.json"

        # Check if persisted state exists
        if not indices_path.exists() or not chunk_map_path.exists():
            logger.info("No persisted state found — starting with empty index.")
            return

        try:
            # Load retriever indices
            loaded = self.retriever.load_indices(str(indices_path))
            if not loaded:
                return

            # Load chunk_id_to_text mapping
            with open(chunk_map_path, "r", encoding="utf-8") as f:
                self.chunk_id_to_text = json.load(f)

            # Load metadata store if exists
            if metadata_store_path.exists():
                self.metadata_store.import_metadata(str(metadata_store_path))

            # Load parent_texts mapping if exists
            parent_texts_path = data_path / "parent_texts.json"
            if parent_texts_path.exists() and hasattr(self.metadata_store, "parent_texts"):
                with open(parent_texts_path, "r", encoding="utf-8") as f:
                    self.metadata_store.parent_texts = json.load(f)

            # Load corpus state
            if corpus_state_path.exists():
                with open(corpus_state_path, "r", encoding="utf-8") as f:
                    corpus_state = json.load(f)
                loaded_texts = corpus_state.get("corpus_texts", [])
                loaded_chunk_ids = corpus_state.get("corpus_chunk_ids", [])
                
                # 1. Deduplicate by chunk_id
                seen_cids = set()
                unique_texts = []
                unique_chunk_ids = []
                for cid, txt in zip(loaded_chunk_ids, loaded_texts):
                    if cid not in seen_cids:
                        seen_cids.add(cid)
                        unique_chunk_ids.append(cid)
                        unique_texts.append(txt)
                
                # 2. Clean up orphan chunks whose documents no longer exist on disk
                upload_dir = Path("uploaded_documents")
                valid_doc_ids = set()
                if upload_dir.exists():
                    for f_path in upload_dir.iterdir():
                        if f_path.is_file():
                            parts = f_path.name.split("_", 1)
                            if parts:
                                valid_doc_ids.add(parts[0])
                
                self._corpus_texts = []
                self._corpus_chunk_ids = []
                for cid, txt in zip(unique_chunk_ids, unique_texts):
                    parts = cid.split("_", 1)
                    if parts and parts[0] in valid_doc_ids:
                        self._corpus_chunk_ids.append(cid)
                        self._corpus_texts.append(txt)
                    else:
                        logger.info(f"Removing orphan chunk {cid} from index (document no longer exists).")
                
                self.total_chunks = len(self._corpus_chunk_ids)
                
                # Rebuild and persist if changes occurred
                if len(self._corpus_chunk_ids) < len(loaded_chunk_ids):
                    logger.info(f"Cleaned corpus (removed duplicates/orphans): {len(loaded_chunk_ids)} -> {len(self._corpus_chunk_ids)} chunks. Rebuilding index...")
                    self.retriever.build_index(self._corpus_texts, self._corpus_chunk_ids)
                    self.persist()

            self.index_built = True

            logger.info(
                f"✅ Restored persisted pipeline state: "
                f"{self.total_chunks} chunks from {data_path}"
            )

        except Exception as e:
            logger.error(f"Failed to load persisted state: {e} — starting fresh.")
            self.index_built = False

    def delete_document(self, doc_id: str) -> bool:
        """
        Delete a document's chunks from the RAG pipeline index and persist the changes.
        """
        prefix = f"{doc_id}_"
        
        # Filter _corpus_chunk_ids and parallel _corpus_texts
        filtered_corpus = [
            (cid, txt) for cid, txt in zip(self._corpus_chunk_ids, self._corpus_texts)
            if not cid.startswith(prefix)
        ]
        
        removed_count = len(self._corpus_chunk_ids) - len(filtered_corpus)
        if removed_count > 0:
            logger.info(f"Removing {removed_count} chunks for document ID {doc_id} from RAG index.")
            self._corpus_chunk_ids = [item[0] for item in filtered_corpus]
            self._corpus_texts = [item[1] for item in filtered_corpus]
            
            # Clean in-memory chunk map
            for cid in list(self.chunk_id_to_text.keys()):
                if cid.startswith(prefix):
                    del self.chunk_id_to_text[cid]
                    
            # Clean in-memory metadata store
            for cid in list(self.metadata_store.chunk_metadata.keys()):
                if cid.startswith(prefix):
                    del self.metadata_store.chunk_metadata[cid]
                    
            for doc_key in list(self.metadata_store.document_metadata.keys()):
                if doc_key.startswith(prefix) or doc_key == doc_id:
                    del self.metadata_store.document_metadata[doc_key]
                    
            # Clean SQLite DB tables (if persistent)
            if self.metadata_store.db_path:
                import sqlite3
                try:
                    conn = sqlite3.connect(str(self.metadata_store.db_path))
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM chunks WHERE chunk_id LIKE ?", (f"{prefix}%",))
                    cursor.execute("DELETE FROM documents WHERE source_doc LIKE ?", (f"{prefix}%",))
                    conn.commit()
                    conn.close()
                except Exception as db_err:
                    logger.warning(f"Failed to delete metadata from database: {db_err}")
            
            # Rebuild retriever index and save
            if self._corpus_chunk_ids:
                self.retriever.build_index(self._corpus_texts, self._corpus_chunk_ids)
                self.index_built = True
            else:
                # Index is now completely empty
                self.retriever.embeddings = None
                self.retriever.chunk_ids = []
                self.retriever.texts = []
                self.retriever._faiss_index = None
                self.index_built = False
                
            self.total_chunks = len(self._corpus_chunk_ids)
            self.persist()
            return True
            
        return False


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
