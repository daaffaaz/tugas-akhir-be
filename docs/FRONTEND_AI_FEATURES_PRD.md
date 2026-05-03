# Frontend PRD — AI-Powered Learning Features

## Fitur AI #1: Course Recommendation
## Fitur AI #2: Learning Path Generation

**Tanggal:** 2026-05-02
**Status:** Backend API selesai — ready untuk frontend integration
**Backend docs:** `docs/RAG_RECOMMEND_TEST.md`, `docs/LEARNING_PATH_TEST.md`

---

## 1. Overview

### 1.1 Fitur yang Akan Dibangun

| # | Fitur | Endpoint | Deskripsi |
|---|-------|----------|-----------|
| **AI #1** | Course Recommendation | `POST /api/rag/recommend/` | Generate N course recommendation dengan AI explanation per course |
| **AI #2** | Learning Path | `POST /api/rag/generate-roadmap/` | Generate sequential learning path dengan phase-by-phase reasoning |

### 1.2 Prerequisites

- User harus **login** (JWT auth)
- User harus **complete questionnaire** (32 pertanyaan) sebelum bisa mengakses fitur AI
- Jika user belum complete questionnaire → HTTP 403 dengan message: `"Complete the onboarding questionnaire before accessing this resource."`

### 1.3 User Flow

```
Register/Login
     │
     ▼
Answer 32 Questions (Questionnaire 1 — learner profile)
     │
     ▼
Dashboard → Pilih "Course Recommendation" atau "Learning Path"
     │
     ├─▶ AI #1: Masukkan topik + context (opsional) → 5 courses + explanation
     │
     └─▶ AI #2: Masukkan topik → Sequential phases + courses + reasoning
```

---

## 2. Fitur AI #1 — Course Recommendation

### 2.1 Screen Design

**Screen: `CourseRecommendationScreen`**

```
┌─────────────────────────────────────────────┐
│  ← Back           AI Recommendations        │
├─────────────────────────────────────────────┤
│                                             │
│  Mau belajar apa?                           │
│  ┌─────────────────────────────────────────┐│
│  │ machine learning untuk data science     ││
│  └─────────────────────────────────────────┘│
│                                             │
│  Ada konteks tambahan? (opsional)           │
│  ┌─────────────────────────────────────────┐│
│  │ saya mau career switch ke data analyst   ││
│  └─────────────────────────────────────────┘│
│                                             │
│  Jumlah kursus: [5 ▼]                       │
│                                             │
│  [🔄 Generate Recommendations]              │
│                                             │
├─────────────────────────────────────────────┤
│  RESULTS (3 courses)                       │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │ [Course Thumbnail]                   │   │
│  │ Machine Learning with Python         │   │
│  │ ⭐ 4.5 (1,234 reviews) | Coursera   │   │
│  │ Level: Intermediate | ⏱ 133 hours   │   │
│  │ 💰 IDR 570,000                        │   │
│  │                                     │   │
│  │ 💡 AI Reason:                        │   │
│  │ "This course is intermediate level   │   │
│  │  and requires 10 hours/week..."      │   │
│  │  ─── match_score: 0.8 ───            │   │
│  │  Best for: Intermediate learners     │   │
│  │  Gaps: Not suitable for beginners    │   │
│  │                                     │   │
│  │ [Bookmark] [Lihat Detail] [Daftar]   │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  [🔄 Regenerate — wajib isi konteks]        │
│  ┌─────────────────────────────────────┐   │
│  │ Context baru:                       │   │
│  │ Saya mau yang hands-on & pendek...  │   │
│  └─────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
```

### 2.2 Input Fields

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| `topic` | Text input | ✅ Yes | — | Min 3 characters, max 500 |
| `additional_context` | Text area | No | `""` | Max 500 chars, for regenerate |
| `count` | Dropdown | No | 5 | Options: 3, 5, 10, 15, 20 |

### 2.3 Button States

| State | Label | Behavior |
|-------|-------|---------|
| Default | `Generate Recommendations` | Triggers fresh recommendation |
| Loading | `🔄 Generating...` (disabled) | Show spinner, disable all inputs |
| Success | Show results | Display 5 course cards |
| Regenerate available | `🔄 Regenerate` | Show only AFTER results exist. Requires `additional_context` filled. |
| Regenerate without context | Validation error | Show inline error: "Konteks tambahan WAJIB diisi saat regenerate" |

### 2.4 Course Card — Display Fields

```
┌──────────────────────────────────────────────────────┐
│ COURSE CARD                                          │
│                                                      │
│ thumbnail_url          → Course thumbnail image       │
│ title                 → Course title (clickable)     │
│ platform.name          → "Coursera" badge             │
│ rating + reviews_count → "⭐ 4.5 (1,234 reviews)"     │
│ level                 → Badge: Beginner/Inter/Adv      │
│ duration              → "⏱ 2 weeks at 10 hours/week"  │
│ video_hours           → "⏱ 133 hours total"           │
│ price + currency      → "💰 IDR 570,000"              │
│                                                      │
│ ── AI Section (transparency) ──                      │
│ ai_explanation        → "💡 AI Reason: [text]"        │
│ match_score           → Visual bar 0-1 or badge       │
│ best_for              → "Best for: [label]"          │
│ potential_gaps        → "⚠️ Gaps: [text]"             │
│ relevance_score       → Hidden (for dev/debug)        │
│ regenerate_count      → Hidden (for dev/debug)        │
│                                                      │
│ Actions: [💾 Simpan] [🔗 Lihat di Coursera]           │
└──────────────────────────────────────────────────────┘
```

### 2.5 Response Mapping

**API Response** → **Frontend Field**

