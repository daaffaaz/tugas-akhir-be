#!/usr/bin/env python
"""
Run RAG evaluation for the career recommendation system.

Usage:
    python scripts/run_evaluation.py [--ground_truth PATH] [--k N] [--llm] [--no-llm]

Examples:
    python scripts/run_evaluation.py                  # Full eval (all metrics + LLM judge)
    python scripts/run_evaluation.py --no-llm          # Skip LLM judge (fast)
    python scripts/run_evaluation.py --k 5             # Use K=5 for retrieval metrics
    python scripts/run_evaluation.py --ground_truth my_tests.json  # Custom ground truth
"""

import argparse
import json
import sys
from pathlib import Path

# Ensure the project root is on sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Setup Django settings before importing any Django models
import django
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()

from apps.rag.evaluation import run_evaluation, print_report


def parse_args():
    parser = argparse.ArgumentParser(description="Run RAG evaluation metrics")
    parser.add_argument(
        "--ground_truth", type=str, default=None,
        help="Path to ground truth JSON file (default: auto-generate apps/rag/test_queries.json)",
    )
    parser.add_argument(
        "--k", type=int, default=None,
        help="Override K for retrieval metrics (default: per-test-case value or 10)",
    )
    parser.add_argument(
        "--llm", action="store_true", default=None,
        help="Include LLM-as-Judge (default: include if OpenAI key is set)",
    )
    parser.add_argument(
        "--no-llm", action="store_true", default=None,
        help="Skip LLM-as-Judge evaluation",
    )
    return parser.parse_args()


def print_section(title):
    print(f"\n{'─' * 70}")
    print(f"  {title}")
    print(f"{'─' * 70}")


def print_bar(label, score):
    status = "PASS" if score >= 0.8 else "FAIL"
    color_code = "\033[32m" if score >= 0.8 else "\033[31m"
    reset = "\033[0m"
    bar_len = int(score * 30)
    bar = "█" * bar_len + "░" * (30 - bar_len)
    print(f"  [{bar}] {label}")
    print(f"  Status: {color_code}{status}{reset}")


def print_error(msg):
    print(f"\033[31m  ERROR: {msg}\033[0m")


def main():
    args = parse_args()

    print("\n" + "=" * 70)
    print("  RAG EVALUATION PIPELINE")
    print("=" * 70)
    print(f"  Ground truth: {args.ground_truth or 'auto-generate'}")
    print(f"  K (retrieval): {args.k or 'per-test-case'}")

    try:
        # Determine LLM flag
        if args.llm:
            skip_llm = False
        elif args.no_llm:
            skip_llm = True
        else:
            import os
            skip_llm = not bool(os.environ.get("OPENROUTER_API_KEY"))

        result = run_evaluation(
            ground_truth_path=args.ground_truth,
            k=args.k,
            skip_llm_judge=skip_llm,
        )
    except Exception as e:
        print_error(f"Evaluation failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # --- Print retrieval results ---
    retrieval = result.get("retrieval")
    if retrieval:
        print_section("RETRIEVAL METRICS")
        print(f"  Queries evaluated: {retrieval.queries_evaluated}")
        print()

        for name, score, target in [
            ("Hit Rate@K", retrieval.hit_rate_at_k, 0.80),
            ("Precision@K", retrieval.precision_at_k, 0.70),
            ("Recall@K", retrieval.recall_at_k, 0.90),
            ("MRR@10", retrieval.mrr_at_10, 0.80),
            ("NDCG@10", retrieval.ndcg_at_10, 0.75),
        ]:
            print_bar(f"{name}: {score:.1%} (target: {target:.1%})", score)

        print()
        print("  Per-query breakdown:")
        for r in retrieval.per_query[:10]:
            print(
                f"    {r['query']:<45} "
                f"P={r['precision']:.2f}  R={r['recall']:.2f}  "
                f"MRR={r['mrr']:.2f}  NDCG={r['ndcg']:.2f}  "
                f"Hit={'Y' if r['hit'] else 'N'}"
            )
        if len(retrieval.per_query) > 10:
            print(f"    ... and {len(retrieval.per_query) - 10} more queries")

    # --- Print groundedness results ---
    groundedness = result.get("groundedness")
    if groundedness:
        print_section("GROUNDEDNESS")
        print(f"  Queries evaluated: {groundedness.queries_evaluated}")
        print()
        score = groundedness.score
        status = "PASS" if score == 1.0 else "FAIL"
        color_code = "\033[32m" if score == 1.0 else "\033[31m"
        reset = "\033[0m"
        print(f"  Score: {score:.1%} (target: 100.0%)")
        print(f"  Status: {color_code}{status}{reset}")

        print()
        print("  Per-query breakdown:")
        for r in groundedness.per_query[:10]:
            print(
                f"    {r['query']:<45} "
                f"Valid={r['valid']}  Invalid={r['invalid']}"
            )
        if len(groundedness.per_query) > 10:
            print(f"    ... and {len(groundedness.per_query) - 10} more queries")

    # --- Print LLM-as-Judge results ---
    llm_judge = result.get("llm_judge")
    if llm_judge:
        print_section("LLM-AS-JUDGE")
        is_skipped = llm_judge.get("skipped") or llm_judge.get("status") == "NOT_IMPLEMENTED"
        if is_skipped:
            print(f"  Skipped: {llm_judge.get('reason', llm_judge.get('error', llm_judge.get('status')))}")
        else:
            avg = llm_judge.get("avg_score", 0)
            print(f"  Avg Score: {avg:.2f}/5.00")

    # --- Save summary ---
    output_file = project_root / "evaluation_results.json"
    # Serialize to JSON (handle dataclass objects)
    serializable = {
        "retrieval": {
            "hit_rate_at_k": retrieval.hit_rate_at_k if retrieval else None,
            "precision_at_k": retrieval.precision_at_k if retrieval else None,
            "recall_at_k": retrieval.recall_at_k if retrieval else None,
            "mrr_at_10": retrieval.mrr_at_10 if retrieval else None,
            "ndcg_at_10": retrieval.ndcg_at_10 if retrieval else None,
            "queries_evaluated": retrieval.queries_evaluated if retrieval else None,
            "per_query": retrieval.per_query if retrieval else [],
        },
        "groundedness": {
            "score": groundedness.score if groundedness else None,
            "queries_evaluated": groundedness.queries_evaluated if groundedness else None,
            "per_query": groundedness.per_query if groundedness else [],
        },
        "llm_judge": result.get("llm_judge"),
    }
    with open(output_file, "w") as f:
        json.dump(serializable, f, indent=2, default=str)
    print(f"\n  Detailed results saved to: {output_file}")

    # --- Exit code ---
    if retrieval:
        below_target = (
            retrieval.hit_rate_at_k < 0.80
            or retrieval.precision_at_k < 0.70
            or retrieval.recall_at_k < 0.90
            or retrieval.mrr_at_10 < 0.80
            or retrieval.ndcg_at_10 < 0.75
        )
        if below_target:
            print("\n  WARNING: Some metrics are below target thresholds.")

    print_report(retrieval=retrieval, groundedness=groundedness)
    print()


if __name__ == "__main__":
    main()
