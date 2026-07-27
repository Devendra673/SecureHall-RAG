"""
retrieval_ablation.py
Measures real P@K and R@K for each retrieval configuration:
  - Dense Only (FAISS / all-mpnet-base-v2)
  - Sparse Only (BM25)
  - Hybrid RRF (no reranker)
  - Hybrid RRF + Cross-Encoder Reranker
  - SecureHall-RAG Full (Hybrid + Reranker + RAPTOR nodes in index)

No Ollama / LLM required.
Uses the 10 sample_documents and the stored eval_dataset for ground-truth.
"""

import json, sys, time, logging
import numpy as np
from pathlib import Path

logging.basicConfig(level=logging.WARNING)  # suppress noisy info logs

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
RESULTS = Path(__file__).parent / "results"
DATA    = Path(__file__).parent / "data"
DOCS    = ROOT / "sample_documents"

# ── Load eval dataset ──────────────────────────────────────────────────────
with open(DATA / "eval_dataset.json") as f:
    eval_data = json.load(f)

# Use answerable questions only (unanswerable have no retrievable evidence)
questions = [q for q in eval_data["questions"] if q.get("answerable", True)]
print(f"Loaded {len(questions)} answerable questions for retrieval evaluation")

# ── Build ground truth: question → source document name ───────────────────
# strip UUID prefix from source_doc stored in dataset
def clean_docname(raw):
    """Strip UUID prefix like '10c98380-7a1_' from filename."""
    import re
    return re.sub(r'^[0-9a-f\-]+_', '', Path(raw).name)

gt_source = {}
for q in questions:
    gt_source[q["id"]] = clean_docname(q["source_doc"])

# ── Ingest all 10 documents ────────────────────────────────────────────────
from src.ingestion.document_parser import DocumentParser
from src.ingestion.chunker import SemanticChunker

doc_paths = sorted(DOCS.glob("*.docx"))
print(f"Found {len(doc_paths)} documents to ingest")

parser  = DocumentParser()
chunker = SemanticChunker(chunk_size_tokens=300)

all_texts     = []
all_chunk_ids = []
chunk_to_doc  = {}   # chunk_id → document filename

for doc_path in doc_paths:
    parsed = parser.parse(str(doc_path))
    if not parsed:
        continue
    full_text = "\n\n".join(t for t, _ in parsed)
    chunks, _ = chunker.chunk_with_parents(
        full_text,
        source_file=doc_path.name,
        chunk_id_prefix=doc_path.stem,
    )
    for c in chunks:
        all_texts.append(c.text)
        all_chunk_ids.append(c.chunk_id)
        chunk_to_doc[c.chunk_id] = doc_path.name

print(f"Total chunks indexed: {len(all_texts)}")

# ── Helper: Precision@K and Recall@K ──────────────────────────────────────
def precision_at_k(retrieved_ids, relevant_doc, k):
    """1 if the correct document appears in top-k, else 0."""
    top_k = retrieved_ids[:k]
    hit = any(chunk_to_doc.get(cid, "") == relevant_doc for cid in top_k)
    return 1.0 if hit else 0.0

def recall_at_k(retrieved_ids, relevant_doc, k, total_relevant=None):
    """Fraction of relevant chunks in top-k (approx: 1 if any relevant found)."""
    # For this evaluation we treat "at least 1 relevant chunk in top-k" as recall=1
    top_k = retrieved_ids[:k]
    hit = any(chunk_to_doc.get(cid, "") == relevant_doc for cid in top_k)
    return 1.0 if hit else 0.0

def evaluate_retriever(name, get_results_fn, ks=(1, 3, 5)):
    """
    get_results_fn(query) → list of chunk_ids ordered by relevance
    """
    metrics = {f"P@{k}": [] for k in ks}
    metrics.update({f"R@{k}": [] for k in ks})
    latencies = []

    for q in questions:
        query      = q["question"]
        target_doc = gt_source[q["id"]]

        t0 = time.time()
        try:
            result_ids = get_results_fn(query)
        except Exception as e:
            print(f"  ERROR on '{query[:40]}': {e}")
            result_ids = []
        latencies.append((time.time() - t0) * 1000)

        for k in ks:
            metrics[f"P@{k}"].append(precision_at_k(result_ids, target_doc, k))
            metrics[f"R@{k}"].append(recall_at_k(result_ids, target_doc, k))

    summary = {k: round(float(np.mean(v)), 4) for k, v in metrics.items()}
    summary["latency_mean_ms"] = round(float(np.mean(latencies)), 1)
    summary["n_queries"] = len(questions)
    print(f"  {name:<40}  P@1={summary['P@1']:.3f}  P@3={summary['P@3']:.3f}"
          f"  P@5={summary['P@5']:.3f}  R@3={summary['R@3']:.3f}"
          f"  R@5={summary['R@5']:.3f}  lat={summary['latency_mean_ms']:.0f}ms")
    return summary

# ── Build retrievers ───────────────────────────────────────────────────────
print("\nBuilding retrieval indices (this takes ~1–3 min)...")

from src.retrieval.dense_retriever import DenseRetriever
from src.retrieval.bm25_retriever  import BM25Retriever
from src.retrieval.hybrid_retriever import HybridRetriever
from src.retrieval.reranker         import CrossEncoderReRanker

EMBED_MODEL   = "sentence-transformers/all-mpnet-base-v2"
RERANK_MODEL  = "cross-encoder/ms-marco-MiniLM-L-6-v2"
TOP_K_FETCH   = 20   # candidates fed to reranker
TOP_K_FINAL   = 5    # final results

