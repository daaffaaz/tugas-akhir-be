from rest_framework import serializers

from apps.courses.models import Course


class SuggestedCourseSerializer(serializers.ModelSerializer):
    """Flat course shape returned inside `career_possibilities.suggested_courses`."""
    platform = serializers.CharField(source='platform.name', read_only=True)
    tags = serializers.SlugRelatedField(
        many=True, read_only=True, slug_field='name',
    )

    class Meta:
        model = Course
        fields = (
            'id',
            'title',
            'thumbnail_url',
            'url',
            'platform',
            'level',
            'duration',
            'video_hours',
            'price',
            'currency',
            'rating',
            'tags',
        )


class CareerPossibilitySerializer(serializers.Serializer):
    role = serializers.CharField()
    confidence = serializers.FloatField()
    description = serializers.CharField()
    suggested_courses = SuggestedCourseSerializer(many=True)


class CompletedCourseSerializer(serializers.Serializer):
    course_id = serializers.UUIDField()
    title = serializers.CharField()
    completed_at = serializers.DateTimeField(allow_null=True)


class BasedOnSerializer(serializers.Serializer):
    completed_courses = CompletedCourseSerializer(many=True)
    reasoning = serializers.CharField(allow_blank=True)


class NextStepsResponseSerializer(serializers.Serializer):
    career_possibilities = CareerPossibilitySerializer(many=True)
    based_on = BasedOnSerializer()
