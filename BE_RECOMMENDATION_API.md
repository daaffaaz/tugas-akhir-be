# BE Spec: Endpoint Rekomendasi Lanjutan

**Dokumen ini untuk Backend (BE).** Berisi 2 endpoint baru + 1 endpoint existing yang di-extend. Frontend sudah final di sisi UI/UX, semua keputusan ada di section "Keputusan Final" di bawah — tinggal ACC dan implement.

**Tanggal:** 2026-05-29  
**Versi:** v1.0  
**Status:** Ready for BE implementation

---

## Ringkasan

User sudah punya course ditandai "selesai dipelajari" di learning path. FE butuh:
1. **GET** untuk ambil rekomendasi karier + course berdasarkan course yang sudah selesai.
2. **POST** untuk buat learning path baru berdasarkan karier yang user pilih dari rekomendasi.

**Penting:** rekomendasi bersifat **eksploratif**, bukan "penentuan target". Jangan pakai field `target_role` / `job_title` user sebagai input — ini tentang apa yang user sudah PELAJARI, bukan preferensi yang dideklarasi.

---

## 1. Endpoint Baru: `GET /api/recommendations/next-steps/`

### Tujuan

Memberikan daftar kemungkinan karier (eksploratif) + rekomendasi course, berdasarkan course yang sudah ditandai selesai oleh user.

### Response 200 — Skema

```typescript
{
  career_possibilities: Array<{
    role: string;                    // "Data Analyst", "Backend Engineer"
    confidence: number;              // 0.0 – 1.0, hasil RAG/LLM scoring
    description: string;             // 1 paragraf naratif (plain string, BUKAN JSON)
    suggested_courses: Array<{       // 3–5 course yang BELUM diselesaikan user
      id: string;
      title: string;
      thumbnail_url: string;
      url: string;
      platform: string;
      level: string;                 // "Beginner" | "Intermediate" | "Advanced"
      duration_hours: number;
      price_idr: number;
      rating: number;                // 0.0 – 5.0
      tags: string[];
    }>;
  }>;                                // 2–4 items

  based_on: {
    completed_courses: Array<{       // course yang jadi input AI
      course_id: string;
      title: string;
      completed_at: string;          // ISO 8601
    }>;
    reasoning: string;               // 1 kalimat: "Berdasarkan X course yang kamu selesaikan..."
  };
}
```

### Aturan Bisnis (WAJIB)

| # | Aturan |
|---|---|
| **A1** | Endpoint hanya return data jika user **login** dan punya **minimal 1 completed course**. Kalau 0 → return `404` atau `200 { career_possibilities: [], based_on: { completed_courses: [], reasoning: "" } }` (pilih satu, FE handle keduanya). |
| **A2** | `career_possibilities.length` = **2 sampai 4** item. Jangan 1, jangan 5+. |
| **A3** | Tiap `career_possibility.suggested_courses` = **3 sampai 5** course. Max 5. Kalau BE generate lebih, truncate. |
| **A4** | `suggested_courses` **WAJIB exclude course yang sudah user selesaikan**. Filter di BE, jangan percayakan ke FE. |
| **A5** | `career_possibilities` diurutkan dari `confidence` tertinggi ke terendah. |
| **A6** | Field `description` adalah **plain string** (1 paragraf, 2-4 kalimat). BUKAN structured JSON. |
| **A7** | Field `based_on.completed_courses` WAJIB dikirim walaupun kosong (untuk transparansi ke FE). |
| **A8** | `confidence` adalah `number` (0.0–1.0), bukan label string. FE yang map ke label. |

### Response Codes

| Code | Kapan |
|---|---|
| **200** | Sukses, ada atau tidak ada data |
| **401** | User belum login |
| **500** | Error LLM/RAG. FE handle silent — jangan expose error detail. |

### Contoh Response (Success)

```json
{
  "career_possibilities": [
    {
      "role": "Data Analyst",
      "confidence": 0.82,
      "description": "Karena kamu sudah menyelesaikan Statistics Fundamentals dan SQL for Beginners, kamu punya fondasi yang kuat untuk mulai berkarier sebagai Data Analyst. Karier ini fokus mengolah data menjadi insight bisnis menggunakan SQL, Excel, dan tools visualisasi.",
      "suggested_courses": [
        {
          "id": "uuid-1",
          "title": "Data Visualization with Tableau",
          "thumbnail_url": "https://...",
          "url": "https://...",
          "platform": "Coursera",
          "level": "Intermediate",
          "duration_hours": 18,
          "price_idr": 0,
          "rating": 4.7,
          "tags": ["data", "visualization", "tableau"]
        }
      ]
    },
    {
      "role": "Backend Developer",
      "confidence": 0.61,
      "description": "...",
      "suggested_courses": [...]
    }
  ],
  "based_on": {
    "completed_courses": [
      {
        "course_id": "uuid-a",
        "title": "Statistics Fundamentals",
        "completed_at": "2026-05-20T10:00:00Z"
      },
      {
        "course_id": "uuid-b",
        "title": "SQL for Beginners",
        "completed_at": "2026-05-25T14:30:00Z"
      }
    ],
    "reasoning": "Berdasarkan 2 course yang sudah kamu selesaikan, ini beberapa karier yang bisa kamu eksplor."
  }
}
```

