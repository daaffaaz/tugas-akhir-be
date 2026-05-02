#!/usr/bin/env python
"""
Manual test script for POST /api/rag/recommend/
Tests 3 scenarios against the live Django dev server.
Usage: python test_recommend.py
"""
import json
import os
import sys

import requests

BASE = "http://localhost:8000/api/rag"

# Test user credentials (Daffa Akmal — has full questionnaire answers)
TEST_USER_TOKEN = os.environ.get("TEST_AUTH_TOKEN", "")
if not TEST_USER_TOKEN:
    print("ERROR: Set TEST_AUTH_TOKEN env var with a JWT/Auth token.")
    print("Example: export TEST_AUTH_TOKEN='Bearer eyJ...'")
    sys.exit(1)

HEADERS = {
    "Authorization": TEST_USER_TOKEN,
    "Content-Type": "application/json",
}


def post(url, payload, description):
    print(f"\n{'='*60}")
    print(f"SCENARIO: {description}")
    print(f"URL: {url}")
    print(f"PAYLOAD: {json.dumps(payload, indent=2)}")
    print("-" * 60)
    try:
        r = requests.post(url, json=payload, headers=HEADERS, timeout=60)
        print(f"STATUS: {r.status_code}")
        data = r.json()
        print(f"RESPONSE: {json.dumps(data, indent=2, ensure_ascii=False)[:2000]}")
        return r.status_code, data
    except Exception as e:
        print(f"ERROR: {e}")
        return None, None


def main():
    topic = "machine learning untuk data science"

    # ── Scenario 1: Fresh recommend (no context, no regenerate)
    # Expected: 201, 5 courses returned, regenerate_count=0
    s1_status, s1_data = post(
        f"{BASE}/recommend/",
        {
            "topic": topic,
            "count": 5,
        },
        "Fresh recommend — no additional_context, no regenerate",
    )

    # ── Scenario 2: Regenerate WITHOUT additional_context
    # Expected: 400 — validation error: "Konteks tambahan WAJIB diisi saat regenerate=True"
    if s1_status == 201:
        s2_status, s2_data = post(
            f"{BASE}/recommend/",
            {
                "topic": topic,
                "regenerate": True,
                # NO additional_context — should fail validation
            },
            "Regenerate WITHOUT additional_context — should return 400",
        )
        if s2_status == 400:
            print("[PASS] Correctly rejected regenerate without context")
        else:
            print(f"[FAIL] Expected 400, got {s2_status}")

    # ── Scenario 3: Regenerate WITH additional_context
    # Expected: 201, regenerate_count incremented, ai_explanation updated
    if s1_status == 201:
        s3_status, s3_data = post(
            f"{BASE}/recommend/",
            {
                "topic": topic,
                "additional_context": "saya mau career switch ke data analyst, budget terbatas, lebih suka kursus yang hands-on",
                "regenerate": True,
                "count": 5,
            },
            "Regenerate WITH additional_context — should return 201, regenerate_count > 0",
        )
        if s3_status == 201:
            rec = s3_data.get('recommendations', [])
            reg_count = s3_data.get('regenerate_count', 0)
            print(f"[INFO] regenerate_count in response: {reg_count}")
            if rec:
                print(f"[INFO] First recommendation:")
                print(f"  title: {rec[0].get('title')}")
                print(f"  ai_explanation: {rec[0].get('ai_explanation', '')[:200]}...")
                print(f"  regenerate_count: {rec[0].get('regenerate_count')}")

    print("\n" + "=" * 60)
    print("All scenarios complete.")


if __name__ == "__main__":
    main()