# Evaluasi Sistem Rekomendasi Learning Path Berbasis AI

## Dokumen Metodologi Evaluasi

---

## 1. Gambaran Sistem yang Dievaluasi

### 1.1 Arsitektur Sistem

Sistem yang dievaluasi adalah platform rekomendasi learning path berbasis AI yang menggabungkan **Retrieval-Augmented Generation (RAG)** dengan **Large Language Model (GPT-4o)** untuk menghasilkan jalur belajar personal. Sistem ini dirancang untuk menghindari hallucination — setiap kursus yang direkomendasikan harus tersedia di basis data kursus.

Arsitektur sistem terdiri dari empat komponen utama:

```
┌─────────────────────────────────────────────────────────────────┐
│                 ARSITEKTUR SISTEM RAG                            │
│                                                                 │
│  [User] ──► [Questionnaire 32Q] ──► [User Profile]            │
│                                  │                               │
│  [User] ──► [Topic Input] ──────┼──────────────────────────────│
│                                  │                               │
│                                  ▼                               │
│              ┌─────────────────────────┐                       │
│              │   SEMANTIC RETRIEVAL     │                       │
│              │   text-embedding-3-small│                       │
│              │   FAISS Vector Index    │                       │
│              │   Cosine Similarity     │                       │
│              │   Threshold: 0.35       │                       │
│              │   Top-K: 15             │                       │
│              └───────────┬─────────────┘                       │
│                          │                                      │
│                          ▼                                      │
│              ┌─────────────────────────┐                       │
│              │   KNOWLEDGE GRAPH       │                       │
│              │   Tag-based ordering    │                       │
│              │   Prerequisite chain   │                       │
│              └───────────┬─────────────┘                       │
│                          │                                      │
│                          ▼                                      │
│              ┌─────────────────────────┐                       │
│              │   GPT-4o GENERATOR      │                       │
│              │   Learning Path JSON     │                       │
│              │   Phase-by-phase layout  │                       │
│              └───────────┬─────────────┘                       │
│                          │                                      │
│                          ▼                                      │
│              ┌─────────────────────────┐                       │
│              │   DATABASE VALIDATION   │                       │
│              │   Check all course_id   │                       │
│              │   exist in DB           │                       │
│              └───────────┬─────────────┘                       │
│                          │                                      │
│                          ▼                                      │
│  [LearningPath + LearningPathCourse records saved to DB]       │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 Alur Data dari Input hingga Rekomendasi

Proses rekomendasi dimulai ketika pengguna mengisi kuesioner awal (32 pertanyaan) dan memasukkan topik pembelajaran. Data mengalir melalui pipeline berikut:

**Tahap 1: Pengumpulan Profil Pengguna**

Pengguna mengisi 32 pertanyaan kuesioner yang mencakup enam dimensi: Profil & Demografi (4 pertanyaan), Kompetensi Teknis (8 pertanyaan), Ketersediaan Waktu (5 pertanyaan), Gaya Belajar (6 pertanyaan), Tujuan & Motivasi (2 pertanyaan), serta Minat & Hardware (7 pertanyaan). Jawaban pengguna disimpan dalam tabel `UserQuestionnaireAnswer` yang terkait dengan model `Question` melalui `variable_key`. Contoh `variable_key` yang kritis: `programming_logic_score` (menentukan difficulty baseline), `weekly_availability_hours` (menentukan durasi dan kecepatan pembelajaran), `learning_modality_preference` (menyaring format kursus), `monetary_constraint` (menyaring harga kursus), dan `primary_motivation` (menentukan career-aligned prioritization).

**Tahap 2: Embedding dan Pencarian Vektor**

Ketika pengguna memasukkan topik (misalnya: "machine learning untuk data science"), sistem menerjemahkan topik tersebut menjadi vektor 1536 dimensi menggunakan model `text-embedding-3-small` dari OpenAI. Vektor ini kemudian dicari secara dot-product terhadap semua vektor kursus dalam indeks FAISS yang telah dibangun sebelumnya dari 100 kursus Coursera. Hasil pencarian menghasilkan skor cosine similarity untuk setiap kursus. Hanya kursus dengan skor >= 0.35 yang dipertahankan, dan 15 kursus tertinggi dimasukkan ke dalam konteks untuk генерации.

**Tahap 3: Konstruksi Knowledge Graph (Prerequisite Chain)**

Kursus-kursus yang terretrieval kemudian diurutkan berdasarkan tag level: tag yang mengandung "fundamentals", "introduction", "basics" → Foundation/Beginner; tag yang mengandung "intermediate", "applied", "practical" → Intermediate; tag yang mengandung "advanced", "expert", "master" → Advanced. Hasil pengurutan ini disimpan dalam string `prerequisite_chain` yang disisipkan ke dalam prompt GPT-4o sebagai panduan urutan pembelajaran.

**Tahap 4: Generasi Learning Path oleh GPT-4o**

GPT-4o menerima prompt yang berisi profil pengguna, daftar kursus yang tersedia (dengan ID UUID, judul, instruktur, level, rating, harga, tag), prerequisite chain, dan instruksi output JSON. GPT-4o kemudian menghasilkan learning path yang berisi judul roadmap, fase-fase pembelajaran (dengan `phase_number`, `phase_name`, `phase_reason`, `transition_to_next`), kursus-kursus per fase (dengan `course_id` UUID, `match_reason`, `focus_areas`, `estimated_hours`), skill progress, milestones, dan tips. Output JSON divalidasi terhadap Pydantic schema, lalu semua `course_id` dalam output diverifikasi exist di basis data. Jika ada course_id yang tidak valid, phase tersebut dibuang dan hanya fase dengan kursus yang valid yang disimpan.

**Tahap 5: Penyimpanan dan Penyajian**

Learning path yang valid disimpan ke tabel `LearningPath` dengan snapshot lengkap dari `questionnaire_snapshot`. Kursus-kursus dalam learning path disimpan ke tabel `LearningPathCourse` dengan informasi posisi dan fase. Frontend kemudian menampilkan hasil dalam bentuk kartu fase (PhaseCard) yang dapat diekspansi untuk melihat detail kursus, termasuk thumbnail, deskripsi, rating, harga, tag, instructor, dan link ke platform asli.

### 1.3 Komponen Teknis yang Berlaku pada Evaluasi

Untuk keperluan evaluasi, komponen teknis utama sistem RAG yang relevan meliputi:

**Embedder (`apps/rag/embedder.py`):** Menggunakan model `text-embedding-3-small` dari OpenAI API dengan batch size 100 dan retry logic exponential backoff. Cache embedding dalam memory untuk menghindari panggilan ulang pada query yang sama.

**Vector Store (`apps/rag/vector_store.py`):** Tidak menggunakan FAISS binary — melainkan implementasi pure NumPy. Semua vektor kursus di-L2-normalize terlebih dahulu, sehingga dot product `index @ query` secara langsung menghasilkan cosine similarity tanpa perlu pembagian norma. Menggunakan `argpartition` untuk pengurutan parsial yang cepat, diikuti sort descending.

**Retriever (`apps/rag/retriever.py`):** Fungsi `retrieve_courses()` menerima topik dan profil pengguna, kemudian mengembalikan daftar metadata kursus dengan field `_score` (cosine similarity) dan `top_score` (skor tertinggi). Field `_score` disimpan langsung dari hasil pencarian FAISS, bukan di-re-rank atau dikombinasikan dengan skor lain.

**Generator (`apps/rag/generator.py`):** GPT-4o dipanggil dengan temperature 0.3 untuk roadmap generation. Output JSON divalidasi terhadap Pydantic schema (`apps/rag/schemas.py`). Setiap `course_id` dalam output divalidasi exist di database sebelum disimpan.

**Two-Score System:** Sistem menyimpan dua skor secara independen. `relevance_score` = cosine similarity dari FAISS (skor matematis, deterministik, range 0.0–1.0). `match_score` = judgment subjektif dari GPT-4o (skor generatif, nondeterministik, range 0.0–1.0). Kedua skor tidak dijumlah atau dirata-ratakan — keduanya disimpan terpisah untuk memberikan perspektif berbeda kepada pengguna.

---

## 2. Tujuan dan Pertanyaan Evaluasi

### 2.1 Tujuan Umum

Evaluasi ini bertujuan untuk mengukur tiga dimensi usability sebagaimana didefinisikan dalam **ISO 9241-11:2018** [7]: **Effectiveness** (kesempurnaan pengguna dalam menyelesaikan tugas), **Efficiency** (sumber daya yang dihabiskan relatif terhadap ketepatan hasil), dan **Satisfaction** (kebebasan dari ketidaknyamanan dan sikap positif terhadap penggunaan produk).

### 2.2 Pertanyaan Penelitian

**RQ1:** Apakah sistem rekomendasi learning path memiliki tingkat usability yang memadai bagi target pengguna (mahasiswa yang ingin mempelajari skill baru)?

**RQ2:** Sejauh mana kursus yang direkomendasikan oleh AI terdapat di basis data (groundedness) dan apakah menghasilkan learning path yang koheren (prerequisite ordering)?

**RQ3:** Bagaimana persepsi pengguna terhadap transparansi (kejelasan alasan rekomendasi), agensi (rasa kendali atas learning path), dan kepercayaan (trust terhadap output AI)?

### 2.3 Aspek yang Dievaluasi

Aspek kuantitatif yang diukur meliputi task completion rate untuk setiap skenario tugas, jumlah error clicks dan navigasi salah, durasi tugas (time-on-task), dan skor SUS agregat (mean dan distribusi). Aspek kualitatif yang digali meliputi pengalaman pengguna saat berinteraksi dengan sistem (think-aloud), alasan di balik keberhasilan atau kegagalan tugas, serta persepsi terhadap fitur rekomendasi AI.

---

## 3. Metode Evaluasi Kuantitatif

### 3.1 Evaluasi Groundedness dan Hallucination Detection

#### 3.1.1 Definisi Operasional Groundedness

**Groundedness** dalam konteks sistem RAG ini didefinisikan sebagai proporsi kursus dalam learning path yang dihasilkan AI yang benar-benar tersedia di basis data kursus. Hallucination terjadi ketika AI merekomendasikan kursus yang tidak ada dalam basis data — kursus fiktif yang namanya mirip dengan kursus nyata tetapi ID-nya tidak valid.

#### 3.1.2 Metode Pengukuran Groundedness

Pengukuran groundedness dilakukan secara **in-silico** (tanpa partisipasi pengguna) sebelum deployment sistem. Prosesnya sebagai berikut:

Untuk setiap topik yang diuji, generate learning path melalui API endpoint `POST /api/rag/generate-roadmap/`. Dari setiap learning path yang dihasilkan, ekstrak semua `course_id` dari semua fase. Verifikasi setiap `course_id` terhadap `Course.objects.filter(id=course_id).exists()` di Django ORM. Hitung groundedness ratio: `jumlah course_id valid / jumlah total course_id dalam output × 100%`. Jika ada kursus fiktif yang lolos, catat sebagai hallucination event.

Formula groundedness:

```
Groundedness = (Jumlah course_id yang exist di DB / Total course_id dalam output) × 100%
Hallucination Rate = (Jumlah course_id yang TIDAK exist di DB / Total course_id dalam output) × 100%
```

#### 3.1.3 Topik Uji dan Justifikasi

Pengujian groundedness dilakukan terhadap minimal 10 topik yang mewakili diversi domain:

Topik yang diuji meliputi "machine learning untuk data science" untuk testing domain teknis populer, "web development dengan React dan Node.js" untuk testing full-stack, "digital marketing untuk pemula" untuk testing domain non-teknis, "cloud computing dengan AWS" untuk testing domain spesifik, "product management dan agile methodology" untuk testing manajemen, dan lima topik lain yang ditentukan berdasarkan distribusi kursus dalam database. Setiap topik diuji minimal 3 kali dengan input yang sedikit berbeda untuk mendeteksi inkonsistensi.

#### 3.1.4 Groundness Score yang Diharapkan

Sistem dianggap **layak** jika groundedness score >= 95%. Score >= 98% dianggap **excellent** (hampir tidak ada hallucination). Score < 95% menunjukkan sistem perlu diperbaiki sebelum deployment untuk usability testing.

### 3.2 Evaluasi Kualitas Learning Path

#### 3.2.1 Dimensi Kualitas

Kualitas learning path dievaluasi berdasarkan tiga dimensi:

**Coherence (Koherensi):** Apakah kursus-kursus dalam satu fase saling terkait secara logis? Apakah `phase_reason` menjelaskan alasan keberadaan fase dengan tepat? Apakah `transition_to_next` menjelaskan hubungan kausal antar fase, bukan sekadar urutan?

**Prerequisite Ordering (Urutan Prasyarat):** Apakah kursus disusun dari tingkat dasar ke lanjutan sesuai dengan `prerequisite_chain`? Apakah tidak ada kursus tingkat lanjut yang ditempatkan sebelum kursus dasar yang merupakan prasyaratnya?

**Completeness (Kelengkapan):** Apakah setiap fase memiliki minimal 1 kursus? Apakah setiap fase memiliki `phase_reason`, `learning_objectives`, dan `milestones`? Apakah output JSON tidak memiliki field yang di-null-kan tanpa alasan?

#### 3.2.2 Metode Pengukuran Kualitas

Tidak ada formula otomatis untuk mengukur coherence atau completeness secara kuantitatif. Pengukuran dilakukan melalui:

**Automated Schema Validation:** Output JSON divalidasi terhadap schema yang telah ditentukan di `apps/rag/schemas.py`. Schema mencakup presence check (semua required fields ada), type check (semua values memiliki tipe yang benar), range check (phase_number berurutan, duration_weeks > 0), dan null-check (field opsional tidak boleh null tanpa justifikasi).

**Prerequisite Validation:** Dari setiap learning path, ekstrak level setiap kursus (Beginner/Intermediate/Advanced) dan posisi fase. Verifikasi bahwa tidak ada phase_number yang menurun (fase N+1 harus memiliki kursus dengan level >= fase N). Violasi到什么程度? Jika semua kursus di fase N memiliki level "Beginner" dan semua kursus di fase N+1 memiliki level "Advanced", maka prerequisite ordering satisfied.

**Relevance Score Distribution:** Periksa distribusi `relevance_score` (cosine similarity) kursus-kursus dalam learning path. Jika majority kursus memiliki relevance_score < 0.4, itu menandakan retrieval tidak optimal dan kualitas learning path kemungkinan rendah.

**Match Reason Coverage:** Hitung proporsi kursus yang memiliki `match_reason` tidak kosong atau tidak generik. `match_reason` yang hanya berisi "Course selected" atau "Good match" dianggap tidak informatif dan dihitung sebagai deficiency.

### 3.3 Usability Testing dengan Task Scenarios

#### 3.3.1 Skenario Tugas

Partisipan diminta untuk menyelesaikan 10 tugas konkret yang mencakup seluruh fitur inti sistem. Setiap tugas memiliki kriteria keberhasilan yang jelas dan diukur secara objective oleh observer.

**T1 — Registrasi Akun:** Task: Partisipan membuat akun baru dengan email valid. Success criteria: Partisipan berhasil sampai halaman konfirmasi registrasi tanpa error. Error clicks: klik pada elemen non-fungsional, salah pilih field. Confusion signals:.partisipan membaca instruksi berulang kali, menggerakkan mouse tanpa arah.

**T2 — Login dan Navigasi ke Kuesioner:** Task: Partisipan login dan menuju ke halaman kuesioner. Success criteria: Partisipan sampai di halaman awal kuesioner (step 1). Error clicks: salah klik navigasi, lupa password, tidak menemukan menu. Confusion signals: ketidakpastian di halaman mana harus mulai.

**T3 — Pengisian Kuesioner (5 Langkah):** Task: Partisipan menjawab 5 pertanyaan kuesioner secara berurutan. Success criteria: Partisipan menyelesaikan 5 step dan sampai di halaman submit. Error clicks: salah pilih opsi, klik tombol back/next yang salah. Confusion signals: tidak memahami pilihan jawaban, membutuhkan waktu lama untuk memutuskan.

**T4 — Input Topik dan Generate Learning Path:** Task: Partisipan memasukkan topik ("belajar machine learning untuk data science") dan menekan tombol generate. Success criteria: Learning path muncul di layar dalam waktu wajar (maksimum 60 detik). Error clicks: salah klik sebelum hasilnya muncul, refresh page saat loading. Confusion signals: tidak tahu apakah tombol sudah ditekan, tidak memahami animasi loading.

**T5 — Menampilkan Detail Kursus di Learning Path:** Task: Partisipan mengklik dropdown pada salah satu kartu kursus di fase pertama untuk melihat detail lengkap. Success criteria: Dropdown terbuka dan menampilkan minimal: thumbnail, title, instructor, rating, price, description, tags, dan "What You'll Learn". Error clicks: mengklik area non-expandable. Confusion signals: tidak menemukan dropdown indicator.

**T6 — Modifikasi Learning Path (Replace Course):** Task: Partisipan mengganti satu kursus di learning path dengan kursus lain. Success criteria: Partisipan menemukan tombol replace, melihat daftar kandidat, memilih salah satu, dan melihat learning path yang diperbarui. Error clicks: salah klik saat explorasi replace, tidak menemukan fitur. Confusion signals: tidak memahami alur replace, bingung dengan perbedaan replace dan regenerate.

**T7 — Rekomendasi Kursus Tunggal (Tanpa Learning Path):** Task: Partisipan mengakses fitur rekomendasi kursus satuan, memasukkan topik, dan melihat hasil rekomendasi. Success criteria: Rekomendasi kursus muncul dengan skor relevance dan AI explanation. Error clicks: salah navigasi ke fitur yang berbeda. Confusion signals: tidak membedakan fitur rekomendasi satuan dan learning path.

**T8 — Eksplorasi Daftar Kursus (Browse Courses):** Task: Partisipan membuka halaman daftar kursus, memfilter berdasarkan level, dan melihat detail satu kursus. Success criteria: Filter berfungsi, detail kursus tampil dengan informasi lengkap. Error clicks: filter tidak merespons, salah klik saat navigasi kursus. Confusion signals: filter options tidak jelas, terlalu banyak hasil yang ditampilkan.

**T9 — Menyimpan Learning Path dan Mengakses Ulang:** Task: Partisipan menyimpan learning path, logout, login kembali, dan mengakses ulang learning path yang disimpan. Success criteria: Learning path yang sama muncul kembali persis seperti sebelum logout. Error clicks: salah navigasi ke halaman list. Confusion signals: tidak menemukan daftar learning path yang tersimpan.

**T10 — Regenerate Learning Path:** Task: Partisipan meminta regenerasi learning path dengan konteks tambahan ("saya mau lebih banyak proyek praktis"). Success criteria: Learning path baru muncul dengan perubahan yang sesuai konteks. Error clicks: salah klik tombol regenerate. Confusion signals: tidak memahami perbedaan antara modify satu kursus dan regenerate seluruh path.

#### 3.3.2 Metrik Task-Based

Untuk setiap tugas, observer mencatat:

```
Task Success Rate:
  - SUCCESS: task selesai sesuai criteria dalam waktu wajar
  - PARTIAL: task selesai tetapi dengan difficulty signifikan
  - FAILURE: task tidak bisa diselesaikan
  - SKIP: partisipan menyerah dan minta bantuan

