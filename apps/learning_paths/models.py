import uuid

from django.conf import settings
from django.db import models


class CourseRecommendation(models.Model):
    """
    Hasil rekomendasi course tunggal per user.
    Disimpan agar user bisa lihat ulang history & toggle saved.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='course_recommendations',
    )
    course = models.ForeignKey(
        'courses.Course',
        on_delete=models.CASCADE,
        related_name='recommendations_received',
    )
    topic_input = models.CharField(max_length=255, blank=True)
    additional_context = models.TextField(blank=True, default='')
    relevance_score = models.FloatField(
        default=0.0,
        help_text='Cosine similarity score dari FAISS (0.0–1.0)'
    )
    ai_explanation = models.TextField(
        blank=True,
        default='',
        help_text='Penjelasan AI kenapa course ini cocok untuk user'
    )
    is_saved = models.BooleanField(
        default=False,
        help_text='User menandai ingin menyimpan course ini'
    )
    regenerate_count = models.PositiveSmallIntegerField(
        default=0,
        help_text='Jumlah kali user regenerate rekomendasi ini'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'course_recommendations'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'course', 'topic_input'],
                name='uniq_user_course_topic',
            ),
        ]

    def __str__(self):
        return f"Rec: {self.user_id} → {self.course_id} ({self.topic_input})"


class LearningPath(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='learning_paths',
    )
    title = models.CharField(max_length=255)
    topic_input = models.TextField(blank=True)
    description = models.TextField(blank=True)
    is_saved = models.BooleanField(default=False)
    questionnaire_snapshot = models.JSONField(null=True, blank=True)
    # Regenerate tracking
    regenerate_count = models.PositiveSmallIntegerField(default=0)
    regenerate_context = models.TextField(
        blank=True,
        default='',
        help_text='Additional context used in last regenerate'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'learning_paths'
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class LearningPathCourse(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    learning_path = models.ForeignKey(
        LearningPath,
        on_delete=models.CASCADE,
        related_name='path_courses',
    )
    course = models.ForeignKey(
        'courses.Course',
        on_delete=models.CASCADE,
        related_name='learning_path_items',
    )
    position = models.PositiveSmallIntegerField()
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    is_manually_added = models.BooleanField(default=False)
    added_at = models.DateTimeField(auto_now_add=True)
    # Replacement tracking
    replaced_by = models.ForeignKey(
        'courses.Course',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='replaced_courses',
        help_text='If this course was replaced, reference the new course here'
    )
    replacement_reason = models.TextField(
        blank=True,
        default='',
        help_text='User-provided reason for replacing this course'
    )
    replacement_context = models.TextField(
        blank=True,
        default='',
        help_text='AI context used to find replacement course'
    )
    # Regenerate tracking (if this course was part of a roadmap regenerate)
    regenerate_version = models.PositiveSmallIntegerField(
        default=0,
        help_text='LearningPath.regenerate_count at time this course was added'
    )

    class Meta:
        db_table = 'learning_path_courses'
        ordering = ['position']
        constraints = [
            models.UniqueConstraint(
                fields=['learning_path', 'course'],
                name='uniq_learning_path_course',
            ),
        ]

    def __str__(self):
        return f'{self.learning_path_id} @ {self.position}'
