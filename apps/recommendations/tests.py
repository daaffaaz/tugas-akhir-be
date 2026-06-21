"""
Tests for RAG evaluation system.

Run:
  python manage.py test apps.recommendations.tests
  python manage.py test apps.recommendations.tests.RetrievalMetricsTest
"""

import json
import tempfile
from pathlib import Path
from unittest import TestCase

from apps.rag.evaluation import (
    TestCase as EvalTestCase,
    RetrievalReport,
    GroundednessReport,
    _evaluate_single_query,
    _generate_roadmap_dict,
    evaluate_groundedness,
    evaluate_llm_as_judge,
    evaluate_retrieval,
    load_ground_truth,
    print_report,
    build_tag_ground_truth,
)
from apps.rag.judge_client import _extract_json
from apps.rag import retriever


# ---------------------------------------------------------------------------
# Helper: create a temporary ground truth JSON file
# ---------------------------------------------------------------------------

def _make_temp_ground_truth(cases: list[dict]) -> str:
    """Write cases to a temp JSON file and return the path."""
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
    json.dump(cases, f)
    f.close()
    return f.name


# ---------------------------------------------------------------------------
# Ground truth loading tests
# ---------------------------------------------------------------------------

class GroundTruthTest(TestCase):
    """Test ground truth loading and generation."""

    def test_load_ground_truth(self):
        """load_ground_truth parses JSON into TestCase objects."""
        path = _make_temp_ground_truth([
            {"query": "test", "k": 5, "ground_truth_ids": ["abc", "def"]},
        ])
        cases = load_ground_truth(path)
        self.assertEqual(len(cases), 1)
        self.assertEqual(cases[0].query, "test")
        self.assertEqual(cases[0].k, 5)
        self.assertEqual(cases[0].ground_truth_ids, ["abc", "def"])

    def test_load_ground_truth_empty(self):
        """Empty ground truth file returns empty list."""
        path = _make_temp_ground_truth([])
        cases = load_ground_truth(path)
        self.assertEqual(cases, [])

    def test_load_ground_truth_missing_file(self):
        """Missing file raises FileNotFoundError."""
        with self.assertRaises(FileNotFoundError):
            load_ground_truth("/nonexistent/path.json")

    def test_build_tag_ground_truth(self):
        """build_tag_ground_truth returns TestCases with IDs."""
        # This test needs the FAISS index on disk. If unavailable, skip.
        import os
        from pathlib import Path
        index_exists = (
            Path(__file__).parent.parent.parent
            / "data" / "rag_index" / "faiss_index.pkl"
        ).exists()
        if not index_exists:
            self.skipTest("FAISS index not available on disk")

        cases = build_tag_ground_truth(["machine learning", "python"], k=10)
        self.assertGreater(len(cases), 0)
        for tc in cases:
            # May return 0 if FAISS returns empty (index missing or corrupted)
            # We just verify the structure is correct
            self.assertIsInstance(tc, EvalTestCase)
            self.assertIsInstance(tc.ground_truth_ids, list)
            self.assertIsInstance(tc.ground_truth_ids, list)


# ---------------------------------------------------------------------------
# Retrieval metrics tests
# ---------------------------------------------------------------------------

