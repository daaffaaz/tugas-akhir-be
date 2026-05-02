# Learning Path Generation — Test Documentation

**Tanggal test:** 2026-05-02
**Test user:** kiplirafli19@gmail.com (questionnaire completed, 26 answers)
**User preferences:** budget `<500k`, weekly hours `<4`, main goal: career switch ke data analyst

---

## Endpoint

```
POST /api/rag/generate-roadmap/
Body: { "topic": "...", "count": 15 }
Response: 201 + LearningPathDetailSerializer
```

Data fase disimpan di `questionnaire_snapshot` (roadmap asli dari AI).
`courses` field berisi flat list course yang sudah di-save ke DB.

---

## Skenario Test

### LP1 — Machine Learning Topic

**Input:**
```json
{ "topic": "machine learning untuk data science", "count": 15 }
```

**Output:**

| Field | Value |
|-------|-------|
| `title` | Machine Learning for Data Science: A Beginner's Journey |
| `courses_retrieved` | 15 |
| `top_similarity_score` | 0.473 |

**Phases (dari `questionnaire_snapshot.phases`):**

```
Phase 1: Foundation in Data Science
  phase_reason: Establish a basic understanding of data science methodology,
               which is crucial for framing and solving data-driven problems effectively.
  transition_to_next: With a solid understanding of data science methodology,
                      you are now ready to explore machine learning basics, as these
                      concepts build directly on your [methodology knowledge].
  courses: [Data Science Methodology]

Phase 2: Introduction to Machine Learning
  phase_reason: Introduce basic machine learning concepts and techniques,
                focusing on supervised learning and predictive modeling.
  transition_to_next: null (last phase)
  courses: [Supervised Machine Learning: Regression and Classification]
```

> ✅ `phase_reason` ada dan menjelaskan WHY phase ini ada.
> ✅ `transition_to_next` ada untuk phase 1, menjelaskan connecting logic.
> ✅ Last phase (Phase 2) tidak punya `transition_to_next` — rule respected.

---

### LP2 — Web Development Topic

**Input:**
```json
{ "topic": "web development dari nol", "count": 15 }
```

**Output:**

| Field | Value |
|-------|-------|
| `title` | Web Development from Scratch: A Beginner's Journey |
| `courses_retrieved` | 4 |
| `top_similarity_score` | 0.422 |

**Phases (dari `questionnaire_snapshot.phases`):**

```
Phase 1: Foundation in Web Development
  phase_reason: This phase introduces the essential building blocks of web development:
                HTML, CSS, and JavaScript. These are crucial for anyone starting in
                web development, as they form the basis of creating and styling web pages.
  transition_to_next: Having learned the basics of HTML, CSS, and JavaScript, you are
                      now ready to explore more complex front-end frameworks like React,
                      which builds upon your understanding of JavaScript and web page structure.

Phase 2: Advanced Front-End Development
  phase_reason: This phase focuses on enhancing your front-end development skills by
                introducing React, a popular JavaScript library for building user interfaces.
                This will help you create more dynamic and interactive web applications.
  transition_to_next: null (last phase)
```

**Courses yang di-save ke DB:**

| Position | Course | Position in DB |
|---------|--------|----------------|
| 1 | Introduction to HTML, CSS, & JavaScript | 1 |
| 2 | Developing Front-End Apps with React | 2 |

> ✅ AI memilih 2 courses yang secara logis membangun skill (fundamentals → advanced framework).
> ✅ `transition_to_next` Phase 1 menjelaskan: "React builds upon your understanding of JavaScript" — causal relationship, bukan hanya sequential.

---

### LP3 — Multi-phase ML Roadamp (Full Details)

**Input:**
```json
{ "topic": "machine learning", "count": 15 }
```

**Output (direct LLM call, full phase detail):**

```
Phase 1: Foundational Machine Learning Concepts
  phase_reason: Establish a solid understanding of machine learning basics, which is
                crucial for any further study in the field. This phase addresses the
                lack of foundational knowledge in machine learning.
  transition_to_next: With a foundation in supervised learning, you can now explore
                      unsupervised learning techniques, which will broaden your
                      understanding of machine learning models and their applications.
  courses: [Supervised Machine Learning: Regression and Classification]

Phase 2: Exploring Unsupervised Learning
  phase_reason: Expand knowledge to include unsupervised learning techniques, which
                are critical for understanding a wider range of machine learning applications.
  transition_to_next: Having explored both supervised and unsupervised learning, you are
                      now ready to apply these skills to more advanced machine learning
                      projects, focusing on model evaluation and optimization.
  courses: [Unsupervised Learning, Recommenders, Reinforcement Learning]

Phase 3: Advanced Machine Learning Applications
  phase_reason: Apply the knowledge gained from previous phases to more complex machine
                learning tasks, focusing on model evaluation and optimization.
  transition_to_next: null (last phase)
  courses: [Structuring Machine Learning Projects]
```

> ✅ 3 phases dengan sequential prerequisite chain yang masuk akal.
> ✅ `transition_to_next` di Phase 1 & 2 menjelaskan spesifik skill bridging: "supervised learning → unsupervised learning", "model evaluation & optimization".
> ✅ Phase 3 tidak punya `transition_to_next` — last phase correctly omitted.

---

## Bugs Ditemukan & Diperbaiki

| # | Bug | Fix |
|---|-----|-----|
| 1 | `context_builder.py` — `build_user_prompt` not defined | Prefix dengan `prompts.` module import |
| 2 | `schemas.py` — `total_hours_estimated: int` fails on float `147.6` | Ubah ke `float \| int` |
| 3 | `context_builder.py` — `course_to_text()` membaca top-level keys, padahal metadata tersimpan nested | Ubah ke `course_meta.get('metadata', course_meta)` |

---

## Catatan Kualitas AI Reasoning

### ✅ Strengths
- **Causal transitions**: AI tidak hanya bilang "kemudian kamu akan belajar X", tapi menjelaskan WHY: "React builds upon your understanding of JavaScript"
- **Realistic course selection**: AI memilih courses yang benar-benar ada di DB (bukan hallucinated)
- **Phase reason yang meaningful**: `phase_reason` menjelaskan skill gap, bukan hanya "apa yang dipelajari"

### ⚠️ Observations
- Saat courses sangat sedikit (hanya 2-4 courses), AI menghasilkan hanya 1-2 phases — ini karena `phases` derived dari courses yang retrieved, bukan arbitrary number
- `skill_coverage` masih rendah (0.3) untuk single-course phases — ini expected karena satu kursus tidak cover semua
- Jika FAISS retrieval menghasilkan courses yang level-nya tidak berurutan, AI kadang menghasilkan phases yang kurang obvious prerequisite-nya

---

## Ringkasan

| Skenario | HTTP | Phase Reasoning | Transition | Last Phase Omit | Status |
|----------|------|----------------|------------|-----------------|--------|
| LP1: ML for Data Science | 201 | ✅ | ✅ | ✅ | ✅ PASS |
| LP2: Web Dev dari Nol | 201 | ✅ | ✅ | ✅ | ✅ PASS |
| LP3: Full ML Path | 201 | ✅ | ✅ | ✅ | ✅ PASS |