```json
// API Response (POST /api/rag/recommend/)
{
  "recommendations": [
    {
      "id": "uuid-recommendation",
      "course_obj": {
        "id": "uuid-course",
        "title": "Machine Learning with Python",
        "instructor": "IBM",
        "rating": "4.5",
        "reviews_count": 1234,
        "price": "570000.00",
        "currency": "IDR",
        "level": "Intermediate",
        "duration": "2 weeks at 10 hours a week",
        "video_hours": "133.00",
        "thumbnail_url": "https://...",
        "url": "https://www.coursera.org/..."
      },
      "relevance_score": 0.4725,
      "ai_explanation": "This course is intermediate level...",
      "match_score": 0.8,
      "best_for": "Intermediate learners...",
      "potential_gaps": "Not suitable for beginners...",
      "is_saved": false,
      "regenerate_count": 0,
      "created_at": "2026-05-02T12:00:00+00:00"
    }
  ],
  "topic": "machine learning untuk data science",
  "total_retrieved": 3,
  "top_similarity_score": 0.473,
  "regenerate": false,
  "regenerate_count": 0
}
```

### 2.6 Regenerate UX Flow

```
1. User tap "🔄 Regenerate"
   → Regenerate button → becomes "Fill context to regenerate"
   → additional_context field appears/activates
   → count selector stays same

2. User fills context
   → "Saya mau kursus hands-on yang pendek"

3. User tap "🔄 Regenerate"
   → If context empty → inline error
   → If context filled → loading state → new results
   → regenerate_count increments in response

4. Results update
   → Same course IDs (usually) with NEW ai_explanation
   → regenerate_count badge: "Regenerated 1x"
```

### 2.7 Error States

| HTTP Code | Condition | User Message |
|-----------|-----------|--------------|
| 400 | Validation error (topic < 3 chars, regenerate without context) | Inline field error below input |
| 401 | Not authenticated | Redirect to login |
| 403 | Questionnaire not completed | "Selesaikan kuesioner terlebih dahulu untuk mengakses fitur ini." |
| 404 | No courses found for topic | "Tidak ada kursus untuk topik ini. Coba topik lain." |
| 500 | Server error | "Terjadi kesalahan. Silakan coba lagi." |

---

## 3. Fitur AI #2 — Learning Path

### 3.1 Screen Design

**Screen: `LearningPathScreen`**

```
┌─────────────────────────────────────────────────────────────┐
│  ← Back              AI Learning Path                       │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Mau belajar apa?                                             │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ web development dari nol                                 │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
│  [🔄 Generate Learning Path]                                 │
│                                                               │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  📍 Machine Learning Foundations for Data Science           │
│  ⏱ ~12 weeks | 48 hours estimated                           │
│                                                               │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  PHASE 1: Foundation in Data Science                  [✓]   │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│                                                               │
│  💡 Why this phase exists:                                   │
│  Build a foundational understanding of data science concepts  │
│  and methodologies, which are crucial for framing and solving  │
│  data-driven problems effectively.                            │
│                                                               │
│  📚 Courses (2)                                              │
│    1. [📷] Data Science Methodology                         │
│            ⭐ 4.5 | Intermediate | ⏱ 12 hours                │
│            IBM · 💰 IDR 0 (Audit)                            │
│            match_reason: "Covers essential DS methodology"   │
│                                                               │
│    2. [📷] Tools for Data Science                            │
│            ⭐ 4.6 | Beginner | ⏱ 10 hours                    │
│            IBM · 💰 IDR 0 (Audit)                            │
│            match_reason: "Introduction to DS tools: Python.."│
│                                                               │
│  🔄 Transition to next phase:                                │
│  "With a solid understanding of data science methodology,     │
│   you are now ready to explore machine learning basics,       │
│   as these concepts build directly on your methodology       │
│   knowledge."                                                │
│                                                               │
│  ─────────────────────────────────────────────────────────── │
│  PHASE 2: Introduction to Machine Learning           [ ]   │
│  ─────────────────────────────────────────────────────────── │
│                                                               │
│  💡 Why this phase exists:                                   │
│  Introduce the principles of supervised machine learning,      │
│  focusing on regression and classification, which are core     │
│  techniques used in real-world data science applications.     │
│                                                               │
│  📚 Courses (1)                                              │
│    1. [📷] Supervised Machine Learning: Regression...        │
│            ⭐ 4.6 | Intermediate | ⏱ 18 hours                │
│            ⭐ Stanford · 💰 IDR 0 (Audit)                    │
│            match_reason: "..."                                │
│                                                               │
│  🔄 Transition: (none — last phase)                          │
│                                                               │
├─────────────────────────────────────────────────────────────┤
│  Overview:                                                  │
│  "This roadmap is designed to introduce complete beginners   │
│   to the world of data science..."                           │
│                                                               │
│  Target Skills: HTML, CSS, JavaScript, React                 │
│  Difficulty: beginner-friendly | progressive                 │
│                                                               │
│  [💾 Simpan Learning Path]  [🔗 Share]  [📋 Export PDF]     │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Input Fields

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `topic` | Text input | ✅ Yes | Same as recommendation — the topic being learned |
| `count` | Hidden / Fixed | — | Always `15` (retrieves 15 courses, AI decides how many per phase) |

### 3.3 Phase Display — All Fields

```
┌──────────────────────────────────────────────────────────┐
│ PHASE N: Phase Name                                      │
│                                                          │
│ 💡 Why this phase exists:                                │
│   {phase_reason}                                         │
│                                                          │
│ 📚 Courses:                                              │
│   • {course.title}                                       │
│     {match_reason}                                       │
│     {level} | {video_hours}h | {price}                   │
│                                                          │
│ 🔄 Transition to next phase:                              │
│   {transition_to_next}  ← only for non-last phases       │
│   (last phase: no transition shown)                      │
│                                                          │
│ Milestones: • milestone 1 • milestone 2                   │
│ Practice Projects: • project idea 1                      │
│                                                          │
│ Skills gained: [tag1] [tag2] [tag3]                      │
│ Skill coverage: ████████░░ 80%                           │
└──────────────────────────────────────────────────────────┘
```

### 3.4 Response Mapping

**API Response** → **Frontend Field**

```json
// POST /api/rag/generate-roadmap/ → HTTP 201
{
  "id": "uuid-learning-path",
  "title": "Machine Learning for Data Science: A Beginner's Journey",
  "topic_input": "machine learning untuk data science",
  "is_saved": false,
  "progress_percentage": 0.0,
  "courses": [
    {
      "id": "uuid-learning-path-course",
      "course": {
        "id": "uuid-course",
        "title": "Data Science Methodology",
        "instructor": "IBM",
        "rating": "4.5",
        "level": "Beginner",
        "video_hours": "12.00",
        "price": "0.00",
        "currency": "IDR",
        "url": "https://...",
        "thumbnail_url": "https://..."
      },
      "position": 1,
      "is_completed": false
    }
  ],
  "created_at": "2026-05-02T12:00:00Z",
  "_rag_meta": {
    "courses_retrieved": 15,
    "top_similarity_score": 0.473,
    "retrieval_method": "semantic vector search + tag-based ordering"
  },
  // Roadmap metadata (for AI reasoning display)
  "questionnaire_snapshot": {
    "roadmap_title": "Machine Learning for Data Science...",
    "total_duration_weeks": 12,
    "total_hours_estimated": 48,
    "difficulty_curve": "beginner-friendly / progressive",
    "overview": "This roadmap is designed to...",
    "target_skills": ["Python", "Machine Learning", "Data Analysis"],
    "phases": [
      {
        "phase_number": 1,
        "phase_name": "Foundation in Data Science",
        "phase_reason": "Build a foundational understanding of data science...",
        "duration_weeks": 6,
        "learning_objectives": ["Understand DS methodology", "Learn Python basics"],
        "courses": [
          {
            "course_id": "uuid-course",
            "title": "Data Science Methodology",
            "match_reason": "Covers essential DS methodology..."
          },
          ...
        ],
        "milestones": ["Complete methodology quiz", "Build first DS project"],
        "practice_projects": ["Data analysis project"],
        "skill_progress": {
          "skills_gained": ["Python", "Data Wrangling"],
          "skill_coverage": 0.3
        },
        "transition_to_next": "With a solid understanding of data science...",
        // ← last phase has transition_to_next: null
      },
      {
        "phase_number": 2,
        "phase_name": "Introduction to Machine Learning",
        "phase_reason": "Introduce the principles of supervised ML...",
        "transition_to_next": null
      }
    ],
    "tips_for_success": ["Practice daily", "Build portfolio"],
    "next_steps_after_roadmap": ["Advanced ML courses"]
  }
}
```

### 3.5 How to Map Courses to Phases

Since `courses` flat array is ordered by `position`, and `questionnaire_snapshot.phases[].courses[]` contains course metadata:

```
Logic:
1. courses[] (flat, ordered by position) is the sequential list
2. questionnaire_snapshot.phases[] contains phase structure with reasoning
3. Map courses to phases by checking:
   - courses[0..n1] belong to phase 1 (by position range)
   - courses[n1+1..n2] belong to phase 2
   - etc.

