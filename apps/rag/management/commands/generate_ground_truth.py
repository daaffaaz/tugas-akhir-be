"""
Django management command: generate_ground_truth

Auto-generates ground truth test cases from course tags and FAISS retrieval.
Outputs: apps/rag/test_queries.json

Usage:
    python manage.py generate_ground_truth
    python manage.py generate_ground_truth --output custom_output.json
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db.models import Count, Q

from apps.courses.models import Course, Tag
from apps.rag import retriever


class Command(BaseCommand):
    help = "Generate ground truth test queries from course tags."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            type=str,
            default=None,
            help="Output file path. Defaults to apps/rag/test_queries.json",
        )
        parser.add_argument(
            "--min-courses",
            type=int,
            default=3,
            help="Minimum courses to include a tag (default: 3).",
        )
        parser.add_argument(
            "--top-tags",
            type=int,
            default=20,
            help="Number of top tags to use (default: 20).",
        )
        parser.add_argument(
            "--top-k",
            type=int,
            default=30,
            help="Top-K courses to consider as ground truth (default: 30).",
        )

    def handle(self, *args, **options):
        output_path = options["output"] or Path(
            __file__
        ).parent.parent.parent / "test_queries.json"

        # --- Step 1: Analyze tags ---
        self.stdout.write("Analyzing course tags...")

        # Count courses per tag
        tag_counts = (
            Tag.objects
            .annotate(course_count=Count("courses", filter=Q(courses__is_active=True)))
            .order_by("-course_count")
        )

        # Filter tags that appear in enough courses
        min_courses = options["min_courses"]
        relevant_tags = [t for t in tag_counts if t.course_count >= min_courses]

        self.stdout.write(
            f"  Found {tag_counts.count()} unique tags, "
            f"{len(relevant_tags)} with >= {min_courses} courses"
        )

        # Take top N tags
        top_tags = relevant_tags[:options["top_tags"]]
        self.stdout.write(f"  Using top {len(top_tags)} tags as query seeds")

        # --- Step 2: Generate queries via FAISS ---
        self.stdout.write("Generating test queries from tags...")
        test_cases = []
        k = options["top_k"]

        for tag in top_tags:
            query = tag.name

            # Retrieve courses using FAISS
            courses, _ = retriever.retrieve_courses(query, top_k=k)
            course_ids = [c.get("course_id") for c in courses if c.get("course_id")]

            # Also get exact DB matches for precise ground truth
            exact_ids = list(
                Course.objects.filter(
                    is_active=True, tags__name__iexact=tag.name
                ).values_list("id", flat=True)
            )
            exact_ids = [str(cid) for cid in exact_ids]

            # Merge: FAISS results + exact DB matches (deduplicate)
            all_ids = list(set(course_ids + exact_ids))

            if not all_ids:
                continue

            test_cases.append({
                "query": query,
                "k": min(k, len(all_ids)),
                "ground_truth_ids": all_ids,
                "_notes": f"Generated from tag: {tag.name} ({tag.course_count} courses)",
            })

        # --- Step 3: Add some hybrid queries ---
        self.stdout.write("Generating hybrid queries...")
        tag_names = [t.name for t in top_tags[:10]]  # top 10 tags

        hybrid_combos = [
            ("python", "data"),
            ("web", "development"),
            ("cloud", "aws"),
            ("security", "cyber"),
            ("mobile", "app"),
        ]

        for w1, w2 in hybrid_combos:
            combo = f"{w1} {w2}"
            if combo in tag_names:
                continue

            courses, _ = retriever.retrieve_courses(combo, top_k=k)
            ids = [c.get("course_id") for c in courses if c.get("course_id")]

            if ids:
                test_cases.append({
                    "query": combo,
                    "k": min(k, len(ids)),
                    "ground_truth_ids": ids,
                    "_notes": "Hybrid query",
                })

        # --- Step 4: Write output ---
        for tc in test_cases:
            tc.pop("_notes", None)

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(test_cases, f, indent=2, ensure_ascii=False)

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"Generated {len(test_cases)} test cases -> {output_path}"
        ))
        self.stdout.write("")
        self.stdout.write("IMPORTANT:")
        self.stdout.write("  1. Review and edit the generated test_queries.json")
        self.stdout.write("  2. Refine ground_truth_ids for accuracy")
        self.stdout.write("  3. Remove queries that aren't relevant")
        self.stdout.write("  4. Run evaluation: python scripts/run_evaluation.py")
