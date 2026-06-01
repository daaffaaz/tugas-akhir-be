# FE Handoff: Endpoint Rekomendasi Lanjutan (Career Recommendation)

**Untuk FE.** Dokumen ini menjelaskan endpoint baru + extend yang sudah diimplementasi di BE, lengkap dengan **field name divergences**, **URL koreksi**, dan **instruksi testing**. Silakan update TS types dan integration code FE berdasarkan dokumen ini.

**Tanggal:** 2026-06-01  
**Versi:** v1.0  
**Status:** BE ready, FE bisa mulai integrasi

---

## TL;DR — 3 Perubahan di BE

| # | Perubahan | URL | Method |
|---|-----------|-----|--------|
| **1** | **Endpoint baru** | `/api/recommendations/next-steps/` | `GET` |
| **2** | **Endpoint baru** | `/api/learning-paths/generate-from-career/` | `POST` |
| **3** | **Extend existing** | `/api/rag/generate-roadmap/` (lihat catatan URL di bawah) | `POST` — tambah field `career_focus` (opsional) |

**Koreksi URL dari spec:** spec di [BE_RECOMMENDATION_API.md](BE_RECOMMENDATION_API.md) menyebut `POST /api/learning-paths/generate/` — itu **tidak ada** di codebase. Endpoint existing yang dipakai untuk generate learning path adalah `POST /api/rag/generate-roadmap/`. FE harus pakai URL itu (atau migrate ke URL baru `generate-from-career/` untuk flow career-driven).

---

## 1. `GET /api/recommendations/next-steps/`

### Tujuan
Memberikan 2-4 kemungkinan karier (eksploratif) + 3-5 rekomendasi course per karier, berdasarkan course yang sudah ditandai selesai oleh user di semua learning path-nya.

### Request
- **Method:** `GET`
- **Auth:** `Authorization: Bearer <jwt>` (wajib)
- **Body:** tidak ada
- **Query params:** tidak ada

### Response 200 — Skema Final

> ⚠️ **Divergence dari spec.** BE pakai field asli dari `Course` model. Field yang berbeda dari spec di-highlight dengan emoji ⚠️.

```typescript
{
  career_possibilities: Array<{
    role: string;                    // "Data Analyst", "Backend Engineer"
    confidence: number;              // 0.0 – 1.0
    description: string;             // plain string paragraf naratif
    suggested_courses: Array<{
      id: string;                    // UUID
      title: string;
      thumbnail_url: string;
      url: string;
      platform: string;              // "Coursera" (string, bukan object)
      level: string;                 // "Beginner" | "Intermediate" | "Advanced" | ""
      duration: string;              // ⚠️ "18 hours" (text) — bukan number
      video_hours: number | null;    // ⚠️ field tambahan supaya FE bisa parse jam
      price: number | null;          // ⚠️ bukan price_idr
      currency: string;              // ⚠️ field tambahan, default "IDR"
      rating: number | null;         // 0.0 – 5.0
      tags: string[];                // ["data", "tableau"] — dari M2M Tag.name
    }>;
  }>;                                // 2-4 items, urut confidence desc

  based_on: {
    completed_courses: Array<{
      course_id: string;             // UUID
      title: string;
      completed_at: string | null;   // ISO 8601, bisa null kalau belum di-set
    }>;                              // bisa kosong [] kalau user belum ada completed
    reasoning: string;               // 1 kalimat summary dari LLM, bisa "" kalau empty state
  };
}
```

### Empty State (PENTING)
- Kalau user **belum punya course yang ditandai selesai**: BE return `200` (bukan `404`) dengan `career_possibilities: []` dan `based_on.completed_courses: []` + `reasoning: ""`.
- FE **tidak perlu handle 2 code path**. Cukup treat `career_possibilities.length === 0` sebagai empty state.

### Response Codes
| Code | Kapan | FE behavior |
|------|-------|-------------|
| `200` | Sukses, dengan atau tanpa data | Render normal atau empty state |
| `401` | Token JWT tidak valid / tidak ada | Redirect ke login |
| `500` | LLM/RAG error | Silent fallback — jangan expose error detail ke user |

### Aturan Bisnis (sudah enforced di BE)
- `career_possibilities.length` = **2-4** (sudah ditruncate di BE).
- `suggested_courses.length` per karier = **3-5** (kalau LLM generate <3, BE top-up pakai FAISS).
- `suggested_courses` **wajar exclude** course yang sudah selesai — BE filter, FE tidak perlu filter lagi.
- `confidence` adalah `number` 0.0-1.0. FE yang map ke label sendiri (e.g. "Tinggi" kalau ≥0.7).
- Sort `career_possibilities` dari `confidence` tertinggi ke terendah (sudah di-sort di BE).

