from rest_framework import serializers

from .models import Course, Platform


class PlatformMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Platform
        fields = ('id', 'name', 'base_url')


class CourseListSerializer(serializers.ModelSerializer):
    platform = PlatformMiniSerializer(read_only=True)
    tags = serializers.SlugRelatedField(many=True, read_only=True, slug_field='name')

    class Meta:
        model = Course
        fields = (
            'id',
            'platform',
            'external_id',
            'title',
            'instructor',
            'price',
            'reviews_count',
            'rating',
            'description',
            'duration',
            'video_hours',
            'reading_count',
            'assignment_count',
            'what_you_learn',
            'tag',
            'url',
            'scraped_date',
            'level',
            'currency',
            'thumbnail_url',
            'tags',
            'scraped_at',
            'created_at',
        )
