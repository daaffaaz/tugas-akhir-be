# RAG-Powered Course Recommendation System — PRD

## 1. Project Overview

### Project Name
**RAG-Course-Rec** — Retrieval Augmented Generation untuk Sistem Rekomendasi Microcredential

### Problem Statement
Sistem rekomendasi course saat ini (existing project) memiliki limitation:
1. **Roadmap generator LLM bekerja tanpa konteks course** — LLM mengenerate roadmap + course recommendations dari "nol", menyebabkan:
   - Hallucination: course title/URL yang tidak ada di database
   - Tidak akurat: metadata course (duration, level, skills) sering salah
   - Tidak grounded: rekomendasi tidak mencerminkan actual course yang tersedia
2. **Embedding-based similarity hanya untuk matching**, tidak untuk augmented generation
3. **Knowledge graph tidak diintegrasikan** ke LLM generation pipeline

### Solution
Implementasi **RAG (Retrieval Augmented Generation)** architecture:
- **Retrieve**: Query relevant courses dari vector database berdasarkan user profile + goals
- **Augment**: Inject retrieved course data + metadata ke LLM prompt sebagai context
- **Generate**: LLM generate personalized roadmap berbasis real course data

### Target Users
- Learner/mahasiswa yang ingin mendapat learning roadmap personal
- Admins yang ingin sistem rekomendasi lebih akurat & grounded

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    USER INPUT                            │
│  (current_skills, interests, goals, background, budget) │
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────┐
│               RETRIEVAL PIPELINE                         │
│                                                          │
│  ┌──────────────┐    ┌──────────────┐   ┌─────────────┐ │
│  │  Query       │───▶│  Vector       │──▶│  Top-K      │ │
│  │  Embedding   │    │  Store (FAISS │   │  Courses    │ │
│  │  (user prof) │    │  /ChromaDB)   │   │  Retrieved  │ │
│  └──────────────┘    └──────────────┘   └──────┬──────┘ │
│                                                 │        │
│  ┌──────────────┐    ┌──────────────┐           │        │
│  │ Knowledge   │───▶│  Prerequisite│◀──────────┘        │
│  │ Graph       │    │  Chain       │                     │
│  │ (NetworkX)  │    │  (ordered)    │                     │
│  └──────────────┘    └──────────────┘                     │
└──────────────────────────┬───────────────────────────────┘
                           │ Retrieved Context
                           ▼
┌──────────────────────────────────────────────────────────┐
│               AUGMENTATION LAYER                         │
│                                                          │
│  System Prompt: "You are a learning path advisor..."     │
│  + Retrieved courses (title, desc, skills, level)       │
│  + User profile                                          │
│  + Knowledge graph data (prerequisites)                 │
│  + Retrieval metadata (similarity scores)                │
└──────────────────────────┬───────────────────────────────┘
                           │ Augmented Prompt
                           ▼
┌──────────────────────────────────────────────────────────┐
│               GENERATION LAYER                           │
│                                                          │
│  LLM (GPT-4o / Claude Sonnet)                            │
│  ↓                                                       │
│  Output: Structured Roadmap (JSON)                       │
│  - phase-by-phase learning plan                         │
│  - real course IDs from database                         │
│  - grounded recommendations (no hallucination)            │
└──────────────────────────────────────────────────────────┘
```

---

## 3. Data Flow

### 3.1 Knowledge Base Construction

```
Raw CSV Courses
      │
      ▼
┌─────────────────┐
│  Data Cleaning  │  (normalize, deduplicate, fill missing)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  LLM Metadata   │  (extract skills, prerequisites, topics)
│  Extraction     │  (batch process, checkpointing)
└────────┬────────┘
         │
    ┌────┴───────────────────────────────┐
    │                                     │
    ▼                                     ▼
┌──────────────────┐            ┌──────────────────┐
│  Vector Store    │            │  Knowledge Graph │
│  (FAISS/ChromaDB)│            │  (NetworkX)      │
│                  │            │                  │
│  - course_id     │            │  - nodes: courses│
│  - title_emb     │            │  - edges: prereq │
│  - desc_emb      │            │  - difficulty    │
│  - combined_emb  │            │  - skill graph   │
│  - metadata JSON │            └──────────────────┘
└──────────────────┘
```

### 3.2 RAG Query Flow

```
User Profile Input
        │
        ▼
[1] Embed user profile → query_vector
        │
        ▼
