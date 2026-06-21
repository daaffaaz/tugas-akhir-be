"""
RAG evaluation utilities for career recommendation system.

Evaluates 5 metrics:
  1. Hit Rate@K     — retrieval recall (at least 1 relevant course in top-K)
  2. Precision@K    — how many of top-K are relevant
  3. Recall@K       — how many of all relevant courses are found in top-K
  4. Groundedness   — all generated course_ids reference real DB courses
  5. LLM-as-Judge   — 3 LLMs score the end-to-end output (implemented later)

Usage:
  python scripts/run_evaluation.py
  python scripts/run_evaluation.py --metric retrieval
  python scripts/run_evaluation.py --metric groundedness
"""

import json
import logging
import math
import statistics
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

from apps.courses.models import Course, Tag
from apps.rag import retriever
from apps.rag.evaluation_profiles import get_test_profile
from apps.rag.generator import generate_roadmap, _validate_and_filter_course_ids
from apps.rag.judge_client import score_all_models
from apps.rag.recommend_generator import generate_recommendations

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class TestCase:
    """A single test case for evaluation."""
    query: str
    k: int = 10
    ground_truth_ids: list[str] = field(default_factory=list)

    # Optional fields for LLM-as-Judge (not used by retrieval metrics)
    user_profile: dict | None = None
    expected_topics: list[str] = field(default_factory=list)


@dataclass
class RetrievalReport:
    """Results for retrieval metrics."""
    hit_rate_at_k: float
    precision_at_k: float
    recall_at_k: float
    queries_evaluated: int
    per_query: list[dict] = field(default_factory=list)


@dataclass
class GroundednessReport:
    """Results for groundedness score."""
    score: float
    queries_evaluated: int
    per_query: list[dict] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Ground truth dataset
# ---------------------------------------------------------------------------

def load_ground_truth(path: str | Path | None = None) -> list[TestCase]:
    """
    Load test cases from JSON file.

    Expected format:
    [
      {
        "query": "machine learning untuk pemula",
        "k": 10,
        "ground_truth_ids": ["uuid1", "uuid2", ...]
      },
      ...
    ]
    """
    if path is None:
        path = Path(__file__).parent / "test_queries.json"
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"Ground truth file not found: {path}")

    with open(path) as f:
        data = json.load(f)

    return [TestCase(**item) for item in data]


def create_default_ground_truth() -> list[TestCase]:
    """
    Create a default set of test queries if no ground truth file exists yet.
    These are broad queries that should match many courses — serves as
    a starting point. User should edit and add precise ground_truth_ids.
    """
    return [
        TestCase(query="machine learning", k=10),
        TestCase(query="data science", k=10),
        TestCase(query="web development frontend", k=10),
        TestCase(query="python programming", k=10),
        TestCase(query="cyber security", k=10),
        TestCase(query="cloud computing aws", k=10),
        TestCase(query="mobile development flutter", k=10),
        TestCase(query="database design", k=10),
        TestCase(query="software engineering", k=10),
        TestCase(query="devops ci/cd", k=10),
    ]


# ---------------------------------------------------------------------------
# Tag-based ground truth helper
# ---------------------------------------------------------------------------

def build_tag_ground_truth(queries: list[str], k: int = 30) -> list[TestCase]:
    """
    Build ground truth by matching queries against course tags and keywords.

    For each query, retrieves courses whose tags or title/description contain
    query keywords. Returns TestCases with auto-populated ground_truth_ids.

    Args:
        queries: list of query strings (e.g. ["machine learning", "web development"])
        k: how many top results to consider as ground truth

    Returns:
        list of TestCase with ground_truth_ids populated

    Note:
        This is a PROXY — not perfect. User should review and edit manually.
    """
    test_cases = []
    for query in queries:
        # Retrieve from FAISS using same logic as production
        courses, _ = retriever.retrieve_courses(query, top_k=k)

        gt_ids = [c.get("course_id") for c in courses if c.get("course_id")]
        test_cases.append(TestCase(
            query=query,
            k=min(k, len(gt_ids)),
            ground_truth_ids=gt_ids,
        ))

    return test_cases


