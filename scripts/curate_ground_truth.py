"""
Offline ground truth curation script.

Works without a running database — loads course metadata directly from the
FAISS index pickle file and uses keyword matching to suggest core/supplementary
sets for each query in test_queries.json.

Usage:
    python scripts/curate_ground_truth.py
"""

import json
import pickle
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
TEST_QUERIES_PATH = PROJECT_ROOT / "apps/rag/test_queries.json"
INDEX_PATH = PROJECT_ROOT / "data" / "rag_index" / "faiss_index.pkl"
GROUND_TRUTH_PATH = PROJECT_ROOT / "data" / "rag_index" / "ground_truth.json"

# Topic keywords for core vs supplementary classification
TOPIC_KEYWORDS = {
    "web development": {
        "core": ["html", "css", "javascript", "frontend", "web development", "web dev", "responsive design"],
        "supplementary": ["react", "bootstrap", "tailwind", "html and css", "next.js"],
    },
    "programming languages": {
        "core": ["python", "java", "javascript", "c++", "php", "ruby", "go language", "rust"],
        "supplementary": ["beginner programming", "coding fundamentals", "algorithm", "data structure"],
    },
    "data science": {
        "core": ["data science", "machine learning", "statistics for data", "python for data"],
        "supplementary": ["big data", "data visualization", "analytics", "pandas"],
    },
    "python": {
        "core": ["python", "pycharm", "python programming", "automate the boring stuff"],
        "supplementary": ["django", "flask", "python automation", "scripting"],
    },
    "model training": {
        "core": ["model training", "fine tuning", "fine-tuning", "model"],
        "supplementary": ["neural network", "deep learning", "tensorflow", "pytorch", "training"],
    },
    "machine learning": {
        "core": ["machine learning", "scikit learn", "regression", "classification", "ml"],
        "supplementary": ["artificial intelligence", "neural network", "deep learning", "tensorflow", "predictive model"],
    },
    "software testing": {
        "core": ["testing", "automated testing", "selenium", "playwright", "qa", "quality assurance"],
        "supplementary": ["ci/cd", "continuous integration", "devops", "cypress"],
    },
    "data analysis": {
        "core": ["data analysis", "sql for data", "excel data", "spreadsheet"],
        "supplementary": ["data visualization", "tableau", "power bi", "sql"],
    },
    "sql": {
        "core": ["sql", "mysql", "postgresql", "database sql", "learn sql"],
        "supplementary": ["database design", "relational database", "query"],
    },
    "artificial intelligence": {
        "core": ["artificial intelligence", "ai", "deep learning", "neural network"],
        "supplementary": ["machine learning", "computer vision", "nlp", "chatbot", "generative ai"],
    },
    "large language modeling": {
        "core": ["llm", "large language model", "transformer", "prompt engineering"],
        "supplementary": ["natural language processing", "nlp", "generative ai", "language model"],
    },
    "javascript": {
        "core": ["javascript", "node.js", "react", "angular", "vue", "express.js"],
        "supplementary": ["typescript", "fullstack", "web development", "frontend"],
    },
    "ai literacy": {
        "core": ["ai literacy", "ai fundamentals", "introduction to ai", "what is ai", "ai for everyone"],
        "supplementary": ["machine learning basics", "ai ethics", "chatbot", "generative ai"],
    },
    "cloud aws": {
        "core": ["aws", "amazon web services", "cloud computing aws"],
        "supplementary": ["azure", "google cloud", "cloud architecture", "cloud computing"],
    },
    "mobile app": {
        "core": ["mobile", "flutter", "android", "ios", "react native", "mobile app development"],
        "supplementary": ["cross-platform", "swift", "kotlin", "app"],
    },
}


def load_metadata() -> list[dict]:
    """Load course metadata from the FAISS index pickle."""
    if not INDEX_PATH.exists():
        print(f"ERROR: Index file not found at {INDEX_PATH}")
        print("Please run: python manage.py build_faiss_index first")
        return []

    with open(INDEX_PATH, "rb") as f:
        data = pickle.load(f)

    if "metadata" in data:
        return data["metadata"]

    print("ERROR: Pickle file has unexpected format. Keys:", list(data.keys()))
    return []


def load_test_cases() -> list[dict]:
    """Load existing test_queries.json."""
    if not TEST_QUERIES_PATH.exists():
        print(f"ERROR: {TEST_QUERIES_PATH} not found.")
        return []

    with open(TEST_QUERIES_PATH) as f:
        data = json.load(f)

    return data


