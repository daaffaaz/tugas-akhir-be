from rest_framework import serializers

from apps.courses.serializers import CourseListSerializer
from apps.learning_paths.models import CourseRecommendation


# ─────────────────────────────────────────────────────────────────────────────
# Request Serializers
# ─────────────────────────────────────────────────────────────────────────────

class RAGGenerateRequestSerializer(serializers.Serializer):
    """Serializer for POST /api/rag/generate-roadmap/ (existing learning path)."""
    topic = serializers.CharField(
        max_length=500,
        help_text='Learning topic or goal (e.g. "machine learning untuk data science")'
    )
    budget_idr = serializers.IntegerField(
        required=False, allow_null=True,
        help_text='Maximum budget in IDR (optional filter)'
    )
    level = serializers.CharField(
        required=False, allow_null=True, max_length=50,
        help_text='Preferred course level (Beginner/Intermediate/Advanced)'
    )

    def validate_topic(self, value):
        if len(value.strip()) < 3:
            raise serializers.ValidationError("Topic must be at least 3 characters.")
        return value.strip()


class RAGRecommendRequestSerializer(serializers.Serializer):
    """Serializer for POST /api/rag/recommend/ (course recommendations).

    Jika regenerate=True, additional_context WAJIB diisi.
    """
    topic = serializers.CharField(
        max_length=500,
        help_text='Learning topic atau goal (e.g. "machine learning untuk data science")'
    )
    additional_context = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=500,
        help_text='Konteks/tujuan tambahan user. WAJIB jika regenerate=True.'
    )
    count = serializers.IntegerField(
        required=False,
        default=5,
        min_value=1,
        max_value=20,
        help_text='Jumlah course yang direkomendasikan (default 5, max 20)'
    )
    regenerate = serializers.BooleanField(
        required=False,
        default=False,
        help_text='True = regenerate hasil sebelumnya. Jika True, additional_context wajib diisi.'
    )

    def validate(self, attrs):
        if attrs.get('regenerate') and not attrs.get('additional_context', '').strip():
            raise serializers.ValidationError({
                'additional_context': 'Konteks tambahan WAJIB diisi saat regenerate=True.'
            })
        return attrs

    def validate_topic(self, value):
        if len(value.strip()) < 3:
            raise serializers.ValidationError("Topik harus minimal 3 karakter.")
        return value.strip()


# ──────────────────────────────���──────────────────────────────────────────────
# Response Serializers
# ─────────────────────────────────────────────────────────────────────────────

class RecommendCourseItemSerializer(serializers.Serializer):
    """
    Single course recommendation item in API response.
    Merges DB fields (ai_explanation, relevance_score, is_saved) with
    AI-computed fields (match_score, best_for, potential_gaps) plus course detail.
    """
    # Course detail (from Course model via CourseListSerializer)
    id = serializers.UUIDField(source='course_obj.id')
    title = serializers.CharField(source='course_obj.title')
    instructor = serializers.CharField(source='course_obj.instructor')
    rating = serializers.DecimalField(source='course_obj.rating', max_digits=3, decimal_places=1)
    reviews_count = serializers.IntegerField(source='course_obj.reviews_count')
    price = serializers.DecimalField(source='course_obj.price', max_digits=12, decimal_places=2)
    currency = serializers.CharField(source='course_obj.currency')
    level = serializers.CharField(source='course_obj.level')
    duration = serializers.CharField(source='course_obj.duration')
    video_hours = serializers.DecimalField(source='course_obj.video_hours', max_digits=8, decimal_places=2)
    thumbnail_url = serializers.CharField(source='course_obj.thumbnail_url')
    url = serializers.CharField(source='course_obj.url')
    # DB-stored recommendation fields
    recommendation_id = serializers.UUIDField(source='id')
    relevance_score = serializers.FloatField()
    ai_explanation = serializers.CharField()
    is_saved = serializers.BooleanField()
    regenerate_count = serializers.IntegerField()
    created_at = serializers.DateTimeField()
    # AI-computed fields (from generation, not stored in DB)
    match_score = serializers.FloatField()
    best_for = serializers.CharField()
    potential_gaps = serializers.CharField()


class RAGRecommendResponseSerializer(serializers.Serializer):
    """Serializer for the POST /api/rag/recommend/ response."""
    recommendations = RecommendCourseItemSerializer(many=True)
    topic = serializers.CharField()
    total_retrieved = serializers.IntegerField()
    top_similarity_score = serializers.FloatField()
    regenerate = serializers.BooleanField()
    regenerate_count = serializers.IntegerField()


# ─────────────────────────────────────────────────────────────────────────────
# Saved Recommendations Serializers (from DB, no AI recompute)
# ─────────────────────────────────────────────────────────────────────────────

class CourseRecommendationListSerializer(serializers.ModelSerializer):
    """Serializer for GET /api/rag/recommendations/ (user's saved/list recommendations)."""
    course = CourseListSerializer(read_only=True)

    class Meta:
        model = CourseRecommendation
        fields = (
            'id',
            'course',
            'topic_input',
            'additional_context',
            'relevance_score',
            'ai_explanation',
            'is_saved',
            'regenerate_count',
            'created_at',
        )
        read_only_fields = fields


class CourseRecommendationUpdateSerializer(serializers.Serializer):
    """Serializer for PATCH /api/rag/recommendations/{id}/."""
    is_saved = serializers.BooleanField(required=True)


