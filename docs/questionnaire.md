# Questionnaire — Daftar Pertanyaan Kuesioner

Platform belajar online. Versi saat ini: **32 pertanyaan**.

> **Arsitektur:** Ada 2 questionnaire berbeda.
> - **Questionnaire 1 (General — ini):** Preferensi + profile pembelajar → untuk AI membangun user profile
> - **Questionnaire 2 (Topic):** Input topik domain (Data Science, Web Dev, Cloud, dll) → masuk langsung ke RAG sebagai `topic`

---

## Daftar Lengkap

### Section: PROFIL & DEMOGRAFI

| # | Variable Key | Pertanyaan | Opsi |
|---|-------------|-----------|------|
| 1 | `age_group` | Berapa usia Anda saat ini? | A: < 18 th, B: 18-24 th, C: 25-34 th, D: 35-44 th, E: > 45 th |
| 2 | `education_level` | Apa tingkat pendidikan formal terakhir Anda? | A: SMA/SMK, B: D3/D4, C: S1 (Sarjana), D: S2/S3, E: Lainnya |
| 3 | `educational_background_relevance` | Apakah jurusan pendidikan Anda berkaitan dengan IT/Komputer? | A: Ya, Sangat Terkait (IT/SI/Ilkom), B: Agak Terkait (Teknik Elektro/Matematika), C: Tidak Terkait (Sosial/Ekonomi/Sastra) |
| 4 | `employment_status` | Apa status pekerjaan utama Anda saat ini? | A: Pelajar/Mahasiswa, B: Fresh Graduate (Jobseeker), C: Karyawan (Non-IT), D: Karyawan (IT), E: Freelancer |

---

### Section: KOMPETENSI TEKNIS

| # | Variable Key | Pertanyaan | Opsi |
|---|-------------|-----------|------|
| 5 | `os_familiarity` | Sistem operasi apa yang biasa Anda gunakan untuk bekerja/belajar? | A: Windows, B: macOS, C: Linux (Ubuntu/Distro lain), D: Hanya Tablet/HP |
| 6 | `cli_proficiency` | Seberapa sering Anda menggunakan Command Line / Terminal? | A: Tidak pernah/Tidak tahu, B: Jarang (Cuma copy-paste tutorial), C: Sering (Navigasi file, git), D: Sangat Sering (Daily driver) |
| 7 | `programming_logic_score` | Apakah Anda memahami konsep dasar pemrograman (Looping, Variable, If-Else)? | A: Tidak paham sama sekali, B: Paham teori, bingung practise, C: Bisa menulis kode sederhana, D: Sangat paham & lancar |
| 8 | `git_competency` | Apakah Anda pernah menggunakan Git / GitHub? | A: Belum pernah, B: Pernah dengar tapi belum coba, C: Bisa git clone & push dasar, D: Mahir (Branching, Merge conflict) |
| 9 | `problem_solving_independence` | Jika kode Anda error, apa langkah pertama yang Anda lakukan? | A: Bingung/Menyerah, B: Tanya Teman/Mentor, C: Googling error message/StackOverflow, D: Baca dokumentasi resmi & Debugging mandiri |
| 10 | `ambiguity_tolerance` | Saat belajar sesuatu yang baru dan sulit, biasanya Anda... | A: Langsung tanya biar cepat paham, B: Mencari jawaban sendiri dulu, baru tanya jika benar-benar stuck, C: Bersabar—belajar pelan-pelan sampai benar-benar paham, D: Lebih suka kursus yang step-by-step, tidak loncat-loncat |
| 11 | `english_technical_proficiency` | Bagaimana kemampuan Anda membaca dokumentasi teknis dalam Bahasa Inggris? | A: Sulit memahami, B: Butuh Google Translate, C: Cukup paham konteks, D: Sangat lancar tanpa bantuan |
| 12 | `project_portfolio_count` | Berapa banyak proyek coding/IT yang pernah Anda selesaikan sampai tuntas? | A: 0 (Belum ada), B: 1-2 (Tugas kuliah/sekolah), C: 3-5 (Proyek hobi/kecil), D: > 5 (Proyek profesional/besar) |
| 33 | `data_comfort` | Seberapa nyaman Anda bekerja dengan data berupa angka, grafik, atau tabel? | A: Tidak nyaman—lebih suka penjelasan verbal, B: Cukup nyaman kalau ada bantuan/guide, C: Nyaman menganalisis data sendiri, D: Sangat nyaman—ini keahlian saya |

---

### Section: KETERSEDIAAN WAKTU

