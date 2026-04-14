import uuid

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models

from .managers import UserManager


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, db_index=True)
    full_name = models.CharField(max_length=255, blank=True)
    avatar_url = models.TextField(blank=True)
    questionnaire_completed_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    class Meta:
        db_table = 'users_user'
        ordering = ['-created_at']

    def __str__(self):
        return self.email


class UserPreferences(models.Model):
    AGE_RANGE_CHOICES = (('18-24', '18-24'), ('25-34', '25-34'), ('35+', '35+'))
    EDUCATION_LEVEL_CHOICES = (('SMA', 'SMA'), ('D3', 'D3'), ('S1', 'S1'), ('S2', 'S2'))
    OPERATING_SYSTEM_CHOICES = (('windows', 'windows'), ('macos', 'macos'), ('linux', 'linux'))
    GIT_SKILL_CHOICES = (('none', 'none'), ('basic', 'basic'), ('intermediate', 'intermediate'))
    WEEKLY_HOURS_CHOICES = (('<4', '<4'), ('4-8', '4-8'), ('8-14', '8-14'), ('15+', '15+'))
    STUDY_SLOT_CHOICES = (('pagi', 'pagi'), ('malam', 'malam'), ('kerja', 'kerja'), ('weekend', 'weekend'))
    MATERIAL_FORMAT_CHOICES = (
        ('video', 'video'),
        ('text', 'text'),
        ('interactive', 'interactive'),
        ('project', 'project'),
    )
    THEORY_PRACTICE_CHOICES = (('theory', 'theory'), ('balanced', 'balanced'), ('practice', 'practice'))
    EVALUATION_TYPE_CHOICES = (
        ('quiz', 'quiz'),
        ('coding_challenge', 'coding_challenge'),
        ('project', 'project'),
    )
    TARGET_ROLE_CHOICES = (('backend', 'backend'), ('devops', 'devops'), ('data_ml', 'data_ml'))
    MAIN_GOAL_CHOICES = (
        ('career_change', 'career_change'),
        ('upskilling', 'upskilling'),
        ('hobby', 'hobby'),
    )
    RAM_GB_CHOICES = (('<8', '<8'), ('8-16', '8-16'), ('16+', '16+'))
    INTERNET_QUALITY_CHOICES = (
        ('unstable', 'unstable'),
        ('stable', 'stable'),
        ('very_stable', 'very_stable'),
    )
    BUDGET_IDR_CHOICES = (('<500k', '<500k'), ('500k-2m', '500k-2m'), ('>2m', '>2m'))

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='preferences')
    job_title = models.CharField(max_length=100, blank=True)
    age_range = models.CharField(max_length=10, blank=True, choices=AGE_RANGE_CHOICES)
    education_level = models.CharField(max_length=10, blank=True, choices=EDUCATION_LEVEL_CHOICES)
    operating_system = models.CharField(max_length=10, blank=True, choices=OPERATING_SYSTEM_CHOICES)
    git_skill = models.CharField(max_length=20, blank=True, choices=GIT_SKILL_CHOICES)
    cli_level = models.SmallIntegerField(null=True, blank=True)
    logic_level = models.SmallIntegerField(null=True, blank=True)
    weekly_hours = models.CharField(max_length=10, blank=True, choices=WEEKLY_HOURS_CHOICES)
    study_slot = models.CharField(max_length=10, blank=True, choices=STUDY_SLOT_CHOICES)
    material_format = models.CharField(max_length=15, blank=True, choices=MATERIAL_FORMAT_CHOICES)
    theory_practice = models.CharField(max_length=10, blank=True, choices=THEORY_PRACTICE_CHOICES)
    evaluation_type = models.CharField(max_length=20, blank=True, choices=EVALUATION_TYPE_CHOICES)
    target_role = models.CharField(max_length=30, blank=True, choices=TARGET_ROLE_CHOICES)
    main_goal = models.CharField(max_length=20, blank=True, choices=MAIN_GOAL_CHOICES)
    ram_gb = models.CharField(max_length=10, blank=True, choices=RAM_GB_CHOICES)
    internet_quality = models.CharField(max_length=15, blank=True, choices=INTERNET_QUALITY_CHOICES)
    budget_idr = models.CharField(max_length=10, blank=True, choices=BUDGET_IDR_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'users_preferences'

    def __str__(self):
        return f'preferences:{self.user_id}'