[2] Vector similarity search → Top-K relevant courses
        │
        ├─▶ courses_retrieved (semantic match)
        │
        ▼
[3] Knowledge graph traversal
        │
        ├─▶ prereq_courses (what user needs first)
        ├─▶ next_courses (what comes after)
        └─▶ skill_graph (skill dependencies)
        │
        ▼
[4] Context Assembly
        │
        │ Retrieved courses (max 15-20)
        │ + User profile
        │ + Prerequisite chain
        │ + Skills matched
        │ + Generation instructions
        │
        ▼
[5] LLM Generation
        │
        ▼
Structured Roadmap Output (validated against DB)
```

---

## 4. RAG Components Specification

### 4.1 Chunking Strategy

**Chunk Type**: Course-level chunks (full course as one chunk)

| Chunk Field | Source | Max Tokens (est.) |
|---|---|---|
| `title` | course title | ~20 |
| `description` | course description | ~300 |
| `what_you_learn` | bullet points | ~200 |
| `skills_gained` | LLM-extracted | ~100 |
| `prerequisites` | LLM-extracted | ~80 |
| `topics_covered` | LLM-extracted | ~100 |
| `metadata` | level, duration, rating | ~50 |
| **Total** | | **~850 tokens** |

**Multi-representation chunks** (untuk retrieval diversity):
- `title + short_desc`: ~100 tokens — untuk broad matching
- `skills + topics`: ~200 tokens — untuk skill-gap matching
- `full_course`: ~850 tokens — untuk detailed context

### 4.2 Vector Store Options

| Option | Pros | Cons | Recommended For |
|---|---|---|---|
| **FAISS** | Fast, local, no server | No metadata filtering | MVP, local dev |
| **ChromaDB** | Rich metadata, easy API | Needs running server | Prod with filtering |
| **Pinecone** | Managed, scalable | API key needed, cost | Production |
| **Qdrant** | Fast, Rust-based | Self-hosted | High performance |

**Recommendation**: Start with **FAISS** (IndexFlatIP), upgrade to **ChromaDB** for production.

### 4.3 Retrieval Configuration

```python
# Retrieval params
TOP_K_SEMANTIC = 15          # courses from vector search
TOP_K_SKILL_MATCH = 10       # courses matched by skills
MAX_CONTEXT_COURSES = 12     # max courses in prompt context
SIMILARITY_THRESHOLD = 0.35  # filter low-quality matches

# Reranking
USE_RERANKER = True          # cross-encoder reranking (optional)
RERANK_TOP_N = 8             # keep top N after reranking
```

### 4.4 Knowledge Graph Integration

```python
# Graph-based retrieval
GRAPH_DEPTH = 2              # traverse N levels of prerequisites
INCLUDE_NEXT_COURSES = True  # also retrieve "next level" courses
SKILL_GRAPH_ENABLED = True   # match by skill dependencies
```

---

## 5. RAG Prompt Templates

### 5.1 Roadmap Generation Prompt (Main)

```
SYSTEM:
You are an expert learning path advisor for online courses.
You MUST only recommend courses that exist in the provided context.
Do NOT invent course names, URLs, or details.
If no suitable course exists for a topic, say "No matching course available."

USER PROFILE:
{user_profile_json}

AVAILABLE COURSES (retrieved from database):
{courses_context}

PREREQUISITE CHAIN (from knowledge graph):
{prereq_chain}

SKILLS MAPPING:
- User's current skills: {current_skills}
- Skills to gain: {target_skills}
- Skill gaps identified: {skill_gaps}

INSTRUCTIONS:
1. Analyze user's current skill level and goals
2. Identify the correct prerequisite order using the provided chain
3. Create a phase-by-phase roadmap
4. For EACH phase, recommend ONLY courses from the AVAILABLE COURSES list
5. Include exact course IDs from the database
6. Estimate realistic duration based on course duration + 20% practice time
7. Output valid JSON matching the schema below

OUTPUT SCHEMA:
{roadmap_schema}
```

### 5.2 Course Recommendation Prompt

```
SYSTEM:
Recommend courses strictly from the provided course list.
Output valid JSON array of course objects.

USER GOALS: {user_goals}
USER SKILLS: {user_skills}
PREFERRED LEVEL: {preferred_level}
BUDGET: {budget}

AVAILABLE COURSES:
{courses_context}