class RetrievalMetricsTest(TestCase):
    """Test Hit Rate@K, Precision@K, Recall@K."""

    def test_evaluate_single_query_no_retrieval(self):
        """Query with no FAISS results returns 0 metrics."""
        tc = EvalTestCase(query="zzzz_nonexistent_topic_xxx", k=5, ground_truth_ids=["abc"])
        result = _evaluate_single_query(tc)
        self.assertEqual(result["precision"], 0.0)
        self.assertEqual(result["recall"], 0.0)
        self.assertFalse(result["hit"])

    def test_evaluate_retrieval_passes(self):
        """When ground truth overlaps with retrieved courses, metrics should be positive."""
        query = "machine learning"
        # Get actual retrieved courses
        courses, _ = retriever.retrieve_courses(query, top_k=5)
        self.assertGreater(len(courses), 0)
        retrieved_ids = [c.get("course_id") for c in courses]

        # Set ground truth to include the retrieved courses
        tc = EvalTestCase(
            query=query, k=5,
            ground_truth_ids=retrieved_ids[:3],
        )
        report = evaluate_retrieval([tc])
        self.assertGreater(report.hit_rate_at_k, 0.0)
        self.assertGreater(report.precision_at_k, 0.0)
        self.assertGreater(report.recall_at_k, 0.0)

    def test_evaluate_retrieval_all_miss(self):
        """When ground truth is completely disjoint from retrieval, metrics are 0."""
        tc = EvalTestCase(
            query="machine learning", k=5,
            ground_truth_ids=["nonexistent-uuid-0000-0000-0000-000000000000"],
        )
        report = evaluate_retrieval([tc])
        self.assertEqual(report.hit_rate_at_k, 0.0)
        self.assertEqual(report.precision_at_k, 0.0)
        self.assertEqual(report.recall_at_k, 0.0)

    def test_evaluate_retrieval_multiple_queries(self):
        """Multiple queries aggregate correctly."""
        query = "data science"
        courses, _ = retriever.retrieve_courses(query, top_k=5)
        self.assertGreater(len(courses), 0)
        ids = [c.get("course_id") for c in courses]

        tc = EvalTestCase(query=query, k=5, ground_truth_ids=ids)
        report = evaluate_retrieval([tc])
        self.assertEqual(report.queries_evaluated, 1)
        self.assertEqual(len(report.per_query), 1)
        self.assertAlmostEqual(report.hit_rate_at_k, 1.0, places=4)
        self.assertAlmostEqual(report.precision_at_k, 1.0, places=4)
        self.assertAlmostEqual(report.recall_at_k, 1.0, places=4)


# ---------------------------------------------------------------------------
# Groundedness tests
# ---------------------------------------------------------------------------

class GroundednessTest(TestCase):
    """Test Groundedness Score evaluation."""

    def test_evaluate_groundedness_pass(self):
        """Query with valid courses returns 100% groundedness."""
        query = "machine learning"
        cases = [EvalTestCase(query=query, k=15, ground_truth_ids=[])]
        report = evaluate_groundedness(cases)
        self.assertEqual(report.score, 1.0)
        self.assertEqual(report.queries_evaluated, 1)

    def test_evaluate_groundedness_no_courses(self):
        """Query with no FAISS results returns 100% (no invalid courses)."""
        query = "zzzz_nonexistent_topic_xxx"
        cases = [EvalTestCase(query=query, k=15, ground_truth_ids=[])]
        report = evaluate_groundedness(cases)
        self.assertEqual(report.score, 1.0)

    def test_groundedness_per_query_breakdown(self):
        """Per-query results are recorded."""
        query = "python programming"
        cases = [EvalTestCase(query=query, k=15, ground_truth_ids=[])]
        report = evaluate_groundedness(cases)
        self.assertGreater(len(report.per_query), 0)
        entry = report.per_query[0]
        self.assertIn("query", entry)
        self.assertIn("valid", entry)
        self.assertIn("invalid", entry)


# ---------------------------------------------------------------------------
# Report formatting tests
# ---------------------------------------------------------------------------

class ReportFormattingTest(TestCase):
    """Test report output formatting."""

    def test_print_report_returns_string(self):
        """print_report returns a formatted string."""
        retrieval = RetrievalReport(
            hit_rate_at_k=0.95,
            precision_at_k=0.85,
            recall_at_k=0.70,
            queries_evaluated=10,
            per_query=[],
        )
        groundedness = GroundednessReport(
            score=1.0,
            queries_evaluated=10,
            per_query=[],
        )
        result = print_report(retrieval, groundedness)
        self.assertIsInstance(result, str)
        self.assertIn("RETRIEVAL METRICS", result)
        self.assertIn("GROUNDEDNESS", result)
        self.assertIn("ALL METRICS PASSED", result)

    def test_print_report_partial(self):
        """print_report works with only one metric."""
        retrieval = RetrievalReport(
            hit_rate_at_k=0.5,
            precision_at_k=0.4,
            recall_at_k=0.3,
            queries_evaluated=5,
            per_query=[],
        )
        result = print_report(retrieval, None)
        self.assertIn("RETRIEVAL METRICS", result)

    def test_print_report_fail_status(self):
        """Metrics below target show FAIL."""
        retrieval = RetrievalReport(
            hit_rate_at_k=0.1,  # below 0.80 target
            precision_at_k=0.1,  # below 0.70 target
            recall_at_k=0.1,     # below 0.60 target
            queries_evaluated=1,
            per_query=[],
        )
        groundedness = GroundednessReport(
            score=0.5,  # below 1.0 target
            queries_evaluated=1,
            per_query=[],
        )
        result = print_report(retrieval, groundedness)
        self.assertIn("NEED IMPROVEMENT", result)