### Contoh Response
```json
{
  "career_possibilities": [
    {
      "role": "Data Analyst",
      "confidence": 0.82,
      "description": "Karena kamu sudah menyelesaikan Statistics Fundamentals dan SQL for Beginners, kamu punya fondasi yang kuat untuk mulai berkarier sebagai Data Analyst. Karier ini fokus mengolah data menjadi insight bisnis menggunakan SQL, Excel, dan tools visualisasi seperti Tableau atau Power BI.",
      "suggested_courses": [
        {
          "id": "a1b2c3d4-...",
          "title": "Data Visualization with Tableau",
          "thumbnail_url": "https://...",
          "url": "https://coursera.org/...",
          "platform": "Coursera",
          "level": "Intermediate",
          "duration": "18 hours",
          "video_hours": 18.0,
          "price": 0,
          "currency": "IDR",
          "rating": 4.7,
          "tags": ["data", "visualization", "tableau"]
        }
      ]
    }
  ],
  "based_on": {
    "completed_courses": [
      {
        "course_id": "uuid-a",
        "title": "Statistics Fundamentals",
        "completed_at": "2026-05-20T10:00:00Z"
      }
    ],
    "reasoning": "Berdasarkan 1 course yang sudah kamu selesaikan, ini karier yang bisa kamu eksplor."
  }
}
```

---

## 2. `POST /api/learning-paths/generate-from-career/`

### Tujuan
Buat learning path baru yang terfokus pada karier yang dipilih user dari card rekomendasi di endpoint #1. Triggered dari tombol "Buat jalur belajar ini" di FE.

### Request Body
```typescript
{
  career_focus: string;              // "Data Analyst" — WAJIB, min 3 char, max 200 char
  based_on_courses?: string[];       // OPSIONAL — list UUID course yang sudah selesai
                                     // (untuk FE consistency; BE sudah punya via auth)
}
```

### Response 201
Pakai shape yang **persis sama** dengan response `POST /api/rag/generate-roadmap/` (yaitu `LearningPathDetailSerializer`):

```typescript
{
  id: string;                        // UUID learning path baru
  title: string;                     // "Data Analyst Learning Path" (dari LLM)
  topic_input: string;               // = career_focus yang dikirim
  description: string;
  is_saved: boolean;
  questionnaire_snapshot: object;    // JSON snapshot dari LLM
  regenerate_count: number;
  regenerate_context: string;
  progress_percentage: number;
  courses: Array<{                   // LearningPathCourseItemSerializer[]
    id: string;
    course: { /* full course object */ };
    position: number;
    phase_number: number | null;
    is_completed: boolean;
    completed_at: string | null;
    is_manually_added: boolean;
    replaced_by: string | null;
    replacement_reason: string;
    replacement_context: string;
    regenerate_version: number;
  }>;
  created_at: string;
  updated_at: string;

  _rag_meta: {                       // ⚠️ field tambahan (sama dengan generate-roadmap)
    courses_retrieved: number;
    top_similarity_score: number;
    retrieval_method: string;
    career_focus: string;            // ⚠️ dikembalikan untuk konfirmasi FE
    source: "generate-from-career";  // ⚠️ discriminator
  };
}
```

### Response Codes
| Code | Kapan | FE behavior |
|------|-------|-------------|
| `201` | Sukses, learning path terbuat | Navigate ke detail page LP baru |
| `400` | `career_focus` kosong / <3 char | Tampilkan error validasi |
| `401` | Belum login | Redirect ke login |
| `404` | Tidak ada course yang match | Tampilkan empty state, sarankan coba karier lain |
| `500` | RAG/LLM error | Silent fallback / retry button |

---

## 3. Extend `POST /api/rag/generate-roadmap/` (existing)

### Yang Berubah
Hanya **1 field baru** yang opsional. **Response shape tidak berubah.** Behavior existing (generate learning path dari `topic` saja) tetap works.

### Field Baru (Opsional)
```typescript
{
  topic?: string,                    // existing — wajib
  career_focus?: string,             // BARU — opsional, max 200 char
  budget_idr?: number,               // existing
  level?: string,                    // existing
}
```

### Logic
- Kalau `career_focus` dikirim → BE inject `"User ingin fokus ke karier: {career_focus}."` ke `additional_context` user profile saat prompt ke LLM. Course yang dipilih LLM akan lebih terarah ke karier itu.
- Kalau `career_focus` **tidak** dikirim → behavior **persis sama** seperti sebelumnya (regression-safe).
- Response shape **identik**, kecuali field `_rag_meta` sekarang punya `career_focus: string | null` (null kalau tidak dikirim).

### Contoh Penggunaan
```typescript
// existing flow — tetep works
POST /api/rag/generate-roadmap/
{ "topic": "machine learning" }

// new flow — career-driven
POST /api/rag/generate-roadmap/
{
  "topic": "machine learning",
  "career_focus": "ML Engineer"
}
```