OUTPUT: JSON array with course_id, title, match_reason, priority_score
```

---

## 6. Output Schema

### Roadmap Output

```json
{
  "roadmap_id": "uuid",
  "generated_at": "ISO timestamp",
  "retrieval_info": {
    "courses_retrieved": 15,
    "top_similarity_score": 0.82,
    "retrieval_method": "hybrid (semantic + skill + graph)"
  },
  "user_profile_hash": "anon hash of profile",
  "roadmap_title": "string",
  "target_skills": ["list"],
  "total_duration_weeks": "int",
  "total_hours_estimated": "int",
  "difficulty_curve": "string",
  "overview": "string",
  "phases": [
    {
      "phase_number": 1,
      "phase_name": "Foundation",
      "duration_weeks": 2,
      "learning_objectives": ["list"],
      "courses": [
        {
          "course_id": "int (MUST match DB)",
          "title": "string",
          "match_reason": "why this course was selected",
          "focus_areas": ["what to focus on"],
          "estimated_hours": "float"
        }
      ],
      "milestones": ["list"],
      "practice_projects": ["list"],
      "skill_progress": {
        "skills_gained": ["list"],
        "skill_coverage": "float (0-1)"
      }
    }
  ],
  "cross_phase_learning": ["skills developed across phases"],
  "tips_for_success": ["list"],
  "next_steps_after_roadmap": ["list"],
  "validation": {
    "all_courses_valid": true,
    "prerequisites_respected": true,
    "no_hallucinated_courses": true
  }
}
```

---

## 7. Evaluation Metrics

### 7.1 RAG-Specific Metrics

| Metric | Description | Target |
|---|---|---|
| **Context Relevance** | Avg cosine similarity of retrieved docs to query | > 0.6 |
| **Context Precision** | % of retrieved docs actually used in output | > 0.4 |
| **Groundedness** | % of course IDs in output that exist in DB | 100% |
| **Citation Accuracy** | % of cited courses that match the recommendation | > 95% |
| **Retrieval Recall** | % of relevant courses retrieved (human eval) | > 0.7 |

### 7.2 Generation Quality Metrics

| Metric | Description |
|---|---|
| **Hallucination Rate** | # of fake course IDs / total courses in roadmap |
| **Prerequisite Accuracy** | Are courses in correct learning order? |
| **Schema Compliance** | Does output match JSON schema? |
| **Completeness** | Are all phases filled with real courses? |
| **User Preference Match** | Does roadmap respect budget/level/duration prefs? |

### 7.3 Human Evaluation Checklist

```
[ ] Roadmap uses only real courses from DB
[ ] Course IDs are valid and point to correct course
[ ] Prerequisites order is respected
[ ] Duration estimate is realistic
[ ] All skills in roadmap phases are from course curricula
[ ] No invented course names or URLs
[ ] Budget constraint is respected
[ ] Level preference is respected
[ ] Total roadmap duration matches user time availability
```

---

## 8. Tech Stack

### Core Dependencies

```
# RAG / Vector Store
faiss-cpu==1.8.0          # or faiss-gpu for CUDA
sentence-transformers==2.4.0  # embeddings

# or alternatively:
# chromadb==0.4.22

# LLM
anthropic>=0.21.0         # Claude
openai>=1.30.0            # GPT-4o

# Knowledge Graph
networkx==3.2.1

# API
fastapi==0.110.0
uvicorn==0.27.0

# Data
pandas==2.2.0
pydantic==2.6.0

