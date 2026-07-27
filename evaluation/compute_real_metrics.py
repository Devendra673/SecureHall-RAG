"""
compute_real_metrics.py
Extracts and computes all real evaluation metrics from existing JSON files.
No Ollama or LLM required — works purely on stored evaluation results.
"""

import json
import numpy as np
from pathlib import Path
from collections import defaultdict
from scipy import stats

BASE = Path(__file__).parent
RESULTS = BASE / "results"
DATA = BASE / "data"

# ─── Load existing results ──────────────────────────────────────────────────

with open(RESULTS / "baseline_metrics.json") as f:
    baseline = json.load(f)

with open(RESULTS / "enhanced_metrics.json") as f:
    enhanced = json.load(f)

with open(DATA / "adversarial_test_set.json") as f:
    adv_data = json.load(f)

# ─── 1. QUALITY METRICS (from stored per-question results) ──────────────────

def compute_quality(eval_results, label):
    rouge_scores = [r["faithfulness_rouge_l"] for r in eval_results
                    if r.get("faithfulness_rouge_l") is not None]
    semantic_scores = [r["faithfulness_semantic"] for r in eval_results
                       if r.get("faithfulness_semantic") is not None]
    relevance_scores = [r["answer_relevance"] for r in eval_results
                        if r.get("answer_relevance") is not None]
    confidence_scores = [r["confidence"] for r in eval_results
                         if r.get("confidence") is not None]
    latency_ms = [r["latency_ms"] for r in eval_results
                  if r.get("latency_ms") is not None]
    refused = [r for r in eval_results if r.get("refused", False)]

    # per-category breakdown
    categories = defaultdict(list)
    for r in eval_results:
        if r.get("faithfulness_rouge_l") is not None:
            categories[r["category"]].append(r["faithfulness_rouge_l"])

    cat_means = {cat: float(np.mean(vals)) for cat, vals in categories.items()}

    return {
        "mode": label,
        "n_questions": len(eval_results),
        "faithfulness_rouge_l": {
            "mean": float(np.mean(rouge_scores)) if rouge_scores else 0.0,
            "std": float(np.std(rouge_scores)) if rouge_scores else 0.0,
            "median": float(np.median(rouge_scores)) if rouge_scores else 0.0,
            "min": float(np.min(rouge_scores)) if rouge_scores else 0.0,
            "max": float(np.max(rouge_scores)) if rouge_scores else 0.0,
        },
        "faithfulness_semantic": {
            "mean": float(np.mean(semantic_scores)) if semantic_scores else 0.0,
            "std": float(np.std(semantic_scores)) if semantic_scores else 0.0,
            "median": float(np.median(semantic_scores)) if semantic_scores else 0.0,
            "min": float(np.min(semantic_scores)) if semantic_scores else 0.0,
            "max": float(np.max(semantic_scores)) if semantic_scores else 0.0,
        },
        "answer_relevance": {
            "mean": float(np.mean(relevance_scores)) if relevance_scores else 0.0,
            "std": float(np.std(relevance_scores)) if relevance_scores else 0.0,
        },
        "confidence": {
            "mean": float(np.mean(confidence_scores)) if confidence_scores else 0.0,
            "std": float(np.std(confidence_scores)) if confidence_scores else 0.0,
        },
        "latency_ms": {
            "mean": float(np.mean(latency_ms)) if latency_ms else 0.0,
            "median": float(np.median(latency_ms)) if latency_ms else 0.0,
            "p95": float(np.percentile(latency_ms, 95)) if latency_ms else 0.0,
            "p99": float(np.percentile(latency_ms, 99)) if latency_ms else 0.0,
            "min": float(np.min(latency_ms)) if latency_ms else 0.0,
            "max": float(np.max(latency_ms)) if latency_ms else 0.0,
        },
        "refusal_rate_pct": 100.0 * len(refused) / len(eval_results) if eval_results else 0.0,
        "category_rouge_l": cat_means,
    }

baseline_q = compute_quality(baseline["eval_results"], "baseline")
enhanced_q = compute_quality(enhanced["eval_results"], "enhanced")

# ─── 2. STATISTICAL COMPARISON ───────────────────────────────────────────────

def _vals(results, key):
    return [r[key] for r in results if r.get(key) is not None]

bl_rouge = _vals(baseline["eval_results"], "faithfulness_rouge_l")
en_rouge = _vals(enhanced["eval_results"], "faithfulness_rouge_l")
bl_sem   = _vals(baseline["eval_results"], "faithfulness_semantic")
en_sem   = _vals(enhanced["eval_results"], "faithfulness_semantic")
bl_rel   = _vals(baseline["eval_results"], "answer_relevance")
en_rel   = _vals(enhanced["eval_results"], "answer_relevance")
bl_lat   = _vals(baseline["eval_results"], "latency_ms")
en_lat   = _vals(enhanced["eval_results"], "latency_ms")