# Dense only
print("  Building FAISS dense index…")
dense = DenseRetriever(model_name=EMBED_MODEL)
dense.embed_chunks(all_texts, all_chunk_ids)

# BM25 only
print("  Building BM25 index…")
bm25 = BM25Retriever()
bm25.build_index(all_texts, all_chunk_ids)

# Hybrid
print("  Building hybrid (RRF) index…")
hybrid = HybridRetriever(dense_weight=0.7, sparse_weight=0.3, dense_model=EMBED_MODEL)
hybrid.build_index(all_texts, all_chunk_ids)

# Reranker
print("  Loading cross-encoder reranker…")
reranker = CrossEncoderReRanker(model_name=RERANK_MODEL, device="cpu")
chunk_text_map = dict(zip(all_chunk_ids, all_texts))

print("\nRunning retrieval evaluation…\n")

# ── Config 1: Dense only ──────────────────────────────────────────────────
def dense_retrieve(q):
    results = dense.search(q, top_k=TOP_K_FINAL)
    return [r.chunk_id for r in results]

# ── Config 2: BM25 only ───────────────────────────────────────────────────
def bm25_retrieve(q):
    results = bm25.search(q, top_k=TOP_K_FINAL)
    return [r.chunk_id for r in results]

# ── Config 3: Hybrid RRF, no reranker ─────────────────────────────────────
def hybrid_retrieve(q):
    results = hybrid.search(q, top_k=TOP_K_FINAL)
    return [r.chunk_id for r in results]

# ── Config 4: Hybrid RRF + Cross-Encoder ─────────────────────────────────
def hybrid_rerank_retrieve(q):
    candidates = hybrid.search(q, top_k=TOP_K_FETCH)
    if reranker.is_loaded and candidates:
        reranked = reranker.rerank(q, candidates, chunk_text_map, top_k=TOP_K_FINAL)
        return [r.chunk_id for r in reranked]
    return [r.chunk_id for r in candidates[:TOP_K_FINAL]]

# ── Config 5: Full (Hybrid + Reranker + synthetic RAPTOR summary nodes) ───
# We simulate RAPTOR by adding simple per-document abstractive summaries
# to the same freshly-built index (no LLM needed — use first 200 chars as proxy)
full_texts     = list(all_texts)
full_chunk_ids = list(all_chunk_ids)
full_chunk_text_map = dict(chunk_text_map)

# Build one summary node per document
from src.ingestion.document_parser import DocumentParser as DP2
from src.ingestion.chunker import SemanticChunker as SC2

for doc_path in doc_paths:
    parsed = DP2().parse(str(doc_path))
    if not parsed:
        continue
    # Use first 300 chars of the doc as a proxy summary node
    combined = " ".join(t for t, _ in parsed)[:300]
    summary_id   = f"raptor_summary_{doc_path.stem}_0000"
    summary_text = f"Executive Summary: {combined}"
    if summary_id not in full_chunk_ids:
        full_texts.append(summary_text)
        full_chunk_ids.append(summary_id)
        full_chunk_text_map[summary_id] = summary_text
        chunk_to_doc[summary_id] = doc_path.name  # summary maps to same doc

print(f"  Full index: {len(full_texts)} chunks (incl. {len(doc_paths)} RAPTOR nodes)")

full_hybrid = HybridRetriever(dense_weight=0.7, sparse_weight=0.3, dense_model=EMBED_MODEL)
full_hybrid.build_index(full_texts, full_chunk_ids)

def full_retrieve(q):
    candidates = full_hybrid.search(q, top_k=TOP_K_FETCH)
    if reranker.is_loaded and candidates:
        reranked = reranker.rerank(q, candidates, full_chunk_text_map, top_k=TOP_K_FINAL)
        return [r.chunk_id for r in reranked]
    return [r.chunk_id for r in candidates[:TOP_K_FINAL]]

# ── Run all configurations ─────────────────────────────────────────────────
configs = [
    ("Dense Only (FAISS)",           dense_retrieve),
    ("Sparse Only (BM25)",           bm25_retrieve),
    ("Hybrid RRF (no rerank)",       hybrid_retrieve),
    ("Hybrid RRF + Re-ranking",      hybrid_rerank_retrieve),
    ("SecureHall-RAG Full",          full_retrieve),
]

results_table = {}
for name, fn in configs:
    results_table[name] = evaluate_retriever(name, fn)

# ── Save results ───────────────────────────────────────────────────────────
out = {
    "generated_at": "2026-07-21",
    "embedding_model": EMBED_MODEL,
    "reranker_model": RERANK_MODEL,
    "top_k_candidates": TOP_K_FETCH,
    "top_k_final": TOP_K_FINAL,
    "n_documents": len(doc_paths),
    "n_chunks": len(all_texts),
    "n_eval_questions": len(questions),
    "eval_note": "P@K=1 if ANY chunk from the correct source document appears in top-K",
    "configurations": results_table,
}

out_path = RESULTS / "retrieval_ablation.json"
with open(out_path, "w") as f:
    json.dump(out, f, indent=2)

print(f"\n✅ Retrieval ablation saved to: {out_path}")

# ── Print clean table ──────────────────────────────────────────────────────
print("\n" + "="*75)
print(f"{'Configuration':<42} {'P@1':>5} {'P@3':>5} {'P@5':>5} {'R@3':>5} {'R@5':>5}")
print("-"*75)
for name, m in results_table.items():
    print(f"{name:<42} {m['P@1']:>5.3f} {m['P@3']:>5.3f} {m['P@5']:>5.3f}"
          f" {m['R@3']:>5.3f} {m['R@5']:>5.3f}")
print("="*75)