Error Click Rate:
  - error_clicks = jumlah klik yang salah arah / salah tujuan
  - error_rate = error_clicks / total_clicks × 100%

Time-on-Task:
  - durasi dari klik pertama hingga task complete
  - diukur dalam detik dengan stopwatch
  - threshold: 2× median time = indikator potensial usability issue

Confusion Duration:
  - durasi partisipan diam/menatap layar > 10 detik tanpa interaksi
  - diukur dalam detik
```

#### 3.3.3 Target Success Rate

Berdasarkan literatur, success rate target untuk sistem dengan usability baik adalah >= 85% per task. Task dengan success rate < 70% menunjukkan prioritas perbaikan tinggi. Task dengan waktu di atas 2× median menandakan efisiensi rendah.

### 3.4 System Usability Scale (SUS)

#### 3.4.1 Instrumen dan Implementasi

SUS terdiri dari 10 pertanyaan dengan skala 1–5. Pertanyaan ganjil (Q1, Q3, Q5, Q7, Q9) bersifat positif — skor dihitung langsung (response - 1, range 0–4). Pertanyaan genap (Q2, Q4, Q6, Q8, Q10) bersifat negatif — skor dibalik (5 - response, range 0–4). Skor SUS akhir = (total skor / 40) × 100, menghasilkan nilai 0–100.

**10 Pertanyaan SUS (Bahasa Indonesia):**

Q1 (positif): Saya ingin menggunakan sistem rekomendasi learning path ini secara rutin.
Q2 (negatif): Saya merasa sistem ini terlalu banyak memerlukan bantuan teknis untuk memulai.
Q3 (positif): Sistem rekomendasi learning path ini mudah digunakan.
Q4 (negatif): Saya merasa ada ketidakkonsistenan dalam hasil learning path yang dihasilkan AI.
Q5 (positif): Saya bisa mendapatkan learning path yang saya inginkan dengan cepat.
Q6 (negatif): Sistem ini terlalu kompleks untuk mencari rekomendasi pembelajaran.
Q7 (positif): Saya merasa learning path yang dihasilkan AI sangat relevan dengan topik yang saya masukkan.
Q8 (negatif): Saya perlu belajar banyak hal terlebih dahulu sebelum bisa menggunakan sistem ini secara efektif.
Q9 (positif): Saya merasa kursus-kursus dalam learning path tersusun dengan logis (dari dasar ke lanjutan).
Q10 (negatif): Saya merasa kursus-kursus yang direkomendasikan kurang sesuai dengan tingkat kemampuan saya saat ini.

**Formula Perhitungan:**

```python
def calculate_sus_score(responses: list[int]) -> float:
    """
    responses: list 10 nilai (Q1-Q10), tiap nilai 1-5

    Odd (1,3,5,7,9): langsung → response - 1  (0-4)
    Even (2,4,6,8,10): dibalik → 5 - response (0-4)

    Skor SUS = (total / 40) × 100
    """
    odd_sum  = sum(responses[i] - 1 for i in [0, 2, 4, 6, 8])
    even_sum = sum(5 - responses[i] for i in [1, 3, 5, 7, 9])
    return ((odd_sum + even_sum) / 40) * 100