Alternatively (simpler):
- phase N gets its courses from questionnaire_snapshot.phases[N].courses[]
- course detail (title, price, level, url, thumbnail) from courses[] by matching course_id
```

### 3.6 Error States

| HTTP Code | Condition | User Message |
|-----------|-----------|--------------|
| 400 | Topic too short | Inline field error |
| 401 | Not authenticated | Redirect to login |
| 403 | Questionnaire not completed | "Selesaikan kuesioner terlebih dahulu..." |
| 404 | No courses found for topic | "Tidak ada kursus ditemukan. Coba topik lain." |
| 500 | Server/LLM error | "Terjadi kesalahan saat generate learning path. Coba lagi." |

---

## 4. Shared Components

### 4.1 Loading State

```
┌────────────────────────────────────────────────┐
│                                                │
│        [Spinner] Generating...                │
│        Please wait while AI analyzes         │
│        your request                           │
│                                                │
│  ○ ○ ○ ○ ○     step 1/5 — Searching courses   │
│                                                │
└────────────────────────────────────────────────┘
```

### 4.2 Empty State — No Results

```
┌────────────────────────────────────────────────┐
│                                                │
│        🔍 Tidak ada kursus ditemukan           │
│                                                │
│  Topik "quantum computing" tidak memiliki     │
│  kursus di database kami saat ini.            │
│                                                │
│  Suggestions:                                 │
│  • Coba topik yang lebih umum:               │
│    "machine learning", "web development"     │
│  • Gunakan bahasa Inggris:                   │
│    "data science", "cloud computing"          │
│                                                │
│  [Coba Topik Lain]                           │
│                                                │
└────────────────────────────────────────────────┘
```

### 4.3 AI Explanation Badge (used in both features)

```
┌────────────────────────────────────────────────┐
│ 💡 AI Explanation                             │
│                                                │
│ "This course is intermediate level and        │
│  requires 10 hours/week, which exceeds your   │
│  preferred study time. Additionally, the      │
│  price is slightly above your budget..."     │
│                                                │
│ ┌─────────────────┐  ┌─────────────────────┐ │
│ │ Match Score     │  │ Best For            │ │
│ │ ████████░░ 0.8  │  │ Intermediate with   │ │
│ │                 │  │ ample time & budget │ │
│ └─────────────────┘  └─────────────────────┘ │
│                                                │
│ ⚠️ Potential Gaps                            │
│ "Not suitable for beginners or those with    │
│  limited study time and budget constraints."  │
└────────────────────────────────────────────────┘
```

---

## 5. State Management

### 5.1 Feature #1 — Course Recommendation State

```typescript
interface CourseRecommendationState {
  // Input
  topic: string;
  additionalContext: string;
  count: number;

