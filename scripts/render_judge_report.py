"""Render LLM-as-Judge evaluation results into a screenshot-friendly Markdown report.

Usage:
    python scripts/render_judge_report.py
Output:
    docs/BAB4_LLM_JUDGE_REPORT.md
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "evaluation_results.json"
DST = ROOT / "docs" / "BAB4_LLM_JUDGE_REPORT.md"


def short_reasoning(text: str, limit: int = 320) -> str:
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0] + "..."


def render() -> str:
    data = json.loads(SRC.read_text())
    judge = data["llm_judge"]
    retrieval = data["retrieval"]
    grounded = data["groundedness"]

    pq_scores = judge["per_query_scores"]
    pq_retrieval = retrieval["per_query"]
    pq_details = judge["per_query_details"]

    ranked = sorted(
        range(len(pq_scores)),
        key=lambda i: -pq_scores[i],
    )
    best_idx = ranked[0]
    worst_idx = ranked[-1]

    lines = []
    lines.append("# LLM-as-Judge — Hasil Evaluasi (Screenshot Pack)")
    lines.append("")
    lines.append("> File ini di-render dari `evaluation_results.json` untuk "
                 "keperluan screenshot sidang. Format vertikal-rapat agar "
                 "tidak melebar ke samping.")
    lines.append("")

    lines.append("## 1. Ringkasan Agregat")
    lines.append("")
    lines.append("| Metrik | Nilai |")
    lines.append("|---|---:|")
    lines.append(f"| Hit Rate@K | **{retrieval['hit_rate_at_k']:.2f}** |")
    lines.append(f"| Precision@K | **{retrieval['precision_at_k']:.4f}** |")
    lines.append(f"| Recall@K | **{retrieval['recall_at_k']:.4f}** |")
    lines.append(f"| Groundedness | **{grounded['score']:.3f}** |")
    lines.append(f"| **LLM Judge Avg** | **{judge['avg_score']:.2f} / 5.00** |")
    lines.append(f"| Query dievaluasi | {judge['queries_evaluated']} |")
    lines.append("")

    lines.append("## 2. Skor per-Model Judge")
    lines.append("")
    lines.append("| Model | Avg Score | Karakteristik |")
    lines.append("|---|---:|---|")
    char = {
        "anthropic/claude-3-haiku": "Permisif (sering skor 5)",
        "qwen/qwen3-235b-a22b-2507": "Konsisten tinggi, reasoning detail",
        "deepseek/deepseek-v4-flash": "Kritis, banyak skor 3-4",
    }
    for m, s in sorted(judge["per_model_scores"].items(), key=lambda x: -x[1]):
        lines.append(f"| `{m}` | **{s:.2f}** | {char.get(m, '-')} |")
    lines.append("")

    lines.append("## 3. Skor per-Query (15 query, diurutkan)")
    lines.append("")
    lines.append("| # | Query | Judge Avg | Hit | Precision | Recall |")
    lines.append("|---:|---|---:|:---:|---:|---:|")
    for rank, i in enumerate(ranked, 1):
        q = pq_retrieval[i]
        name = q.get("query", "?")
        score = pq_scores[i]
        if i == best_idx:
            name = f"**{name}** [Best]"
        elif i == worst_idx:
            name = f"**{name}** [Worst]"
        lines.append(
            f"| {rank} | {name} | **{score:.2f}** | "
            f"{'Ya' if q.get('hit') else 'Tidak'} | "
            f"{q.get('precision', 0):.2f} | {q.get('recall', 0):.2f} |"
        )
    lines.append("")

    lines.append("## 4. Detail Query Terbaik")
    lines.append("")
    best = pq_details[best_idx]
    best_name = best["query"]
    lines.append(f"### 4.1 `{best_name}` (Best) — Skor **{best['avg_score']:.2f}**")
    lines.append("")
    lines.append("**Skor per-model:**")
    lines.append("")
    for jr in best["judge_results"]:
        model = jr["model"]
        per_dim = jr.get("dimensions", {})
        dim_str = ", ".join(f"{k}={v}" for k, v in per_dim.items())
        lines.append(f"- `{model}`: {dim_str}")
    lines.append("")

    lines.append("**Per-dimension average:**")
    lines.append("")
    lines.append("| Dimensi | Skor |")
    lines.append("|---|---:|")
    for dim, val in best["per_dimension_avg"].items():
        lines.append(f"| {dim.capitalize()} | {val:.2f} |")
    lines.append("")

    lines.append("**Reasoning (3 model):**")
    lines.append("")
    for jr in best["judge_results"]:
        lines.append(f"> **{jr['model']}**")
        lines.append(f">")
        lines.append(f"> {short_reasoning(jr['reasoning'])}")
        lines.append("")

    lines.append("## 5. Detail Query Terburuk")
    lines.append("")
    worst = pq_details[worst_idx]
    worst_name = worst["query"]
    lines.append(f"### 5.1 `{worst_name}` (Worst) — Skor **{worst['avg_score']:.2f}**")
    lines.append("")
    lines.append("**Skor per-model:**")
    lines.append("")
    for jr in worst["judge_results"]:
        model = jr["model"]
        per_dim = jr.get("dimensions", {})
        dim_str = ", ".join(f"{k}={v}" for k, v in per_dim.items())
        lines.append(f"- `{model}`: {dim_str}")
    lines.append("")

    lines.append("**Per-dimension average:**")
    lines.append("")
    lines.append("| Dimensi | Skor |")
    lines.append("|---|---:|")
    for dim, val in worst["per_dimension_avg"].items():
        lines.append(f"| {dim.capitalize()} | {val:.2f} |")
    lines.append("")

    lines.append("**Reasoning (3 model):**")
    lines.append("")
    for jr in worst["judge_results"]:
        lines.append(f"> **{jr['model']}**")
        lines.append(f">")
        lines.append(f"> {short_reasoning(jr['reasoning'])}")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("*Generated by `scripts/render_judge_report.py` from "
                 "`evaluation_results.json`.*")
    lines.append("")

    return "\n".join(lines)


def main():
    DST.write_text(render())
    print(f"Wrote {DST.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
