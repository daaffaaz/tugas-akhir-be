# RAG Course Recommendation — Test Documentation

**Tanggal test:** 2026-05-02
**Test user:** kiplirafli19@gmail.com (questionnaire completed, 26 answers)
**Jumlah courses di database:** 187 (Coursera, seeded via `import_coursera_fast.py`)

---

## Endpoint

```
POST /api/rag/recommend/
```

### Request Schema

```json
{
  "topic": "machine learning untuk data science",   // wajib, min 3 char
  "additional_context": "...",                        // opsional, max 500 char
  "count": 5,                                         // opsional, default 5, max 20
  "regenerate": false                                 // opsional, default false
}
```

> Jika `regenerate: true`, maka `additional_context` **wajib diisi**. Jika tidak → HTTP 400.

---

## Skenario Test

### S1 — Fresh Recommend (tanpa context, tanpa regenerate)

**Input:**
```json
{
  "topic": "machine learning untuk data science",
  "count": 3
}
```

**Respons:** HTTP 201

| Field | Value |
|-------|-------|
| `total_retrieved` | 3 |
| `top_similarity_score` | 0.473 |
| `regenerate` | `false` |
| `regenerate_count` | 0 |

**Recommendation #1:**

| Field | Value |
|-------|-------|
| `title` | Machine Learning with Apache Spark |
| `level` | Intermediate |
| `relevance_score` (FAISS) | 0.473 |
| `match_score` (AI) | 0.3 |
| `ai_explanation` | "This course is not well-suited for the user due to its intermediate level and high time commitment, which exceeds the user's preferred study hours. Additionally, the course price is above the user's budget of 500k." |
| `best_for` | Intermediate learners with ample time and budget |
| `potential_gaps` | The course does not accommodate beginners or those with limited study time and budget constraints. |
| `regenerate_count` | 0 |
| `is_saved` | `false` |

> **Observasi:** AI explanation secara akurat membaca user profile (`<4 hours/week`, `budget: <500k`) dan memberikan alasan kenapa kursus ini *kurang cocok* untuk user tersebut. Ini bagus — user tahu kenapa kursus direkomendasikan meskipun ada caveat.

---

### S2 — Regenerate TANPA additional_context

**Input:**
```json
{
  "topic": "machine learning untuk data science",
  "regenerate": true
  // ⚠️ additional_context tidak diisi
}
```

**Respons:** HTTP 400

```json
{
  "additional_context": [
    "Konteks tambahan WAJIB diisi saat regenerate=True."
  ]
}
```

**Status:** ✅ PASS

---

### S3 — Regenerate DENGAN additional_context

**Input:**
```json
{
  "topic": "machine learning untuk data science",
  "additional_context": "saya mau career switch ke data analyst, budget Rp 500rb, lebih suka kursus hands-on yang pendek",
  "regenerate": true,
  "count": 3
}
```

**Respons:** HTTP 201

| Field | Value |
|-------|-------|
| `regenerate` | `true` |
| `regenerate_count` | 1 |

**Recommendation #1 (setelah regenerate):**

| Field | Before (S1) | After (S3) |
|-------|-----------|-----------|
| `ai_explanation` | "intermediate level... exceeds preferred study time... price is above budget" | "intermediate level... requires 10 hours a week, which exceeds your preferred study time... cost is slightly above your budget" |
| `best_for` | "Intermediate learners with ample time and budget" | "Intermediate learners with more time and budget" |

> **Observasi:** AI explanation sedikit berbeda karena ada context tambahan dari user yang memberikan informasi baru (career switch ke data analyst). Course yang dikembalikan sama tapi reasoning AI berbeda.

---

### S4 — Regenerate Kedua (increment counter)

**Input:** (setelah S3)
```json
{
  "topic": "machine learning untuk data science",
  "additional_context": "context 2 — saya mau belajar dari nol, lebih suka video singkat",
  "regenerate": true,
  "count": 3
}
```

**Respons:** HTTP 201

| Field | Value |
|-------|-------|
| `regenerate_count` | 2 |

**Semua recommendation record:**

| Course | `regenerate_count` |
|--------|-------------------|
| Machine Learning with Apache Spark | 2 |
| Data Science Methodology | 2 |
| Machine Learning in the Enterprise | 2 |

**Status:** ✅ PASS — counter incremented correctly per record.

---

### S5 — GET /api/rag/recommendations/ (List)

**Input:** `GET /api/rag/recommendations/?page=1&page_size=10`

**Respons:** HTTP 200

```json
{
  "results": [
    {
      "id": "uuid",
      "course": { "title": "Machine Learning in the Enterprise", ... },
      "topic_input": "machine learning untuk data science",
      "additional_context": "context 2 — saya mau belajar dari nol, lebih suka video singkat",
      "relevance_score": 0.467,
      "ai_explanation": "This course is intermediate level...",
      "is_saved": false,
      "regenerate_count": 2,
      "created_at": "2026-05-02T11:53:30+00:00"
    },
    ...
  ],
  "total": 3,
  "page": 1,
  "page_size": 10,
  "total_pages": 1
}
```

**Status:** ✅ PASS — semua field terisi, pagination works.

---

## Bugs Ditemukan & Diperbaiki

| # | Bug | Fix |
|---|-----|-----|
| 1 | `userpreferences` → `AttributeError` (related name salah) | Ganti ke `user.preferences` |
| 2 | `budget_idr` di-cast ke `int()` padahal berisi string `"<500k"` | Simpan sebagai string, tidak di-cast |
| 3 | `weekly_hours` di-cast ke `int()` padahal berisi `"<4"` | Simpan sebagai string |
| 4 | `course_to_text()` membaca top-level keys dari metadata, padahal metadata tersimpan nested di `metadata.metadata` | Ubah ke `course_meta.get('metadata', course_meta)` |
| 5 | `recommend_generator.py` gagal karena LLM error → semua explanation jadi fallback "Penjelasan tidak tersedia." | Fixed: sekarang context builder menggunakan metadata yang benar |

---

## Catatan Kualitas AI Explanation

### ✅ Strengths
- AI membaca `UserPreferences` (`budget: <500k`, `weekly_hours: <4`) secara akurat
- Memberikan alasan yang spesifik per user, bukan generic
- Mention gap/kekurangan kursus (duration, price, level) — ini bagus untuk transparansi

### ⚠️ Observations
- `match_score` konsisten di 0.3 untuk kursus yang "tidak cocok" — ini karena user profile sangat constrained
- Course pertama (Machine Learning with Apache Spark) punya `relevance_score` (FAISS) 0.473 tapi `match_score` (AI) 0.3 → AI memberi reasoning kenapa kursus tersebut tidak ideal untuk user tersebut
- Hasil regenerate masih mengembalikan **course yang sama** — ini expected karena FAISS retrieval berdasarkan topic, bukan additional_context. Additional context hanya mengubah *reasoning/explanation* dari AI per course.

---

## Ringkasan

| Skenario | HTTP | Status |
|----------|------|--------|
| S1: Fresh recommend | 201 | ✅ PASS |
| S2: Regenerate tanpa context | 400 | ✅ PASS |
| S3: Regenerate dengan context | 201 | ✅ PASS |
| S4: Second regenerate | 201 | ✅ PASS (counter=2) |
| S5: GET recommendations list | 200 | ✅ PASS |