  // Output
  recommendations: CourseRecommendation[];
  isLoading: boolean;
  error: string | null;
  regenerateCount: number;
  topSimilarityScore: number;

  // Actions
  generate: (topic: string, context?: string) => Promise<void>;
  regenerate: (topic: string, context: string) => Promise<void>; // context REQUIRED
  toggleSaved: (recommendationId: string) => Promise<void>;
  reset: () => void;
}

interface CourseRecommendation {
  id: string;
  course: CourseDetail;
  relevanceScore: number;
  aiExplanation: string;
  matchScore: number;       // 0-1
  bestFor: string;
  potentialGaps: string;
  isSaved: boolean;
  regenerateCount: number;
  createdAt: string;
}
```

### 5.2 Feature #2 — Learning Path State

```typescript
interface LearningPathState {
  // Input
  topic: string;

  // Output
  learningPath: LearningPathDetail | null;
  isLoading: boolean;
  error: string | null;

  // Actions
  generate: (topic: string) => Promise<void>;
  save: (learningPathId: string) => Promise<void>;
  reset: () => void;
}

interface LearningPathDetail {
  id: string;
  title: string;
  phases: Phase[];
  overview: string;
  targetSkills: string[];
  totalDurationWeeks: number;
  totalHoursEstimated: number;
  difficultyCurve: string;
  tipsForSuccess: string[];
  nextStepsAfterRoadmap: string[];
  courses: FlatCourseList;  // for detail/drill-down
}