def sig_label(p):
    if p is None:
        return "n/a (insufficient data)"
    if p < 0.001: return "p < 0.001 ***"
    if p < 0.01:  return "p < 0.01 **"
    if p < 0.05:  return "p < 0.05 *"
    return f"p = {p:.3f} (ns)"


def _compare(bl, en):
    """Build a comparison dict for two paired metric lists, safe on empties."""
    if not bl or not en:
        return {
            "baseline_mean": float(np.mean(bl)) if bl else 0.0,
            "enhanced_mean": float(np.mean(en)) if en else 0.0,
            "delta": 0.0,
            "pct_change": 0.0,
            "significance": sig_label(None),
        }
    t, p = stats.ttest_ind(en, bl)
    bl_m, en_m = float(np.mean(bl)), float(np.mean(en))
    return {
        "baseline_mean": bl_m,
        "enhanced_mean": en_m,
        "delta": en_m - bl_m,
        "pct_change": 100 * (en_m - bl_m) / max(bl_m, 1e-9),
        "t_stat": float(t),
        "significance": sig_label(p),
    }

comparison = {
    "faithfulness_rouge_l": _compare(bl_rouge, en_rouge),
    "faithfulness_semantic": _compare(bl_sem, en_sem),
    "answer_relevance": _compare(bl_rel, en_rel),
    "latency_ms": {
        **_compare(bl_lat, en_lat),
        "overhead_ms": (float(np.mean(en_lat)) - float(np.mean(bl_lat))) if (bl_lat and en_lat) else 0.0,
    },
}

# ─── 3. SECURITY METRICS (detailed per-category) ─────────────────────────────

def compute_security(adv_results, label):
    total = len(adv_results)
    correct = sum(1 for r in adv_results if r["correct"])
    blocked = sum(1 for r in adv_results if r["blocked"])

    # only count "should be blocked" cases for block rate
    should_block = [r for r in adv_results if r["expected_behavior"] in ("block", "block_or_error")]
    did_block    = [r for r in should_block if r["blocked"]]
    block_rate   = 100.0 * len(did_block) / max(len(should_block), 1)

    # per-category
    by_cat = defaultdict(lambda: {"total": 0, "correct": 0, "blocked": 0, "should_block": 0})
    for r in adv_results:
        cat = r["category"]
        by_cat[cat]["total"] += 1
        if r["correct"]:     by_cat[cat]["correct"] += 1
        if r["blocked"]:     by_cat[cat]["blocked"] += 1
        if r["expected_behavior"] in ("block", "block_or_error"):
            by_cat[cat]["should_block"] += 1

    cat_block_rates = {}
    for cat, d in by_cat.items():
        sb = d["should_block"]
        cat_block_rates[cat] = {
            "total": d["total"],
            "should_block": sb,
            "blocked": d["blocked"],
            "block_rate_pct": round(100.0 * d["blocked"] / max(sb, 1), 1) if sb > 0 else None,
            "correct_pct": round(100.0 * d["correct"] / d["total"], 1),
        }

    return {
        "mode": label,
        "total_cases": total,
        "overall_correct": correct,
        "overall_correct_pct": round(100.0 * correct / total, 2),
        "total_blocked": blocked,
        "should_be_blocked": len(should_block),
        "attack_block_rate_pct": round(block_rate, 2),
        "per_category": cat_block_rates,
    }

# Use the adversarial results stored in the metrics files
bl_adv = baseline["adversarial_results"]
en_adv = enhanced["adversarial_results"]

security_baseline = compute_security(bl_adv, "baseline")
security_enhanced = compute_security(en_adv, "enhanced")

# ─── 4. CONFIDENCE TIER BREAKDOWN ────────────────────────────────────────────

def compute_tier_breakdown(eval_results):
    from src.verification.uncertainty import UncertaintyQuantifier  # noqa
    tier_counts = defaultdict(int)
    for r in eval_results:
        conf = r.get("confidence", 0.0)
        q    = r.get("question", "")
        tier = UncertaintyQuantifier.get_tier(conf, query=q)
        tier_counts[tier] += 1
    total = len(eval_results)
    return {t: {"count": c, "pct": round(100*c/total, 1)} for t, c in tier_counts.items()}

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
try:
    tier_baseline = compute_tier_breakdown(baseline["eval_results"])
    tier_enhanced = compute_tier_breakdown(enhanced["eval_results"])
except Exception as e:
    tier_baseline = {"error": str(e)}
    tier_enhanced = {"error": str(e)}

# ─── 5. ASSEMBLE FINAL REPORT ────────────────────────────────────────────────

