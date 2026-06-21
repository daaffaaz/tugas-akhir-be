"""
Reranker evaluation: compare retrieval with vs. without cross-encoder rerank.

Provides two additional retrieval quality metrics:
  - MRR  (Mean Reciprocal Rank):  how quickly the first relevant result appears
  - NDCG@K (Normalized Discounted Cumulative Gain): graded relevance
"""

from __future__ import annotations

import logging
import math
import statistics
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

from apps.rag import retriever, reranker


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class RerankReport:
    """Comparison of retrieval metrics with vs. without reranking."""
    # Without rerank (baseline)
    base_mrr: float
    base_ndcg_at_k: float
    base_hit_rate_at_k: float
    base_precision_at_k: float
    base_recall_at_k: float

    # With rerank
    rerank_mrr: float
    rerank_ndcg_at_k: float
    rerank_hit_rate_at_k: float
    rerank_precision_at_k: float
    rerank_recall_at_k: float

    queries_evaluated: int
    reranker_available: bool
    per_query: list[dict] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Core ranking metrics
# ---------------------------------------------------------------------------

def reciprocal_rank(retrieved_ids: list[str], relevant_ids: set[str]) -> float:
    """Reciprocal rank of the first relevant doc (1/position), 0 if none."""
    for i, rid in enumerate(retrieved_ids, start=1):
        if rid in relevant_ids:
            return 1.0 / i
    return 0.0


def dcg_at_k(retrieved_ids: list[str], relevant_ids: set[str], k: int) -> float:
    """Discounted Cumulative Gain with binary relevance."""
    score = 0.0
    for i, rid in enumerate(retrieved_ids[:k], start=1):
        if rid in relevant_ids:
            score += 1.0 / math.log2(i + 1)
    return score


def ndcg_at_k(retrieved_ids: list[str], relevant_ids: set[str], k: int) -> float:
    """NDCG@k — binary relevance, IDCG assumes all relevant docs at top."""
    dcg = dcg_at_k(retrieved_ids, relevant_ids, k)
    ideal_count = min(len(relevant_ids), k)
    if ideal_count == 0:
        return 0.0
    idcg = sum(1.0 / math.log2(i + 1) for i in range(1, ideal_count + 1))
    return dcg / idcg if idcg > 0 else 0.0


# ---------------------------------------------------------------------------
# Per-query helpers
# ---------------------------------------------------------------------------