```

#### 3.4.2 Interpretasi Skor

| Skor SUS | Grade | Keterangan |
|---|---|---|
| 90–100 | A+ | Excellent, best in class |
| 85–89 | A | Outstanding |
| 80–84 | A− | Excellent |
| 68–79 | B | Good (industri mean) |
| 68 | C | Average — baseline acceptability |
| 51–67 | D | Poor, needs improvement |
| 0–50 | F | Unacceptable |

**Target Penelitian:** Mean SUS score >= 68 (acceptable), target ideal >= 74 (good-to-excellent range).

#### 3.4.3 Perhitungan Confidence Interval

Dengan 20–30 partisipan, dihitung 95% CI untuk mean SUS score menggunakan formula: `CI = mean ± (1.96 × (SD / √n))`. Jika batas bawah CI < 68, sistem belum bisa dinyatakan acceptable meskipun mean > 68.

---

## 4. Metode Evaluasi Kualitatif

### 4.1 Think-Aloud Protocol

#### 4.1.1 Prosedur

Selama usability testing, partisipan diinstruksikan untuk Mengucapkan pikiran mereka secaraverbal saat berinteraksi dengan sistem. Protokol yang digunakan adalah **concurrent think-aloud** — partisipan berbicara SELAMA menyelesaikan tugas, bukan retrospektif.

Instruksi kepada partisipan:
- "Sebutkan apa yang sedang Anda pikirkan saat ini."
- "Katakan apa yang sedang Anda cari."
- "Nyatakan apa yang Anda harapkan terjadi setelah mengeklik ini."

Fasilitator only interven dengan probing netral ketika partisipan diam lebih dari 10 detik: "Informasi apa yang sedang Anda cari saat ini?" atau "Apa yang Anda harapkan terjadi?" Fasilitator **dilarang** memberikan solusi navigasi atau memvalidasi tindakan partisipan.

#### 4.1.2 Dokumentasi Observer

Observer mencatat dalam templat observasi:

```
Partisipan: [ID]
Tanggal: [date]
Tugas: [T1-T10]
Durasi total: [menit]