def build_index_map(metadata: list[dict]) -> dict[str, dict]:
    """Map course_id → metadata dict."""
    index_map = {}
    for i, m in enumerate(metadata):
        cid = m.get("course_id") or m.get("id") or str(i)
        index_map[cid] = m
    return index_map


def score_course(course: dict, keywords: list[str]) -> int:
    """Count how many keywords match course title/description/what_you_learn."""
    text = " ".join([
        course.get("title", "").lower(),
        course.get("description", "").lower(),
        course.get("what_you_learn", "").lower(),
        course.get("tag", "").lower(),
    ]).strip()

    if not text:
        text = json.dumps(course).lower()

    score = 0
    for kw in keywords:
        if kw.lower() in text:
            score += 1
    return score


def find_matching_topics(query: str) -> list[str]:
    """Find TOPIC_KEYWORDS entries that match the query."""
    query_lower = query.lower().strip()
    matches = []

    # Exact match
    if query_lower in TOPIC_KEYWORDS:
        matches.append(query_lower)
        return matches

    # Substring match
    for topic in TOPIC_KEYWORDS:
        for word in query_lower.split():
            if word in topic or topic in word:
                matches.append(topic)
                break
        if matches:
            break

    return matches


def curate():
    """Main curation logic."""
    metadata = load_metadata()
    if not metadata:
        print("No metadata available. Cannot curate ground truth.")
        return

    index_map = build_index_map(metadata)
    print(f"Loaded {len(metadata)} courses from index.")

    test_cases = load_test_cases()
    if not test_cases:
        print("No test cases found. Exiting.")
        return

    results = []
    for tc in test_cases:
        query = tc.get("query", "")
        k = tc.get("k", 30)
        matched_ids = tc.get("ground_truth_ids", [])

        # Find matching topics
        topics = find_matching_topics(query)
        if not topics:
            print(f"  '{query}': no topic match found — keeping existing GT ({len(matched_ids)})")
            continue

        topic = topics[0]
        keywords = TOPIC_KEYWORDS[topic]["core"]

        # Score all courses
        scored = []
        for cid, course in index_map.items():
            s = score_course(course, keywords)
            if s > 0:
                scored.append((s, cid))

        scored.sort(key=lambda x: -x[0])

        # Select core (top scorers) and supplementary
        num_core = min(15, len(scored))
        num_supp = min(20, max(0, len(scored) - num_core))

        core_ids = [cid for _, cid in scored[:num_core]]
        supp_ids = [cid for _, cid in scored[num_core:num_core + num_supp]]

        # Merge with existing GT if available (keep human-reviewed IDs)
        existing_core = set(matched_ids[:20])  # first 20 are likely core
        all_ids = list(dict.fromkeys(core_ids + list(existing_core | set(supp_ids))))
        # Cap at reasonable size
        all_ids = all_ids[:min(len(all_ids), 60)]

        # Override k if needed
        new_k = max(k, len(all_ids))

        results.append({
            "query": query,
            "k": new_k,
            "ground_truth_ids": all_ids,
            "_core": core_ids[:20],
            "_supplementary": supp_ids[:15],
            "_matched_count": len(scored),
        })

        print(f"  '{query}': matched={len(scored)}, core={len(core_ids)}, supp={len(supp_ids)}, gt={len(all_ids)}, k={new_k}")

    # Sort by matched count desc
    results.sort(key=lambda x: x["_matched_count"], reverse=True)

    # Save both the full output (with annotations) and a clean version
    save_path = GROUND_TRUTH_PATH.parent / "curated_ground_truth.json"
    with open(save_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nSaved annotated results to {save_path}")

    # Clean output (strip _ annotations) for test_queries.json
    clean_output = []
    for r in results:
        clean_output.append({
            "query": r["query"],
            "k": r["k"],
            "ground_truth_ids": r["ground_truth_ids"],
        })

    # Show quick stats
    total_gt = sum(len(e["ground_truth_ids"]) for e in clean_output)
    print(f"Total ground truth courses: {total_gt}")
    print(f"Avg GT per query: {total_gt / len(clean_output):.0f}")

    # Identify potential issues
    print("\nPOTENTIAL ISSUES:")
    for r in results:
        gt_size = len(r["ground_truth_ids"])
        k = r["k"]
        if gt_size > 80:
            print(f"  ⚠ '{r['query']}': GT too large ({gt_size}). Consider narrowing to core set.")
        if gt_size == 0:
            print(f"  ✗ '{r['query']}': No GT generated. Manual review needed.")

    print("\nReview the output in 'curated_ground_truth.json', then update test_queries.json.")


if __name__ == "__main__":
    curate()