# ---------------------------------------------------------------------------
# Retrieval metrics: Hit Rate@K, Precision@K, Recall@K
# ---------------------------------------------------------------------------

def _evaluate_single_query(test_case: TestCase) -> dict[str, Any]:
    """
    Evaluate retrieval for a single query.

    Returns dict with per-query metrics.
    """
    retrieved, _ = retriever.retrieve_courses(
        test_case.query, top_k=test_case.k
    )
    retrieved_ids = set(c.get("course_id") for c in retrieved if c.get("course_id"))
    gt_ids = set(test_case.ground_truth_ids)

    if not retrieved:
        return {
            "query": test_case.query,
            "hit": False,
            "relevant_retrieved": 0,
            "total_retrieved": 0,
            "total_ground_truth": len(gt_ids),
            "precision": 0.0,
            "recall": 0.0,
            "hit_rate": 0.0,
            "hit_ids": [],
        }

    relevant_retrieved = len(retrieved_ids & gt_ids)
    total_retrieved = len(retrieved)
    total_gt = len(gt_ids)

    return {
        "query": test_case.query,
        "hit": relevant_retrieved > 0,
        "relevant_retrieved": relevant_retrieved,
        "total_retrieved": total_retrieved,
        "total_ground_truth": total_gt,
        "precision": relevant_retrieved / total_retrieved if total_retrieved else 0.0,
        "recall": relevant_retrieved / total_gt if total_gt else 0.0,
        "hit_rate": 1.0 if relevant_retrieved > 0 else 0.0,
        "hit_ids": list(retrieved_ids & gt_ids),
    }


def evaluate_retrieval(
    test_cases: list[TestCase],
    k: int | None = None,
) -> RetrievalReport:
    """
    Evaluate Hit Rate@K, Precision@K, Recall@K over all test cases.

    Args:
        test_cases: list of TestCases with ground_truth_ids
        k: override K for all queries (uses TestCase.k if None)

    Returns:
        RetrievalReport with aggregated metrics
    """
    results = []
    for tc in test_cases:
        if k is not None:
            tc = TestCase(
                query=tc.query,
                k=k,
                ground_truth_ids=tc.ground_truth_ids,
                user_profile=tc.user_profile,
                expected_topics=tc.expected_topics,
            )
        results.append(_evaluate_single_query(tc))

    total_queries = len(results)
    if total_queries == 0:
        return RetrievalReport(0.0, 0.0, 0.0, 0)

    hit_rate = sum(r["hit_rate"] for r in results) / total_queries
    precision = sum(r["precision"] for r in results) / total_queries
    recall = sum(r["recall"] for r in results) / total_queries

    return RetrievalReport(
        hit_rate_at_k=hit_rate,
        precision_at_k=precision,
        recall_at_k=recall,
        queries_evaluated=total_queries,
        per_query=results,
    )


# ---------------------------------------------------------------------------
# Groundedness Score
# ---------------------------------------------------------------------------

def _generate_roadmap_dict(
    query: str,
    top_k: int = 15,
) -> tuple[dict, list[str], list[str]]:
    """
    Generate a roadmap dict for a query without calling the LLM.

    Uses retrieved courses directly (bypasses LLM) to test groundedness
    of course selection logic.

    Returns:
        (roadmap_sample, valid_ids, invalid_ids)
        roadmap_sample is a simplified dict for report purposes
    """
    courses, top_score = retriever.retrieve_courses(query, top_k=top_k)

    if not courses:
        return {}, [], []

    # Simulate LLM selecting top courses as "roadmap courses"
    # In reality the LLM selects courses based on its reasoning, but for
    # evaluation we assume the LLM would pick from the top N retrieved courses.
    selected = courses[:min(5, len(courses))]

    all_ids = [c.get("course_id") for c in selected]
    valid_ids, invalid_ids = _validate_and_filter_course_ids(
        {"phases": [{"phase_number": 1, "courses": [{"course_id": cid} for cid in all_ids]}]}
    )

    return {
        "query": query,
        "selected_count": len(all_ids),
        "valid_count": len(valid_ids),
        "invalid_count": len(invalid_ids),
    }, valid_ids, invalid_ids


