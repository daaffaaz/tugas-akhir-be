# Questionnaire Answers API

## GET /api/questionnaires/users/questionnaire/

Fetch all questionnaire answers for the currently authenticated user.

### Auth

Requires `Authorization: Bearer <access_token>` header.

### Response

**200 OK** — returns an array of answer objects (empty array if user hasn't submitted yet).

```json
[
  {
    "id": "uuid",
    "question_id": "uuid",
    "order_number": 1,
    "answer_option": "A",
    "submitted_at": "2026-05-15T10:00:00Z"
  }
]
```

| Field | Type | Description |
|---|---|---|
| `id` | UUID | Answer record ID |
| `question_id` | UUID | Foreign key to the question |
| `order_number` | integer | Question order (1–32) |
| `answer_option` | string | Selected option key (e.g. `"A"`, `"B"`) |
| `submitted_at` | ISO 8601 datetime | Last time this answer was saved |

### Checking if questionnaire is completed

Use `GET /api/users/profile/` — the `questionnaire_completed_at` field is `null` if not yet submitted, or a datetime string if completed.

---

## POST /api/questionnaires/users/questionnaire/

Submit all questionnaire answers for the first time (32 answers required).

### Auth

Requires `Authorization: Bearer <access_token>` header.

### Request Body

Array of 32 answer objects — one per question, covering all question IDs.

```json
[
  { "question_id": "uuid", "answer_option": "A" },
  { "question_id": "uuid", "answer_option": "C" }
]
```

### Response

**201 Created** — same shape as GET response.

**400 Bad Request** — if questionnaire already completed, wrong number of answers, duplicate question IDs, or invalid `answer_option` for a question.

---

## PATCH /api/questionnaires/users/questionnaire/

Update one or more specific answers after initial submission.

### Auth

Requires `Authorization: Bearer <access_token>` header.

### Request Body

Partial array — only include the answers you want to update.

```json
[
  { "question_id": "uuid", "answer_option": "B" }
]
```

### Response

**200 OK** — returns only the updated answer objects (same shape as GET).

**400 Bad Request** — if questionnaire hasn't been completed yet (POST first), empty array, duplicate question IDs, or invalid `answer_option`.

---

## Integration Notes

1. On app load / onboarding check: call `GET /api/users/profile/` and inspect `questionnaire_completed_at`.
2. If `null` → show questionnaire form, fetch questions from `GET /api/questionnaires/questions/`, then submit via `POST`.
3. If not `null` → user already answered; fetch existing answers via `GET /api/questionnaires/users/questionnaire/` to pre-fill or display a summary.
4. For partial updates (e.g. user edits a single answer): use `PATCH`.