interface Phase {
  phaseNumber: number;
  phaseName: string;
  phaseReason: string;        // "WHY this phase exists"
  durationWeeks: number;
  courses: PhaseCourse[];
  milestones: string[];
  practiceProjects: string[];
  transitionToNext: string | null;  // null for last phase
  skillProgress: {
    skillsGained: string[];
    skillCoverage: number;  // 0-1
  };
}
```

---

## 6. API Integration Summary

### 6.1 Base URL

```
Development:  http://localhost:8000/api
Production:   https://api.adacode.ai/api
```

All endpoints di bawah ini menggunakan base URL di atas.

### 6.2 Endpoints

| Method | Full URL | Auth | Body | Response |
|--------|----------|------|------|-----------|
| POST | `{BASE}/rag/recommend/` | JWT | `{topic, additional_context?, count?, regenerate?}` | `201 + RAGRecommendResponse` |
| GET | `{BASE}/rag/recommendations/` | JWT | `?topic=&is_saved=&page=&page_size=` | `200 + paginated list` |
| PATCH | `{BASE}/rag/recommendations/{{id}}/` | JWT | `{is_saved: bool}` | `200 + updated rec` |
| POST | `{BASE}/rag/generate-roadmap/` | JWT | `{topic, count?}` | `201 + LearningPathDetailSerializer` |

**Contoh full URL:**
```
POST http://localhost:8000/api/rag/recommend/
POST https://api.adacode.ai/api/rag/generate-roadmap/
```

### 6.3 Existing Learning Path Endpoints

Jika frontend perlu operasi tambahan pada learning path (selain generate baru), endpoint berikut sudah ada:

| Method | Full URL | Auth | Body | Response | Notes |
|--------|----------|------|------|---------|-------|
| GET | `{BASE}/learning-paths/` | JWT | — | `200 + paginated list` | List semua learning path user |
| GET | `{BASE}/learning-paths/{uuid}/` | JWT | — | `200 + detail` | Detail satu learning path |
| PATCH | `{BASE}/learning-paths/{uuid}/bulk-update/` | JWT | `{courses: [{course_id, position}]}` | `200 + updated` | Reorder courses |
| POST | `{BASE}/learning-paths/courses/{uuid}/toggle-complete/` | JWT | — | `200 + {is_completed}` | Toggle course completion |

### 6.4 Full API Summary

| # | Method | Full URL | Auth | Body | Response |
|---|--------|----------|------|------|---------|---------|
| 1 | POST | `{BASE}/rag/recommend/` | JWT | `{topic, additional_context?, count?, regenerate?}` | `201` | Generate course recommendations |
| 2 | GET | `{BASE}/rag/recommendations/` | JWT | `?topic=&is_saved=&page=&page_size=` | `200` | List saved recommendations |
| 3 | PATCH | `{BASE}/rag/recommendations/{id}/` | JWT | `{is_saved: bool}` | `200` | Toggle saved status |
| 4 | POST | `{BASE}/rag/generate-roadmap/` | JWT | `{topic, count?}` | `201` | Generate learning path |
| 5 | GET | `{BASE}/learning-paths/` | JWT | — | `200` | List user's saved paths |
| 6 | GET | `{BASE}/learning-paths/{uuid}/` | JWT | — | `200` | Get path detail |
| 7 | PATCH | `{BASE}/learning-paths/{uuid}/bulk-update/` | JWT | `{courses}` | `200` | Reorder courses in path |
| 8 | POST | `{BASE}/learning-paths/courses/{uuid}/toggle-complete/` | JWT | — | `200` | Mark course complete/incomplete |

### 6.5 Auth Header

```
Authorization: Bearer <jwt_access_token>
```

### 6.6 Questionnaire Guard

Both RAG endpoints (`/rag/recommend/` dan `/rag/generate-roadmap/`) return `403` jika user belum complete questionnaire.

Frontend harus menangani dengan:

```
HTTP 403 → {"detail": "Complete the onboarding questionnaire before accessing this resource."}
→ Show full-screen CTA: "Selesaikan Kuesioner" → redirect ke /onboarding/questionnaire
```

---

### 6.7 Request & Response Examples

#### AI #1 — Course Recommendation

**POST /api/rag/recommend/ (fresh recommend)**

Request:
```json
{
  "topic": "machine learning untuk data science",
  "count": 5
}
```

Response 201:
```json
{
  "recommendations": [
    {
      "id": "rec-uuid-1",
      "course_obj": {
        "id": "course-uuid-1",
        "title": "Machine Learning with Python",
        "instructor": "IBM",
        "rating": "4.5",
        "reviews_count": 1234,
        "price": "570000.00",
        "currency": "IDR",
        "level": "Intermediate",
        "duration": "2 weeks at 10 hours a week",
        "video_hours": "133.00",
        "thumbnail_url": "https://...",
        "url": "https://www.coursera.org/..."
      },
      "relevance_score": 0.4725,
      "ai_explanation": "This course is intermediate level and requires...",
      "match_score": 0.8,
      "best_for": "Intermediate learners with more time and budget",
      "potential_gaps": "Not suitable for beginners...",
      "is_saved": false,
      "regenerate_count": 0,
      "created_at": "2026-05-02T12:00:00+00:00"
    },
    // ... 4 more recommendations
  ],
  "topic": "machine learning untuk data science",
  "total_retrieved": 3,
  "top_similarity_score": 0.473,
  "regenerate": false,
  "regenerate_count": 0
}
```

**POST /api/rag/recommend/ (regenerate with context)**

Request:
```json
{
  "topic": "machine learning untuk data science",
  "additional_context": "saya mau career switch ke data analyst, budget Rp 500rb, lebih suka kursus hands-on",
  "regenerate": true,
  "count": 5
}
```

Response 201:
```json
{
  "recommendations": [
    {
      "id": "rec-uuid-1",
      // ... same fields as above ...
      "ai_explanation": "This course is intermediate level... now explanation mentions career switch...",
      "regenerate_count": 1
      // ↑ incremented!
    },
    // ...
  ],
  "regenerate": true,
  "regenerate_count": 1
}
```

**PATCH /api/rag/recommendations/{id}/ (toggle saved)**

Request:
```json
{
  "is_saved": true
}
```

Response 200:
```json
{
  "id": "rec-uuid-1",
  "is_saved": true,
  // ... other fields
}
```

---

#### AI #2 — Learning Path Generation

**POST /api/rag/generate-roadmap/**

Request:
```json
{
  "topic": "web development dari nol",
  "count": 15
}
```

Response 201:
```json
{
  "id": "lp-uuid-1",
  "title": "Web Development from Scratch: A Beginner's Journey",
  "topic_input": "web development dari nol",
  "description": "...",
  "is_saved": false,
  "progress_percentage": 0.0,
  "courses": [
    {
      "id": "lpc-uuid-1",
      "course": {
        "id": "course-uuid-1",
        "title": "Introduction to HTML, CSS, & JavaScript",
        "instructor": "",
        "rating": "4.4",
        "level": "Beginner",
        "video_hours": "123.00",
        "price": "570000.00",
        "currency": "IDR",
        "url": "https://www.coursera.org/...",
        "thumbnail_url": "https://..."
      },
      "position": 1,
      "is_completed": false,
      "completed_at": null,
      "is_manually_added": false
    },
    {
      "id": "lpc-uuid-2",
      "course": {
        "title": "Developing Front-End Apps with React",
        // ... course detail
      },
      "position": 2,
      "is_completed": false,
      // ...
    }
  ],
  "created_at": "2026-05-02T12:00:00Z",
  "updated_at": "2026-05-02T12:00:00Z",
  "_rag_meta": {
    "courses_retrieved": 15,
    "top_similarity_score": 0.422,
    "retrieval_method": "semantic vector search + tag-based ordering"
  },
  "questionnaire_snapshot": {
    "roadmap_title": "Web Development from Scratch: A Beginner's Journey",
    "total_duration_weeks": 24,
    "total_hours_estimated": 270,
    "difficulty_curve": "beginner-friendly / progressive",
    "overview": "This roadmap is designed...",
    "target_skills": ["HTML", "CSS", "JavaScript", "React", "Front-End Development"],
    "phases": [
      {
        "phase_number": 1,
        "phase_name": "Foundation in Web Development",
        "phase_reason": "This phase introduces the essential building blocks of web development: HTML, CSS, and JavaScript...",
        "duration_weeks": 12,
        "learning_objectives": ["Understand HTML, CSS, JS basics", "Build simple web pages"],
        "courses": [
          {
            "course_id": "course-uuid-1",
            "title": "Introduction to HTML, CSS, & JavaScript",
            "match_reason": "Covers the fundamental technologies..."
          }
        ],
        "milestones": ["Create basic webpage", "Style a webpage with CSS"],
        "practice_projects": ["Build personal portfolio webpage"],
        "skill_progress": {
          "skills_gained": ["HTML", "CSS", "JavaScript"],
          "skill_coverage": 0.3
        },
        "transition_to_next": "Having learned the basics of HTML, CSS, and JavaScript, you are now ready to explore more complex front-end frameworks like React..."
      },
      {
        "phase_number": 2,
        "phase_name": "Advanced Front-End Development",
        "phase_reason": "This phase focuses on enhancing your front-end development skills by introducing React...",
        "duration_weeks": 12,
        "learning_objectives": ["Learn React basics", "Build interactive UIs"],
        "courses": [
          {
            "course_id": "course-uuid-2",
            "title": "Developing Front-End Apps with React",
            "match_reason": "Builds on your JavaScript knowledge..."
          }
        ],
        "transition_to_next": null
      }
    ],
    "tips_for_success": ["Practice coding daily", "Build projects regularly"],
    "next_steps_after_roadmap": ["Explore back-end development with Node.js"]
  }
}
```

---

Both endpoints return `403` if user has `questionnaire_completed_at = null`.
Frontend must handle this by redirecting to questionnaire screen.

```
HTTP 403 → {"detail": "Complete the onboarding questionnaire before accessing this resource."}
→ Show full-screen CTA: "Selesaikan Kuesioner" → redirect to /onboarding/questionnaire
```

---

## 7. UX Edge Cases

| Case | Behavior |
|------|---------|
| User generates same topic twice | Results may be identical (same FAISS retrieval). Regenerate with new context gives different explanation. |
| Regenerate with same context | AI explanation may be slightly different due to LLM temperature, but course IDs likely same. |
| FAISS returns only 1 course | Show 1 course card. Learning path may have 1 phase. |
| User types topic in Indonesian | Works — embedding model handles Indonesian text well. |
| User types topic in English | Also works. Recommend using English for better retrieval. |
| Rapid double-click on Generate | Debounce: disable button for 500ms after first click. |
| Network timeout during generation | Show error: "Request timeout. Silakan coba lagi." with retry button. |

---

## 8. Performance Considerations

| Concern | Mitigation |
|---------|------------|
| LLM call timeout (60s) | Show "Generating..." with step indicator |
| FAISS retrieval slow | Index pre-loaded in memory at server start |
| Large response (15 courses) | Frontend virtualized list for course cards |
| Regenerate = 5 more LLM calls | One LLM call per course × count. Max 20 courses. ~20-40s wait. Consider showing progress. |

---

## 9. Suggested Component Structure

```
src/
├── pages/
│   ├── CourseRecommendationPage.tsx
│   └── LearningPathPage.tsx
├── components/
│   ├── ai/
│   │   ├── TopicInput.tsx
│   │   ├── ContextTextarea.tsx
│   │   ├── CourseCard.tsx          ← used by both features
│   │   ├── PhaseCard.tsx
│   │   ├── AIExplanationBadge.tsx
│   │   ├── RegenerateSection.tsx
│   │   └── LoadingState.tsx
│   └── shared/
│       ├── CourseThumbnail.tsx
│       ├── LevelBadge.tsx
│       ├── RatingStars.tsx
│       └── PriceDisplay.tsx
├── hooks/
│   ├── useCourseRecommendation.ts
│   └── useLearningPath.ts
├── api/
│   └── ragApi.ts               ← centralized API calls
└── types/
    └── rag.ts                 ← TypeScript interfaces
