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
            'description',
            'url',
            'instructor_name',
            'price',
            'currency',
            'rating',
            'review_count',
            'duration_hours',
            'difficulty_level',
            'thumbnail_url',
            'tags',
            'scraped_at',
            'created_at',
        )
