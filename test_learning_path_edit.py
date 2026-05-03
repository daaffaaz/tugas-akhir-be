#!/usr/bin/env python
"""
Test script for Learning Path Edit Features (AI Feature #2).
Tests: regenerate, replace-course, apply-replacement, delete, add, similar.

Usage:
    source .env && export TEST_AUTH_TOKEN && python test_learning_path_edit.py

Or (auto-loads token from .env):
    python test_learning_path_edit.py
"""
import json
import os
import sys
import requests

BASE = "http://localhost:8000/api/rag"

# Auto-load token from .env
TEST_USER_TOKEN = os.environ.get("TEST_AUTH_TOKEN", "")
if not TEST_USER_TOKEN:
    # Try to read from .env file
    try:
        with open(".env") as f:
            for line in f:
                if line.startswith("TEST_AUTH_TOKEN="):
                    TEST_USER_TOKEN = line.strip().split("=", 1)[1].strip()
                    break
    except Exception:
        pass

if not TEST_USER_TOKEN:
    print("ERROR: Set TEST_AUTH_TOKEN env var or add to .env")
    print("Example: export TEST_AUTH_TOKEN='Bearer eyJ...'")
    sys.exit(1)

HEADERS = {
    "Authorization": TEST_USER_TOKEN,
    "Content-Type": "application/json",
}


def get(url, params=None, description=""):
    print(f"\n{'='*60}")
    print(f"GET: {description}")
    print(f"URL: {url}")
    print("-" * 60)
    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=30)
        print(f"STATUS: {r.status_code}")
        data = r.json()
        print(f"RESPONSE: {json.dumps(data, indent=2, ensure_ascii=False)[:1500]}")
        return r.status_code, data
    except Exception as e:
        print(f"ERROR: {e}")
        return None, None


def post(url, payload, description, timeout=90):
    print(f"\n{'='*60}")
    print(f"POST: {description}")
    print(f"URL: {url}")
    print(f"PAYLOAD: {json.dumps(payload, indent=2)}")
    print("-" * 60)
    try:
        r = requests.post(url, json=payload, headers=HEADERS, timeout=timeout)
        print(f"STATUS: {r.status_code}")
        data = r.json()
        print(f"RESPONSE: {json.dumps(data, indent=2, ensure_ascii=False)[:2000]}")
        return r.status_code, data
    except Exception as e:
        print(f"ERROR: {e}")
        return None, None


def delete(url, description):
    print(f"\n{'='*60}")
    print(f"DELETE: {description}")
    print(f"URL: {url}")
    print("-" * 60)
    try:
        r = requests.delete(url, headers=HEADERS, timeout=30)
        print(f"STATUS: {r.status_code}")
        data = r.json()
        print(f"RESPONSE: {json.dumps(data, indent=2, ensure_ascii=False)[:500]}")
        return r.status_code, data
    except Exception as e:
        print(f"ERROR: {e}")
        return None, None


def patch(url, payload, description):
    print(f"\n{'='*60}")
    print(f"PATCH: {description}")
    print(f"URL: {url}")
    print(f"PAYLOAD: {json.dumps(payload, indent=2)}")
    print("-" * 60)
    try:
        r = requests.patch(url, json=payload, headers=HEADERS, timeout=30)
        print(f"STATUS: {r.status_code}")
        data = r.json()
        print(f"RESPONSE: {json.dumps(data, indent=2, ensure_ascii=False)[:1000]}")
        return r.status_code, data
    except Exception as e:
        print(f"ERROR: {e}")
        return None, None