```

---

## 3.7 Fitur Edit — Learning Path (Per-Course Operations)

Setelah learning path di-generate, user bisa mengedit secara granular: regenerate seluruh path, replace satu course, atau add/delete course.

### 3.7.1 Screen Design — Edit Mode

```
┌─────────────────────────────────────────────────────────────┐
│  ← Back              AI Learning Path                       │
├─────────────────────────────────────────────────────────────┤
│  📍 Machine Learning Foundations                      [🔄] │
│     ↑ Tap to regenerate entire path                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  PHASE 1: Foundation in Data Science                 [✓]   │
│                                                             │
│  ┌─── Individual Course Actions ───────────────────────┐  │
│  │ 1. [📷] Data Science Methodology                    │  │
│  │      ⭐ 4.5 | Intermediate | IBM                     │  │
│  │      [Replace] [Remove] [Mark Complete]              │  │
│  │                                                       │  │
│  │ 2. [📷] Tools for Data Science                 [✓]  │  │
│  │      ⭐ 4.6 | Beginner | IBM                         │  │
│  │      [Replace] [Remove] [Undo Complete]              │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  [+ Add Course]                                             │
│                                                             │
│  🔄 Transition: "With a solid understanding of DS..."      │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  [🔄 Regenerate Path]  [💾 Save]  [↩ Undo]                 │
└─────────────────────────────────────────────────────────────┘
```

### 3.7.2 Course Card — Edit Actions

```
┌────────────────────────────────────────────────────────────┐
│ [📷] Data Science Methodology                    [⋮ menu] │
│      ⭐ 4.5 (1,234) | Intermediate | IBM | Coursera      │
│      ⏱ 12 hours | 💰 IDR 0 (Audit)                        │
│                                                            │
│ 💡 match_reason: "Covers essential DS methodology..."    │
│                                                            │
│ ┌──────────────┐ ┌────────────┐ ┌─────────────────────┐  │
│ │ 🔄 Replace    │ │ ✕ Remove   │ │ ✓ Mark Completed    │  │
│ └──────────────┘ └────────────┘ └─────────────────────┘  │
└────────────────────────────────────────────────────────────┘
```

**Tap "🔄 Replace"** → opens replacement modal (see 3.7.3).
**Tap "✕ Remove"** → course removed, positions reindexed.

### 3.7.3 Replace Course Modal

```
┌─────────────────────────────────────────────────────────────┐
│  🔄 Replace Course                              [✕ Close] │
├─────────────────────────────────────────────────────────────┤
│  Replacing: "Data Science Methodology"                     │
│                                                             │
│  Kenapa mau ganti? (opsional)                               │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ terlalu panjang dan teori, saya mau yang lebih         │ │
│  │ practical dan hands-on                                │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
│  [🔍 Cari Replacement...]  ← loading → results appear     │
│                                                             │
│  ── Replacement Candidates ─────────────────────────────── │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ ⭐ 4.8 [Best Match]                                  │  │
│  │ Data Science Essentials                              │  │
│  │ IBM · Coursera · Intermediate · 8 hours              │  │
│  │ 💰 IDR 0 (Audit)                                     │  │
│  │                                                      │  │
│  │ 💡 AI Reason:                                        │  │
│  │ "Shorter and more practical than Data Science        │  │
│  │  Methodology — focuses on hands-on Python..."        │  │
│  │ Best for: learners who prefer practical projects    │  │
│  │ ⚠️ Concern: Less theoretical depth                  │  │
│  │                                                      │  │
│  │ [Select This Replacement]                            │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ ⭐ 4.6 [Good Match]                                  │  │
│  │ Python for Data Science and Machine Learning         │  │
│  │ ...                                                  │  │
│  │ [Select This Replacement]                           │  │
│  └─────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 3.7.4 Add Course Flow