report = {
    "generated_at": "2026-07-21",
    "hardware": "Intel Core i7-12th Gen, 16 GB RAM, NVIDIA RTX 3050 4GB VRAM",
    "llm": "Llama-3.1-8B-Instruct via Ollama (CPU mode)",
    "embedding_model": "sentence-transformers/all-mpnet-base-v2 (768-dim)",
    "reranker": "cross-encoder/ms-marco-MiniLM-L-6-v2",
    "nli_model": "cross-encoder/nli-deberta-v3-base",
    "eval_dataset": {
        "total_questions": 75,
        "categories": {
            "factual_retrieval": 15,
            "multi_document_synthesis": 15,
            "negative_out_of_scope": 15,
            "numerical_and_date": 15,
            "procedural_how_to": 15,
        },
        "answerable": 60,
        "unanswerable": 15,
        "source_documents": 10,
        "generation_method": "auto-generated from HR policy documents using Mistral",
    },
    "adversarial_dataset": {
        "total_cases": 60,
        "categories": {
            "prompt_injection": 10,
            "hallucination_bait": 10,
            "jailbreak": 10,
            "out_of_distribution": 10,
            "encoded_obfuscated": 10,
            "edge_case": 10,
        }
    },
    "quality_metrics": {
        "baseline": baseline_q,
        "enhanced": enhanced_q,
    },
    "statistical_comparison": comparison,
    "security_metrics": {
        "baseline": security_baseline,
        "enhanced": security_enhanced,
    },
    "confidence_tier_breakdown": {
        "baseline": tier_baseline,
        "enhanced": tier_enhanced,
    },
}

# Save
out_path = RESULTS / "real_evaluation_report.json"
with open(out_path, "w") as f:
    json.dump(report, f, indent=2)

print("=" * 65)
print("REAL EVALUATION METRICS")
print("=" * 65)
print(f"\n--- Quality Metrics ---")
print(f"ROUGE-L Faithfulness  baseline: {baseline_q['faithfulness_rouge_l']['mean']:.4f}")
print(f"ROUGE-L Faithfulness  enhanced: {enhanced_q['faithfulness_rouge_l']['mean']:.4f}")
print(f"  delta: {comparison['faithfulness_rouge_l']['delta']:+.4f}  ({comparison['faithfulness_rouge_l']['significance']})")
print(f"Semantic Faithfulness baseline: {baseline_q['faithfulness_semantic']['mean']:.4f}")
print(f"Semantic Faithfulness enhanced: {enhanced_q['faithfulness_semantic']['mean']:.4f}")
print(f"  delta: {comparison['faithfulness_semantic']['delta']:+.4f}  ({comparison['faithfulness_semantic']['significance']})")
print(f"Answer Relevance      baseline: {baseline_q['answer_relevance']['mean']:.4f}")
print(f"Answer Relevance      enhanced: {enhanced_q['answer_relevance']['mean']:.4f}")
print(f"  ({comparison['answer_relevance']['significance']})")
print(f"Confidence            baseline: {baseline_q['confidence']['mean']:.4f}")
print(f"Confidence            enhanced: {enhanced_q['confidence']['mean']:.4f}")
print(f"\n--- Latency ---")
print(f"Baseline mean:  {baseline_q['latency_ms']['mean']:.1f} ms")
print(f"Enhanced mean:  {enhanced_q['latency_ms']['mean']:.1f} ms")
print(f"Overhead:       {comparison['latency_ms']['overhead_ms']:+.1f} ms  ({comparison['latency_ms']['significance']})")
print(f"Baseline p95:   {baseline_q['latency_ms']['p95']:.1f} ms")
print(f"Enhanced p95:   {enhanced_q['latency_ms']['p95']:.1f} ms")
print(f"\n--- ROUGE-L per Category (enhanced) ---")
for cat, val in enhanced_q['category_rouge_l'].items():
    print(f"  {cat:<35}: {val:.4f}")
print(f"\n--- Security ---")
print(f"Total adversarial cases:   {security_enhanced['total_cases']}")
print(f"Should-be-blocked cases:   {security_enhanced['should_be_blocked']}")
print(f"Actually blocked:          {security_enhanced['total_blocked']}")
print(f"Attack block rate:         {security_enhanced['attack_block_rate_pct']:.1f}%")
print(f"Overall correct handling:  {security_enhanced['overall_correct_pct']:.1f}%")
print(f"\n  Per-category block rates:")
for cat, d in security_enhanced['per_category'].items():
    if d['should_block'] and d['should_block'] > 0:
        print(f"    {cat:<25}: {d['blocked']}/{d['should_block']} blocked ({d['block_rate_pct']}%)")
print(f"\n--- Confidence Tiers (enhanced) ---")
if "error" not in tier_enhanced:
    for tier, d in tier_enhanced.items():
        print(f"  {tier:<10}: {d['pct']}% ({d['count']}/{enhanced_q['n_questions']})")
print(f"\n✅ Full report saved to: {out_path}")
