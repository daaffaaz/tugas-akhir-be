# Task: Improve Frontend from Backend API

Dokumentasi endpoint-endpoint yang perlu diimplementasi atau diintegrasikan oleh frontend agent.

---

## Daftar Endpoint

### Learning Path — Course Management

| Method | Endpoint | Fungsi |
|--------|----------|--------|
| `POST` | `/api/rag/learning-paths/{id}/courses/add/` | Tambah 1 course dari katalog (support fase spesifik) |
| `PUT` | `/api/learning-paths/{id}/bulk-update/` | Bulk update semua courses (add/remove/reorder) |
| `PATCH` | `/api/rag/learning-paths/{id}/courses/reorder/` | Reorder urutan courses |

### Learning Path — Progress

| Method | Endpoint | Fungsi |
|--------|----------|--------|
| `PATCH` | `/api/learning-paths/courses/{id}/toggle-complete/` | Toggle course selesai/belum |
| `GET` | `/api/learning-paths/{id}/` | Detail learning path + progress per course |
| `GET` | `/api/learning-paths/` | List semua learning path + progress ringkasan |
| `GET` | `/api/learning-paths/progress/` | Global progress semua learning path user |

---

## Bagian 1: Course Management

### 1.1 Tambah Course Individual

**`POST /api/rag/learning-paths/{learning_path_id}/courses/add/`**

Menambah satu course dari katalog ke dalam learning path. Mendukung dua mode:
- **Mode fase** — course disisipkan di akhir fase tertentu, course setelahnya digeser otomatis
- **Mode tambahan** — course ditambahkan di paling akhir tanpa fase (muncul sebagai "course tambahan")

**Auth:** Bearer Token (required)

#### Request Body

```json
{
  "course_id": "550e8400-e29b-41d4-a716-446655440000",
  "phase_number": 2
}
```

| Field | Type | Required | Keterangan |
|-------|------|----------|------------|
| `course_id` | UUID | Ya | UUID course dari katalog |
| `phase_number` | integer (>= 1) | Tidak | Nomor fase tujuan. Course disisipkan di akhir fase tersebut. Jika tidak diisi, course ditambah di paling akhir tanpa fase |
| `position` | integer (>= 1) | Tidak | Posisi insert manual. Diabaikan jika `phase_number` diisi |

> **Prioritas:** `phase_number` > `position` > append di akhir

#### Cara mendapatkan `phase_number`

Setiap course di response learning path sekarang memiliki field `phase_number`. Gunakan nilai tersebut untuk mengetahui fase mana yang tersedia.

```json
// GET /api/learning-paths/{id}/ → courses[]
{
  "id": "uuid-lp-course-item",
  "position": 3,
  "phase_number": 2,        // ← gunakan nilai ini
  "course": { ... }
}
```

#### Contoh: Tambah ke Fase 2

```json
{
  "course_id": "550e8400-e29b-41d4-a716-446655440000",
  "phase_number": 2
}
```

#### Contoh: Tambah sebagai course tambahan (tanpa fase)

