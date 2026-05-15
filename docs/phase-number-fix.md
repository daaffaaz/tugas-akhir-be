# Fix: phase_number Not Preserved on Course Replace / Bulk Update

## Background

Since commit `b828cb8`, the frontend groups courses in a learning path by `phase_number`. Courses with `phase_number=null` fall into a catch-all "Kursus Tambahan" bucket.

## Root Cause

Two separate flows both had the same bug: when replacing an existing `LearningPathCourse` record (delete old → create new), `phase_number` from the old record was never copied to the new one, so it defaulted to `null`.

### Flow 1 — PATCH `/api/learning-paths/{id}/courses/{course_id}/`

`apps/rag/views.py` ~line 647

```python
# Before (broken)
old_position = item.position
item.delete()
LearningPathCourse.objects.create(
    learning_path=lp,
    course_id=new_course_id,
    position=old_position,
    is_manually_added=True,
    # phase_number missing → defaults to null
)

# After (fixed)
old_position = item.position
old_phase_number = item.phase_number   # save before delete
item.delete()
LearningPathCourse.objects.create(
    learning_path=lp,
    course_id=new_course_id,
    position=old_position,
    phase_number=old_phase_number,     # preserved
    is_manually_added=True,
)
```

### Flow 2 — POST `/api/learning-paths/{id}/apply/`

`apps/rag/views.py` ~line 1101 — identical pattern, same fix applied.

### Flow 3 — PUT `/api/learning-paths/{id}/`  (bulk update)

`BulkCourseItemSerializer` did not accept `phase_number` at all, so it was never written on create or update.

**`apps/learning_paths/serializers.py`**

```python
# Added to BulkCourseItemSerializer
phase_number = serializers.IntegerField(required=False, allow_null=True, default=None)
```

**`apps/learning_paths/views.py`** — `LearningPathBulkUpdateView.put`

```python
# Before (broken)
lpc.save(update_fields=['position', 'is_manually_added'])
LearningPathCourse.objects.create(..., is_manually_added=manual)

# After (fixed)
phase = row.get('phase_number')
lpc.phase_number = phase
lpc.save(update_fields=['position', 'is_manually_added', 'phase_number'])
LearningPathCourse.objects.create(..., is_manually_added=manual, phase_number=phase)
```

## Frontend Integration Notes

- `PUT /api/learning-paths/{id}/` now accepts `phase_number` (integer or null) per course item in the `courses` array.
- On replace (PATCH / POST apply), the backend automatically inherits `phase_number` from the replaced record — no FE change needed for those flows.
- For bulk update, FE **must** include `phase_number` in each course object to preserve phase grouping. If omitted, it defaults to `null` (course moves to "Kursus Tambahan").

### Updated bulk update payload shape

```json
{
  "courses": [
    {
      "course_id": "uuid",
      "position": 1,
      "phase_number": 1,
      "is_manually_added": false
    }
  ]
}
```