---

## Catatan Penting untuk FE

### 1. Koreksi URL (PENTING)
Spec FE di [BE_RECOMMENDATION_API.md](BE_RECOMMENDATION_API.md) menyebut `POST /api/learning-paths/generate/` — URL itu **tidak ada** di codebase. Pilihan FE:
- **Opsi A (recommended):** Pakai endpoint baru `POST /api/learning-paths/generate-from-career/` untuk flow "Buat jalur belajar ini dari rekomendasi". URL existing `POST /api/rag/generate-roadmap/` tetap dipakai untuk flow awal (input topic manual).
- **Opsi B:** Pakai endpoint existing `POST /api/rag/generate-roadmap/` + field `career_focus` baru untuk semua flow. Lebih simpel, 1 URL saja. Logic BE sama saja.

Diskusikan dengan tim mana yang lebih clean untuk FE code.

### 2. Field Name Divergences dari Spec
Spec menyebut beberapa field yang **tidak ada** di `Course` model. Ini divergence yang perlu FE adapt:

| Spec | BE actual | Alasan |
|------|-----------|--------|
| `price_idr: number` | `price: number` + `currency: "IDR"` | Model pisah price & currency |
| `duration_hours: number` | `duration: string` + `video_hours: number` | Model simpan duration sebagai text ("18 hours") + numeric `video_hours` |
| `tags: string[]` | `tags: string[]` | ✅ match (dari M2M Tag.name) |
| `platform: string` | `platform: string` | ✅ match (bukan object) |

**Rekomendasi FE:** parse `duration` ke number di FE kalau perlu display "18h", atau pakai `video_hours` langsung. Untuk currency display, format `price + " " + currency` (default IDR).

### 3. Caching & Rate Limiting
- **Tidak ada caching** di BE untuk endpoint ini. Setiap call akan trigger LLM. Pertimbangkan di FE:
  - Debounce 5-10 detik saat user buka halaman rekomendasi
  - Tampilkan cached result di memory (React Query / SWR) supaya navigasi balik tidak hit BE
  - Tombol "Refresh" eksplisit untuk force re-fetch
- LLM call ke GPT-4o ~3-8 detik, kasih loading state yang jelas.

### 4. Empty State UX
- `GET /api/recommendations/next-steps/` dengan 0 completed → return array kosong (bukan 404).
- FE harus handle empty state dengan copy yang jelas: "Selesaikan minimal 1 course di learning path untuk dapat rekomendasi karier."
- Tombol CTA: "Lihat learning path saya" (link ke `/learning-path` page).

### 5. Error Handling
- BE **tidak expose error detail** untuk 500 (sesuai spec A: "FE handle silent — jangan expose error detail").
- FE tampilkan generic message: "Gagal memuat rekomendasi. Coba lagi." + tombol retry.
- 401 → redirect ke login.

---

## Testing

### Script Test Manual BE
BE sudah menyediakan [test_next_steps.py](test_next_steps.py) — script yang bisa FE pakai untuk verify endpoint lokal:

```bash
export TEST_AUTH_TOKEN='Bearer eyJ...'   # minta JWT dari BE owner
python manage.py runserver               # di terminal 1
python test_next_steps.py                # di terminal 2
```

Script ini mencakup 6 skenario:
1. GET next-steps happy path (dengan completed courses)
2. GET next-steps empty state (0 completed)
3. GET next-steps tanpa auth → 401
4. POST generate-from-career happy path
5. POST generate-from-career tanpa career_focus → 400
6. POST generate-roadmap dengan + tanpa career_focus (regression check)

### Skenario FE yang Perlu Diuji
1. **Happy path:** User dengan 2-3 completed course → buka halaman rekomendasi → dapat 2-4 career cards dengan course.
2. **Empty state:** User fresh (0 completed) → halaman rekomendasi → empty state copy + CTA ke learning path.
3. **Click "Buat jalur belajar ini":** Trigger `POST generate-from-career` → loading state → navigate ke detail LP baru.
4. **Verify exclude completed:** Suggested course **tidak** boleh muncul di `based_on.completed_courses`.
5. **Field shape:** Verify di console bahwa field di response FE = `{id, title, ..., price, currency, video_hours, duration, ...}` (bukan `price_idr`/`duration_hours`).
6. **Regression:** Flow existing `POST /api/rag/generate-roadmap/` tanpa `career_focus` → tetep works.

---

## Kontak

Kalau ada pertanyaan atau butuh koreksi schema, hubungi BE owner. Field name divergences di section "Catatan Penting" di atas adalah **sengaja** (BE pakai model asli, FE adapt TS types).
