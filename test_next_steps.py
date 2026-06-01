#!/usr/bin/env python
"""
Manual test script for the new career recommendation endpoints.

Covers:
  1. GET  /api/recommendations/next-steps/         — happy path
  2. GET  /api/recommendations/next-steps/         — empty state (no completed courses)
  3. POST /api/learning-paths/generate-from-career/
  4. POST /api/rag/generate-roadmap/ with career_focus field (regression)

Usage:
  export TEST_AUTH_TOKEN='Bearer <jwt>'
  python test_next_steps.py
"""
import json
import os
import sys

import requests

RECOMMENDATIONS_URL = "http://localhost:8000/api/recommendations/next-steps/"
LEARNING_PATHS_URL = "http://localhost:8000/api/learning-paths/generate-from-career/"
RAG_GENERATE_URL = "http://localhost:8000/api/rag/generate-roadmap/"

TEST_AUTH_TOKEN = os.environ.get("TEST_AUTH_TOKEN", "")
if not TEST_AUTH_TOKEN:
    print("ERROR: Set TEST_AUTH_TOKEN env var with a JWT/Auth token.")
    print("Example: export TEST_AUTH_TOKEN='Bearer eyJ...'")
    sys.exit(1)

HEADERS = {
    "Authorization": TEST_AUTH_TOKEN,
    "Content-Type": "application/json",
}


def get(url, description):
    print(f"\n{'='*60}")
    print(f"SCENARIO: {description}")
    print(f"URL: {url}")
    print("-" * 60)
    try:
        r = requests.get(url, headers=HEADERS, timeout=60)
        print(f"STATUS: {r.status_code}")
        data = r.json()
        print(f"RESPONSE: {json.dumps(data, indent=2, ensure_ascii=False)[:2500]}")
        return r.status_code, data
    except Exception as e:
        print(f"ERROR: {e}")
        return None, None


def post(url, payload, description):
    print(f"\n{'='*60}")
    print(f"SCENARIO: {description}")
    print(f"URL: {url}")
    print(f"PAYLOAD: {json.dumps(payload, indent=2, ensure_ascii=False)}")
    print("-" * 60)
    try:
        r = requests.post(url, json=payload, headers=HEADERS, timeout=120)
        print(f"STATUS: {r.status_code}")
        try:
            data = r.json()
            print(f"RESPONSE: {json.dumps(data, indent=2, ensure_ascii=False)[:2500]}")
        except ValueError:
            data = {"raw": r.text[:500]}
            print(f"RESPONSE (raw): {r.text[:500]}")
        return r.status_code, data
    except Exception as e:
        print(f"ERROR: {e}")
        return None, None