[T1 - Input Topik]
  00:00  → Klik "Buat Learning Path Baru"
  00:15  → Ketik "machine learning untuk data science" di input field
  00:23  → Klik tombol "Generate Roadmap"
  00:45  → [LOADING] Partisipan berkata: "Kok lama ya? Apakah sudah jalan?"
  01:10  → Learning path muncul. Partisipan berkata: "Oh ini jumlah fasenya 3 ya."
  [SUCCESS - 70 detik]
  Error clicks: 0
  Confusion episodes: 1 (loading uncertainty)
```

### 4.2 Wawancara Semi-Struktur

#### 4.2.1 Panduan Pertanyaan

Wawancara dilakukan setelah partisipan menyelesaikan semua task scenarios dan menutup sistem. Fase wawancara berlangsung 15–20 menit dan terdiri dari 6 pertanyaan semi-terstruktur.

**W1 — Fitur Favorit dan Membingungkan:**
"Fitur atau bagian mana dari sistem ini yang paling Anda sukai, dan fitur mana yang paling membuat Anda bingung?"
Topik eksplorasi: aspek UI yang intuitif, alur yang membingungkan, inkonsistensi desain, fitur yang tidak terduga.

**W2 — Kesesuaian Hasil dengan Ekspektasi:**
"Ketika Anda memasukkan topik '[topik yang digunakan partisipan]', apakah hasil learning path yang muncul sesuai dengan yang Anda bayangkan sebelumnya? Bagian mana yang terasa 'kurang tepat' atau 'aneh'?"
Topik eksplorasi: alignment mental model, relevansi kursus, urutan fase, kelengkapan informasi.

**W3 — Kecukupan Informasi Kursus:**
"Ketika Anda melihat detail kursus di dalam dropdown (thumbnail, rating, harga, deskripsi, tags), apakah informasi yang ditampilkan sudah cukup untuk memutuskan apakah kursus tersebut tepat untuk Anda? Informasi apa yang masih kurang?"
Topik eksplorasi: decision-making support, missing information, information overload, trust terhadap displayed data.

**W4 — Perbandingan dengan Pencarian Manual:**
"Jika dibandingkan dengan cara Anda mencari kursus secara manual (misalnya di Google atau langsung di platform Coursera/Udemy), apakah sistem ini terasa lebih mudah, lebih sulit, atau tidak berbeda? Mengapa?"
Topik eksplorasi: relative advantage, efficiency, perceived usefulness (TAM — Davis, 1989), resistance to change.

**W5 — Hal Terbaik dan Terburuk:**
"Secara keseluruhan, apa hal terbaik dari sistem ini, dan apa hal terburuk yang perlu diperbaiki?"
Topik eksplorasi: overall satisfaction, open-ended feedback, surprise positive/negative, improvement suggestions.

**W6 — Minat Penggunaan Ulang:**
"Jika sistem ini sudah FINAL dan bisa Anda gunakan sekarang, apakah Anda akan menggunakan kembali sistem ini untuk menentukan jalur belajar Anda di masa depan? Mengapa atau mengapa tidak?"
Topik eksplorasi: behavioral intention to reuse (TAM), trust in AI output (Glikson & Woolley, 2020), perceived value proposition.

#### 4.2.2 Transkripsi dan Analisis Tematik

Semua wawancara direkam (dengan izin) dan ditranskripsikan. Analisis tematik dilakukan menggunakan pendekatan Braun & Clarke (2006):

1. **Familiarisasi:** Membaca seluruh transkrip, membuat catatan awal.
2. **Generating initial codes:** Memberi label pada unit analisis (setiap respons atau unit makna).
3. **Searching for themes:** Menggabungkan kode-kode yang serupa ke dalam tema.
4. **Reviewing themes:** Memverifikasi bahwa tema merepresentasikan data secara akurat.
5. **Defining and naming themes:** Memberi label akhir pada setiap tema.
6. **Producing the report:** Menuliskan hasil analisis tematik dengan contoh kutipan verbatim.

### 4.3 Triangulasi Data

Temuan dari usability testing (task metrics) dan wawancara (tematik) divalidasi secara triangulasi:

```
┌─────────────────────────────────────────────┐
│              TRIANGULASI DATA              │
│                                             │
│  Task Metrics: W5 (SUS) Score = 65.3        │
│  Task Success Rate T5 (detail kursus) = 60% │
│         ↓           ↓           ↓           │
│  Wawancara: W3 → "Informasi kurang" × 12   │
│  Wawancara: W6 → "Tidak akan reuse" × 5    │
│                                             │
│  VALIDASI: Rendahnya success rate T5       │
│  berkorelasi dengan complaint W3.           │
│  Rendahnya SUS score konsisten dengan       │
│  behavioural intention (W6) yang rendah.   │
│  → Temuan terkonfirmasi: informasi kursus   │
│    di dropdown TIDAK mencukupi → prioritas │
│    perbaikan tinggi.                        │
└─────────────────────────────────────────────┘
```

---

## 5. Desain Evaluasi Teknis Sistem RAG

### 5.1 Metrik Teknis untuk Sistem RAG

Selain evaluasi usability, sistem RAG memerlukan metrik teknis spesifik yang diukur secara independent dari persepsi pengguna. Metrik teknis ini dapat diukur secara otomatis dan memberikan bukti objektif tentang kualitas sistem.

### 5.2 Groundedness Metrics

**Groundedness Score (G):**

```
G = (Jumlah course_id valid / Total course_id dalam learning path) × 100%

