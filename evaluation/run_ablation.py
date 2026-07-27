"""
run_ablation.py
================
Genuine baseline-vs-enhanced ablation runner for SecureHall-RAG.

WHY THIS EXISTS
---------------
The previous `baseline_metrics.json` / `enhanced_metrics.json` were hand-authored
summaries whose *quality* numbers (ROUGE-L, relevance, confidence) were identical
between the two modes — only latency differed. That made the ablation
statistically meaningless (delta = 0, p = 1.000). This script actually runs the
evaluation twice against two genuinely different pipeline configurations and
writes real per-question / per-attack records, so the comparison is honest.

WHAT DIFFERS BETWEEN THE TWO MODES
----------------------------------
  baseline  : hybrid retrieval (FAISS + BM25 + RRF) + cross-encoder reranker.
              Claim-level NLI verification + self-correction DISABLED.
              Security: regex/pattern content filter only (no semantic detector).
  enhanced  : everything in baseline PLUS the NLI verification + self-correction
              loop AND the embedding-similarity semantic attack detector.

The single pipeline toggle is `enable_verification`; the single security toggle is
`enable_semantic` on the ContentFilter.

METRICS
-------
  faithfulness_rouge_l : lexical overlap (LCS) of answer vs gold answer. Kept for
                         continuity with the old report, but it is a weak metric
                         for this task (short auto-generated gold answers).
  faithfulness_semantic: cosine similarity between the answer embedding and the
                         retrieved-context embedding. This measures *grounding*
                         (is the answer supported by what was retrieved) and is a
                         far better proxy for faithfulness than ROUGE-L.
  answer_relevance     : cosine similarity between answer and question embeddings.
  confidence           : pipeline confidence score.
  latency_ms           : end-to-end latency.

NOTE ON REQUIREMENTS
--------------------
The *quality* ablation requires a running Ollama LLM — the verification loop only
executes when the LLM is loaded, so without it baseline and enhanced answers are
identical (retrieval-only). The *security* ablation does NOT need the LLM and will
always produce a genuine baseline-vs-enhanced difference (semantic detector on/off).

USAGE
-----
  python evaluation/run_ablation.py                 # full run (needs Ollama)
  python evaluation/run_ablation.py --questions 15  # quick quality subset
  python evaluation/run_ablation.py --security-only # security ablation only (no LLM)
"""

import argparse
import json
import sys
import time
from pathlib import Path

# Project root on path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DATA = ROOT / "evaluation" / "data"
RESULTS = ROOT / "evaluation" / "results"

# ─── Lightweight scoring model (shared) ──────────────────────────────────────
_SCORER = None


def _get_scorer():
    """Lazily load a small sentence-transformer used only for metric scoring."""
    global _SCORER
    if _SCORER is None:
        from sentence_transformers import SentenceTransformer

        _SCORER = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    return _SCORER


def _cosine(a: str, b: str) -> float:
    """Cosine similarity between two texts. Returns 0.0 if either is empty."""
    if not a or not a.strip() or not b or not b.strip():
        return 0.0
    import numpy as np

    model = _get_scorer()
    embs = model.encode([a, b], normalize_embeddings=True, convert_to_numpy=True)
    return float(np.clip(embs[0] @ embs[1], 0.0, 1.0))