```
1. User tap "+ Add Course"
   → Show search input + similar course list

2. Search for course by title/keyword
   → FAISS retrieves similar courses from DB

3. User selects course from list
   → Course inserted at chosen position
   → Positions reindexed

4. Path saved automatically (positions updated)
```

### 3.7.5 Regenerate Path Modal/Sheet

```
┌─────────────────────────────────────────────────────────────┐
│  🔄 Regenerate Learning Path                    [✕ Close] │
├─────────────────────────────────────────────────────────────┤
│  Regenerate akan membuat ulang seluruh path berdasarkan     │
│  topik yang sama, dengan mempertimbangkan konteks baru.    │
│                                                             │
│  ⚠️ Catatan:                                                │
│  • Courses yang sudah ditandai "completed" akan DIPERTAHANKAN│
│  • Courses lain akan di-regenerate                          │
│  • Regen count akan naik +1                                 │
│                                                             │
│  Konteks tambahan (opsional):                               │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ saya mau yang lebih fokus ke hands-on practice        │ │
│  │ dan kurang teori                                       │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
│  [🔄 Regenerate]                                            │
└─────────────────────────────────────────────────────────────┘
```

---

## 3.8 Learning Path Edit — API Endpoints

### 3.8.1 POST `/api/rag/learning-paths/{id}/regenerate/`

Regenerate seluruh learning path. Courses yang sudah ditandai "completed" akan dipertahankan.

**Request:**
```json
POST /api/rag/learning-paths/2555b372-.../regenerate/
Authorization: Bearer <token>
Content-Type: application/json

{
  "additional_context": "saya mau yang lebih hands-on dan kurang teori"
}
```

**Response** (HTTP 200):
```json
{
  "id": "2555b372-...",
  "title": "Machine Learning Foundations...",
  "regenerate_count": 2,
  "regenerate_context": "saya mau yang lebih hands-on dan kurang teori",
  "progress_percentage": 33.33,
  "courses": [...],
  "_rag_meta": {
    "regenerate_count": 2,
    "regenerate_context": "saya mau yang lebih hands-on dan kurang teori",
    "completed_courses_preserved": 1,
    "courses_retrieved": 20,
    "top_similarity_score": 0.478
  }
}
```

### 3.8.2 POST `/api/rag/learning-paths/{id}/courses/{course_id}/replace/`

Mendapatkan kandidat course pengganti beserta AI explanation.

**Request:**
```json
POST /api/rag/learning-paths/2555b372-.../courses/abc-.../replace/
Authorization: Bearer <token>
Content-Type: application/json

{
  "additional_context": "terlalu teori, saya mau yang hands-on",
  "count": 5
}
```

**Response** (HTTP 200):
```json
{
  "original_course_id": "abc-...",
  "original_course_title": "Data Science Methodology",
  "replacement_reason_summary": "User likely wants more practical, hands-on approach",
  "candidates": [
    {
      "course_id": "new-course-uuid",
      "title": "Data Science Essentials",
      "instructor": "IBM",
      "platform": "Coursera",
      "level": "Beginner",
      "rating": 4.8,
      "price": 0,
      "currency": "IDR",
      "duration": "4 weeks",
      "thumbnail_url": "https://...",
      "url": "https://...",
      "score": 0.92,
      "faiss_score": 0.489,
      "match_reason": "Shorter and more practical than Data Science Methodology...",
      "best_for": "Learners who prefer hands-on projects over theory",
      "potential_concerns": "Less theoretical depth than the original course"
    }
  ]
}
```

**Frontend Flow:**
1. Call replace endpoint → show loading
2. Display candidates sorted by `score` (AI evaluation)
3. User picks one → call **apply-replacement** (see 3.8.3)
4. If no candidate liked → user can cancel

### 3.8.3 PATCH `/api/rag/learning-paths/{id}/courses/{course_id}/` (Apply Replacement)

Menyatukan "find replacement" + "apply" menjadi satu endpoint. Set body `new_course_id` untuk replace, atau kosongkan untuk delete.

> **Note:** Untuk simplicity, replace dan delete di-handle oleh endpoint yang sama.

**Request (Replace):**
```json
PATCH /api/rag/learning-paths/2555b372-.../courses/abc-.../
Authorization: Bearer <token>
Content-Type: application/json

{
  "new_course_id": "new-uuid-...",
  "action": "replace",
  "replacement_reason": "saya tidak suka course yang terlalu teori"
}
```

**Response** (HTTP 200):
```json
{
  "detail": "Course replaced successfully.",
  "learning_path": { ... full LearningPathDetailSerializer ... }
}
```

**Request (Delete):**
```json
PATCH /api/rag/learning-paths/2555b372-.../courses/abc-.../
Authorization: Bearer <token>
Content-Type: application/json

{
  "action": "delete"
}
```

**Response** (HTTP 200):
```json
{
  "detail": "Course removed from learning path.",
  "deleted_position": 3
}
```

### 3.8.4 DELETE `/api/rag/learning-paths/{id}/courses/{course_id}/`

Hapus course dari learning path. Positions di-reindex otomatis.

**Request:**
```json
DELETE /api/rag/learning-paths/2555b372-.../courses/abc-.../
Authorization: Bearer <token>
```

