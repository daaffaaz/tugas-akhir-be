# Badges / Gamification API

Sistem badge berbasis kategori + level. Badge di-award otomatis saat user menyelesaikan course (toggle complete). Doc ini mencakup semua yang dibutuhkan frontend untuk:

1. Menampilkan toast/animasi badge baru saat user menyelesaikan course
2. Menampilkan daftar badge di **halaman profile**
3. Menampilkan badge di **dashboard learning path** (di bawah progress keseluruhan)

---

## Konsep & Model Data

### Badge (catalog)

Sistem punya katalog tetap 24 badge: 8 kategori x 3 level.

**Categories** (`category` field — enum string):

| Code | Label |
|---|---|
| `ui_ux` | UI/UX |
| `frontend` | Frontend |
| `backend` | Backend |
| `mobile` | Mobile |
| `data_science` | Data Science |
| `ml_ai` | Machine Learning |
| `devops` | DevOps |
| `cybersecurity` | Cybersecurity |

**Levels** (`level` field — enum string):

| Code | Label |
|---|---|
| `pemula` | Pemula |
| `menengah` | Menengah |
| `mahir` | Mahir |

**Badge codes** mengikuti pola `<slug-kategori>-<level>`:
`ui-ux-pemula`, `ui-ux-menengah`, `ui-ux-mahir`, `frontend-pemula`, … `cybersecurity-mahir`.

### UserBadge (achievement record)

Record per (user, badge) — **unique constraint**, jadi 1 user maksimal punya 1 record untuk badge tertentu. Setelah earned, achievement bersifat **permanent** (tidak akan dihapus walaupun user un-complete course-nya).

### Rule award

Saat user menyelesaikan sebuah course:

1. Backend cek tags & level course terhadap `criteria` setiap badge aktif.
2. Untuk setiap badge yang match:
   - User **belum punya** → award baru → masuk `awarded[]`
   - User **sudah punya** → tidak duplikat → masuk `already_owned[]` (warning ke FE)
3. 1 course bisa men-trigger >1 badge (misal course "ML & Data Science Intermediate" bisa award `data-science-menengah` + `ml-ai-menengah`).

---

## Auth

Semua endpoint butuh `Authorization: Bearer <access_token>`. User juga harus sudah menyelesaikan onboarding questionnaire (middleware existing), kalau belum akan dapat `403`.

---

## Endpoints

### 1. GET `/api/badges/`

Catalog penuh semua badge (24 badge), dengan flag `is_earned` untuk user saat ini. Cocok untuk halaman "all badges" yang menampilkan badge yang sudah dan belum di-earn (locked/unlocked state).

**Response 200**:

```json
{
  "count": 24,
  "earned_count": 3,
  "results": [
    {
      "id": "a1b2c3d4-...",
      "code": "ui-ux-pemula",
      "name": "UI/UX Pemula",
      "description": "Selesaikan course UI/UX pertamamu di level pemula.",
      "category": "ui_ux",
      "category_label": "UI/UX",
      "level": "pemula",
      "level_label": "Pemula",
      "icon_url": "",
      "sort_order": 1,
      "is_earned": true,
      "earned_at": "2026-05-28T09:12:33.123Z"
    },
    {
      "id": "...",
      "code": "ui-ux-menengah",
      "name": "UI/UX Menengah",
      "description": "Selesaikan course UI/UX di level menengah.",
      "category": "ui_ux",
      "category_label": "UI/UX",
      "level": "menengah",
      "level_label": "Menengah",
      "icon_url": "",
      "sort_order": 2,
      "is_earned": false,
      "earned_at": null
    }
  ]
}
```

| Field | Type | Notes |
|---|---|---|
| `count` | integer | Total badge di catalog |
| `earned_count` | integer | Berapa badge yang sudah di-earn user |
| `results[].is_earned` | boolean | `true` kalau user sudah punya |
| `results[].earned_at` | ISO datetime \| null | Kapan badge di-earn (null kalau belum) |

---

### 2. GET `/api/users/me/badges/`

Daftar **UserBadge** yang user sudah miliki, di-sort `earned_at` descending (terbaru di atas). **Digunakan di halaman profile.**

Tidak ada pagination (asumsi jumlah badge per user terbatas, max 24).

**Response 200**:

```json
[
  {
    "id": "ub-uuid-1",
    "badge": {
      "id": "...",
      "code": "ml-ai-menengah",
      "name": "Machine Learning Menengah",
      "description": "Selesaikan course Machine Learning di level menengah.",
      "category": "ml_ai",
      "category_label": "Machine Learning",
      "level": "menengah",
      "level_label": "Menengah",
      "icon_url": "",
      "sort_order": 17
    },
    "earned_via_course": {
      "id": "course-uuid",
      "title": "Fundamentals of AI Agents Using RAG and LangChain",
      "platform": { "id": "...", "name": "Coursera", "base_url": "..." },
      "level": "Intermediate",
      "tags": ["LLM Application", "Large Language Modeling", "..."]
      // ... full CourseListSerializer fields
    },
    "earned_via_learning_path": {
      "id": "lp-uuid",
      "title": "Machine Learning for Data Science"
    },
    "earned_at": "2026-05-28T09:12:33.123Z"
  }
]
```

