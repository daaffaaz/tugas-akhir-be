# FE PRD: Kuesioner v3 — 13Q Adjustment

**Versi:** v3.0  
**Tanggal:** 2026-05-25  
**Status:** Ready for implementation

---

## 1. Apa yang Berubah

| Sebelum | Sesudah |
|---------|---------|
| 32 pertanyaan | **13 pertanyaan** |
| 6 section | **3 group** |
| Level dari 8Q teknis | Level dari **3Q + weighted scoring** |
| `target_role` ada | **`target_role` dihapus** |
| Payload 32 jawaban | Payload **9 jawaban** (Qa1–Qa9) |

### Struktur 13Q Baru

```
DEMOGRAFI (Qd1–Qd4)           ← opsional, analytics only
  Qd1: Usia
  Qd2: Pendidikan
  Qd3: Relevansi jurusan
  Qd4: Status pekerjaan

SUB-BAGIAN A — LEVEL (Qa1–Qa3) ← Wajib, hitung level
  Qa1: Seberapa sering coding?
  Qa2: Seberapa nyaman dengan bidang ini?
  Qa3: Persiapan formal Anda?

SUB-BAGIAN B — PREFERENCE (Qa4–Qa9) ← Wajib
  Qa4: Jam per minggu?
  Qa5: Format materi?
  Qa6: Teori vs Praktek?
  Qa7: Motivasi utama?
  Qa8: Budget?
  Qa9: Sertifikat?
```

---

## 2. API Contract

### GET /api/questions/

Backend mengembalikan **13 pertanyaan aktif**. FE tinggal render semua yang di-return.

```json
// Response
[
  { "id": "...", "order_number": 1, "section": "DEMOGRAFI", "question_text": "...", "variable_key": "age_group", "options_json": {...} },
  // ... 13 items total
]
```

> Tidak perlu filter manual — API sudah filter `is_active=True`.

### POST /api/users/questionnaire/

**Payload: 9 jawaban** (Qa1–Qa9 saja, demografi TIDAK wajib):

```json
{
  "answers": [
    { "question_id": "uuid-qa1", "answer_option": "C" },
    { "question_id": "uuid-qa2", "answer_option": "D" },
    { "question_id": "uuid-qa3", "answer_option": "B" },
    { "question_id": "uuid-qa4", "answer_option": "B" },
    { "question_id": "uuid-qa5", "answer_option": "A" },
    { "question_id": "uuid-qa6", "answer_option": "C" },
    { "question_id": "uuid-qa7", "answer_option": "A" },
    { "question_id": "uuid-qa8", "answer_option": "B" },
    { "question_id": "uuid-qa9", "answer_option": "B" }
  ]
}
```

> Demografi (Qd1–Qd4) bisa di-skip — tidak masuk payload.

---

## 3. UI Flow

```
[STEP 1: Evaluasi Level]          ← Qa1, Qa2, Qa3
  ├── Live level indicator setelah Qa3 answered
  └── "Lanjut ke Preferensi →"

[STEP 2: Preferensi & Tujuan]    ← Qa4, Qa5, Qa6, Qa7, Qa8, Qa9
  └── "Submit Kuesioner"
```

### Level Indicator (muncul setelah Qa3 dijawab)

```typescript
function computeLevel(signalAnswers) {
  const scores = {
    programming_familiarity: { A: 0.0, B: 0.25, C: 0.55, D: 1.0 },
    domain_comfort:          { A: 0.0, B: 0.25, C: 0.40, D: 0.70, E: 1.0 },
    formal_preparation:      { A: 0.0, B: 0.35, C: 0.60, D: 1.0 },
  };
  const score =
    scores.programming_familiarity[signalAnswers.programming_familiarity] * 0.35 +
    scores.domain_comfort[signalAnswers.domain_comfort]                     * 0.40 +
    scores.formal_preparation[signalAnswers.formal_preparation]             * 0.25;

  if (score <= 0.35) return { label: 'Beginner', color: '#22c55e' };
  if (score <= 0.55) return { label: 'Lower Intermediate', color: '#f59e0b' };
  if (score <= 0.75) return { label: 'Intermediate', color: '#3b82f6' };
  return { label: 'Advanced', color: '#8b5cf6' };
}
```

**UI:**
```
┌─────────────────────────────────────┐
│  🎯 Level Anda: Intermediate        │
│  ████████████░░░░░░░░  65%         │
└─────────────────────────────────────┘
```

---

## 4. Variable Mapping (untuk state management)

| State Key | Source | Type |
|-----------|--------|------|
| `programming_familiarity` | Qa1 | `A\|B\|C\|D` |
| `domain_comfort` | Qa2 | `A\|B\|C\|D\|E` |
| `formal_preparation` | Qa3 | `A\|B\|C\|D` |
| `weekly_availability_hours` | Qa4 | `A\|B\|C\|D\|E` |
| `learning_modality_preference` | Qa5 | `A\|B\|C\|D` |
| `practicality_ratio` | Qa6 | `A\|B\|C` |
| `primary_motivation` | Qa7 | `A\|B\|C\|D\|E` |
| `monetary_constraint` | Qa8 | `A\|B\|C` |
| `certification_importance` | Qa9 | `A\|B\|C` |

---

## 5. Checklist FE

- [ ] Fetch dari `GET /api/questions/` — harusnya 13 items
- [ ] Render 3 step: Level (3Q) → Preferensi (6Q)
- [ ] Live level indicator setelah Qa3 dijawab
- [ ] Submit payload hanya 9 jawaban (Qa1–Qa9), demografi di-skip
- [ ] Progress stepper: 2 step (bukan 3+)
- [ ] Error handling: minimal 9 jawaban wajib

---

## 6. Catatan

- **`target_role` hilang** — tidak ada pertanyaan / pilihan "role IT" lagi
- Topic untuk roadmap sudah datang dari **input user saat generate**, bukan dari kuesioner
- Data demografi tetap dikumpulkan tapi **tidak dikirim ke BE** dalam payload submit