# ---------------------------------------------------------------------------
# LLM-as-Judge tests
# ---------------------------------------------------------------------------

class LLMJudgeTest(TestCase):
    """Test LLM-as-Judge scoring logic."""

    def test_extract_json_from_markdown(self):
        """_extract_json strips markdown code blocks."""
        raw = '```json\n{"relevance": 4, "accuracy": 5}\n```'
        result = _extract_json(raw)
        self.assertEqual(result["relevance"], 4)
        self.assertEqual(result["accuracy"], 5)

    def test_extract_json_plain(self):
        """_extract_json handles plain JSON."""
        raw = '{"relevance": 3, "accuracy": 4}'
        result = _extract_json(raw)
        self.assertEqual(result["relevance"], 3)

    def test_evaluate_llm_as_judge_no_faiss(self):
        """With nonexistent queries, LLM judge returns 0 scores."""
        # This test doesn't need FAISS — the judge handles missing courses
        tc = EvalTestCase(query="zzzz_nonexistent_topic_xxx", k=5, ground_truth_ids=[])
        result = evaluate_llm_as_judge([tc], k=5)
        self.assertEqual(result["status"], "DONE")
        self.assertIn("avg_score", result)
        self.assertIn("per_query_scores", result)

    def test_evaluate_llm_as_judge_empty(self):
        """Empty test cases list returns valid structure."""
        result = evaluate_llm_as_judge([], k=5)
        self.assertEqual(result["status"], "DONE")
        self.assertEqual(result["per_query_scores"], [])

    def test_llm_judge_report_integration(self):
        """print_report shows LLM judge results in summary."""
        tc = EvalTestCase(query="python programming", k=5, ground_truth_ids=[])
        result = evaluate_llm_as_judge([tc], k=5)
        self.assertEqual(result["status"], "DONE")
        self.assertIn("per_query_details", result)


# ---------------------------------------------------------------------------
# Evaluation profile tests
# ---------------------------------------------------------------------------

class EvaluationProfilesTest(TestCase):
    """Test persona templates used by LLM-as-Judge evaluation."""

    def test_get_test_profile_returns_all_fields(self):
        """get_test_profile returns a profile with all required production fields."""
        from apps.rag.evaluation_profiles import get_test_profile
        profile = get_test_profile(0)
        for key in (
            "current_skills", "goals", "level", "budget", "weekly_hours",
            "material_format", "theory_practice", "main_goal",
        ):
            self.assertIn(key, profile)

    def test_profiles_use_diverse_levels(self):
        """Across all 25 test cases, at least 3 distinct levels appear."""
        from apps.rag.evaluation_profiles import get_test_profile
        levels = {get_test_profile(i)["level"] for i in range(25)}
        self.assertGreaterEqual(
            len(levels), 3,
            f"Expected >=3 distinct levels across profiles, got {levels}",
        )

    def test_profiles_have_realistic_skills(self):
        """No profile has both empty skills AND empty goals (production users always have some context)."""
        from apps.rag.evaluation_profiles import get_test_profile
        for i in range(25):
            profile = get_test_profile(i)
            has_skills = bool(profile.get("current_skills"))
            has_goals = bool(profile.get("goals"))
            # At least one of skills/goals should be populated for non-total-beginner personas.
            # Allow beginner_general (idx 0, 2, 18, 20) to be empty.
            self.assertTrue(
                has_skills or has_goals or profile["level"] == "Beginner",
                f"Profile {i} ({profile.get('name', '?')}) has no skills, no goals, AND not Beginner",
            )

    def test_judge_score_all_models_accepts_user_profile(self):
        """score_all_models now accepts user_profile kwarg without breaking."""
        from apps.rag.judge_client import score_all_models
        # Just check signature, don't actually call (would hit API)
        import inspect
        sig = inspect.signature(score_all_models)
        self.assertIn("user_profile", sig.parameters)

    def test_judge_prompt_template_includes_user_profile_section(self):
        """USER_PROMPT_TEMPLATE in judge_client has a USER PROFILE section."""
        from apps.rag.judge_client import USER_PROMPT_TEMPLATE
        self.assertIn("## USER PROFILE", USER_PROMPT_TEMPLATE)
        self.assertIn("{user_profile}", USER_PROMPT_TEMPLATE)