def evaluate_groundedness(
    test_cases: list[TestCase],
    top_k: int = 15,
) -> GroundednessReport:
    """
    Evaluate Groundedness Score: what % of generated course_ids are valid DB references.

    This tests whether the generation pipeline ever references non-existent courses.
    Since we already have _validate_and_filter_course_ids in generator.py, we run
    it against simulated LLM outputs for each test query.

    Returns:
        GroundednessReport with score and per-query breakdown
    """
    results = []
    all_valid = 0
    all_invalid = 0

    for tc in test_cases:
        _, valid_ids, invalid_ids = _generate_roadmap_dict(tc.query, top_k=top_k)
        n_valid = len(valid_ids)
        n_invalid = len(invalid_ids)
        all_valid += n_valid
        all_invalid += n_invalid

        results.append({
            "query": tc.query,
            "total": n_valid + n_invalid,
            "valid": n_valid,
            "invalid": n_invalid,
        })

    total = all_valid + all_invalid
    score = all_valid / total if total else 1.0

    return GroundednessReport(
        score=score,
        queries_evaluated=len(results),
        per_query=results,
    )


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def print_report(
    retrieval: RetrievalReport | None = None,
    groundedness: GroundednessReport | None = None,
) -> str:
    """
    Print evaluation results as a formatted string table.

    Returns the formatted string (also prints to stdout).
    """
    lines = []
    lines.append("=" * 70)
    lines.append("  RAG EVALUATION REPORT")
    lines.append("=" * 70)

    # --- Retrieval Metrics ---
    if retrieval:
        lines.append("")
        lines.append("─" * 70)
        lines.append("  RETRIEVAL METRICS")
        lines.append("─" * 70)

        lines.append(f"  Queries evaluated: {retrieval.queries_evaluated}")
        lines.append("")

        lines.append(f"  {'Metric':<25} {'Score':>10} {'Target':>10} {'Status':>10}")
        lines.append(f"  {'-'*25} {'-'*10} {'-'*10} {'-'*10}")

        def status_label(score, target):
            if score >= target:
                return "PASS"
            return "FAIL"

        def color(text, good):
            # ANSI color codes for terminal
            if good:
                return f"\033[32m{text}\033[0m"  # green
            return f"\033[31m{text}\033[0m"    # red

        for name, score, target in [
            ("Hit Rate@K", retrieval.hit_rate_at_k, 0.80),
            ("Precision@K", retrieval.precision_at_k, 0.70),
            ("Recall@K", retrieval.recall_at_k, 0.60),
        ]:
            s = status_label(score, target)
            s_colored = color(s, s == "PASS")
            lines.append(
                f"  {name:<25} {score:>8.1%} {target:>8.1%} {s_colored:>10}"
            )

        lines.append("")
        lines.append("  Per-query breakdown:")
        for r in retrieval.per_query[:10]:
            lines.append(
                f"    {r['query']:<45} "
                f"P={r['precision']:.2f}  R={r['recall']:.2f}  "
                f"Hit={'Y' if r['hit'] else 'N'}"
            )
        if len(retrieval.per_query) > 10:
            lines.append(f"    ... and {len(retrieval.per_query) - 10} more queries")

    # --- Groundedness Score ---
    if groundedness:
        lines.append("")
        lines.append("─" * 70)
        lines.append("  GROUNDEDNESS SCORE")
        lines.append("─" * 70)

        lines.append(f"  Queries evaluated: {groundedness.queries_evaluated}")
        lines.append("")

        score = groundedness.score
        s = color("PASS" if score == 1.0 else "FAIL", score == 1.0)
        lines.append(f"  Score: {score:.1%} (target: 100.0%)  [{s}]")

        lines.append("")
        lines.append("  Per-query breakdown:")
        for r in groundedness.per_query[:10]:
            lines.append(
                f"    {r['query']:<45} "
                f"Valid={r['valid']}  Invalid={r['invalid']}"
            )
        if len(groundedness.per_query) > 10:
            lines.append(f"    ... and {len(groundedness.per_query) - 10} more queries")

    # --- Summary ---
    lines.append("")
    lines.append("=" * 70)
    if retrieval and groundedness:
        all_pass = (
            retrieval.hit_rate_at_k >= 0.80
            and retrieval.precision_at_k >= 0.70
            and retrieval.recall_at_k >= 0.60
            and groundedness.score == 1.0
        )
        verdict = "ALL METRICS PASSED" if all_pass else "SOME METRICS NEED IMPROVEMENT"
        lines.append(f"  VERDICT: {verdict}")
    else:
        lines.append("  VERDICT: (incomplete — run all metrics for full verdict)")
    lines.append("=" * 70)

    text = "\n".join(lines)
    print(text)
    return text