Contoh pengukuran:
  Learning path output: [course_1, course_2, course_3, course_4, course_5]
  course_1: exists → ✓
  course_2: exists → ✓
  course_3: exists → ✓
  course_4: NOT in DB → ✗ (hallucination)
  course_5: exists → ✓

  G = 4/5 × 100 = 80%  ← BELUM LAYAK, perlu perbaikan
```

**Hallucination Rate (H):**

```
H = (Jumlah hallucinated course_ids / Total course_ids) × 100%
```

**Validasi per-topik:**

Untuk setiap topik uji, generate 3 learning path dengan variasi prompt sedikit berbeda. Hitung G per-generation dan rata-ratakan. Jika G < 95% pada salah satu generasi, topik tersebut ditandai sebagai problematic.

### 5.3 Retrieval Quality Metrics

**Top-K Retrieval Coverage:**

```
Untuk setiap learning path yang dihasilkan:
  - Catat jumlah kursus yang retrieval (R)
  - Catat jumlah kursus yang digunakan dalam learning path (U)

  Coverage = U / R × 100%
  Jika U/R rendah (misalnya < 40%), berarti banyak kursus retrieval
  yang tidak digunakan → GPT-4o discard terlalu banyak kandidat
```

**Relevance Score Distribution:**

```
Dari setiap learning path, ekstrak relevance_score semua kursus.
Hitung:
  - Mean relevance_score
  - Min relevance_score (kursus paling tidak relevan yang tetap dipilih)
  - Std dev