| # | Variable Key | Pertanyaan | Opsi |
|---|-------------|-----------|------|
| 13 | `weekly_availability_hours` | Berapa jam REALISTIS yang bisa Anda alokasikan untuk belajar per minggu? | A: < 3 jam (Sangat Sibuk), B: 3-7 jam (Santai), C: 8-14 jam (Moderat), D: 15-25 jam (Intensif), E: > 25 jam (Full Time) |
| 14 | `learning_session_span` | Berapa lama durasi fokus Anda dalam satu kali sesi duduk belajar? | A: < 30 menit (Micro-learning), B: 30-60 menit, C: 1-2 jam, D: > 2 jam (Deep work) |
| 15 | `preferred_time_slot` | Kapan waktu utama Anda akan mengakses materi kursus? | A: Pagi hari (Sebelum aktivitas), B: Jam kerja/kuliah (Sela-sela waktu), C: Malam hari (Setelah aktivitas), D: Akhir pekan saja (Weekend) |
| 16 | `target_completion_duration` | Berapa target waktu Anda untuk menyelesaikan seluruh learning path ini? | A: 1 Bulan (Crash Course), B: 3 Bulan (Quarterly Goal), C: 6 Bulan (Semester Goal), D: 1 Tahun (Long-term) |
| 17 | `login_frequency_intent` | Seberapa sering Anda berencana login ke platform? | A: Setiap hari, B: 3-4 kali seminggu, C: 1-2 kali seminggu, D: Tidak tentu |

---

### Section: GAYA BELAJAR

| # | Variable Key | Pertanyaan | Opsi |
|---|-------------|-----------|------|
| 18 | `learning_modality_preference` | Format materi mana yang paling cepat membuat Anda paham? | A: Video (Visual & Audio), B: Teks/Artikel (Membaca & Skimming), C: Interactive Code (Langsung ketik di browser), D: Project (Langsung practise kasus) |
| 19 | `practicality_ratio` | Bagaimana komposisi Teori vs Praktek yang Anda inginkan? | A: Banyak Teori (70%), Sedikit Praktek (30%), B: Seimbang (50%-50%), C: Dominan Praktek/Hands-on (80%) |
| 20 | `learning_curve_steepness` | Bagaimana preferensi kenaikan tingkat kesulitan materi? | A: Landai: Perlahan-lahan, detail, step-by-step, B: Curam: Cepat ke inti, tantangan tinggi sejak awal |
| 21 | `social_dependency_level` | Apakah Anda membutuhkan interaksi dengan instruktur/komunitas? | A: Solo: Lebih suka belajar sendiri, B: Forum: Cukup tanya jawab via chat/forum, C: Live: Wajib ada sesi zoom/tatap muka |
| 22 | `assessment_type_preference` | Jenis evaluasi/ujian apa yang paling Anda sukai? | A: Kuis Pilihan Ganda (Cepat), B: Coding Challenge Otomatis, C: Proyek Besar (Peer/Expert Review), D: Tidak suka ujian |

---

### Section: TUJUAN & MOTIVASI

| # | Variable Key | Pertanyaan | Opsi |
|---|-------------|-----------|------|
| 23 | `primary_motivation` | Apa tujuan utama mengikuti program ini? | A: Cari Kerja Baru (Career Switch), B: Promosi/Upskilling di kerjaan sekarang, C: Freelance/Side hustle, D: Akademis/Kuliah, E: Hobi semata |
| 24 | `certification_importance` | Seberapa penting sertifikat kelulusan bagi Anda? | A: Sangat Penting (Untuk CV/Syarat), B: Biasa saja (Nice to have), C: Tidak Penting (Yang penting ilmunya) |

---

### Section: MINAT & HARDWARE