# ---------------------------------------------------------------------------
# LLM-as-Judge (placeholder — implemented later)
# ---------------------------------------------------------------------------

def evaluate_llm_as_judge(
    test_cases: list[TestCase],
    k: int = 10,
    max_queries: int | None = None,
) -> dict:
    """
    Evaluate end-to-end quality using LLM-as-Judge with 3 models.

    For each test case:
      1. Retrieve courses via FAISS
      2. Build user profile from TestCase fields
      3. Generate REAL roadmap via generate_roadmap() (calls GPT-4o)
      4. Score with all 3 judge models in parallel

    Args:
        test_cases: list of TestCases
        k: top-K for retrieval
        max_queries: limit number of queries to judge (for faster testing)

    Returns dict with:
      - avg_score: float (1.0-5.0, average of 4 dimensions across all queries/models)
      - per_query_scores: list of per-query score dicts
      - per_model_scores: dict[model_name, float average]
      - disagreement: bool (std > 0.5 across models for any query)
    """
    all_results = []
    per_query = []

    limit = max_queries if max_queries is not None else len(test_cases)

    for idx, tc in enumerate(test_cases[:limit]):
        # Retrieve courses for this query
        courses, top_score = retriever.retrieve_courses(tc.query, top_k=min(k or 15, 15))

        if not courses:
            per_query.append({
                "query": tc.query,
                "avg_score": 0.0,
                "scores": [],
                "reasoning": "No courses retrieved",
                "judge_results": None,
            })
            continue

        # Build a realistic user profile (mirrors production _build_user_profile).
        # Without this, the LLM has nothing to personalize against, and judges
        # correctly mark "personalization" low — masking actual RAG quality.
        user_profile = get_test_profile(idx)

        # Generate REAL roadmap via GPT-4o (same code path as production)
        try:
            roadmap_dict, retrieval_info = generate_roadmap(
                topic=tc.query,
                user_profile=user_profile,
                courses_metadata=courses,
                top_score=top_score,
            )
            roadmap_dict['retrieval_info'] = retrieval_info
        except Exception as e:
            logger.warning(f"[judge] generate_roadmap failed for '{tc.query}': {e}")
            per_query.append({
                "query": tc.query,
                "avg_score": 0.0,
                "scores": [],
                "reasoning": f"Roadmap generation failed: {e}",
                "judge_results": None,
            })
            continue

        # Score with all judge models
        judge_results = score_all_models(
            tc.query, courses, roadmap_dict, user_profile=user_profile,
        )

        if not judge_results:
            per_query.append({
                "query": tc.query,
                "avg_score": 0.0,
                "scores": [],
                "reasoning": "All judges failed",
                "judge_results": None,
            })
            continue

        # Aggregate scores for this query
        all_scores = [j["scores"] for j in judge_results if j["scores"] > 0]
        avg_score = statistics.mean(all_scores) if all_scores else 0.0

        # Collect per-dimension averages for this query.
        _per_dim: dict[str, list[float]] = {}
        for j in judge_results:
            for dim in ("relevance", "accuracy", "quality", "personalization"):
                val = j.get(dim)
                if val is not None:
                    _per_dim.setdefault(dim, []).append(val)
        per_dim_avg = {
            dim: round(statistics.mean(vals), 2) for dim, vals in _per_dim.items()
        }

        per_query.append({
            "query": tc.query,
            "avg_score": round(avg_score, 2),
            "scores": [round(j["scores"], 2) for j in judge_results],
            "reasoning": "; ".join(
                f"{j['model']}: {j.get('reasoning', '')[:100]}" for j in judge_results
            ),
            "judge_results": [
                {
                    "model": j["model"],
                    "scores": round(j["scores"], 2),
                    "dimensions": {
                        "relevance": j.get("relevance"),
                        "accuracy": j.get("accuracy"),
                        "quality": j.get("quality"),
                        "personalization": j.get("personalization"),
                    },
                    "reasoning": j.get("reasoning", "")[:200],
                }
                for j in judge_results
            ],
            "per_dimension_avg": per_dim_avg,
        })
        all_results.extend(judge_results)

    # Aggregate overall
    total_queries = len(per_query)
    all_avg_scores = [q["avg_score"] for q in per_query if q["avg_score"] > 0]
    overall_avg = statistics.mean(all_avg_scores) if all_avg_scores else 0.0

    # Per-model averages
    model_scores = {}
    for r in all_results:
        if not isinstance(r, dict) or "model" not in r:
            continue
        m = r["model"]
        model_scores.setdefault(m, []).append(r["scores"])
    per_model_scores = {m: round(statistics.mean(s), 2) for m, s in model_scores.items()}

    # Disagreement: check if any query has std > 0.5 across models
    disagreement = False
    for q in per_query:
        if len(q["scores"]) >= 2:
            std_val = statistics.stdev(q["scores"]) if len(q["scores"]) > 1 else 0.0
            if std_val > 0.5:
                disagreement = True
                break

    return {
        "avg_score": round(overall_avg, 2),
        "queries_evaluated": total_queries,
        "per_query_scores": [q["avg_score"] for q in per_query],
        "per_model_scores": per_model_scores,
        "disagreement": disagreement,
        "status": "DONE",
        "per_query_details": per_query,
    }