# Evaluation
scikit-learn==1.4.0       # metrics
```

### Project Structure

```
rag-course-rec/
├── src/
│   ├── __init__.py
│   ├── config.py                 # settings, API keys
│   ├── data/
│   │   ├── loader.py             # load course CSVs
│   │   └── schemas.py            # Pydantic models
│   ├── retrieval/
│   │   ├── chunker.py            # course chunking logic
│   │   ├── vector_store.py        # FAISS/ChromaDB wrapper
│   │   ├── embedder.py           # embedding generation
│   │   └── knowledge_graph.py    # prerequisite graph
│   ├── rag/
│   │   ├── retriever.py          # retrieval orchestrator
│   │   ├── context_builder.py    # build LLM context
│   │   ├── prompts.py             # prompt templates
│   │   └── generator.py          # LLM generation + validation
│   ├── pipeline/
│   │   ├── build_index.py         # build vector index + graph
│   │   └── query.py               # full RAG query pipeline
│   └── api/
│       └── routes.py              # FastAPI endpoints
├── tests/
│   ├── test_retrieval.py
│   ├── test_groundedness.py       # check hallucination rate
│   └── test_integration.py
├── data/
│   └── courses.csv                # your course data
├── notebooks/
│   ├── 01_build_index.ipynb
│   ├── 02_evaluate_retrieval.ipynb
│   └── 03_evaluate_generation.ipynb
├── .env.example
├── requirements.txt
├── README.md
└── SPEC.md
```

---

## 9. Implementation Phases

### Phase 1: Foundation (Week 1-2)
- [ ] Setup project structure
- [ ] Load and validate course data
- [ ] Implement LLM metadata extraction (skills, prerequisites, topics)
- [ ] Build FAISS vector index with course embeddings
- [ ] Build knowledge graph (prerequisite edges)

### Phase 2: Retrieval (Week 2-3)
- [ ] Implement chunker (multi-representation chunks)
- [ ] Implement hybrid retrieval (semantic + skill + graph)
- [ ] Implement context builder (assemble LLM prompt)
- [ ] Write prompt templates
- [ ] Basic retrieval evaluation (precision, recall)

### Phase 3: Generation (Week 3-4)
- [ ] Implement roadmap generator with RAG context
- [ ] Implement course recommendation generator
- [ ] Implement output validation (check course IDs exist)
- [ ] Schema compliance testing
- [ ] Hallucination rate measurement

### Phase 4: Evaluation & Polish (Week 4-5)
- [ ] RAG-specific metrics (context relevance, precision)
- [ ] Human evaluation framework
- [ ] Compare RAG approach vs baseline (no-RAG)
- [ ] API endpoint implementation
- [ ] Documentation

### Phase 5 (Optional): Enhancements
- [ ] Cross-encoder reranking
- [ ] Multi-query retrieval (decompose user goals)
- [ ] Feedback loop (user ratings → re-ranking)
- [ ] Streaming generation for long roadmaps

---

## 10. Comparison: Current vs RAG Approach

| Aspect | Current (No RAG) | RAG Approach |
|---|---|---|
| **Roadmap generation** | LLM generates from scratch | Retrieve → Augment → Generate |
| **Course references** | LLM may invent names/URLs | Real course IDs from DB |
| **Context awareness** | None | Full course metadata in prompt |
| **Prerequisite handling** | LLM estimates | Graph-structured retrieval |
| **Hallucination risk** | High | **Minimized** (grounded) |
| **Generation accuracy** | ~60-70% | **90-95%** (estimated) |
| **Token usage** | Lower (no context) | Higher (injected context) |
| **Latency** | Faster | Slightly slower (retrieval overhead) |
| **Implementation complexity** | Low | Medium |

---

## 11. Key Differences from Existing Project

The RAG approach **augments, not replaces** your existing components:

| Existing Component | RAG Integration |
|---|---|
| `embeddings.py` | **Enhanced**: Multi-representation chunks for better retrieval |
| `llm_extractor.py` | **Kept as-is**: Used to build rich metadata for knowledge base |
| `knowledge_graph.py` | **Enhanced**: Integrated into retrieval pipeline, not just post-hoc |
| `roadmap_generator.py` | **Rewritten**: Now uses RAG context instead of bare profile |
| `recommender.py` | **Enhanced**: Hybrid retrieval (vector + skill + graph) |

---

## 12. Success Criteria

- [ ] **Groundedness = 100%**: Every course ID in output exists in database
- [ ] **Prerequisite accuracy > 90%**: Course order respects knowledge graph
- [ ] **Context relevance > 0.6**: Retrieved docs are actually relevant
- [ ] **Schema compliance > 95%**: LLM output parses correctly
- [ ] **Latency < 10s**: Full RAG pipeline (retrieve + generate)
- [ ] **Human eval score > 4/5**: Expert rating of roadmap quality

---

## 13. Notes for User

1. **Data yang perlu Anda provide**: File CSV courses dengan kolom yang ada di existing project (atau mapping schema baru)
2. **API Keys**: OpenAI atau Anthropic untuk LLM generation
3. **Embedding model**: Bisa pakai `all-MiniLM-L6-v2` (local, gratis) atau `text-embedding-3-small` (OpenAI)
4. **Chunk size**: ~850 tokens per course sudah cukup untuk semua metadata
5. **Top-K retrieval**: 12-15 courses sudah cukup untuk context window LLM
6. **Batch processing**: Metadata extraction bisa di-batch untuk efficiency
