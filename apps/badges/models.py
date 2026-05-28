import uuid

from django.conf import settings
from django.db import models


class BadgeLevel(models.TextChoices):
    PEMULA = 'pemula', 'Pemula'
    MENENGAH = 'menengah', 'Menengah'
    MAHIR = 'mahir', 'Mahir'


class BadgeCategory(models.TextChoices):
    UI_UX = 'ui_ux', 'UI/UX'
    FRONTEND = 'frontend', 'Frontend'
    BACKEND = 'backend', 'Backend'
    MOBILE = 'mobile', 'Mobile'
    DATA_SCIENCE = 'data_science', 'Data Science'
    ML_AI = 'ml_ai', 'Machine Learning / AI'
    DEVOPS = 'devops', 'DevOps'
    CYBERSECURITY = 'cybersecurity', 'Cybersecurity'


class Badge(models.Model):
    """
    Katalog badge yang dapat di-earn user saat menyelesaikan course.
    Di-seed lewat management command `seed_badges`.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.SlugField(max_length=80, unique=True)
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=40, choices=BadgeCategory.choices)
    level = models.CharField(max_length=20, choices=BadgeLevel.choices)
    icon_url = models.URLField(blank=True)
    criteria = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            'Rule-based matching criteria. Format: '
            '{"tags_any": ["ui/ux", ...], "level_any": ["beginner", "pemula", ...]}'
        ),
    )
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'badges'
        ordering = ['sort_order', 'category', 'level']
        constraints = [
            models.UniqueConstraint(
                fields=['category', 'level'],
                name='uniq_badge_category_level',
            ),
        ]

    def __str__(self):
        return self.name


class UserBadge(models.Model):
    """
    Record badge yang sudah di-earn user.
    Unique per (user, badge) — anti duplikat.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='badges',
    )
    badge = models.ForeignKey(
        Badge,
        on_delete=models.CASCADE,
        related_name='awards',
    )
    earned_via_course = models.ForeignKey(
        'courses.Course',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='badge_awards',
        help_text='Course yang men-trigger badge ini di-award (kalau ada)',
    )
    earned_via_learning_path = models.ForeignKey(
        'learning_paths.LearningPath',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='badge_awards',
        help_text='Learning path tempat course men-trigger badge ini (kalau ada)',
    )
    earned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'user_badges'
        ordering = ['-earned_at']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'badge'],
                name='uniq_user_badge',
            ),
        ]

    def __str__(self):
        return f'{self.user_id} -> {self.badge_id}'