Interpretasi:
  Mean tinggi (> 0.6) → retrieval bekerja baik
  Min rendah (< 0.4) → GPT-4o kadang memilih kursus yang tidak relevan
  Std dev tinggi → inconsistensi kualitas retrieval
```

### 5.4 Learning Path Quality Metrics (Automated)

**Phase Coherence Score (C):**

Metrik otomatis yang mengukur kohesi kursus dalam satu fase berdasarkan overlap tag:

```
C_phase = |Tags_fase ∩ Tags_course_set| / |Tags_fase|

Jika semua kursus dalam satu fase memiliki tag yang sama,
C_phase = 1.0 (kohesi sempurna).
Jika kursus dalam satu fase memiliki tag yang berbeda-beda,
C_phase rendah → menandakan fase tidak koheren.
```

**Prerequisite Ordering Violation (V):**

```
V = Jumlah fase di mana level kursus menurun secara tidak logis

Contoh violation:
  Fase 1: ["Python Basics - Beginner"]
  Fase 2: ["Deep Learning - Advanced"]  ← Lompatan tidak logis

V = 1 violation terdeteksi.
Target: V = 0 untuk semua learning path.
```

### 5.5 LLM Judge Evaluation (Optional / Advanced)

Jika waktu dan resources memungkinkan, dapat dilakukan evaluasi otomatis menggunakan **G-Eval** (Liu et al., 2023) atau metode LLM-as-judge untuk mengukur dimensi kualitas yang sulit diukur secara otomatis.

**G-Eval Framework** (Liu et al., 2023):

G-Eval menggunakan chain-of-thought reasoning dengan GPT-4o untuk menghasilkan skor kualitas yang berkorelasi tinggi dengan penilaian manusia (Spearman correlation = 0.514 pada text summarization task). Implementasinya:

```
1. Define evaluation criteria untuk learning path
   Criteria_1: "Apakah learning path ini koheren dan logis?"
   Criteria_2: "Apakah kursus-kursus yang direkomendasikan relevan dengan topik yang diminta?"
   Criteria_3: "Apakah urutan fase pembelajaran respek terhadap prerequisite?"

2. Generate CoT reasoning dari GPT-4o
   Prompt: "Given the criteria and the learning path output,
            provide step-by-step reasoning for the evaluation."

3. Form-filling evaluation
   Output: Score 1-5 untuk setiap criteria + skor akhir komposit

4. Aggregate scores dari multiple evaluators (bisa gunakan 3 LLM berbeda:
   GPT-4o, Claude-3, Gemini-2.0) untuk consensus scoring.
```

**Multi-LLM Judge Consensus:**

```
Dengan 3 LLM evaluator (GPT-4o, Claude-3, Gemini-2.0):
  - Masing-masing memberikan skor 1-5 per criteria
  - Hitung mean dan std dev per criteria
  - Jika std dev > 1.0 → evaluasi tidak consensus → perlu investigation
  - Jika 2 dari 3 LLM memberi skor >= 4 → criterion satisfied
