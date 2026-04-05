import uuid

from django.db import models


class Platform(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    base_url = models.CharField(max_length=255)
    logo_url = models.TextField(blank=True)

    class Meta:
        db_table = 'platforms'

    def __str__(self):
        return self.name


class Course(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    platform = models.ForeignKey(Platform, on_delete=models.CASCADE, related_name='courses')
    external_id = models.CharField(max_length=255, blank=True, db_index=True)
    title = models.CharField(max_length=500)
    instructor = models.CharField(max_length=255, blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    reviews_count = models.IntegerField(default=0)
    rating = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    description = models.TextField(blank=True)
    duration = models.TextField(blank=True)
    video_hours = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    reading_count = models.IntegerField(default=0)
    assignment_count = models.IntegerField(default=0)
    what_you_learn = models.TextField(blank=True)
    tag = models.TextField(blank=True)
    url = models.TextField()
    scraped_date = models.DateField(null=True, blank=True)
    level = models.CharField(max_length=80, blank=True)

    currency = models.CharField(max_length=3, default='IDR')
    thumbnail_url = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    scraped_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    tags = models.ManyToManyField('Tag', through='CourseTag', related_name='courses')

    class Meta:
        db_table = 'courses'
        constraints = [
            models.UniqueConstraint(
                fields=['platform', 'external_id'],
                name='uniq_platform_external_id',
            ),
        ]

    def __str__(self):
        return self.title[:80]


class Tag(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=120, unique=True)

    class Meta:
        db_table = 'tags'

    def __str__(self):
        return self.name


class CourseTag(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='course_tags')
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE, related_name='course_tags')

    class Meta:
        db_table = 'course_tags'
        constraints = [
            models.UniqueConstraint(fields=['course', 'tag'], name='uniq_course_tag'),
        ]