def main():
    # ── Scenario 1: GET /api/recommendations/next-steps/ (happy path)
    s1_status, s1_data = get(
        RECOMMENDATIONS_URL,
        "GET next-steps — should return 2-4 career possibilities if user has completed courses",
    )
    if s1_status == 200:
        cps = s1_data.get('career_possibilities', [])
        based_on = s1_data.get('based_on', {})
        completed = based_on.get('completed_courses', [])
        print(f"\n[INFO] career_possibilities: {len(cps)}")
        print(f"[INFO] completed_courses used as input: {len(completed)}")
        if cps:
            print(f"[INFO] First career: {cps[0].get('role')} "
                  f"(confidence={cps[0].get('confidence')})")
            print(f"[INFO]   description: {cps[0].get('description', '')[:150]}...")
            print(f"[INFO]   suggested_courses: {len(cps[0].get('suggested_courses', []))}")
            # Check no suggested course == completed course
            completed_ids = {c['course_id'] for c in completed}
            for cp in cps:
                for sc in cp.get('suggested_courses', []):
                    if sc['id'] in completed_ids:
                        print(f"[FAIL] A4 violation: suggested_course {sc['id']} is in completed_courses")
                        sys.exit(1)
            print("[PASS] A4 — no suggested course in completed_courses")
            if not (2 <= len(cps) <= 4):
                print(f"[FAIL] A2 — expected 2-4 career possibilities, got {len(cps)}")
            else:
                print(f"[PASS] A2 — {len(cps)} career possibilities (within 2-4)")
            confidences = [cp.get('confidence', 0) for cp in cps]
            if confidences != sorted(confidences, reverse=True):
                print(f"[FAIL] A5 — confidences not sorted desc: {confidences}")
            else:
                print(f"[PASS] A5 — confidences sorted desc: {confidences}")
        else:
            print("[INFO] No career possibilities returned — user has 0 completed courses "
                  "(expected for a fresh test user). Empty state OK per A1.")

    # ── Scenario 2: GET next-steps without auth
    print(f"\n{'='*60}")
    print("SCENARIO: GET next-steps WITHOUT auth — should return 401")
    try:
        r = requests.get(RECOMMENDATIONS_URL, timeout=10)
        print(f"STATUS: {r.status_code}")
        if r.status_code == 401:
            print("[PASS] Correctly rejected unauthenticated request")
        else:
            print(f"[INFO] Got {r.status_code} (expected 401)")
    except Exception as e:
        print(f"ERROR: {e}")

    # ── Scenario 3: POST /api/learning-paths/generate-from-career/ (happy path)
    s3_status, s3_data = post(
        LEARNING_PATHS_URL,
        {"career_focus": "Data Analyst"},
        "POST generate-from-career — should create learning path focused on Data Analyst",
    )
    if s3_status == 201:
        lp_id = s3_data.get('id')
        title = s3_data.get('title', '')
        rag_meta = s3_data.get('_rag_meta', {})
        print(f"\n[INFO] New learning path id: {lp_id}")
        print(f"[INFO] Title: {title}")
        print(f"[INFO] career_focus in meta: {rag_meta.get('career_focus')}")
        print(f"[INFO] source: {rag_meta.get('source')}")
        if 'data analyst' not in title.lower():
            print(f"[WARN] A2-soft — title does not mention 'Data Analyst': {title!r}")
    elif s3_status == 404:
        print("[INFO] Got 404 — likely no courses matched. Verify index is built.")
    elif s3_status == 401:
        print("[INFO] Got 401 — check auth token")

    # ── Scenario 4: POST generate-from-career WITHOUT career_focus — should 400
    s4_status, s4_data = post(
        LEARNING_PATHS_URL,
        {},
        "POST generate-from-career WITHOUT career_focus — should return 400",
    )
    if s4_status == 400:
        print("[PASS] Correctly rejected missing career_focus")
    else:
        print(f"[INFO] Got {s4_status} (expected 400)")

    # ── Scenario 5: POST /api/rag/generate-roadmap/ WITH career_focus (regression)
    s5_status, s5_data = post(
        RAG_GENERATE_URL,
        {
            "topic": "Python programming",
            "career_focus": "Backend Engineer",
        },
        "POST generate-roadmap with career_focus field — should succeed and include career_focus in meta",
    )
    if s5_status == 201:
        meta = s5_data.get('_rag_meta', {})
        print(f"\n[INFO] career_focus in meta: {meta.get('career_focus')}")
        if meta.get('career_focus') == 'Backend Engineer':
            print("[PASS] career_focus properly echoed in _rag_meta")
        else:
            print(f"[FAIL] Expected career_focus='Backend Engineer', got {meta.get('career_focus')!r}")

    # ── Scenario 6: POST /api/rag/generate-roadmap/ WITHOUT career_focus (regression)
    s6_status, s6_data = post(
        RAG_GENERATE_URL,
        {"topic": "JavaScript basics"},
        "POST generate-roadmap WITHOUT career_focus — should still work (regression)",
    )
    if s6_status == 201:
        meta = s6_data.get('_rag_meta', {})
        print(f"\n[INFO] career_focus in meta: {meta.get('career_focus')!r}")
        if meta.get('career_focus') is None:
            print("[PASS] career_focus is None when not provided (regression OK)")
        else:
            print(f"[WARN] Expected None, got {meta.get('career_focus')!r}")

    print("\n" + "=" * 60)
    print("All scenarios complete.")


if __name__ == "__main__":
    main()
