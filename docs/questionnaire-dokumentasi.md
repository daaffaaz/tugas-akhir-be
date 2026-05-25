# Kuesioner — Dokumentasi Sistem Rekomendasi Learning Path

> **Versi:** 2.0 | **Jumlah pertanyaan:** 32 | **Bahasa:** Indonesia

---

## Daftar Isi

1. [Ringkasan](#1-ringkasan)
2. [Struktur Data](#2-struktur-data)
3. [Variabel Kritis AI](#3-variabel-kritis-untuk-ai-rag)
4. [Pertanyaan per Bagian](#4-pertanyaan-per-bagian)
5. [Alur Pengisian](#5-alur-pengisian)
6. [Integrasi RAG](#6-integrasi-dengan-sistem-rag)

---

## 1. Ringkasan

Kuesioner ini digunakan sebagai **masukan utama (input profile)** bagi sistem rekomendasi course berbasis AI (RAG). Jawaban kuesioner tidak menghasilkan skor numerik, melainkan membentuk **user profile dict** yang dikirim ke sistem RAG untuk:

- Menentukan **level kesulitan awal** course (Beginner / Intermediate / Advanced)
- Menghitung **durasi setiap fase** berdasarkan ketersediaan waktu mingguan
- **Menyaring course** berdasarkan format (video / teks / project)
- **Mengatur proporsi teori vs hands-on** sesuai preferensi user
- **Mendeteksi batasan teknis** (budget, hardware, bandwidth)

Kuesioner terdiri dari **6 bagian** dan **32 pertanyaan** dengan format *single choice* (A–E).

---

## 2. Struktur Data

### Database Model

```
Question
├── id            : UUID (Primary Key)
├── order_number  : Integer (1-32, unik, diindeks)
├── section       : String (nama bagian, misal "KOMPETENSI TEKNIS")
├── question_text : Text
├── input_type    : String ("Single Choice")
├── options_json  : JSON Object { "A": "...", "B": "...", "C": "...", "D": "...", "E": "..." }
└── variable_key  : String (identifikator unik untuk AI/RAG)

UserQuestionnaireAnswer
├── id             : UUID
├── user           : FK ke User
├── question       : FK ke Question
├── answer_option  : String ("A" | "B" | "C" | "D" | "E")
├── submitted_at   : Timestamp
└── UNIQUE CONSTRAINT: (user, question) — satu jawaban per user per pertanyaan
```

### API Endpoint

| Method | Endpoint | Fungsi |
|---|---|---|
| GET | `/api/questions/` | Ambil semua 32 pertanyaan |
| POST | `/api/users/questionnaire/` | Submit semua jawaban |
| GET | `/api/users/questionnaire/` | Ambil jawaban user |
| PATCH | `/api/users/questionnaire/` | Update jawaban tertentu |

### Payload POST

```json
[
  { "question_id": "<UUID>", "answer_option": "B" },
  { "question_id": "<UUID>", "answer_option": "C" },
  ... (32 entries)
]
```

---

## 3. Variabel Kritis untuk AI (RAG)

### High-Impact (Langsung mempengaruhi hasil rekomendasi)

| `variable_key` | Pengaruh | Nilai yang Direkomendasikan |
|---|---|---|
| `programming_logic_score` | Level dasar course | A → Beginner, C → Intermediate, D → Advanced |
| `weekly_availability_hours` | Jumlah & durasi fase | A (<3 jam) → 2 fase, D (>15 jam) → 4-5 fase |
| `target_completion_duration` | Total durasi roadmap | A → 1 fase/bulan, D → 1 fase/3 bulan |
| `learning_modality_preference` | Format materi | A → Video, B → Teks, C → Interactive, D → Project |
| `practicality_ratio` | Proporsi teori vs hands-on | A → Teori-dominant, C → Hands-on-dominant |
| `monetary_constraint` | Budget course | A → Free only, C → Paid course OK |
| `hardware_constraint` | Filter kursus yang perlu GPU/high-spec | A → kursus ringan saja, C → boleh GPU-heavy |
| `bandwidth_constraint` | Format video vs teks | A → teks/低速 video, C → HD video OK |

### Analytics Only (Tidak mempengaruhi rekomendasi secara langsung)

| `variable_key` | Keterangan |
|---|---|
| `age_group` | Analisis demografi |
| `employment_status` | Analisis demografi |
| `preferred_time_slot` | Engagement pattern |
| `login_frequency_intent` | Prediksi retensi |
| `certification_importance` | Prioritas fitur sertifikat |
| `assessment_type_preference` | Preferensi format evaluasi |

---

## 4. Pertanyaan per Bagian

---

### BAGIAN 1 — PROFIL & DEMOGRAFI (4 pertanyaan)

> **Tujuan:** Mengidentifikasi profil dasar user untuk segmentasi demografis.

**Q1.** `age_group` — Berapa usia Anda saat ini?

| Opsi | Label |
|---|---|
| A | < 18 tahun |
| B | 18–24 tahun |
| C | 25–34 tahun |
| D | 35–44 tahun |
| E | > 45 tahun |

---

**Q2.** `education_level` — Apa tingkat pendidikan formal terakhir Anda?

| Opsi | Label |
|---|---|
| A | SMA/SMK |
| B | D3/D4 |
| C | S1 (Sarjana) |
| D | S2/S3 |
| E | Lainnya |

---

**Q3.** `educational_background_relevance` — Apakah jurusan pendidikan Anda berkaitan dengan IT/Komputer?

| Opsi | Label |
|---|---|
| A | Ya, Sangat Terkait (IT/SI/Ilkom) |
| B | Agak Terkait (Teknik Elektro/Matematika) |
| C | Tidak Terkait (Sosial/Ekonomi/Sastra) |

---

**Q4.** `employment_status` — Apa status pekerjaan utama Anda saat ini?

| Opsi | Label |
|---|---|
| A | Pelajar/Mahasiswa |
| B | Fresh Graduate (Jobseeker) |
| C | Karyawan (Non-IT) |
| D | Karyawan (IT) |
| E | Freelancer |

---

### BAGIAN 2 — KOMPETENSI TEKNIS (8 pertanyaan)

> **Tujuan:** Menentukan baseline kemampuan teknis user untuk penyesuaian tingkat kesulitan course.

**Q5.** `os_familiarity` — Sistem operasi apa yang biasa Anda gunakan untuk bekerja/belajar?

| Opsi | Label |
|---|---|
| A | Windows |
| B | macOS |
| C | Linux (Ubuntu/Distro lain) |
| D | Hanya Tablet/HP |

---

**Q6.** `cli_proficiency` — Seberapa sering Anda menggunakan Command Line / Terminal (layar hitam)?

| Opsi | Label |
|---|---|
| A | Tidak pernah / Tidak tahu |
| B | Jarang (Cuma copy-paste tutorial) |
| C | Sering (Navigasi file, git) |
| D | Sangat Sering (Daily driver) |

---

**Q7.** `programming_logic_score` — Apakah Anda memahami konsep dasar pemrograman (Looping, Variable, If-Else)?

| Opsi | Label |
|---|---|
| A | Tidak paham sama sekali |
| B | Paham teori, bingung praktek |
| C | Bisa menulis kode sederhana |
| D | Sangat paham & lancar |

> **Pengarruh AI:** Opsi C/D → boleh mulai dari Intermediate course. Opsi A → wajib Beginner.

---

**Q8.** `git_competency` — Apakah Anda pernah menggunakan Git / GitHub?

| Opsi | Label |
|---|---|
| A | Belum pernah |
| B | Pernah dengar tapi belum coba |
| C | Bisa git clone & push dasar |
| D | Mahir (Branching, Merge conflict) |

---

**Q9.** `problem_solving_independence` — Jika kode Anda error, apa langkah pertama yang Anda lakukan?

| Opsi | Label |
|---|---|
| A | Bingung/Menyerah |
| B | Tanya Teman/Mentor |
| C | Googling error message/StackOverflow |
| D | Baca dokumentasi resmi & Debugging mandiri |

---

**Q10.** `ambiguity_tolerance` — Saat belajar sesuatu yang baru dan sulit, biasanya Anda...

| Opsi | Label |
|---|---|
| A | Langsung tanya biar cepat paham |
| B | Mencari jawaban sendiri dulu, baru tanya jika benar-benar stuck |
| C | Bersabar — belajar pelan-pelan sampai benar-benar paham |
| D | Lebih suka kursus yang step-by-step, tidak loncat-loncat |

---

**Q11.** `english_technical_proficiency` — Bagaimana kemampuan Anda membaca dokumentasi teknis dalam Bahasa Inggris?

| Opsi | Label |
|---|---|
| A | Sulit memahami |
| B | Butuh Google Translate |
| C | Cukup paham konteks |
| D | Sangat lancar tanpa bantuan |

---

**Q12.** `project_portfolio_count` — Berapa banyak proyek coding/IT yang pernah Anda selesaikan sampai tuntas?

| Opsi | Label |
|---|---|
| A | 0 (Belum ada) |
| B | 1–2 (Tugas kuliah/sekolah) |
| C | 3–5 (Proyek hobi/kecil) |
| D | > 5 (Proyek profesional/besar) |

---

**Q13.** `data_comfort` — Seberapa nyaman Anda bekerja dengan data berupa angka, grafik, atau tabel?

| Opsi | Label |
|---|---|
| A | Tidak nyaman — lebih suka penjelasan verbal |
| B | Cukup nyaman kalau ada bantuan/guide |
| C | Nyaman menganalisis data sendiri |
| D | Sangat nyaman — ini keahlian saya |

---

### BAGIAN 3 — GAYA BELAJAR (6 pertanyaan)

> **Tujuan:** Menyesuaikan format, kecepatan, dan jenis materi dengan preferensi belajar user.

**Q14.** `learning_modality_preference` — Format materi mana yang paling cepat membuat Anda paham?

| Opsi | Label | Filter Course |
|---|---|---|
| A | Video (Visual & Audio) | courses dengan `video_hours > 0` |
| B | Teks/Artikel (Membaca & Skimming) | courses tanpa video |
| C | Interactive Code (Langsung ketik di browser) | courses bertipe hands-on/project |
| D | Project (Langsung practise kasus) | courses bertipe project-based |

---

**Q15.** `practicality_ratio` — Bagaimana komposisi Teori vs Praktek yang Anda inginkan?

| Opsi | Label |
|---|---|
| A | Banyak Teori (70%), Sedikit Praktek (30%) |
| B | Seimbang (50% – 50%) |
| C | Dominan Praktek/Hands-on (80%) |

---

**Q16.** `learning_curve_steepness` — Bagaimana preferensi kenaikan tingkat kesulitan materi?

| Opsi | Label | Pengaruh AI |
|---|---|---|
| A | Landai: Perlahan-lahan, detail, step-by-step | RAG disuruh buat fase lebih banyak & gradual |
| B | Curam: Cepat ke inti, tantangan tinggi sejak awal | RAG boleh mulai dari materi advanced lebih awal |

---

**Q17.** `social_dependency_level` — Apakah Anda membutuhkan interaksi dengan instruktur/komunitas?

| Opsi | Label |
|---|---|---|
| A | Solo: Lebih suka belajar sendiri |
| B | Forum: Cukup tanya jawab via chat/forum |
| C | Live: Wajib ada sesi zoom/tatap muka |

---

**Q18.** `assessment_type_preference` — Jenis evaluasi/ujian apa yang paling Anda sukai?

| Opsi | Label |
|---|---|---|
| A | Kuis Pilihan Ganda (Cepat) |
| B | Coding Challenge Otomatis |
| C | Proyek Besar (Peer/Expert Review) |
| D | Tidak suka ujian |

---

### BAGIAN 4 — KETERSEDIAAN WAKTU (5 pertanyaan)

> **Tujuan:** Menghitung durasi dan kecepatan belajar user untuk menentukan panjang fase dan durasi roadmap.

**Q19.** `weekly_availability_hours` — Berapa jam REALISTIS yang bisa Anda alokasikan untuk belajar per minggu?

| Opsi | Label | Pengaruh AI |
|---|---|---|
| A | < 3 jam (Sangat Sibuk) | Maks 2 fase, durasi panjang |
| B | 3–7 jam (Santai) | 2–3 fase |
| C | 8–14 jam (Moderat) | 3–4 fase |
| D | 15–25 jam (Intensif) | 4–5 fase |
| E | > 25 jam (Full Time) | 5+ fase, durasi pendek |

---

**Q20.** `learning_session_span` — Berapa lama durasi fokus Anda dalam satu kali sesi duduk belajar?

| Opsi | Label |
|---|---|---|
| A | < 30 menit (Micro-learning) |
| B | 30–60 menit |
| C | 1–2 jam |
| D | > 2 jam (Deep work) |

---

**Q21.** `preferred_time_slot` — Kapan waktu utama Anda akan mengakses materi kursus?

| Opsi | Label |
|---|---|---|
| A | Pagi hari (Sebelum aktivitas) |
| B | Jam kerja/kuliah (Sela-sela waktu) |
| C | Malam hari (Setelah aktivitas) |
| D | Akhir pekan saja (Weekend) |

---

**Q22.** `target_completion_duration` — Berapa target waktu Anda untuk menyelesaikan seluruh learning path ini?

| Opsi | Label | Pengaruh AI |
|---|---|---|
| A | 1 Bulan (Crash Course) | Semua fase dimampatkan |
| B | 3 Bulan (Quarterly Goal) | 3 fase dalam 12 minggu |
| C | 6 Bulan (Semester Goal) | 4 fase dalam 24 minggu |
| D | 1 Tahun (Long-term) | 5+ fase, durasi santai |

---

**Q23.** `login_frequency_intent` — Seberapa sering Anda berencana login ke platform?

| Opsi | Label |
|---|---|---|
| A | Setiap hari |
| B | 3–4 kali seminggu |
| C | 1–2 kali seminggu |
| D | Tidak tentu |

---

### BAGIAN 5 — TUJUAN & MOTIVASI (2 pertanyaan)

> **Tujuan:** Mengarahkan prioritas skill dan career-alignment dalam rekomendasi.

**Q24.** `primary_motivation` — Apa tujuan utama mengikuti program ini?

| Opsi | Label | Filter AI |
|---|---|---|
| A | Cari Kerja Baru (Career Switch) | Prioritas: kursus dengan project portfolio + sertifikasi |
| B | Promosi/Upskilling di kerjaan sekarang | Prioritas: advanced topics + applied skills |
| C | Freelance/Side hustle | Prioritas: marketable skills + portofolio |
| D | Akademis/Kuliah | Prioritas: fundamental + theoretical depth |
| E | Hobi semata | Prioritas: interesse personal, tanpa batasan |

---

**Q25.** `certification_importance` — Seberapa penting sertifikat kelulusan bagi Anda?

| Opsi | Label | Filter AI |
|---|---|---|
| A | Sangat Penting (Untuk CV/Syarat) | Prioritas: kursus bersertifikat |
| B | Biasa saja (Nice to have) | Sertifikat加分, bukan prioritas |
| C | Tidak Penting (Yang penting ilmunya) | Sertifikat diabaikan |

---

### BAGIAN 6 — MINAT & HARDWARE (7 pertanyaan)

> **Tujuan:** Mendeteksi batasan teknis dan preferensi pembelajaran spesifik.

**Q26.** `problem_approach` — Ketika menghadapi masalah baru, apa pendekatan pertama Anda?

| Opsi | Label |
|---|---|
| A | Langsung coba — belajar sambil melakukan |
| B | Mencari tutorial atau contoh dulu |
| C | Membaca dokumentasi resmi sampai paham |
| D | Bertanya ke orang yang lebih tahu |

---

**Q27.** `explanation_style` — Jika harus menjelaskan ide ke orang lain, Anda lebih suka...

| Opsi | Label |
|---|---|
| A | Melalui angka, grafik, atau spreadsheet |
| B | Melalui cerita, analogi, atau gambar |
| C | Langsung demonstrasi / demo |
| D | Tergantung situasi |

---

**Q28.** `debugging_approach` — Jika kode Anda error dan solusi instan tidak berhasil, apa yang Anda lakukan?

| Opsi | Label |
|---|---|
| A | Langsung googling error message |
| B | Baca dokumentasi resmi sampai ketemu akar masalahnya |
| C | Tanya di forum/komunitas |
| D | Sering tidak tahu harus mulai dari mana |

---

**Q29.** `format_frustration` — Format belajar mana yang PALING membuat Anda frustrasi?

| Opsi | Label |
|---|---|
| A | Video panjang tanpa kode yang bisa dipraktekkan |
| B | Teks/teori yang sangat teknis tanpa contoh nyata |
| C | Langsung latihan tanpa penjelasan konsep |
| D | Tidak pernah frustrasi — saya adaptif |

---

**Q30.** `hardware_constraint` — Berapa kapasitas RAM komputer/laptop yang Anda gunakan belajar?

| Opsi | Label | Filter AI |
|---|---|---|
| A | < 4 GB (Low-end) | HANYA kursus ringan, tidak ada ML/DL |
| B | 4–8 GB (Mid-range) | Kursus standard, boleh sedikit ML |
| C | > 8 GB (High-end) | Semua kursus OK termasuk ML/GPU |
| D | Tidak pakai laptop (HP Only) | Prioritas kursus mobile-friendly |

---

**Q31.** `bandwidth_constraint` — Bagaimana kualitas koneksi internet Anda untuk streaming video?

| Opsi | Label | Filter AI |
|---|---|---|
| A | Tidak stabil/Kuota terbatas | Prioritas: teks + offline material |
| B | Cukup stabil | Video 720p OK, teks OK |
| C | Sangat cepat & Unlimited | Semua format OK |

---

**Q32.** `monetary_constraint` — Berapa budget maksimal untuk pembelian tools/lisensi software (jika ada)?

| Opsi | Label | Filter AI |
|---|---|---|
| A | Rp 0 (Harus gratis/Open source) | HANYA kursus Free / Financial Aid |
| B | < Rp 500.000 | Kursus berbayar di bawah Rp 500k OK |
| C | Tidak Masalah (Ada budget khusus) | Semua kursus OK |

---

## 5. Alur Pengisian

```
┌─────────────────────────────────────────────────────┐
│  USER MULAI                                          │
│  /questionnaire                                      │
│         │                                             │
│         ▼                                             │
│  GET /api/questions/                                 │
│  → Ambil 32 pertanyaan                               │
│         │                                             │
│         ▼                                             │
│  User menjawab 1 pertanyaan per halaman step [1-32]  │
│  Jawaban disimpan ke localStorage                     │
│  (saveAnswer: personalearn_questionnaire_answers)   │
│         │                                             │
│         ▼                                             │
│  Step akhir (32) → Submit                            │
│         │                                             │
│         ▼                                             │
│  POST /api/users/questionnaire/                      │
│  Payload: [{question_id, answer_option}, ...] x 32  │
│         │                                             │
│         ▼                                             │
│  Jawaban disimpan ke DB                              │
│  → user_profile dict dibuild                         │
│  → Siap dipakai untuk generate learning path         │
│         │                                             │
│         ▼                                             │
│  /questionnaire/completion                           │
│  "Kuesioner selesai" + opsi mulai bikin learning path│
└─────────────────────────────────���───────────────────┘
```

---

## 6. Integrasi dengan Sistem RAG

```
questionnaire answers
        │
        ▼
┌──────────────────────────────────────────────┐
│  context_builder.build_user_profile_text()    │
│  ─────────────────────────────────────────── │
│  • level ← programming_logic_score            │
│  • budget_idr ← monetary_constraint           │
│  • weekly_hours ← weekly_availability_hours   │
│  • target_skills ← primary_motivation        │
│  • current_skills ← educational_background   │
│  • preferences:                               │
│      format ← learning_modality_preference   │
│      hardware ← hardware_constraint           │
│      bandwidth ← bandwidth_constraint        │
│      theory_practice ← practicality_ratio    │
└──────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────┐
│  Inject ke LLM prompt untuk:                │
│  1. Generate learning path roadmap         │
│  2. Rank retrieved courses                 │
│  3. Compute match_score + relevance_score   │
└──────────────────────────────────────────────┘
```

### Mapping `variable_key` → Prompt Field

| `variable_key` (Kuesioner) | Field di Prompt RAG | Fungsi |
|---|---|---|
| `programming_logic_score` | `level` | Menentukan level course awal |
| `monetary_constraint` | `budget_str` | Filter/hint harga course |
| `weekly_availability_hours` | `weekly_hours` | Estimasi durasi fase |
| `primary_motivation` | `goals` | Target skill untuk rekomendasi |
| `educational_background_relevance` | `current_skills` | Baseline skill saat ini |
| `learning_modality_preference` | `material_format` | Filter format course |
| `practicality_ratio` | `theory_practice` | Proporsi teori vs hands-on |
| `hardware_constraint` | `hardware` | Filter course berdasar spec |
| `bandwidth_constraint` | `bandwidth` | Preferensi format delivery |

---

## Changelog

| Versi | Perubahan |
|---|---|
| v2.0 | Hapus 6 pertanyaan interest-topik spesifik. Tambah 6 pertanyaan gaya belajar & teknis umum. Semua pertanyaan sekarang GENERAL — tidak ada clue topik spesifik. |
| v1.0 | Versi awal dengan 26 pertanyaan + pertanyaan interest-topik. |

---

*Sumber data: `/BE/docs/questionnaire.json` | `/BE/docs/questionnaire.md`*