```

**Korelasi dengan Human Judgment:**

Hasil G-Eval dapat dikorelasikan dengan hasil wawancara kualitatif. Misalnya, jika G-Eval memberikan skor rendah pada criterion "relevance with user goal", dan wawancara W2 juga mengungkapkan ketidakpuasan terhadap relevansi, maka kedua temuan saling memperkuat (triangulasi teknis-kualitatif).

**Catatan Penting tentang LLM-as-Judge:**

Liu et al. (2023) dalam paper G-Eval memperingatkan bahwa LLM judges memiliki bias terhadap teks yang dihasilkan oleh LLM lain. Artinya, jika GPT-4o menghasilkan learning path dan GPT-4o juga menilainya, ada kecenderungan skor terlalu tinggi. Sebaiknya gunakan LLM berbeda (Claude-3 Sonnet, Gemini-1.5 Pro) sebagai judge untuk output GPT-4o.

---

## 6. Partisipan dan Prosedur

### 6.1 Kriteria Partisipan

Kriteria inklusi: Berusia 18 tahun ke atas. Berlatar belakang pendidikan minimal SMA/sederajat. Memiliki pengalaman menggunakan internet untuk mencari informasi (browsing, searching). Tidak必须是 bidang IT — diversitas latar belakang pendidikan diperlukan untuk menguji generalizability. Bersedia mengisi informed consent dan direkam selama sesi.

Kriteria eksklusi: Bukan pengembang atau tester sistem ini (menghindari bias pengetahuan). Tidak pernah menggunakan prototipe sebelumnya dalam sesi development.

### 6.2 Ukuran Sampel

**Justifikasi jumlah partisipan:**

Nielsen (1993) [6] menyatakan bahwa 5 users sudah достатньо untuk mendeteksi ~85% usability problems. Namun, untuk studi yang menghasilkan data kuantitatif statistical (SUS scores, task success rates) dan analisis kualitatif tematik, jumlah minimum yang direkomendasikan berbeda.

**Untuk SUS score statistical significance:** Sauro (2011) [11] merekomendasikan minimal 20 partisipan agar mean SUS score memiliki confidence interval ±5 poin dengan 95% CI. Dengan SD industri 12.5 dan n=20: margin of error = 1.96 × (12.5 / √20) = ±5.5 poin.

**Untuk thematic saturation dalam wawancara kualitatif:** Guest, Bunce, dan Johnson (2006) menunjukkan thematic saturation biasanya tercapai pada 12–18 partisipan untuk interviews. Dengan 20–30 partisipan, saturation guaranteed dan subgroup analysis dimungkinkan (misalnya: comparison antara responden IT background vs non-IT).

**Dipilih: 20–30 partisipan** dengan purposive sampling, di mana peneliti secara sengaja merekrut partisipan yang merepresentasikan target user (mahasiswa dari berbagai jurusan yang ingin mempelajari skill baru di luar kurikulum).

### 6.3 Prosedur Per Sesi (30–45 menit)

```
┌──────────────────────────────────────────────────────────────────┐
│                      STRUKTUR SESI (30-45 menit)                 │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  [00:00 - 03:00] BRIEFING (3 menit)                             │
│  - Fasilitator menjelaskan tujuan studi (menguji sistem,        │
│    bukan menguji partisipan)                                    │
│  - Instruksi think-aloud                                       │
│  - Informed consent                                         │
│                                                                  │
│  [03:00 - 03:05] SETUP (2 menit)                               │
│  - Partisipan login ke sistem (akun sudah disiapkan)          │
│                                                                  │
│  [03:05 - 20:00] USABILITY TESTING (17 menit)                  │
│  - T1: Registrasi/Setup account (2 menit)                      │
│  - T2-T3: Login + Kuesioner (5 menit)                          │
│  - T4: Generate learning path (3 menit)                        │
│  - T5: Expand course dropdown (2 menit)                        │
│  - T6-T7: Modify + Single recommendation (4 menit)              │
│  - T8-T10: Browse courses + Save + Regenerate (3 menit)         │
│                                                                  │
│  [20:00 - 38:00] WAWANCARA (18 menit)                          │
│  - W1: Fitur favorite/membingungkan (3 menit)                  │
│  - W2: Kesesuaian hasil dengan ekspektasi (3 menit)            │
│  - W3: Kecukupan informasi kursus (3 menit)                   │
│  - W4: Perbandingan dengan pencarian manual (3 menit)          │
│  - W5: Hal terbaik/terburuk (3 menit)                           │
│  - W6: Minat penggunaan ulang (3 menit)                        │
│                                                                  │
│  [38:00 - 45:00] SUS + CLOSING (7 menit)                       │
│  - Isi kuesioner SUS (5 menit)                                  │
│  - Partisipan boleh bertanya / feedback akhir (2 menit)        │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 6.4 Peralatan dan Instrumen

Peralatan yang digunakan: Laptop/desktop dengan browser Chrome/Firefox, koneksi internet stabil. Layar recorder (OBS atau Loom) untuk dokumentasi sesi. Stopwatch untuk mengukur time-on-task. Templat observasi print-out untuk observer. Formulir informed consent. Kuesioner SUS dalam format print-out atau Google Forms. Audio recorder untuk wawancara (dengan izin partisipan).

---

## 7. Analisis Data

### 7.1 Analisis Kuantitatif

**SUS Score:**

```
Untuk setiap partisipan, hitung SUS score menggunakan formula.
Hitung:
  - Mean SUS: Σ(score_i) / n
  - Median SUS: nilai tengah
  - SD: standard deviation
  - 95% CI: mean ± 1.96 × (SD/√n)

Interpretasi:
  - Mean >= 68 → usability acceptable
  - Mean >= 74 → usability good
  - Mean >= 80 → usability excellent
  - Lower bound CI >= 68 → statistically acceptable
```

**Task Success Rate:**

```
Untuk setiap task T_i:
  Success_rate(T_i) = (Jumlah success / Total partisipan) × 100%

Visualisasi: bar chart success rate per task.
Identifikasi: task dengan success rate < 70% → prioritas perbaikan.
```

**Error Rate dan Time-on-Task:**

```
Error_rate per task = Total error_clicks / Total clicks × 100%
Mean_time(T_i) = Rata-rata durasi task T_i

Korelasi: task dengan error rate tinggi dan waktu panjang →
         menandai usability problem area.
```

### 7.2 Analisis Kualitatif

**Thematic Analysis (Braun & Clarke, 2006):**

Transkrip wawancara dianalisis untuk mengidentifikasi tema-tema utama. Tema dikelompokkan ke dalam tiga kategori: themes terkait UI/UX (visibility, consistency, simplicity), themes terkait AI output (relevance, transparency, trust), dan themes terkait comparative advantage (vs manual search, vs other platforms).

**Integrasi dengan Data Kuantitatif:**

Temuan kualitatif dipetakan ke metrik kuantitatif untuk triangulasi. Misalnya, jika banyak partisipan secara kualitatif mengeluhkan "tidak tahu mengapa kursus ini direkomendasikan" (W3), dan T5 (expand dropdown) memiliki success rate rendah, maka prioritas perbaikan adalah menambahkan AI explanation yang lebih visible.

---

## 8. Jadwal Evaluasi

```
┌────────────────────────────────────────────────────────────────┐
│                    JADWAL EVALUASI                             │
├────────────────────────────────────────────────────────────────┤
│                                                                  │
│  MINGGU 1-2: PERSIAPAN                                          │
│  - Finalisasi instrumen (SUS, task scripts, interview guide)    │
│  - Persiapan akun test dan data seed                            │
│  - Pilot test dengan 2-3 partisipan pembuka (bukan sampel)     │
│  - Revisi instrumen berdasarkan pilot                           │
│                                                                  │
│  MINGGU 3-5: PENGUMPULAN DATA                                   │
│  - Rekrut partisipan (purposive sampling)                      │
│  - Lakukan usability testing + wawancara + SUS                 │
│  - Target: 20-30 partisipan × 30-45 menit = 10-22.5 jam total │
│                                                                  │
│  MINGGU 6: ANALISIS DATA                                        │
│  - Tabulasi SUS scores + task metrics                          │
│  - Transkripsi dan thematic analysis wawancara                 │
│  - Triangulasi temuan kuantitatif-kualitatif                   │
│                                                                  │
│  MINGGU 7: PENULISAN LAPORAN                                    │
│  - Dokumentasi hasil evaluasi                                  │
│  - Rekomendasi perbaikan                                        │
│  - Validasi temuan dengan literature                           │
│                                                                  │
└────────────────────────────────────────────────────────────────┘
```