`earned_via_course` dan `earned_via_learning_path` bisa **null** kalau course / path-nya sudah dihapus (FK pakai `SET_NULL`). FE harus handle case ini saat render.

---

### 3. GET `/api/learning-paths/<uuid:pk>/badges/`

Badge yang di-earn user **via** learning path tertentu. **Digunakan di dashboard learning path** (di bawah progress keseluruhan).

Path UUID di URL harus milik user yang sedang login, kalau bukan akan return `404`.

**Response 200**:

```json
{
  "learning_path_id": "lp-uuid",
  "count": 2,
  "results": [
    {
      "id": "ub-uuid-1",
      "badge": { /* ... lihat shape di atas ... */ },
      "earned_via_course": { /* CourseListSerializer */ },
      "earned_via_learning_path": { "id": "lp-uuid", "title": "..." },
      "earned_at": "2026-05-28T09:12:33.123Z"
    }
  ]
}
```

**404** kalau learning path tidak ditemukan atau bukan milik user.

---

### 4. PATCH `/api/learning-paths/courses/<uuid:pk>/toggle-complete/` — **UPDATED RESPONSE**

Endpoint existing untuk toggle complete sebuah `LearningPathCourse`. **Response sekarang dilengkapi field `badges`** berisi hasil evaluasi badge.

**Behavior**:

- Toggle dari `false` → `true` → backend evaluate badge, response berisi `badges.awarded` (badge baru) dan/atau `badges.already_owned` (badge yang sudah pernah di-earn user).
- Toggle dari `true` → `false` → tidak ada evaluasi badge, response `badges.awarded = []` dan `badges.already_owned = []`. Badge yang sudah di-earn user **tidak dicabut**.

**Request**: tidak ada body, hanya `PATCH` dengan auth header.

**Response 200** (saat baru complete pertama kali untuk badge tertentu):

```json
{
  "id": "lpc-uuid",
  "course": { /* CourseListSerializer */ },
  "position": 3,
  "phase_number": 1,
  "is_completed": true,
  "completed_at": "2026-05-28T09:12:33.123Z",
  "is_manually_added": false,
  "replaced_by": null,
  "replacement_reason": "",
  "replacement_context": "",
  "regenerate_version": 0,
  "badges": {
    "awarded": [
      {
        "id": "...",
        "code": "frontend-pemula",
        "name": "Frontend Pemula",
        "description": "Selesaikan course Frontend pertamamu di level pemula.",
        "category": "frontend",
        "category_label": "Frontend",
        "level": "pemula",
        "level_label": "Pemula",
        "icon_url": "",
        "sort_order": 4
      }
    ],
    "already_owned": []
  }
}
```

**Response 200** (saat course kedua match badge yang sama):

```json
{
  "id": "lpc-uuid-2",
  "course": { /* ... */ },
  "is_completed": true,
  "completed_at": "2026-05-28T10:00:00.000Z",
  "badges": {
    "awarded": [],
    "already_owned": [
      {
        "id": "...",
        "code": "frontend-pemula",
        "name": "Frontend Pemula",
        "category": "frontend",
        "level": "pemula",
        "...": "..."
      }
    ]
  }
}
```

**Response 200** (saat un-toggle, atau course tidak match badge apapun):

```json
{
  "id": "lpc-uuid",
  "is_completed": false,
  "completed_at": null,
  "badges": { "awarded": [], "already_owned": [] }
}
```

---

## Frontend Integration Patterns

### A. Toast saat user toggle complete

Setelah call `PATCH .../toggle-complete/`, periksa response `badges` field:

```ts
const res = await api.patch(`/learning-paths/courses/${lpcId}/toggle-complete/`);

const { awarded, already_owned } = res.data.badges;

if (awarded.length > 0) {
  // Tampilkan animasi/toast SUKSES — 1 toast per badge baru
  awarded.forEach((badge) => {
    showBadgeAwardedToast({
      title: `Selamat! Kamu dapat badge ${badge.name}`,
      description: badge.description,
      icon: badge.icon_url || defaultIconFor(badge.category, badge.level),
    });
  });
}

if (already_owned.length > 0) {
  // Tampilkan warning toast — informational, non-blocking
  already_owned.forEach((badge) => {
    showInfoToast({
      title: `Kamu sudah punya badge ${badge.name}`,
      description: 'Badge ini sudah di-earn dari course sebelumnya.',
    });
  });
}
```

Course tetap dimark complete walaupun ada warning — `already_owned` hanya informational.

### B. Halaman Profile — daftar badge user

Fetch `GET /api/users/me/badges/` saat halaman profile dibuka. Group by `badge.category` untuk display per kategori.

```ts
const userBadges = await api.get('/users/me/badges/');
// userBadges.data adalah array UserBadge

const groupedByCategory = groupBy(userBadges.data, (ub) => ub.badge.category);
```

