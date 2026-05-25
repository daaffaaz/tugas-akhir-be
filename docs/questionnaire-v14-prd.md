# PRD: Restrukturirani Kuesioner — dari 32Q ke 13Q

**Versi Proposal:** v3.1 (fix: hapus target_role)
**Tanggal:** 2026-05-25
**Status:** Ready for seeding — import via `python manage.py import_questions --clear`

---

## Daftar Isi

1. [Ringkasan Perubahan](#1-ringkasan-perubahan)
2. [Struktur 13 Pertanyaan Baru](#2-struktur-13-pertanyaan-baru)
3. [Logika Level: 3-Signal Weighted Scoring](#3-logika-level-3-signal-weighted-scoring)
4. [Adjustment Backend](#4-adjustment-backend)
5. [Adjustment Frontend](#5-adjustment-frontend)
6. [Integration Map: FE → BE variable_key](#6-integration-map-fe--be-variable_key)
7. [Backward Compatibility & Migrasi Data](#7-backward-compatibility--migrasi-data)
8. [Checklist Testing](#8-checklist-testing)

---

## 1. Ringkasan Perubahan

### Sebelum (32Q, 6 Section)

| # | Section | Q | Variabel |
|---|---------|---|----------|
| 1–4 | Profil & Demografi | 4 | `age_group`, `education_level`, `educational_background_relevance`, `employment_status` |
| 5–12 | Kompetensi Teknis | 8 | `os_familiarity`, `cli_proficiency`, `programming_logic_score`, `git_competency`, `problem_solving_independence`, `data_literacy_score`, `english_technical_proficiency`, `project_portfolio_count` |
| 13–17 | Ketersediaan Waktu | 5 | `weekly_availability_hours`, `learning_session_span`, `preferred_time_slot`, `target_completion_duration`, `login_frequency_intent` |
| 18–23 | Gaya Belajar | 6 | `learning_modality_preference`, `practicality_ratio`, `learning_curve_steepness`, `social_dependency_level`, `assessment_type_preference`, `learning_curve_steepness` |
| 23–25 | Tujuan & Motivasi | 2 | `primary_motivation`, `certification_importance` |
| 26–32 | Minat & Hardware | 7 | `interest_frontend_ui`, `interest_data_math`, `interest_infrastructure`, `negative_constraint`, `hardware_constraint`, `bandwidth_constraint`, `monetary_constraint` |

### Sesudah (14Q, 2 Group)

| # | Section | Q | Variabel |
|---|---------|---|----------|
| Qd1–Qd4 | **DEMOGRAFI** (tidak dikirim ke AI) | 4 | `age_group`, `education_level`, `educational_background_relevance`, `employment_status` |
| Qa1 | **SUB-BAGIAN A** — Level Signal #1 | 1 | `programming_familiarity` |
| Qa2 | **SUB-BAGIAN A** — Level Signal #2 | 1 | `domain_comfort` |
| Qa3 | **SUB-BAGIAN A** — Level Signal #3 (validasi) | 1 | `formal_preparation` |
| Qa4 | **SUB-BAGIAN B** — Preferensi | 1 | `weekly_availability_hours` |
| Qa5 | **SUB-BAGIAN B** — Preferensi | 1 | `learning_modality_preference` |
| Qa6 | **SUB-BAGIAN B** — Preferensi | 1 | `practicality_ratio` |
| Qa7 | **SUB-BAGIAN B** — Preferensi | 1 | `primary_motivation` |
| Qa8 | **SUB-BAGIAN B** — Preferensi | 1 | `monetary_constraint` |
| Qa9 | **SUB-BAGIAN B** — Preferensi | 1 | `certification_importance` |

### Apa yang DIHAPUS (19Q dihapus total)

- `os_familiarity`, `cli_proficiency`, `programming_logic_score`, `git_competency`, `problem_solving_independence`, `data_literacy_score`, `english_technical_proficiency`, `project_portfolio_count`
- `learning_session_span`, `preferred_time_slot`, `target_completion_duration`, `login_frequency_intent`
- `learning_curve_steepness`, `social_dependency_level`, `assessment_type_preference`
- `interest_frontend_ui`, `interest_data_math`, `interest_infrastructure`, `negative_constraint`, `hardware_constraint`, `bandwidth_constraint`
- `target_role`

---

## 2. Struktur 13 Pertanyaan Baru

### Group A: Demografi (Qd1–Qd4) — analytics only, TIDAK dikirim ke AI

> Frontend mengumpulkan data ini tapi **TIDAK** dikirim dalam payload saat submit kuesioner. Backend tetap simpan ke DB (untuk analytics), tapi sistem RAG/roadmap generation mengabaikan variabel ini.

```json
// GET /api/questions/  — Question records tetap ada untuk kompatibilitas
// tapi frontend HANYA kirim 9 jawaban (Qa1–Qa9) ke POST /api/users/questionnaire/
// Backend tetap accept 13 jawaban tapi AI prompt hanya baca variable_key yang relevan
```

### Qd1 — `age_group`

| Option | Value | Label |
|--------|-------|-------|
| A | `<18` | Kurang dari 18 tahun |
| B | `18-24` | 18–24 tahun |
| C | `25-34` | 25–34 tahun |
| D | `35-44` | 35–44 tahun |
| E | `>45` | Lebih dari 45 tahun |

### Qd2 — `education_level`

| Option | Value | Label |
|--------|-------|-------|
| A | `sma` | SMA/SMK |
| B | `d3d4` | D3/D4 |
| C | `s1` | S1 (Sarjana) |
| D | `s2s3` | S2/S3 |
| E | `other` | Lainnya |

### Qd3 — `educational_background_relevance`

| Option | Value | Label |
|--------|-------|-------|
| A | `highly_related` | Ya, Sangat Terkait (IT/SI/Ilkom) |
| B | `somewhat_related` | Agak Terkait (Teknik Elektro/Matematika) |
| C | `not_related` | Tidak Terkait (Sosial/Ekonomi/Sastra) |

### Qd4 — `employment_status`

| Option | Value | Label |
|--------|-------|-------|
| A | `student` | Pelajar/Mahasiswa |
| B | `fresh_graduate` | Fresh Graduate (Jobseeker) |
| C | `employee_non_it` | Karyawan (Non-IT) |
| D | `employee_it` | Karyawan (IT) |
| E | `freelancer` | Freelancer |

---

### Sub-Bagian A: Level Measurement (Qa1–Qa3)

#### Qa1 — `programming_familiarity` (Signal #1 — aktivitas coding aktual)

> Bobot dalam level_score: **35%**

```
"Seberapa sering Anda menulis kode / script dalam pekerjaan/hobi Anda?"
```

| Option | Value | Level | Skor |
|--------|-------|-------|------|
| A | `never` | Beginner | 0.0 |
| B | `rarely` | Beginner-Lower Intermediate | 0.25 |
| C | `weekly` | Intermediate | 0.55 |
| D | `daily_pro` | Advanced | 1.0 |

#### Qa2 — `domain_comfort` (Signal #2 — comfort di domain spesifik)

> Bobot dalam level_score: **40%** (paling tinggi — indikasi paling akurat)

```
"Sebelum mengikuti program ini, seberapa nyaman Anda dengan bidang yang Anda tuju?"
```

| Option | Value | Level | Skor |
|--------|-------|-------|------|
| A | `not_familiar` | Beginner | 0.0 |
| B | `theoretical_only` | Beginner-Lower Intermediate | 0.25 |
| C | `light_practice` | Lower Intermediate | 0.40 |
| D | `proficient` | Intermediate-Upper Intermediate | 0.70 |
| E | `professional` | Advanced | 1.0 |

#### Qa3 — `formal_preparation` (Signal #3 — validasi dari sudut pendidikan/formal preparation)

```
"Apa yang PALING menggambarkan persiapan Anda untuk belajar di bidang ini?"
```

| Option | Value | Level | Skor |
|--------|-------|-------|------|
| A | `none` | Beginner | 0.0 |
| B | `basic_school` | Lower Intermediate | 0.35 |
| C | `portfolio_small` | Intermediate | 0.60 |
| D | `work_experience` | Advanced | 1.0 |

---

### Sub-Bagian B: Preference & Goal (Qa4–Qa10)

#### Qa4 — `weekly_availability_hours`

```
"Berapa jam REALISTIS yang bisa Anda alokasikan untuk belajar per minggu?"
```

| Option | Value | Label |
|--------|-------|-------|
| A | `<3` | < 3 jam (Sangat Sibuk) |
| B | `3-7` | 3–7 jam (Santai) |
| C | `8-14` | 8–14 jam (Moderat) |
| D | `15-25` | 15–25 jam (Intensif) |
| E | `>25` | > 25 jam (Full Time) |

#### Qa5 — `learning_modality_preference`

```
"Format materi mana yang paling cepat membuat Anda paham?"
```

| Option | Value | Label |
|--------|-------|-------|
| A | `video` | Video (Visual & Audio) |
| B | `text` | Teks/Artikel (Membaca & Skimming) |
| C | `interactive` | Interactive Code (Langsung ketik di browser) |
| D | `project` | Project-based (Langsung praktek kasus nyata) |

#### Qa6 — `practicality_ratio`

```
"Bagaimana komposisi Teori vs Praktek yang Anda inginkan?"
```

| Option | Value | Label |
|--------|-------|-------|
| A | `theory_heavy` | Banyak Teori (70%), Sedikit Praktek (30%) |
| B | `balanced` | Seimbang (50% Teori – 50% Praktek) |
| C | `practice_heavy` | Dominan Praktek/Hands-on (80%) |

#### Qa7 — `primary_motivation`

```
"Apa tujuan utama mengikuti program ini?"
```

| Option | Value | Label |
|--------|-------|-------|
| A | `career_switch` | Cari Kerja Baru (Career Switch) |
| B | `upskilling` | Promosi / Upskilling di tempat kerja sekarang |
| C | `freelance` | Freelance / Side Hustle |
| D | `academic` | Akademis / Kuliah |
| E | `hobby` | Hobi semata |

#### Qa8 — `monetary_constraint`

```
"Berapa budget maksimal untuk pembelian tools/lisensi software?"
```

| Option | Value | Label |
|--------|-------|-------|
| A | `free_only` | Rp 0 — Harus gratis / Open source |
| B | `under_500k` | < Rp 500.000 |
| C | `no_limit` | Tidak Masalah (Ada budget khusus) |

#### Qa9 — `certification_importance`

```
"Seberapa penting sertifikat kelulusan bagi Anda?"
```

| Option | Value | Label |
|--------|-------|-------|
| A | `very_important` | Sangat Penting — Untuk CV / Syarat lamaran |
| B | `nice_to_have` | Biasa saja — Nice to have |
| C | `not_important` | Tidak Penting — Yang penting ilmunya |

---

## 3. Logika Level: 3-Signal Weighted Scoring

### 3.1 Skor per Signal

Setiap jawaban memiliki skor numerik (`level_score_value`):

| Signal | `programming_familiarity` | Skor | `domain_comfort` | Skor | `formal_preparation` | Skor |
|--------|---------------------------|------|------------------|------|---------------------|------|
| Beginner | `never` (A) | 0.0 | `not_familiar` (A) | 0.0 | `none` (A) | 0.0 |
| Beginner-Lower Int | `rarely` (B) | 0.25 | `theoretical_only` (B) | 0.25 | — | — |
| Lower Intermediate | — | — | `light_practice` (C) | 0.40 | `basic_school` (B) | 0.35 |
| Intermediate | `weekly` (C) | 0.55 | `proficient` (D) | 0.70 | `portfolio_small` (C) | 0.60 |
| Advanced | `daily_pro` (D) | 1.0 | `professional` (E) | 1.0 | `work_experience` (D) | 1.0 |

### 3.2 Weighted Score Formula

```
level_score = (
    programming_familiarity_score × 0.35 +
    domain_comfort_score         × 0.40 +
    formal_preparation_score     × 0.25
)
```

### 3.3 Level Bucket

| level_score | Level Label | Used by RAG |
|-------------|-------------|-------------|
| 0.00 – 0.35 | `Beginner` | ✓ |
| 0.35 – 0.55 | `Lower Intermediate` | ✓ |
| 0.55 – 0.75 | `Intermediate` | ✓ |
| 0.75 – 1.00 | `Advanced` | ✓ |

### 3.4 Conflict Detection

Jika 3 sinyal menghasilkan level yang berbeda > 1 bucket, gunakan **weighted majority**:

```
score_1 = programming_familiarity_score  × 0.35
score_2 = domain_comfort_score          × 0.40
score_3 = formal_preparation_score       × 0.25

# Urutkan descending → ambil weighted majority (score dengan bobot tertinggi)
# domain_comfort (bobot 0.40) paling kuat → menang jika ada conflict
```

**Contoh conflict:**
- Qa1 = Advanced (score 1.0)
- Qa2 = Beginner (score 0.0)
- Qa3 = Intermediate (score 0.60)

→ `domain_comfort` dengan bobot 0.40 menang → **Intermediate** (karena 0.70 × 0.40 = 0.28 > 0.20 vs 0.55 × 0.35 = 0.19)

---

## 4. Adjustment Backend

### 4.1 Database — Migrasi Schema (Manual SQL)

Dua pendekatan tersedia. Pilih salah satu:

#### Opsi A: Soft Deprecation (Recommended — backward compat)

- Tambah kolom `is_active` ke model `Question` → default `True`
- Pertanyaan yang dihapus di-set `is_active = False`
- `GET /api/questions/` menambahkan filter `is_active=True` (hanya pertanyaan aktif)
- API tetap menerima semua 32 jawaban (dari user lama) tanpa error
- User baru hanya melihat 14 pertanyaan; DB menyimpan 32 record

```sql
-- Tambahkan kolom is_active
ALTER TABLE questions ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE;

-- Nonaktifkan 18 pertanyaan yang dihapus
UPDATE questions
SET is_active = FALSE
WHERE order_number IN (
    5,6,7,8,9,10,11,12,
    14,15,16,17,
    19,20,21,22,23,
    26,27,28,29,30,31,32
);
```

#### Opsi B: Hard Cut (Bersih, untuk fresh DB)

```sql
-- Hapus record pertanyaan yang dihapus
DELETE FROM questions WHERE order_number NOT IN (1,2,3,4,33,34,35,36,...14Q);
-- Dan update order_number jadi 1-14
```

**Rekomendasi:** Gunakan Opsi A agar user yang sudah mengisi kuesioner lama tidak kehilangan data.

### 4.2 Model Adjustment

**File:** `apps/questionnaires/models.py`

```python
class Question(models.Model):
    # ... existing fields ...
    is_active = models.BooleanField(default=True)  # ← Tambahan

    class Meta:
        # existing ...
        # Tambahan index untuk query performa
        indexes = [
            models.Index(fields=['is_active', 'order_number']),
        ]
```

**Validasi saat submit (`_validate_answer_rows`):**

```python
def _validate_answer_rows(rows: list[dict]) -> dict:
    """
    Validate submission:
    - Accept either 14 new questions OR 32 old questions (backward compat)
    - new: only active questions
    - old: all questions (from existing users who need to re-take)
    """
    active_qs = Question.objects.filter(is_active=True)
    expected_new = active_qs.count()   # should be 14
    total_qs    = Question.objects.count()  # may include inactive (old users)

    if len(rows) == expected_new:
        # New user flow — validate only active questions
        questions = {q.id: q for q in active_qs}
    elif len(rows) == total_qs:
        # Old user re-take flow — accept all
        questions = {q.id: q for q in Question.objects.all()}
    else:
        raise ValidationError(
            {'detail': f'Expected {expected_new} answers (new) or {total_qs} (old), got {len(rows)}.'},
        )
    # ... rest of validation unchanged ...
```

### 4.3 CSV Import — Perbarui Source Data

**File:** `data/pertanyaan_kuesioner.csv`

Buat file baru `data/pertanyaan_kuesioner_v14.csv` dengan 14 pertanyaan baru.

Run import:

```bash
python manage.py import_questions data/pertanyaan_kuesioner_v14.csv
```

### 4.4 Level Computation Logic — Tambahkan di `_build_user_profile`

**File:** `apps/rag/views.py` — update `_build_user_profile()`

```python
# ── Level Scoring ──────────────────────────────────────────────────────────

# Skor per jawaban, range 0.0 – 1.0
_PROGRAMMING_FAMILIARITY_SCORES = {
    'A': 0.00,   # never → Beginner
    'B': 0.25,   # rarely → Beginner-Lower Intermediate
    'C': 0.55,   # weekly → Intermediate
    'D': 1.00,   # daily_pro → Advanced
}

_DOMAIN_COMFORT_SCORES = {
    'A': 0.00,   # not_familiar → Beginner
    'B': 0.25,   # theoretical_only → Beginner-Lower Intermediate
    'C': 0.40,   # light_practice → Lower Intermediate
    'D': 0.70,   # proficient → Intermediate-Upper Intermediate
    'E': 1.00,   # professional → Advanced
}

_FORMAL_PREPARATION_SCORES = {
    'A': 0.00,   # none → Beginner
    'B': 0.35,   # basic_school → Lower Intermediate
    'C': 0.60,   # portfolio_small → Intermediate
    'D': 1.00,   # work_experience → Advanced
}

_WEIGHTS = {
    'programming_familiarity': 0.35,
    'domain_comfort':          0.40,
    'formal_preparation':       0.25,
}


def _compute_level(answers: dict[str, UserQuestionnaireAnswer]) -> str:
    """
    Hitung level user dari 3-signal weighted average.
    answers: dict { variable_key: UserQuestionnaireAnswer instance }
    """
    s1 = _PROGRAMMING_FAMILIARITY_SCORES.get(
        answers.get('programming_familiarity', AnswerMock(option='A')).answer_option, 0.0
    )
    s2 = _DOMAIN_COMFORT_SCORES.get(
        answers.get('domain_comfort', AnswerMock(option='A')).answer_option, 0.0
    )
    s3 = _FORMAL_PREPARATION_SCORES.get(
        answers.get('formal_preparation', AnswerMock(option='A')).answer_option, 0.0
    )

    score = s1 * _WEIGHTS['programming_familiarity'] \
          + s2 * _WEIGHTS['domain_comfort'] \
          + s3 * _WEIGHTS['formal_preparation']

    if score <= 0.35:
        return 'Beginner'
    elif score <= 0.55:
        return 'Lower Intermediate'
    elif score <= 0.75:
        return 'Intermediate'
    else:
        return 'Advanced'


class AnswerMock:
    """Helper for defaulting missing answers."""
    def __init__(self, option='A'):
        self.answer_option = option
```

**Update `_build_user_profile()`:**

```python
# Di dalam _build_user_profile(), setelah membaca answers:
answer_map = {ans.question.variable_key: ans for ans in answers}

# Compute level from 3 signals
profile['level'] = _compute_level(answer_map)

# Prefs from UserPreferences model (if any — for backward compat):
if hasattr(user, 'preferences') and user.preferences:
    prefs = user.preferences
    profile.setdefault('current_skills', []).extend(
        [v for v in (prefs.cli_level, prefs.logic_level) if v]
    )
    # ... existing pref reading code ...
```

### 4.5 AI Prompt Update — Sertakan Certification Importance

**File:** `apps/rag/prompts.py`

`certification_importance` dari Qa10 perlu ada di prompt yang dikirim ke AI:

```python
# Tambahkan di USER_PROMPT_TEMPLATE, di dalam {user_profile} block:
# certification_importance akan di-inject oleh _build_user_profile_text()

def build_user_profile_text(..., certification_importance: str = '') -> str:
    lines = [
        # ... existing fields ...
    ]
    if certification_importance:
        lines.append(f"Certification Preference: {certification_importance}")
    return '\n'.join(lines)
```

**Pastikan `certification_importance` dibaca di `_build_user_profile` dan passed ke prompt builder:**

```python
# apps/rag/views.py — _build_user_profile()
for ans in answers:
    key = ans.question.variable_key
    if not key:
        continue
    val = ans.answer_option
    # ... existing mappings ...
    elif key == 'certification_importance':
        profile['certification_importance'] = val
```

### 4.6 Frontend API Contract — Ubah Expected Answer Count

| Endpoint | Sebelum | Sesudah |
|----------|---------|---------|
| `GET /api/questions/` | 32 rows | 14 rows (`is_active=True`) |
| `POST /api/users/questionnaire/` | array of 32 | array of 14 (new users) |
| `PATCH /api/users/questionnaire/` | array of N | array of N (unchanged) |

---

## 5. Adjustment Frontend

### 5.1 Question Fetching — Handle Active Filter

```typescript
// GET /api/questions/ — fetch with is_active filter
const response = await fetch('/api/questions/');
const questions = await response.json();

// Filter only active questions (for v14 flow)
// Backend should return only is_active=True, but double-check
const activeQuestions = questions.filter((q: any) => q.is_active !== false);
const demographyQuestions = activeQuestions.filter(/* section === "DEMOGRAFI" */);
const levelQuestions      = activeQuestions.filter(/* section === "SUB-BAGIAN A" */);
const preferenceQuestions = activeQuestions.filter(/* section === "SUB-BAGIAN B" */);
```

### 5.2 Two-Group Rendering

Pertanyaan ditampilkan dalam 2 grup:

```
┌──────────────────────────────────────────────┐
│ STEP 1: Tentang Anda (4 pertanyaan)         │  ← Qd1–Qd4 (opsional, bisa skip)
│                                               │
│  Qd1: Usia?                                   │
│  Qd2: Pendidikan?                             │
│  ...                                          │
└──────────────────────────────────────────────┘

┌──────────────────────────────────────────────┐
│ STEP 2: Assess Level Anda (3 pertanyaan)      │  ← Qa1–Qa3
│                                               │
│  Qa1: Seberapa sering coding?                 │
│  Qa2: Seberapa nyaman dengan bidang ini?      │
│  Qa3: Persiapan formal Anda?                  │
└──────────────────────────────────────────────┘

┌──────────────────────────────────────────────┐
│ STEP 3: Preferensi & Tujuan (6 pertanyaan)     │  ← Qa4–Qa9
│                                               │
│  Qa4: Jam per minggu?                         │
│  Qa5: Format materi?                         │
│  Qa6: Teori vs Praktek?                      │
│  Qa7: Motivasi utama?                        │
│  Qa8: Budget?                                 │
│  Qa9: Sertifikat?                            │
└──────────────────────────────────────────────┘
```

### 5.3 Submit Payload — Only 13 Answers

```typescript
interface QuestionnaireSubmit {
  answers: {
    question_id: string;   // UUID of question
    answer_option: string; // 'A' | 'B' | 'C' | 'D' | 'E'
  }[];
}

// Kirim 9 jawaban (Qa1–Qa9 — Sub-Bagian A + Sub-Bagian B)
const payload = selectedAnswers.map(answer => ({
  question_id: answer.question_id,
  answer_option: answer.selectedOption, // 'A', 'B', 'C', etc.
}));

const response = await fetch('/api/users/questionnaire/', {
  method: 'POST',
  headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
  body: JSON.stringify(payload),
});
```

### 5.4 Level Indicator — Live Preview dari 3 Jawaban

Saat user menjawab Qa1, Qa2, Qa3, tampilkan "Level Indicator" secara real-time:

```typescript
const SIGNAL_SCORES = {
  programming_familiarity: { A: 0.0, B: 0.25, C: 0.55, D: 1.0 },
  domain_comfort:          { A: 0.0, B: 0.25, C: 0.40, D: 0.70, E: 1.0 },
  formal_preparation:      { A: 0.0, B: 0.35, C: 0.60, D: 1.0 },
};

const WEIGHTS = { programming_familiarity: 0.35, domain_comfort: 0.40, formal_preparation: 0.25 };

function computeLevel(answers: Record<string, string>) {
  const score =
    (SIGNAL_SCORES.programming_familiarity[answers.programming_familiarity] || 0) * 0.35 +
    (SIGNAL_SCORES.domain_comfort[answers.domain_comfort] || 0)               * 0.40 +
    (SIGNAL_SCORES.formal_preparation[answers.formal_preparation] || 0)        * 0.25;

  if (score <= 0.35) return { label: 'Beginner', color: '#22c55e' };
  if (score <= 0.55) return { label: 'Lower Intermediate', color: '#f59e0b' };
  if (score <= 0.75) return { label: 'Intermediate', color: '#3b82f6' };
  return { label: 'Advanced', color: '#8b5cf6' };
}
```

**UI Mockup — Level Indicator (appears after Qa3):**

```
┌─────────────────────────────────────┐
│  🎯 Level Anda: Intermediate        │
│  ████████████░░░░░░░░  65%         │
│                                     │
│  Berdasarkan 3 penilaian Anda:     │
│  • Coding frequency  → Intermediate │
│  • Domain comfort    → Intermediate │
│  • Formal prep      → Intermediate  │
└─────────────────────────────────────┘
```

### 5.5 Skip Demography Step (Optional)

Qd1–Qd4 (Demografi) bersifat opsional. Frontend boleh menampilkan step ini tapi user boleh skip tanpa memilih jawaban.

**Dua pendekatan:**
- **Pendekatan A:** Render step tapi tampilkan tombol "Lewati" di samping "Lanjut" — jawaban demografi TIDAK wajib dikirim
- **Pendekatan B:** Hilangkan step demografi sepenuhnya dari UI — datanya tetap tersimpan di DB via `UserPreferences` yang sudah ada

**Rekomendasi:** Gunakan Pendekatan B (hilangkan step demografi dari UI) karena:
1. User sudah mengisi data demografi saat registrasi (jika ada)
2. Mengurangi friction di questionnaire flow
3. 4 pertanyaan demografi → 0 di payload = lebih simpel

Jika menggunakan Pendekatan B, payload POST tetap 9 jawaban (Qa1–Qa9 saja).

### 5.6 Frontend State Management

```typescript
interface QuestionnaireState {
  currentStep: number;           // 1-indexed
  levelSignalAnswers: {
    programming_familiarity?: string;  // 'A'|'B'|'C'|'D'
    domain_comfort?: string;           // 'A'|'B'|'C'|'D'|'E'
    formal_preparation?: string;       // 'A'|'B'|'C'|'D'
  };
  preferenceAnswers: {
    weekly_availability_hours?: string;
    learning_modality_preference?: string;
    practicality_ratio?: string;
    primary_motivation?: string;
    monetary_constraint?: string;
    certification_importance?: string;
  };
  computedLevel?: string;
  computedLevelScore?: number;  // 0.0–1.0 (for display)
}
```

### 5.7 Progress Stepper UI

```
[●●○○○○] Langkah 1: Evaluasi Level
  ↓
[○○●○○○] Langkah 2: Preferensi & Tujuan
  ↓
[○○○○●○] Selesai — Generate Roadmap!
```

atau single-page scroll:

```
┌─ Assess Level ─────────────────────────┐
│ Qa1: [================================]│
│ Qa2: [================================]│
│ Qa3: [================================]│
│                                         │
│ [🎯 Level: Intermediate — 65%]        │  ← Live preview
│                                         │
│ [ Lanjut ke Preferensi → ]             │
└─────────────────────────────────────────┘
┌─ Preferensi & Tujuan ─────────────────┐
│ Qa4–Qa10                              │
│ [ Submit Kuesioner ]                  │
└─────────────────────────────────────────┘
```

---

## 6. Integration Map: FE → BE variable_key

### Payload Field Mapping

| FE Field | `variable_key` | Q# | Tipe Value | Keterangan |
|----------|---------------|-----|-----------|-------------|
| `question_id` → Qa1 | `programming_familiarity` | Qa1 | `A\|B\|C\|D` | Coding frequency |
| `question_id` → Qa2 | `domain_comfort` | Qa2 | `A\|B\|C\|D\|E` | Domain-specific comfort |
| `question_id` → Qa3 | `formal_preparation` | Qa3 | `A\|B\|C\|D` | Formal education level |
| `question_id` → Qa4 | `weekly_availability_hours` | Qa4 | `A\|B\|C\|D\|E` | Weekly hours bucket |
| `question_id` → Qa5 | `learning_modality_preference` | Qa5 | `A\|B\|C\|D` | Format preference |
| `question_id` → Qa6 | `practicality_ratio` | Qa6 | `A\|B\|C` | Theory vs practice |
| `question_id` → Qa7 | `primary_motivation` | Qa7 | `A\|B\|C\|D\|E` | Main goal |
| `question_id` → Qa8 | `monetary_constraint` | Qa8 | `A\|B\|C` | Budget constraint |
| `question_id` → Qa9 | `certification_importance` | Qa9 | `A\|B\|C` | In prompt for AI |

### RAG Prompt Variable Usage

Variable dari kuesioner yang dibaca di `_build_user_profile()` dan masuk ke prompt AI:

| variable_key | Digunakan di RAG? | Purpose |
|-------------|-------------------|---------|
| `programming_familiarity` | ✓ (via level_score) | Level determination |
| `domain_comfort` | ✓ (via level_score) | Level determination |
| `formal_preparation` | ✓ (via level_score) | Level determination |
| `weekly_availability_hours` | ✓ | Phase count estimation |
| `learning_modality_preference` | ✓ | Format filter |
| `practicality_ratio` | ✓ | Course selection bias |
| `primary_motivation` | ✓ | AI tone/persona dalam prompt |
| `monetary_constraint` | ✓ | Budget filter |
| `certification_importance` | ✓ (via additional_context) | AI recommendation tone |

Variable yang DIHAPUS dari RAG (tidak dipakai lagi):

| variable_key Lama | Previously Used For | Digantikan Oleh |
|-------------------|---------------------|-----------------|
| `cli_proficiency` | Part of level | `domain_comfort` (Qa2) |
| `programming_logic_score` | Part of level | `programming_familiarity` (Qa1) |
| `git_competency` | Part of level | `formal_preparation` (Qa3) |
| `project_portfolio_count` | Part of level | `formal_preparation` (Qa3) |
| `data_literacy_score` | Part of level | `domain_comfort` (Qa2) |
| `english_technical_proficiency` | Skill gap | Dihapus — tidak critical |
| `learning_session_span` | Phase duration | `weekly_availability_hours` |
| `preferred_time_slot` | Study pattern | Dihapus |
| `target_completion_duration` | Roadmap duration | `weekly_availability_hours` (derived) |
| `login_frequency_intent` | Engagement signal | Dihapus |
| `learning_curve_steepness` | Course pacing | Dihapus |
| `social_dependency_level` | Community filter | Dihapus |
| `assessment_type_preference` | Evaluation filter | Dihapus |
| `interest_*` fields | Interest matching | Dihapus — topic berasal dari input user, bukan kuesioner |
| `hardware_constraint` | Device filter | Dihapus |
| `bandwidth_constraint` | Video quality | Dihapus |
| `negative_constraint` | Avoidance filter | Dihapus |

---

## 7. Backward Compatibility & Migrasi Data

### 7.1 Existing Users with Old 32-Answer Data

User yang sudah mengisi kuesioner lama (32Q) bisa:
- **Tetap menggunakan roadmap lama** → tidak perlu retake
- **Retake kuesioner** → POST `/api/users/questionnaire/` (PATCH) dengan 13 jawaban baru → level di-recompute

**Endpoint baru untuk retake:**

```
PATCH /api/users/questionnaire/
Body: array of 14 AnswerItemSerializer
```

Validasi harus accept array length 14 (new) atau 32 (old).

### 7.2 Migration Checklist

- [ ] Tambah kolom `is_active` ke `questions` table (Opsi A)
- [ ] Nonaktifkan 18 pertanyaan lama (Opsi A)
- [ ] Update `QuestionListView` untuk filter `is_active=True`
- [ ] Update `_validate_answer_rows` untuk accept 14 atau 32 jawaban
- [ ] Update `_build_user_profile` dengan `_compute_level()`
- [ ] Tambahkan scoring maps di `rag/views.py`
- [ ] Update CSV import script untuk handle `is_active` field
- [ ] Import 14 pertanyaan baru ke database
- [ ] Update AI prompt builder untuk baca `certification_importance`
- [ ] Update frontend questionnaire flow (14Q, 3-group, live level preview)
- [ ] Test: user baru bisa submit 14 jawaban
- [ ] Test: user lama bisa retake dengan 14 jawaban baru
- [ ] Test: level computation menghasilkan level yang benar
- [ ] Test: roadmap generation menggunakan level baru

---

## 8. Checklist Testing

### Backend

- [ ] `GET /api/questions/` returns exactly 14 questions (new user flow)
- [ ] `GET /api/questions/` returns 14 questions for new users, 32 for old users (backward compat)
- [ ] `POST /api/users/questionnaire/` accepts array of 14 answers
- [ ] `PATCH /api/users/questionnaire/` accepts array of 13 answers (retake flow)
- [ ] Level computation: Qa1=A(never), Qa2=A(not_familiar), Qa3=A(none) → `Beginner`
- [ ] Level computation: Qa1=D(daily_pro), Qa2=E(professional), Qa3=D(work_exp) → `Advanced`
- [ ] Level computation: mixed signals → weighted majority
- [ ] `certification_importance` appears in RAG prompt context
- [ ] `monetary_constraint` filters course price correctly
- [ ] Old 32-answer data still readable after migration

### Frontend

- [ ] 13 questions displayed (not 32)
- [ ] Demography step optional (or hidden)
- [ ] Level indicator updates live after Qa3 answered
- [ ] Submit payload contains exactly 9 answer items (Qa1–Qa9)
- [ ] Progress stepper shows correct steps
- [ ] Error shown if answer missing for required question
- [ ] Retake flow: old answers pre-populated from GET response

### RAG / Roadmap

- [ ] Roadmaps generated use new level bucket (Beginner/Lower Intermediate/Intermediate/Advanced)
- [ ] `weekly_availability_hours` affects phase count
- [ ] `monetary_constraint` respects budget filter
- [ ] `certification_importance` reflected in AI recommendation tone
- [ ] No hallucinated courses — all courses exist in DB

---

## Appendix A: Seeding via JSON

Seed data ada di `docs/questionnaire.json` (v3.0, 13Q).

```bash
# Hapus semua pertanyaan lama, import 13Q baru
python manage.py import_questions --clear
```

`docs/questionnaire.json` adalah single source of truth — tidak perlu file CSV terpisah.

*Document ini adalah living document — update sesuai hasil testing dan feedback user.*