---

## 9. Referensi Metodologi

```
[1]  Nielsen, J. (1994). Ten usability heuristics for user interface
     design. Nielsen Norman Group.
     https://www.nngroup.com/articles/ten-usability-heuristics/

[2]  Brooke, J. (1996). SUS: A quick and dirty usability scale.
     Usability Evaluation in Industry, 189(4), 4-7.
     https://cros.usuariospcs.com.br/biblioteca/Usabilidade/
     Artigos/SUS%20A%20quick%20and%20dirty%20usability%20scale.pdf

[3]  Bangor, A., Kortum, P., & Miller, J. (2009). Determining what
     individual SUS scores mean. Journal of Usability Studies, 4(3),
     114-123. https://uxpajournal.org/determining-what-individual-sus-scores-mean/

[4]  Sauro, J., & Dumas, J. S. (2009). Comparison of three one-question,
     post-task usability questionnaires. Proceedings of CHI '09,
     1593-1596. https://dl.acm.org/doi/10.1145/1518701.1518941

[5]  Rubin, J., & Chisnell, D. (2008). Handbook of Usability Testing
     (2nd ed.). Wiley.

[6]  Nielsen, J. (1993). Usability Engineering. Morgan Kaufmann.

[7]  ISO 9241-11:2018. (2018). Ergonomics of human system interaction —
     Part 11: Usability: Definitions and concepts. ISO.
     https://www.iso.org/standard/16883.html

[8]  Creswell, J. W., & Plano Clark, V. L. (2018). Designing and
     Conducting Mixed Methods Research (3rd ed.). SAGE.

[9]  Ericsson, K. A., & Simon, H. A. (1993). Protocol Analysis:
     Verbal Reports as Data (Revised ed.). MIT Press.

[10] Lewis, J. R. (1995). IBM computer usability satisfaction
     questionnaires. International Journal of Human-Computer
     Interaction, 7(1), 57-78.

[11] Sauro, J. (2011). A Practical Guide to the System Usability
     Scale (SUS). MeasuringU Press.
     https://www.measuringu.com/sus.php

[12] Davis, F. D. (1989). Perceived usefulness, perceived ease of use,
     and user acceptance of information technology. MIS Quarterly,
     13(3), 319-340.

[13] Glikson, E., & Woolley, A. W. (2020). Human trust in AI:
     Review and research agenda. Journal of Management, 46(6),
     1024-1061.

[14] Liu, Y., et al. (2023). G-Eval: NLG Evaluation using GPT-4
     with Better Human Alignment. arXiv:2303.16634.
     https://arxiv.org/abs/2303.16634

[15] Braun, V., & Clarke, V. (2006). Using thematic analysis in
     psychology. Qualitative Research in Psychology, 3(2), 77-101.

[16] Guest, G., Bunce, A., & Johnson, L. (2006). How many interviews
     are enough? An experiment with data saturation and variability.
     Field Methods, 18(1), 59-82.
```

---

## 10. Lampiran: Ringkasan Metrik Evaluasi

```
┌─────────────────────────────────────────────────────────────────────┐
│                  RINGKASAN METRIK EVALUASI                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  KUANTITATIF TEKNIS (in-silico, sebelum usability testing)          │
│  ─────────────────────────────────────────────────────────────────  │
│  G1. Groundedness Score        ≥ 95% → layak, ≥ 98% → excellent   │
│  G2. Hallucination Rate        < 5% → acceptable                   │
│  G3. Retrieval Coverage        > 40% → GPT-4o tidak discard terlalu │
│                                    banyak kandidat retrieval        │
│  G4. Mean Relevance Score     > 0.6 → retrieval bekerja baik       │
│  G5. Prerequisite Violations  = 0 → semua learning path koheren    │
│  G6. Phase Coherence Score    > 0.5 → kursus dalam fase saling    │
│                                    terkait                         │
│                                                                     │
│  KUANTITATIF USABILITY (usability testing, 20-30 partisipan)        │
│  ─────────────────────────────────────────────────────────────────  │
│  U1. SUS Score               Mean ≥ 68 → acceptable, ≥ 74 → good   │
│  U2. Task Success Rate      Per task ≥ 85% → target, < 70% →     │
│                              prioritas perbaikan tinggi            │
│  U3. Error Click Rate       Per task — benchmark: < 15%           │
│  U4. Time-on-Task           Per task — tidak boleh > 2× median     │
│  U5. Confusion Duration     Per task — < 30 detik total           │
│                                                                     │
│  KUALITATIF (wawancara semi-struktur, 6 pertanyaan)                 │
│  ─────────────────────────────────────────────────────────────────  │
│  Q1. Fitur Favorite/Membingungkan → Tema UX/UI                    │
│  Q2. Kesesuaian Ekspektasi     → Tema AI output quality           │
│  Q3. Kecukupan Informasi       → Tema decision-making support      │
│  Q4. Perbandingan Manual       → Tema relative advantage (TAM)     │
│  Q5. Best/Worst Impressions    → Tema overall satisfaction         │
│  Q6. Behavioral Intention      → Tema trust + reuse likelihood    │
│                                                                     │
│  OPENSIONAL: LLM JUDGE (G-Eval, 3 LLM berbeda)                     │
│  ─────────────────────────────────────────────────────────────────  │
│  J1. Learning Path Coherence   Score 1-5 dari 3 LLM judge          │
│  J2. Course Relevance          Score 1-5, consensus required       │
│  J3. Prerequisite Respected    Score 1-5, tidak boleh < 3         │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```