```json
{
  "course_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

#### Response `200 OK`

```json
{
  "id": "uuid-learning-path",
  "title": "Belajar Machine Learning",
  "topic_input": "machine learning untuk pemula",
  "description": "Learning path yang dihasilkan AI untuk belajar machine learning",
  "is_saved": true,
  "questionnaire_snapshot": {},
  "regenerate_count": 0,
  "regenerate_context": "",
  "progress_percentage": 0.0,
  "courses": [
    {
      "id": "uuid-lp-course-item",
      "course": {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "platform": {
          "id": "uuid-platform",
          "name": "Udemy",
          "base_url": "https://www.udemy.com"
        },
        "external_id": "python-ml-bootcamp",
        "title": "Python for Machine Learning",
        "instructor": "John Doe",
        "price": "99000.00",
        "reviews_count": 12000,
        "rating": "4.80",
        "description": "Kursus lengkap Python untuk Machine Learning...",
        "duration": "20 hours",
        "video_hours": "19.5",
        "reading_count": 5,
        "assignment_count": 3,
        "what_you_learn": ["Dasar Python", "NumPy", "Pandas", "Scikit-learn"],
        "tag": "python",
        "url": "https://www.udemy.com/course/python-ml-bootcamp/",
        "scraped_date": "2025-01-01",
        "level": "Beginner",
        "currency": "IDR",
        "thumbnail_url": "https://img-c.udemyassets.com/...",
        "tags": ["python", "machine-learning", "data-science"],
        "scraped_at": "2025-01-01T00:00:00Z",
        "created_at": "2025-01-01T00:00:00Z"
      },
      "position": 3,
      "is_completed": false,
      "completed_at": null,
      "is_manually_added": true,
      "replaced_by": null,
      "replacement_reason": "",
      "replacement_context": "",
      "regenerate_version": 0
    }
  ],
  "created_at": "2025-01-01T00:00:00Z",
  "updated_at": "2025-01-02T10:00:00Z"
}
```

#### Error Responses

| Status | Body | Keterangan |
|--------|------|------------|
| `404` | `{"detail": "Learning path not found."}` | Learning path tidak ditemukan / bukan milik user |
| `404` | `{"detail": "Course not found."}` | `course_id` tidak ada di katalog |
| `400` | `{"detail": "Course already exists in this learning path."}` | Course sudah ada di learning path tersebut |

---

### 1.2 Bulk Update Courses

**`PUT /api/learning-paths/{learning_path_id}/bulk-update/`**

Mengganti seluruh daftar courses dalam satu learning path sekaligus. Cocok untuk operasi reorder, hapus, atau tambah banyak course dalam satu request.

> **Perhatian:** Course yang tidak disertakan dalam array `courses` akan **dihapus** dari learning path.

**Auth:** Bearer Token (required)

#### Request Body

```json
{
  "title": "Judul Baru (opsional)",
  "courses": [
    {
      "course_id": "uuid-course-1",
      "position": 1,
      "is_manually_added": false
    },
    {
      "course_id": "uuid-course-2",
      "position": 2,
      "is_manually_added": true
    },
    {
      "course_id": "uuid-course-3",
      "position": 3
    }
  ]
}
```

| Field | Type | Required | Keterangan |
|-------|------|----------|------------|
| `title` | string | Tidak | Update judul learning path |
| `courses` | array | Ya | Daftar lengkap courses yang diinginkan |
| `courses[].course_id` | UUID | Ya | UUID course |
| `courses[].position` | integer (>= 1) | Ya | Posisi dalam learning path |
| `courses[].is_manually_added` | boolean | Tidak | Default `false`. Tandai apakah course ditambah manual oleh user |

**Validasi:**
- Tidak boleh ada duplikat `position` dalam satu request
- Tidak boleh ada duplikat `course_id` dalam satu request
- Semua `course_id` harus ada di database

#### Response `200 OK`

Format sama dengan endpoint add course (`LearningPathDetailSerializer`).

#### Error Responses

| Status | Keterangan |
|--------|------------|
| `400` | Duplikat position atau course_id |
| `400` | Salah satu course_id tidak ditemukan |
| `404` | Learning path tidak ditemukan |

---

### 1.3 Reorder Courses

**`PATCH /api/rag/learning-paths/{learning_path_id}/courses/reorder/`**

Mengubah urutan courses tanpa add/remove. Kirim array `course_ids` dalam urutan baru yang diinginkan.

**Auth:** Bearer Token (required)

#### Request Body

```json
{
  "course_ids": [
    "uuid-course-3",
    "uuid-course-1",
    "uuid-course-2"
  ]
}
```

| Field | Type | Required | Keterangan |
|-------|------|----------|------------|
| `course_ids` | UUID[] | Ya | Semua course UUID milik learning path dalam urutan baru |

#### Response `200 OK`

Format sama dengan `LearningPathDetailSerializer`.

---

## Bagian 2: Progress Pembelajaran

### 2.1 Toggle Course Selesai / Belum

**`PATCH /api/learning-paths/courses/{lp_course_id}/toggle-complete/`**

Toggle status selesai sebuah course dalam learning path. Setiap call akan membalik status `is_completed`.

> **Penting:** `{lp_course_id}` adalah `id` dari item `LearningPathCourse` (field `courses[].id` di response), **bukan** `course.id`.

**Auth:** Bearer Token (required)

#### Request Body

Tidak ada request body.

#### Response `200 OK`

```json
{
  "id": "uuid-lp-course-item",
  "course": { ... },
  "position": 2,
  "is_completed": true,
  "completed_at": "2025-05-09T10:30:00Z",
  "is_manually_added": false,
  "replaced_by": null,
  "replacement_reason": "",
  "replacement_context": "",
  "regenerate_version": 0
}
```

---

### 2.2 Detail Learning Path + Progress Per Course

**`GET /api/learning-paths/{learning_path_id}/`**

**Auth:** Bearer Token (required)

#### Response `200 OK`

```json
{
  "id": "uuid-learning-path",
  "title": "Belajar Machine Learning",
  "topic_input": "machine learning untuk pemula",
  "description": "...",
  "is_saved": true,
  "questionnaire_snapshot": {},
  "regenerate_count": 0,
  "regenerate_context": "",
  "progress_percentage": 70.0,
  "courses": [
    {
      "id": "uuid-lp-course-item",
      "course": { ... },
      "position": 1,
      "is_completed": true,
      "completed_at": "2025-05-09T10:30:00Z",
      "is_manually_added": false,
      "replaced_by": null,
      "replacement_reason": "",
      "replacement_context": "",
      "regenerate_version": 0
    }
  ],
  "created_at": "2025-01-01T00:00:00Z",
  "updated_at": "2025-05-09T10:30:00Z"
}
```

---

### 2.3 List Learning Path + Progress Ringkasan

**`GET /api/learning-paths/`**

**Auth:** Bearer Token (required)

#### Response `200 OK`

```json
[
  {
    "id": "uuid-learning-path",
    "title": "Belajar Machine Learning",
    "topic_input": "machine learning untuk pemula",
    "description": "...",
    "is_saved": true,
    "total_courses": 10,
    "completed_courses": 7,
    "progress_percentage": 70.0,
    "difficulty": "Intermediate",
    "total_duration_weeks": 8,
    "target_skills": ["Python", "Machine Learning", "Data Science"],
    "created_at": "2025-01-01T00:00:00Z",
    "updated_at": "2025-05-09T10:30:00Z"
  }
]
```

---

### 2.4 Global Progress Semua Learning Path

**`GET /api/learning-paths/progress/`**

Mengembalikan ringkasan progress user secara keseluruhan — cocok untuk halaman dashboard.

**Auth:** Bearer Token (required)

#### Response `200 OK`

```json
{
  "total_learning_paths": 5,
  "total_courses": 42,
  "total_completed_courses": 18,
  "overall_progress_percentage": 42.86,
  "completed_paths": 1,
  "in_progress_paths": 3,
  "not_started_paths": 1,
  "learning_paths": [
    {
      "id": "uuid-learning-path",
      "title": "Belajar Machine Learning",
      "is_saved": true,
      "total_courses": 10,
      "completed_courses": 7,
      "progress_percentage": 70.0,
      "created_at": "2025-01-01T00:00:00Z",
      "updated_at": "2025-05-09T10:30:00Z"
    }
  ]
}
```

#### Field Keterangan

| Field | Type | Keterangan |
|-------|------|------------|
| `total_learning_paths` | integer | Total learning path milik user |
| `total_courses` | integer | Total course di semua learning path |
| `total_completed_courses` | integer | Total course yang sudah selesai |
| `overall_progress_percentage` | float | Persentase global (0.0 – 100.0) |
| `completed_paths` | integer | Learning path yang 100% selesai |
| `in_progress_paths` | integer | Learning path yang sedang dikerjakan (sebagian selesai) |
| `not_started_paths` | integer | Learning path yang belum ada course yang diselesaikan |
| `learning_paths` | array | Ringkasan progress tiap learning path |

---

## Struktur Response: LearningPathDetail

### LearningPath

| Field | Type | Keterangan |
|-------|------|------------|
| `id` | UUID | ID learning path |
| `title` | string | Judul learning path |
| `topic_input` | string | Input topik dari user |
| `description` | string | Deskripsi learning path |
| `is_saved` | boolean | Status saved |
| `questionnaire_snapshot` | object | Snapshot data questionnaire saat dibuat |
| `regenerate_count` | integer | Berapa kali learning path di-regenerate |
| `regenerate_context` | string | Konteks terakhir regenerate |
| `progress_percentage` | float | Persentase course yang sudah completed |
| `courses` | array | Daftar courses |
| `created_at` | datetime | Waktu dibuat |
| `updated_at` | datetime | Waktu terakhir diubah |

### LearningPathCourse Item (tiap elemen di `courses`)

| Field | Type | Keterangan |
|-------|------|------------|
| `id` | UUID | ID item — gunakan ini untuk toggle-complete |
| `course` | object | Detail course |
| `position` | integer | Urutan dalam learning path |
| `phase_number` | integer/null | Nomor fase. `null` berarti course tambahan tanpa fase |
| `is_completed` | boolean | Status selesai |
| `completed_at` | datetime/null | Waktu selesai |
| `is_manually_added` | boolean | `true` jika ditambah manual user, `false` jika dari AI |
| `replaced_by` | UUID/null | ID course pengganti jika course ini diganti |
| `replacement_reason` | string | Alasan penggantian |
| `replacement_context` | string | Konteks penggantian dari AI |
| `regenerate_version` | integer | Versi regenerate saat course ini ditambahkan |

### Course Object (nested di dalam `course`)

| Field | Type | Keterangan |
|-------|------|------------|
| `id` | UUID | ID course |
| `platform` | object | `{id, name, base_url}` |
| `title` | string | Judul course |
| `instructor` | string | Nama instruktur |
| `price` | decimal string | Harga course |
| `rating` | decimal string | Rating (0.0 – 5.0) |
| `description` | string | Deskripsi course |
| `duration` | string | Durasi (contoh: "20 hours") |
| `video_hours` | decimal string | Jam video |
| `level` | string | Level (`Beginner`, `Intermediate`, `Advanced`) |
| `url` | string | URL ke halaman course |
| `thumbnail_url` | string | URL thumbnail |
| `tags` | string[] | Daftar tag course |
| `currency` | string | Mata uang harga |

---

## Panduan Penggunaan untuk Frontend

### Skenario: User menambah course ke fase spesifik

1. Fetch learning path detail → tampilkan daftar fase yang tersedia dari `courses[].phase_number` (distinct values, exclude null)
2. User pilih course dari katalog → dapat `course_id`
3. User pilih fase tujuan → dapat `phase_number`
4. Panggil `POST /api/rag/learning-paths/{id}/courses/add/` dengan `course_id` + `phase_number`
5. Response berisi learning path terbaru dengan course sudah masuk di fase yang dipilih — update state UI dari response

### Skenario: User menambah course sebagai tambahan (tanpa fase)

1. User browse katalog → dapat `course_id`
2. Panggil `POST /api/rag/learning-paths/{id}/courses/add/` hanya dengan `course_id` (tanpa `phase_number`)
3. Course ditambahkan di paling akhir dengan `phase_number: null`
4. Frontend bisa render course ini di group "Course Tambahan"

### Skenario: User drag-and-drop reorder courses

1. User selesai reorder → susun ulang array `course_ids` sesuai urutan baru
2. Panggil `PATCH /api/rag/learning-paths/{id}/courses/reorder/`
3. Update UI dari response

### Skenario: User hapus beberapa course sekaligus

1. Kumpulkan courses yang masih diinginkan user (exclude yang dihapus)
2. Panggil `PUT /api/learning-paths/{id}/bulk-update/` dengan array courses yang tersisa
3. Update UI dari response

### Skenario: User menandai course selesai

1. User klik tombol "Selesai" pada course
2. Ambil `id` dari item course (`courses[].id`, bukan `courses[].course.id`)
3. Panggil `PATCH /api/learning-paths/courses/{id}/toggle-complete/`
4. Update state UI dari response (field `is_completed` dan `completed_at`)

### Skenario: Tampilkan dashboard progress user

1. Panggil `GET /api/learning-paths/progress/` saat halaman dashboard dimuat
2. Gunakan `overall_progress_percentage` untuk progress bar global
3. Gunakan `completed_paths`, `in_progress_paths`, `not_started_paths` untuk statistik ringkasan
4. Gunakan `learning_paths[]` untuk daftar progress per learning path