def _rouge_l(candidate: str, reference: str) -> float:
    """ROUGE-L F1 based on longest-common-subsequence of tokens."""
    cand = (candidate or "").lower().split()
    ref = (reference or "").lower().split()
    if not cand or not ref:
        return 0.0
    # LCS length via DP
    m, n = len(cand), len(ref)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if cand[i - 1] == ref[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
    lcs = dp[m][n]
    if lcs == 0:
        return 0.0
    prec = lcs / m
    rec = lcs / n
    return 2 * prec * rec / (prec + rec)


# ─── Quality ablation ────────────────────────────────────────────────────────
def build_pipeline(enable_verification: bool):
    """Build a RAGPipeline for the given ablation mode and ensure it has an index."""
    from src.rag_pipeline import RAGPipeline

    import os
    llm_model = os.getenv("ABLATION_LLM_MODEL", "llama3.1:8b")
    pipeline = RAGPipeline(
        llm_model=llm_model,
        data_dir=str(ROOT / "app_data"),
        enable_cache=False,              # no caching during benchmarking
        enable_verification=enable_verification,
    )

    if not pipeline.index_built:
        # Ingest sample documents so retrieval has something to work with.
        sample_dir = ROOT / "sample_documents"
        upload_dir = ROOT / "uploaded_documents"
        src_dir = upload_dir if upload_dir.exists() else sample_dir
        if src_dir.exists():
            files = [str(f) for f in src_dir.iterdir() if f.is_file()]
            if files:
                print(f"  Ingesting {len(files)} documents from {src_dir.name}/ ...")
                pipeline.ingest_documents(files)
    return pipeline


def run_quality(mode: str, enable_verification: bool, limit: int | None):
    print(f"\n=== QUALITY: mode={mode} (verification={'ON' if enable_verification else 'OFF'}) ===")
    with open(DATA / "eval_dataset.json", encoding="utf-8") as f:
        dataset = json.load(f)
    questions = dataset.get("questions", [])
    if limit:
        # Keep category balance: take up to `limit` total, round-robin by category.
        by_cat: dict[str, list] = {}
        for q in questions:
            by_cat.setdefault(q.get("category", "general"), []).append(q)
        per_cat = max(1, limit // max(len(by_cat), 1))
        sel = []
        for items in by_cat.values():
            sel.extend(items[:per_cat])
        questions = sel[:limit]

    pipeline = build_pipeline(enable_verification)
    llm_ready = pipeline.llm.is_loaded
    if not llm_ready:
        try:
            pipeline.llm.load_model()
            llm_ready = pipeline.llm.is_loaded
        except Exception:
            llm_ready = False
    if not llm_ready:
        print("  [WARN] Ollama LLM not available — answers will be retrieval-only and")
        print("         the verification ablation cannot differentiate the two modes.")

    eval_results = []
    for idx, item in enumerate(questions, 1):
        q = item.get("question", "")
        gold = item.get("gold_answer", "")
        cat = item.get("category", "general")
        try:
            res = pipeline.query(q)
        except Exception as e:
            print(f"  [{idx}/{len(questions)}] ERROR: {e}")
            continue
        answer = res.get("answer", "") or ""
        citations = res.get("citations", [])
        context = "\n\n".join(c[2] for c in citations) if citations else ""
        tier = res.get("uncertainty_tier", "")

        record = {
            "id": item.get("id"),
            "question": q,
            "category": cat,
            "answer": answer,
            "faithfulness_rouge_l": _rouge_l(answer, gold),
            "faithfulness_semantic": _cosine(answer, context),
            "answer_relevance": _cosine(answer, q),
            "confidence": float(res.get("confidence", 0.0)),
            "uncertainty_tier": tier,
            "latency_ms": float(res.get("latency_ms", 0.0)),
            "refused": tier == "ABSTAIN",
        }
        eval_results.append(record)
        print(
            f"  [{idx}/{len(questions)}] {cat:<24} "
            f"rougeL={record['faithfulness_rouge_l']:.3f} "
            f"sem={record['faithfulness_semantic']:.3f} "
            f"conf={record['confidence']:.2f} tier={tier}"
        )
    return eval_results, llm_ready


# ─── Security ablation ───────────────────────────────────────────────────────
def run_security(mode: str, enable_semantic: bool):
    print(f"\n=== SECURITY: mode={mode} (semantic detector={'ON' if enable_semantic else 'OFF'}) ===")
    from src.security.content_filter import ContentFilter, SeverityLevel

    cf = ContentFilter(
        sql_severity=SeverityLevel.BLOCK,
        jailbreak_severity=SeverityLevel.BLOCK,
        obfuscation_severity=SeverityLevel.SANITIZE,
        enable_semantic=enable_semantic,
    )

    with open(DATA / "adversarial_test_set.json", encoding="utf-8") as f:
        adv = json.load(f)
    cases = adv.get("cases", [])

    results = []
    for case in cases:
        query = case.get("query", "")
        expected = case.get("expected_behavior", "")
        should_block = expected in ("block", "block_or_error")
        fr = cf.filter_content(query)
        blocked = fr.severity_level == SeverityLevel.BLOCK
        # "correct" = blocked exactly when it should be blocked
        correct = (blocked == should_block)
        results.append({
            "id": case.get("id"),
            "category": case.get("category", "general"),
            "expected_behavior": expected,
            "blocked": blocked,
            "correct": correct,
            "detected_patterns": fr.detected_patterns,
        })

    total = len(results)
    correct_n = sum(1 for r in results if r["correct"])
    should_n = sum(1 for r in results if r["expected_behavior"] in ("block", "block_or_error"))
    blocked_should = sum(
        1 for r in results
        if r["blocked"] and r["expected_behavior"] in ("block", "block_or_error")
    )
    block_rate = 100.0 * blocked_should / max(should_n, 1)
    print(f"  correct: {correct_n}/{total} ({100*correct_n/total:.1f}%)  "
          f"attack-block-rate: {blocked_should}/{should_n} ({block_rate:.1f}%)")
    return results


# ─── Main ────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description="SecureHall-RAG baseline vs enhanced ablation")
    ap.add_argument("--questions", type=int, default=None,
                    help="Limit the number of quality questions (category-balanced subset)")
    ap.add_argument("--security-only", action="store_true",
                    help="Run only the security ablation (no LLM required)")
    args = ap.parse_args()

    RESULTS.mkdir(parents=True, exist_ok=True)
    llm_ready = None

    for mode, verif, sem in (("baseline", False, False), ("enhanced", True, True)):
        eval_results = []
        if not args.security_only:
            eval_results, llm_ready = run_quality(mode, verif, args.questions)
        security_results = run_security(mode, sem)

        out = {
            "mode": mode,
            "description": (
                "Hybrid retrieval (FAISS + BM25 + RRF) + reranker. "
                "Verification DISABLED, pattern-only security."
                if mode == "baseline" else
                "Full pipeline: retrieval + reranker + NLI verification + "
                "self-correction + semantic attack detection."
            ),
            "llm_available": bool(llm_ready) if not args.security_only else None,
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "eval_results": eval_results,
            "adversarial_results": security_results,
        }
        out_path = RESULTS / f"{mode}_metrics.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2)
        print(f"\nSaved {out_path.relative_to(ROOT)}")

    print("\nDone. Now run:  python evaluation/compute_real_metrics.py")
    if llm_ready is False:
        print("\n[!] LLM was unavailable, so quality metrics are retrieval-only and")
        print("    baseline==enhanced for quality. Start Ollama and re-run for the")
        print("    genuine verification ablation. The SECURITY ablation is valid as-is.")


if __name__ == "__main__":
    main()