Suggested UX: tampilkan badge yang sudah di-earn dengan warna penuh, dan kalau mau show "belum earn" gunakan endpoint catalog `GET /api/badges/` yang punya flag `is_earned`.

### C. Dashboard Learning Path — badges section

Setelah render progress bar keseluruhan, tampilkan section "Badge yang kamu dapat dari learning path ini":

```ts
const pathBadges = await api.get(`/learning-paths/${pathId}/badges/`);
// { learning_path_id, count, results: [UserBadge, ...] }

if (pathBadges.data.count > 0) {
  renderBadgeStrip(pathBadges.data.results.map((ub) => ub.badge));
} else {
  renderEmptyState('Belum ada badge dari learning path ini. Selesaikan course untuk mendapatkan badge!');
}
```

---

## TypeScript Types (suggested)

```ts
export type BadgeCategory =
  | 'ui_ux' | 'frontend' | 'backend' | 'mobile'
  | 'data_science' | 'ml_ai' | 'devops' | 'cybersecurity';

export type BadgeLevel = 'pemula' | 'menengah' | 'mahir';

export interface Badge {
  id: string;                  // UUID
  code: string;                // e.g. "ui-ux-pemula"
  name: string;                // e.g. "UI/UX Pemula"
  description: string;
  category: BadgeCategory;
  category_label: string;      // human-readable
  level: BadgeLevel;
  level_label: string;
  icon_url: string;            // may be empty string
  sort_order: number;
}

export interface BadgeCatalogItem extends Badge {
  is_earned: boolean;
  earned_at: string | null;    // ISO 8601
}

export interface UserBadge {
  id: string;                  // UserBadge record UUID
  badge: Badge;
  earned_via_course: CourseListItem | null;
  earned_via_learning_path: { id: string; title: string } | null;
  earned_at: string;           // ISO 8601
}

export interface BadgeEvaluationResult {
  awarded: Badge[];
  already_owned: Badge[];
}

// Updated response shape from PATCH toggle-complete
export interface LearningPathCourseToggleResponse {
  id: string;
  course: CourseListItem;
  position: number;
  phase_number: number | null;
  is_completed: boolean;
  completed_at: string | null;
  is_manually_added: boolean;
  replaced_by: string | null;
  replacement_reason: string;
  replacement_context: string;
  regenerate_version: number;
  badges: BadgeEvaluationResult;
}

export interface BadgeCatalogResponse {
  count: number;
  earned_count: number;
  results: BadgeCatalogItem[];
}

export interface LearningPathBadgesResponse {
  learning_path_id: string;
  count: number;
  results: UserBadge[];
}
```

---

## Edge Cases & Hal yang Perlu Di-handle FE

| Case | Behavior backend | Yang harus FE handle |
|---|---|---|
| Toggle complete course tidak match badge apapun | `badges: { awarded: [], already_owned: [] }` | Jangan tampilkan toast — fallback ke perilaku lama |
| Course match >1 badge sekaligus | `awarded` berisi multiple badge | Loop & tampilkan toast 1 per badge, atau toast gabungan |
| User un-toggle (uncomplete) | `badges: { awarded: [], already_owned: [] }`, badge user tidak berubah | Tidak perlu update list badge user di state |
| Course atau learning path penghasil badge sudah dihapus | `earned_via_course` / `earned_via_learning_path` bisa `null` di `UserBadge` | Render dengan fallback label (mis. "Course tidak tersedia") |
| User belum menyelesaikan questionnaire | API return `403` dengan detail message dari middleware | Redirect ke halaman onboarding |
| `icon_url` kosong | String kosong `""`, bukan null | FE pakai default icon per `(category, level)` |

---

## Ringkasan untuk Implementasi FE

1. **Update tipe response** `PATCH /learning-paths/courses/<id>/toggle-complete/` — tambah field `badges`.
2. **Tampilkan toast** saat ada `awarded` atau `already_owned` di response toggle-complete.
3. **Halaman profile** → fetch `GET /api/users/me/badges/`, group by category.
4. **Dashboard learning path** → fetch `GET /api/learning-paths/<id>/badges/`, render di bawah progress section.
5. **(Opsional)** Halaman "all badges" → fetch `GET /api/badges/` untuk show locked/unlocked state.

---

## Catatan Pengembangan Backend (untuk referensi)

- Matching menggunakan word-boundary regex case-insensitive terhadap `course.tags` + `course.level`. False-positive minimal.
- Catalog di-seed lewat `python manage.py seed_badges` (idempotent — aman dijalankan ulang).
- Untuk menambah kategori/level/keyword baru, edit `apps/badges/management/commands/seed_badges.py` lalu re-run command. Atau edit langsung lewat Django admin (`/admin/badges/badge/`).
- Tidak ada signal Django — evaluasi badge dipanggil eksplisit dari `LearningPathCourseToggleCompleteView.patch()` agar mudah di-debug & di-test.