---

## 2. Endpoint Baru: `POST /api/learning-paths/generate-from-career/`

### Tujuan

Buat learning path baru yang terfokus pada karier yang dipilih user dari hasil rekomendasi di endpoint #1. Triggered dari card "Buat jalur belajar ini" di FE.

### Request Body

```typescript
{
  career_focus: string;              // "Data Analyst" (sama dengan `role` di endpoint #1)
  based_on_courses?: string[];       // opsional: list course_id yang sudah selesai
                                     // (untuk FE consistency, BE sudah punya via auth)
}
```

### Response 201

```typescript
{
  id: string;                        // UUID learning path yang baru dibuat
  title: string;                     // "Data Analyst Learning Path"
  // ... fields lain sesuai schema LearningPath existing
}
```

**Behavior:** Endpoint ini internal-nya **panggil ulang `POST /api/learning-paths/generate/`** (yang existing) dengan `career_focus` di-inject ke prompt. Jadi logic generate tidak duplicate.

### Response Codes

| Code | Kapan |
|---|---|
| **201** | Learning path berhasil dibuat, return object |
| **400** | `career_focus` kosong / invalid |
| **401** | User belum login |
| **500** | Error RAG/generate |

---

## 3. Extend Existing: `POST /api/learning-paths/generate/`

Endpoint ini **sudah ada** (dipakai oleh `/ai/course-recommendation`). Cukup tambah 1 field baru di body, **jangan ubah behavior existing**.

### Field Baru (Opsional)

```typescript
{
  topic?: string,                    // existing — bebas topic dari user
  career_focus?: string,             // BARU — opsional, kalau ada BE inject ke prompt
  // ... field existing lain
}
```

### Logic

- Kalau `career_focus` ada → tambahkan ke prompt: `"User ingin fokus ke karier: {career_focus}."`
- Kalau tidak ada → behavior existing (seperti sekarang).
- Response shape **tidak berubah**.

**Effort:** edit serializer, edit service/prompt template, edit 1 test. Estimasi 1-2 jam.

---

## Keputusan Final (TL;DR untuk BE)

| # | Keputusan | Detail |
|---|---|---|
| **K1** | 2 endpoint baru | `GET /api/recommendations/next-steps/` + `POST /api/learning-paths/generate-from-career/` |
| **K2** | 1 endpoint extend | `POST /api/learning-paths/generate/` tambah field opsional `career_focus` |
| **K3** | 2-4 career possibilities | Max 4, diurut dari confidence tertinggi |
| **K4** | 3-5 suggested courses per karier | Max 5, BE truncate |
| **K5** | BE filter completed courses | `suggested_courses` dijamin exclude yang sudah selesai |
| **K6** | Description plain string | Bukan JSON, bukan structured — paragraf naratif |
| **K7** | Confidence adalah number | 0.0–1.0, FE yang map ke label |
| **K8** | Tidak pakai `target_role`/`job_title` | Input hanya dari course yang sudah selesai |
| **K9** | Auth required | Semua endpoint butuh user login |

---

## Open Questions untuk BE (yang mungkin perlu klarifikasi)

1. **Course model:** Apakah field course yang dipakai existing sudah punya `level`, `duration_hours`, `price_idr`, `rating`, `tags`? Kalau nama field berbeda, kasih tau FE supaya TypeScript types di FE disesuaikan.
2. **Thumbnail URL:** Apakah `thumbnail_url` adalah full URL (signed/absolute) atau path relatif? FE expect absolute URL.
3. **Rate limiting:** Apakah endpoint `next-steps` perlu rate-limit (mis. 1x per 5 menit per user)? Implementasi RAG/LLM bisa mahal.
4. **Caching:** Apakah response bisa di-cache (Redis) per user, atau selalu fresh? User yang baru saja selesaikan course butuh fresh data.
5. **Empty state 0 completed course:** Pakai `404` atau `200 { ...empty }`? Rekomendasi FE: `200` dengan array kosong, supaya FE tidak perlu handle 2 code path.

---

## Dependencies yang Mungkin BE Butuh

- **Vector store / RAG pipeline:** untuk match course yang sudah selesai → career possibilities. Kalau belum ada, bisa mulai dari rule-based sederhana dulu (mis. tag-based matching) lalu upgrade ke LLM.
- **LLM call:** untuk generate `description` naratif per career possibility. Atau kalau mau cepat, pakai template-based string.
- **Course catalog service:** untuk fetch course yang relevan + filter yang sudah selesai. Kemungkinan sudah ada di service lain.

---

## Setelah BE Selesai

1. BE kirim link Postman / OpenAPI spec.
2. FE implement di sisi mereka (estimasi ~3.5 jam, detail di [proposal-fitur-rekomendasi-lanjutan.md](proposal-fitur-rekomendasi-lanjutan.md)).
3. Joint testing: user flow dari `/learning-path` → klik card → learning path baru terbuat.

**Kontak FE:** kalau ada perubahan nama field, schema, atau response code, langsung diskusi sebelum push ke FE.