# ─────────────────────────────────────────────────────────────────────────────
# Learning Path Regenerate Serializers
# ─────────────────────────────────────────────────────────────────────────────

class LearningPathRegenerateRequestSerializer(serializers.Serializer):
    """Serializer for POST /api/rag/learning-paths/{id}/regenerate/."""
    additional_context = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=1000,
        help_text='Konteks tambahan untuk regenerate seluruh learning path.'
    )
    # Override options (partial regeneration)
    keep_courses = serializers.BooleanField(
        required=False,
        default=False,
        help_text='Jika True, mencoba preserve courses yang sudah ditandai selesai.'
    )

    def validate_additional_context(self, value):
        if value and len(value.strip()) < 5:
            raise serializers.ValidationError(
                "Konteks tambahan minimal 5 karakter jika diberikan."
            )
        return value.strip() if value else ''


# ─────────────────────────────────────────────────────────────────────────────
# Learning Path Course Replace Serializers
# ─────────────────────────────────────────────────────────────────────────────

class LearningPathReplaceCourseRequestSerializer(serializers.Serializer):
    """Serializer for POST /api/rag/learning-paths/{id}/courses/{course_id}/replace/."""
    additional_context = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=1000,
        help_text='Alasan/harapan user untuk course pengganti.'
    )
    count = serializers.IntegerField(
        required=False,
        default=5,
        min_value=3,
        max_value=20,
        help_text='Jumlah kandidat course pengganti (default 5, max 20)'
    )

    def validate_additional_context(self, value):
        if value and len(value.strip()) < 3:
            raise serializers.ValidationError(
                "Konteks minimal 3 karakter jika diberikan."
            )
        return value.strip() if value else ''


class ReplacementCandidateSerializer(serializers.Serializer):
    """Single candidate course in replacement response."""
    course_id = serializers.UUIDField()
    title = serializers.CharField()
    instructor = serializers.CharField()
    platform = serializers.CharField()
    level = serializers.CharField()
    rating = serializers.FloatField(allow_null=True)
    price = serializers.FloatField(allow_null=True)
    currency = serializers.CharField()
    duration = serializers.CharField()
    thumbnail_url = serializers.CharField(allow_blank=True)
    url = serializers.CharField(allow_blank=True)
    # AI evaluation
    score = serializers.FloatField()
    faiss_score = serializers.FloatField()
    match_reason = serializers.CharField()
    best_for = serializers.CharField()
    potential_concerns = serializers.CharField()


class LearningPathReplaceCourseResponseSerializer(serializers.Serializer):
    """Serializer for replacement search response."""
    original_course_id = serializers.UUIDField()
    original_course_title = serializers.CharField()
    replacement_reason_summary = serializers.CharField()
    candidates = ReplacementCandidateSerializer(many=True)


# ─────────────────────────────────────────────────────────────────────────────
# Learning Path Course Add / Similar Serializers
# ─────────────────────────────────────────────────────────────────────────────

class SimilarCourseSerializer(serializers.Serializer):
    """Serializer for similar course candidates."""
    course_id = serializers.UUIDField()
    title = serializers.CharField()
    instructor = serializers.CharField(allow_null=True)
    platform = serializers.CharField()
    level = serializers.CharField(allow_blank=True)
    rating = serializers.FloatField(allow_null=True)
    reviews_count = serializers.IntegerField(allow_null=True)
    price = serializers.FloatField(allow_null=True)
    currency = serializers.CharField()
    duration = serializers.CharField(allow_blank=True)
    thumbnail_url = serializers.CharField(allow_blank=True)
    url = serializers.CharField(allow_blank=True)
    relevance_score = serializers.FloatField()
    faiss_score = serializers.FloatField()


class SimilarCoursesResponseSerializer(serializers.Serializer):
    """Serializer for GET /api/rag/learning-paths/{id}/courses/{course_id}/similar/."""
    original_course_id = serializers.UUIDField()
    original_course_title = serializers.CharField()
    topic = serializers.CharField()
    courses = SimilarCourseSerializer(many=True)


class LearningPathAddCourseRequestSerializer(serializers.Serializer):
    """Serializer for POST /api/rag/learning-paths/{id}/courses/add/."""
    course_id = serializers.UUIDField(
        help_text='UUID dari course yang mau ditambahkan'
    )
    phase_number = serializers.IntegerField(
        required=False,
        min_value=1,
        help_text='Fase tujuan. Course akan disisipkan di akhir fase tersebut. Jika tidak diisi, course ditambahkan di paling akhir tanpa fase.'
    )
    position = serializers.IntegerField(
        required=False,
        min_value=1,
        help_text='Posisi insertion manual (opsional, diabaikan jika phase_number diisi).'
    )


class LearningPathApplyReplacementRequestSerializer(serializers.Serializer):
    """Serializer for POST /api/rag/learning-paths/{id}/courses/{course_id}/apply/."""
    new_course_id = serializers.UUIDField(
        help_text='UUID dari course pengganti'
    )
    replacement_reason = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=500,
        help_text='Alasan user mengganti course ini'
    )


class LearningPathReorderRequestSerializer(serializers.Serializer):
    """Serializer for PATCH /api/rag/learning-paths/{id}/courses/reorder/."""
    course_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1,
        help_text='List course IDs dalam urutan baru. Frontend sudah kirim urutan yang benar.'
    )