**Response** (HTTP 200):
```json
{
  "detail": "Course removed from learning path.",
  "position": 3
}
```

### 3.8.5 POST `/api/rag/learning-paths/{id}/courses/add/`

Tambahkan course ke learning path.

**Request:**
```json
POST /api/rag/learning-paths/2555b372-.../courses/add/
Authorization: Bearer <token>
Content-Type: application/json

{
  "course_id": "new-course-uuid",
  "position": 3  // optional, omit to append at end
}
```

**Response** (HTTP 200):
```json
{
  ...full LearningPathDetailSerializer...
}
```

### 3.8.6 GET `/api/rag/learning-paths/{id}/courses/{course_id}/similar/`

Dapatkan daftar course serupa (dari FAISS) — untuk Add Course atau browsing alternatif.

**Request:**
```
GET /api/rag/learning-paths/2555b372-.../courses/abc-.../similar/?limit=10
Authorization: Bearer <token>
```

**Response** (HTTP 200):
```json
{
  "original_course_id": "abc-...",
  "original_course_title": "Data Science Methodology",
  "topic": "data science",
  "courses": [
    {
      "course_id": "similar-uuid-1",
      "title": "Data Science Essentials",
      "instructor": "IBM",
      "platform": "Coursera",
      "level": "Beginner",
      "rating": 4.8,
      "reviews_count": 2341,
      "price": 0,
      "currency": "IDR",
      "duration": "4 weeks",
      "thumbnail_url": "https://...",
      "url": "https://...",
      "relevance_score": 0.478,
      "faiss_score": 0.478
    }
  ]
}
```

### 3.8.7 GET `/api/rag/learning-paths/` — List All User Paths

**Request:**
```
GET /api/rag/learning-paths/
Authorization: Bearer <token>
```

**Response** (HTTP 200):
```json
{
  "results": [
    {
      "id": "2555b372-...",
      "title": "Machine Learning Foundations...",
      "topic_input": "machine learning",
      "is_saved": true,
      "total_courses": 5,
      "completed_courses": 1,
      "progress_percentage": 20.0,
      "regenerate_count": 2,
      "created_at": "2026-05-02T12:00:00Z"
    }
  ],
  "total": 5,
  "page": 1,
  "page_size": 10
}
```

---

## 3.9 Learning Path — TypeScript Interfaces

```typescript
// ─── Request Types ───────────────────────────────────────────────

interface RegeneratePathRequest {
  additional_context?: string;
  keep_courses?: boolean;
}

interface ReplaceCourseRequest {
  additional_context?: string;
  count?: number;  // default 5
}

interface ApplyReplacementRequest {
  new_course_id: string;
  replacement_reason?: string;
}

interface DeleteCourseRequest {
  action: 'delete';
}

interface AddCourseRequest {
  course_id: string;
  position?: number;  // omit = append at end
}

// ─── Response Types ───────────────────────────────────────────────

interface ReplacementCandidate {
  course_id: string;
  title: string;
  instructor: string;
  platform: string;
  level: string;
  rating: number | null;
  price: number | null;
  currency: string;
  duration: string;
  thumbnail_url: string;
  url: string;
  score: number;       // AI evaluation score (0-1)
  faiss_score: number; // Vector search score (0-1)
  match_reason: string;
  best_for: string;
  potential_concerns: string;
}

interface ReplaceCourseResponse {
  original_course_id: string;
  original_course_title: string;
  replacement_reason_summary: string;
  candidates: ReplacementCandidate[];
}

interface SimilarCourse {
  course_id: string;
  title: string;
  instructor: string | null;
  platform: string;
  level: string;
  rating: number | null;
  reviews_count: number | null;
  price: number | null;
  currency: string;
  duration: string;
  thumbnail_url: string;
  url: string;
  relevance_score: number;
  faiss_score: number;
}

interface SimilarCoursesResponse {
  original_course_id: string;
  original_course_title: string;
  topic: string;
  courses: SimilarCourse[];
}

interface LearningPathListItem {
  id: string;
  title: string;
  topic_input: string;
  is_saved: boolean;
  total_courses: number;
  completed_courses: number;
  progress_percentage: number;
  regenerate_count: number;
  created_at: string;
  updated_at: string;
}
```

---

## 3.10 Complete URL Reference — Learning Path Edit Feature

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/rag/learning-paths/` | List all user's learning paths |
| `GET` | `/api/rag/learning-paths/{id}/` | Get single learning path detail |
| `POST` | `/api/rag/generate-roadmap/` | Generate new learning path |
| `POST` | `/api/rag/learning-paths/{id}/regenerate/` | **Regenerate entire path** |
| `POST` | `/api/rag/learning-paths/{id}/courses/{course_id}/replace/` | **Get replacement candidates** |
| `POST` | `/api/rag/learning-paths/{id}/courses/{course_id}/apply/` | **Apply selected replacement** |
| `DELETE` | `/api/rag/learning-paths/{id}/courses/{course_id}/` | **Delete a course** |
| `POST` | `/api/rag/learning-paths/{id}/courses/add/` | **Add course to path** |
| `GET` | `/api/rag/learning-paths/{id}/courses/{course_id}/similar/` | Get similar course recommendations |
| `PATCH` | `/api/rag/learning-paths/{id}/courses/{course_id}/toggle-complete/` | Toggle course completion |

1. **Count selector** — should user be able to pick count (3/5/10/15/20) or fix at 5?
2. **Bookmark/save** — should saved recommendations appear in a separate "My Saved Courses" page?
3. **Learning path phase completion** — should user be able to mark a phase as "completed" or only individual courses?
4. **Share/export** ��� what format for sharing? Copy link, PDF, or image?
5. **History** — should user see history of previous recommendations/paths (from `GET /api/rag/recommendations/`)?