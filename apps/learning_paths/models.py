import uuid

from django.conf import settings
from django.db import models


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