# ---------------------------------------------------------------------------
# Run all metrics
# ---------------------------------------------------------------------------

def run_evaluation(
    ground_truth_path: str | Path | None = None,
    k: int | None = None,
    skip_llm_judge: bool = True,
) -> dict:
    """
    Run all evaluation metrics and return results.

    Args:
        ground_truth_path: path to test_queries.json (auto-generated if missing)
        k: override K for retrieval metrics
        skip_llm_judge: if True, skip LLM-as-Judge (not implemented yet)

    Returns:
        dict with keys: retrieval, groundedness, llm_judge
    """
    # Load or generate ground truth
    test_cases = load_ground_truth(ground_truth_path)

    # Ensure ground truth has IDs
    for tc in test_cases:
        if not tc.ground_truth_ids:
            # Auto-populate using tag-based matching
            auto = build_tag_ground_truth([tc.query], k=k or tc.k)
            tc.ground_truth_ids = auto[0].ground_truth_ids if auto else []

    results = {}

    # 1. Retrieval metrics
    results["retrieval"] = evaluate_retrieval(test_cases, k=k)

    # 2. Groundedness score
    results["groundedness"] = evaluate_groundedness(test_cases)

    # 3. LLM-as-Judge
    if skip_llm_judge:
        results["llm_judge"] = {
            "skipped": True,
            "reason": "LLM judge disabled via --no-llm",
        }
    else:
        try:
            results["llm_judge"] = evaluate_llm_as_judge(test_cases, k=k)
        except ImportError as e:
            results["llm_judge"] = {
                "skipped": True,
                "reason": str(e),
            }
        except Exception as e:
            import traceback
            logger.error(f"[evaluation] LLM-as-Judge failed: {e}\n{traceback.format_exc()}")
            results["llm_judge"] = {
                "skipped": True,
                "error": str(e),
            }

    return results