| # | Variable Key | Pertanyaan | Opsi |
|---|-------------|-----------|------|
| 26 | `problem_approach` | Ketika menghadapi masalah baru, apa pendekatan pertama Anda? | A: Langsung coba—belajar sambil melakukan, B: Mencari tutorial atau contoh dulu, C: Membaca dokumentasi resmi sampai paham, D: Bertanya ke orang yang lebih tahu |
| 27 | `explanation_style` | Jika harus menjelaskan ide ke orang lain, Anda lebih suka... | A: Melalui angka, grafik, atau spreadsheet, B: Melalui cerita, analogi, atau gambar, C: Langsung demonstrasi / demo, D: Tergantung situasi |
| 28 | `debugging_approach` | Jika kode Anda error dan solusi instan tidak berhasil, apa yang Anda lakukan? | A: Langsung googling error message, B: Baca dokumentasi resmi sampai ketemu akar masalahnya, C: Tanya di forum/komunitas, D: Sering tidak tahu harus mulai dari mana |
| 29 | `format_frustration` | Format belajar mana yang PALING membuat Anda frustrasi? | A: Video panjang tanpa kode yang bisa dipraktekkan, B: Teks/teori yang sangat teknis tanpa contoh nyata, C: Langsung latihan tanpa penjelasan konsep, D: Tidak pernah frustrasi—saya adaptif |
| 30 | `hardware_constraint` | Berapa kapasitas RAM komputer/laptop yang Anda gunakan belajar? | A: < 4 GB (Low-end), B: 4-8 GB (Mid-range), C: > 8 GB (High-end), D: Tidak pakai laptop (HP Only) |
| 31 | `bandwidth_constraint` | Bagaimana kualitas koneksi internet Anda untuk streaming video? | A: Tidak stabil/Kuota terbatas, B: Cukup stabil, C: Sangat cepat & Unlimited |
| 32 | `monetary_constraint` | Berapa budget maksimal untuk pembelian tools/lisensi software (jika ada)? | A: Rp 0 (Harus gratis/Open source), B: < Rp 500rb, C: Tidak Masalah (Ada budget khusus) |

---

## AI Relevance Mapping (untuk RAG)

### 🔴 Critical (Langsung Affect Roadmap)

| Variable Key | Alasan |
|------------|--------|
| `programming_logic_score` (#7) | Difficulty baseline — Beginner vs Intermediate |
| `weekly_availability_hours` (#13) | Phase count & pace planning |
| `target_completion_duration` (#16) | Total roadmap duration |
| `learning_modality_preference` (#18) | Format filter: video / teks / interactive / project |
| `practicality_ratio` (#19) | Theory vs Hands-on course selection |
| `primary_motivation` (#23) | Career-aligned course prioritization |
| `hardware_constraint` (#30) | Filter courses yang perlu high-end specs (ML, Docker) |
| `monetary_constraint` (#32) | Price tier filter |

### 🟡 High (Affects Course Detail)

| Variable Key | Alasan |
|------------|--------|
| `ambiguity_tolerance` (#10) | Difficulty curve & learning pacing |
| `learning_curve_steepness` (#20) | Landai vs curam phase progression |
| `git_competency` (#8) | Project-based course inclusion |
| `project_portfolio_count` (#12) | Experience level indicator |
| `problem_approach` (#26) | Learning style: pragmatic vs conceptual vs documentation-driven |
| `explanation_style` (#27) | Course format hint: numeric vs visual vs demo |
| `debugging_approach` (#28) | Milestone structure & support layer |
| `format_frustration` (#29) | **AVOID** format tertentu — filter out courses |
| `bandwidth_constraint` (#31) | Video vs text format preference |
| `data_comfort` (#33) | Numeric/data-heavy course inclusion |

### 🟢 Medium / Analytics Only

| Variable Key | Notes |
|------------|-------|
| `educational_background_relevance` (#3) | Affects pacing if IT-related |
| `os_familiarity` (#5) | Tooling environment hint |
| `cli_proficiency` (#6) | Affects terminal-heavy courses |
| `english_technical_proficiency` (#11) | Complexity of resource recommendations |
| `social_dependency_level` (#21) | Community/platform hint |
| `age_group` (#1) | Analytics only |
| `employment_status` (#4) | Analytics / motivation context |
| `preferred_time_slot` (#15) | Analytics only |
| `login_frequency_intent` (#17) | Analytics only |
| `assessment_type_preference` (#22) | UX only |
| `certification_importance` (#24) | Course ordering by cert status |

---

## RAG Usage

```python
key = ans.question.variable_key

if key == 'programming_logic_score':
    profile['skill_level'] = val  # maps to Beginner/Intermediate/Advanced
elif key == 'weekly_availability_hours':
    profile['weekly_hours'] = val  # affects phase count
elif key == 'learning_modality_preference':
    profile['format'] = val  # A=video, B=text, C=interactive, D=project
elif key == 'format_frustration':
    profile['avoid_formats'] = val  # A=long video, B=theory text, C=no-concept, D=none
elif key == 'problem_approach':
    profile['learning_style'] = val  # pragmatic/tutorial/doc/social
elif key == 'debugging_approach':
    profile['debug_style'] = val  # affects milestone structure
```

---

*Generated: 2026-05-02 | Updated: 2026-05-02 (6 questions replaced)*