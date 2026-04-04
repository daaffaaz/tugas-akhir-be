from rest_framework import serializers

from apps.courses.serializers import CourseListSerializer

from .models import LearningPath, LearningPathCourse


class LearningPathCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = LearningPath
        fields = ('title', 'topic_input', 'description', 'is_saved', 'questionnaire_snapshot')


class LearningPathListSerializer(serializers.ModelSerializer):
    total_courses = serializers.IntegerField(read_only=True)
    completed_courses = serializers.IntegerField(read_only=True)
    progress_percentage = serializers.SerializerMethodField()

    class Meta:
        model = LearningPath
        fields = (
            'id',
            'title',
            'topic_input',
            'description',
            'is_saved',
            'total_courses',
            'completed_courses',
            'progress_percentage',
            'created_at',
            'updated_at',
        )

    def get_progress_percentage(self, obj):
        total = getattr(obj, 'total_courses', None)
        done = getattr(obj, 'completed_courses', None)
        if total is None:
            total = obj.path_courses.count()
            done = obj.path_courses.filter(is_completed=True).count()
        if not total:
            return 0.0
        return round(100.0 * float(done) / float(total), 2)


class LearningPathCourseItemSerializer(serializers.ModelSerializer):
    course = CourseListSerializer(read_only=True)

    class Meta:
        model = LearningPathCourse
        fields = (
            'id',
            'course',
            'position',
            'is_completed',
            'completed_at',
            'is_manually_added',
        )


class LearningPathDetailSerializer(serializers.ModelSerializer):
    progress_percentage = serializers.SerializerMethodField()
    courses = serializers.SerializerMethodField()

    class Meta:
        model = LearningPath
        fields = (
            'id',
            'title',
            'topic_input',
            'description',
            'is_saved',
            'questionnaire_snapshot',
            'progress_percentage',
            'courses',
            'created_at',
            'updated_at',
        )

    def get_progress_percentage(self, obj):
        pcs = obj.path_courses.all()
        total = pcs.count()
        if not total:
            return 0.0
        done = sum(1 for p in pcs if p.is_completed)
        return round(100.0 * done / total, 2)

    def get_courses(self, obj):
        items = (
            obj.path_courses.select_related('course__platform')
            .prefetch_related('course__tags')
            .order_by('position')
        )
        return LearningPathCourseItemSerializer(items, many=True).data


class BulkCourseItemSerializer(serializers.Serializer):
    course_id = serializers.UUIDField()
    position = serializers.IntegerField(min_value=1)
    is_manually_added = serializers.BooleanField(required=False, default=False)


class LearningPathBulkUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(required=False, allow_blank=True)
    courses = BulkCourseItemSerializer(many=True)
