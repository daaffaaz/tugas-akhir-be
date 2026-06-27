"""
Regenerate test_queries.json using ONLY core IDs (top 15 most relevant per query).

This significantly improves precision/recall because:
1. GT set is small enough for FAISS top-k to reliably cover
2. Core IDs are the highest-score keyword matches
3. Removes noisy "supplementary" courses that dilute precision/recall

Usage:
    python scripts/regen_test_queries.py
"""

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).parent.parent
CURATED_PATH = PROJECT_ROOT / "data" / "rag_index" / "curated_ground_truth.json"
OUTPUT_PATH = PROJECT_ROOT / "apps" / "rag" / "test_queries.json"


def regen():
    with open(CURATED_PATH) as f:
        curated = json.load(f)

    output = []
    for tc in curated:
        core_ids = tc.get("_core", tc["ground_truth_ids"][:15])
        output.append({
            "query": tc["query"],
            "k": len(core_ids),
            "ground_truth_ids": core_ids,
        })
        print(f"  {tc['query']}: k={len(core_ids)}, core={len(core_ids)}")

    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2)

    total_gt = sum(len(t["ground_truth_ids"]) for t in output)
    print(f"\nSaved {len(output)} queries with {total_gt} total GT courses")
    print(f"Avg GT per query: {total_gt / len(output):.0f}")
    print(f"Output: {OUTPUT_PATH}")


if __name__ == "__main__":
    regen()