def main():
    print("="*60)
    print("LEARNING PATH EDIT FEATURES — TEST SUITE")
    print("="*60)

    # ── S1: List all learning paths
    s1_status, s1_data = get(
        f"{BASE}/learning-paths/",
        description="List all learning paths",
    )

    if s1_status == 200 and s1_data.get("total", 0) == 0:
        print("\n⚠️  No learning paths found. Creating one first...")

        # Generate a learning path first
        gen_status, gen_data = post(
            f"{BASE}/generate-roadmap/",
            {"topic": "machine learning untuk data science"},
            "Generate a learning path first",
        )

        if gen_status != 201:
            print("❌ Failed to generate learning path. Aborting tests.")
            return

        lp_id = gen_data.get("id")
        current_course_id = gen_data.get("courses", [{}])[0].get("course", {}).get("id") if gen_data.get("courses") else None

        print(f"\n✅ Created learning path: {lp_id}")
        print(f"   First course ID: {current_course_id}")

    else:
        lp_id = s1_data.get("results", [{}])[0].get("id") if s1_data.get("results") else None
        lp_data = s1_data.get("results", [{}])[0] if s1_data.get("results") else {}

        if lp_id:
            # Get full detail
            detail_status, detail_data = get(
                f"http://localhost:8000/api/learning-paths/{lp_id}/",
                description=f"Get learning path detail: {lp_id}",
            )
            if detail_status == 200 and detail_data.get("courses"):
                current_course_id = detail_data["courses"][0].get("course", {}).get("id") if detail_data["courses"] else None
            else:
                current_course_id = None
            print(f"\n📋 Using existing learning path: {lp_id}")
        else:
            print("❌ No learning path found to test with.")
            return

    # ── S2: Regenerate entire learning path (with context)
    s2_status, s2_data = post(
        f"{BASE}/learning-paths/{lp_id}/regenerate/",
        {
            "additional_context": "saya mau yang lebih hands-on practice, kurang teori"
        },
        "Regenerate entire path with additional context",
    )

    if s2_status == 200:
        print(f"  ✅ Regenerate OK — count={s2_data.get('regenerate_count')}")
    else:
        print(f"  ❌ Regenerate failed: {s2_data}")

    # Re-fetch detail after regenerate and replacement
    _, lp_detail = get(
        f"http://localhost:8000/api/learning-paths/{lp_id}/",
        description="Get updated path detail after regenerate",
    )

    # Use current course ID (may have been replaced)
    current_course_id = (lp_detail.get("courses", [{}])[0].get("course", {}).get("id")
                        if lp_detail and lp_detail.get("courses") else current_course_id)

    # ── S3: Get similar courses (for a course in the path)
    if current_course_id:
        s3_status, s3_data = get(
            f"{BASE}/learning-paths/{lp_id}/courses/{current_course_id}/similar/",
            description=f"Get similar courses (course: {current_course_id[:8]}...)",
        )
        if s3_status == 200:
            print(f"  ✅ Similar courses: {len(s3_data.get('courses', []))} found")
        else:
            print(f"  ❌ Similar courses failed: {s3_data}")

    # ── S4: Get replacement candidates
    if current_course_id:
        s4_status, s4_data = post(
            f"{BASE}/learning-paths/{lp_id}/courses/{current_course_id}/replace/",
            {
                "additional_context": "saya tidak suka course yang terlalu teori, preferensi hands-on",
                "count": 3,
            },
            "Get replacement candidates (with context)",
        )
        if s4_status == 200:
            candidates = s4_data.get("candidates", [])
            print(f"  ✅ Replacement candidates: {len(candidates)} found")
            if candidates:
                best_candidate_id = candidates[0].get("course_id")
                print(f"     Best candidate: {candidates[0].get('title', '')[:50]}")
        else:
            print(f"  ❌ Replace failed: {s4_data}")
            best_candidate_id = None

    # ── S5: Apply replacement (if we have a candidate)
    if current_course_id and 'best_candidate_id' in dir() and best_candidate_id:
        s5_status, s5_data = post(
            f"{BASE}/learning-paths/{lp_id}/courses/{current_course_id}/apply/",
            {
                "new_course_id": best_candidate_id,
                "replacement_reason": "Course terlalu teori, saya prefer hands-on"
            },
            "Apply replacement course",
        )
        if s5_status == 200:
            print(f"  ✅ Replacement applied OK")
        else:
            print(f"  ❌ Apply replacement failed: {s5_data}")

    # ── S6: Delete a course
    if current_course_id:
        s6_status, s6_data = delete(
            f"{BASE}/learning-paths/{lp_id}/courses/{current_course_id}/",
            "Delete a course from path",
        )
        if s6_status == 200:
            print(f"  ✅ Course deleted at position {s6_data.get('position')}")
        else:
            print(f"  ❌ Delete failed: {s6_data}")

    # ── S7: Add a course (get a course ID to add first)
    # Find any course not in the path
    if lp_id:
        _, lp_after_delete = get(
            f"http://localhost:8000/api/learning-paths/{lp_id}/",
            description="Get path after delete",
        )

        existing_ids = [c.get("course", {}).get("id") for c in lp_after_delete.get("courses", [])]

        # Get similar courses to find a course to add
        if lp_after_delete.get("courses"):
            ref_course_id = lp_after_delete["courses"][0].get("course", {}).get("id")
            _, similar_data = get(
                f"{BASE}/learning-paths/{lp_id}/courses/{ref_course_id}/similar/",
                description="Get similar courses for add",
            )
            available = [c for c in similar_data.get("courses", []) if c.get("course_id") not in existing_ids]
            if available:
                course_to_add = available[0].get("course_id")
                s7_status, s7_data = post(
                    f"{BASE}/learning-paths/{lp_id}/courses/add/",
                    {"course_id": course_to_add, "position": 1},
                    "Add a course to path",
                )
                if s7_status == 200:
                    print(f"  ✅ Course added at position 1")
                else:
                    print(f"  ❌ Add failed: {s7_data}")
            else:
                print("  ⚠️  No available courses to add (all in path already)")

    print("\n" + "="*60)
    print("All learning path edit tests complete!")
    print("="*60)


if __name__ == "__main__":
    main()