def _measure(
    query: str,
    k: int,
    gt_ids: set[str],
    use_rerank: bool,
) -> dict[str, Any]:
    """Measure one query either with or without reranking."""
    # Retrieve larger pool when reranking (rerank then cut to k)
    pool_k = k * 3 if use_rerank else k
    pool_k = min(pool_k, 100)

    courses, _ = retriever.retrieve_courses(query, top_k=pool_k)

    if use_rerank and reranker.is_available() and courses:
        courses = reranker.rerank(query, courses, top_k=k, return_scores=False)
    else:
        courses = courses[:k]

    retrieved_ids = [c.get("course_id") for c in courses if c.get("course_id")]
    retrieved_set = set(retrieved_ids)

    relevant_retrieved = len(retrieved_set & gt_ids)
    total = len(retrieved_ids)
    total_gt = len(gt_ids)

    return {
        "query": query,
        "k": k,
        "rr": reciprocal_rank(retrieved_ids, gt_ids),
        "ndcg": ndcg_at_k(retrieved_ids, gt_ids, k),
        "hit": 1.0 if relevant_retrieved > 0 else 0.0,
        "precision": relevant_retrieved / total if total else 0.0,
        "recall": relevant_retrieved / total_gt if total_gt else 0.0,
        "relevant_retrieved": relevant_retrieved,
        "total_retrieved": total,
        "total_ground_truth": total_gt,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def evaluate_reranker(
    test_cases: list,
    k: int | None = None,
) -> RerankReport:
    """
    Compare retrieval with vs. without cross-encoder rerank.

    For each test case:
      1. Baseline  = plain FAISS retrieve, top-K
      2. Reranked  = FAISS retrieve top-(3K) → cross-encoder rerank → top-K

    Metrics per side: MRR, NDCG@K, Hit Rate, Precision, Recall.
    """
    rerank_ok = reranker.is_available()
    if not rerank_ok:
        logger.warning(
            "[eval_reranker] Cross-encoder unavailable, rerank metrics will be "
            "computed with original order (no effect). Error: %s",
            reranker._load_error,
        )

    per_query: list[dict] = []

    for tc in test_cases:
        k_used = k or tc.k
        gt_ids = set(tc.ground_truth_ids)
        if not gt_ids:
            continue

        base = _measure(tc.query, k_used, gt_ids, use_rerank=False)
        rer = _measure(tc.query, k_used, gt_ids, use_rerank=True)

        per_query.append({
            "query": tc.query,
            "k": k_used,
            "baseline": {
                "rr": base["rr"],
                "ndcg": base["ndcg"],
                "hit_rate": base["hit"],
                "precision": base["precision"],
                "recall": base["recall"],
            },
            "rerank": {
                "rr": rer["rr"],
                "ndcg": rer["ndcg"],
                "hit_rate": rer["hit"],
                "precision": rer["precision"],
                "recall": rer["recall"],
            },
            "delta_ndcg": round(rer["ndcg"] - base["ndcg"], 4),
            "delta_mrr": round(rer["rr"] - base["rr"], 4),
        })

    n = len(per_query)
    if n == 0:
        return RerankReport(
            base_mrr=0.0, base_ndcg_at_k=0.0,
            base_hit_rate_at_k=0.0, base_precision_at_k=0.0, base_recall_at_k=0.0,
            rerank_mrr=0.0, rerank_ndcg_at_k=0.0,
            rerank_hit_rate_at_k=0.0, rerank_precision_at_k=0.0, rerank_recall_at_k=0.0,
            queries_evaluated=0, reranker_available=rerank_ok,
        )

    def avg(side: str, metric: str) -> float:
        vals = [q[side][metric] for q in per_query if metric in q[side]]
        return round(statistics.mean(vals), 4) if vals else 0.0

    return RerankReport(
        base_mrr=avg("baseline", "rr"),
        base_ndcg_at_k=avg("baseline", "ndcg"),
        base_hit_rate_at_k=avg("baseline", "hit_rate"),
        base_precision_at_k=avg("baseline", "precision"),
        base_recall_at_k=avg("baseline", "recall"),
        rerank_mrr=avg("rerank", "rr"),
        rerank_ndcg_at_k=avg("rerank", "ndcg"),
        rerank_hit_rate_at_k=avg("rerank", "hit_rate"),
        rerank_precision_at_k=avg("rerank", "precision"),
        rerank_recall_at_k=avg("rerank", "recall"),
        queries_evaluated=n,
        reranker_available=rerank_ok,
        per_query=per_query,
    )


def print_rerank_report(report: RerankReport) -> str:
    """Format the reranker comparison as a readable table."""
    lines = []
    lines.append("─" * 70)
    lines.append("  RERANKER COMPARISON  (baseline vs cross-encoder)")
    lines.append("─" * 70)
    lines.append(f"  Reranker available: {report.reranker_available}")
    lines.append(f"  Queries evaluated:  {report.queries_evaluated}")
    lines.append("")
    lines.append(f"  {'Metric':<18} {'Baseline':>12} {'Rerank':>12} {'Δ':>10}")
    lines.append(f"  {'-'*18} {'-'*12} {'-'*12} {'-'*10}")

    def row(name, b, r):
        delta = r - b
        sign = "+" if delta >= 0 else ""
        return f"  {name:<18} {b:>12.4f} {r:>12.4f} {sign}{delta:>9.4f}"

    lines.append(row("MRR",        report.base_mrr,        report.rerank_mrr))
    lines.append(row("NDCG@K",     report.base_ndcg_at_k,  report.rerank_ndcg_at_k))
    lines.append(row("Hit Rate@K", report.base_hit_rate_at_k, report.rerank_hit_rate_at_k))
    lines.append(row("Precision@K",report.base_precision_at_k, report.rerank_precision_at_k))
    lines.append(row("Recall@K",   report.base_recall_at_k, report.rerank_recall_at_k))

    lines.append("")
    lines.append("  Per-query NDCG delta (top 10 by |delta|):")
    sorted_q = sorted(
        report.per_query, key=lambda q: abs(q.get("delta_ndcg", 0)), reverse=True,
    )[:10]
    for q in sorted_q:
        d = q.get("delta_ndcg", 0)
        sign = "+" if d >= 0 else ""
        lines.append(
            f"    {q['query'][:50]:<50} "
            f"base={q['baseline']['ndcg']:.3f} → "
            f"rerank={q['rerank']['ndcg']:.3f}  ({sign}{d:.3f})"
        )

    text = "\n".join(lines)
    print(text)
    return text
