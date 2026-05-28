from rest_framework import serializers

from apps.courses.serializers import CourseListSerializer

from .models import Badge, UserBadge


class BadgeSerializer(serializers.ModelSerializer):
    category_label = serializers.CharField(source='get_category_display', read_only=True)
    level_label = serializers.CharField(source='get_level_display', read_only=True)

    class Meta:
        model = Badge
        fields = (
            'id',
            'code',
            'name',
            'description',
            'category',
            'category_label',
            'level',
            'level_label',
            'icon_url',
            'sort_order',
        )


class BadgeCatalogSerializer(BadgeSerializer):
    """Catalog view: tambahkan flag `is_earned` untuk user saat ini."""
    is_earned = serializers.SerializerMethodField()
    earned_at = serializers.SerializerMethodField()

    class Meta(BadgeSerializer.Meta):
        fields = BadgeSerializer.Meta.fields + ('is_earned', 'earned_at')

    def _earned_map(self) -> dict:
        return self.context.get('earned_map', {}) or {}

    def get_is_earned(self, obj) -> bool:
        return obj.id in self._earned_map()

    def get_earned_at(self, obj):
        ub = self._earned_map().get(obj.id)
        return ub.earned_at if ub else None


class _LearningPathMiniSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    title = serializers.CharField(read_only=True)


class UserBadgeSerializer(serializers.ModelSerializer):
    badge = BadgeSerializer(read_only=True)
    earned_via_course = CourseListSerializer(read_only=True)
    earned_via_learning_path = _LearningPathMiniSerializer(read_only=True)

    class Meta:
        model = UserBadge
        fields = (
            'id',
            'badge',
            'earned_via_course',
            'earned_via_learning_path',
            'earned_at',
        )
