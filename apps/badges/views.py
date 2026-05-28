from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.learning_paths.models import LearningPath

from .models import Badge, UserBadge
from .serializers import BadgeCatalogSerializer, UserBadgeSerializer


class BadgeListView(APIView):
    """
    GET /api/badges/

    Katalog penuh badge yang ada di sistem, dengan flag `is_earned`
    dan `earned_at` untuk user saat ini.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        badges = Badge.objects.filter(is_active=True).order_by('sort_order', 'category', 'level')
        earned_qs = UserBadge.objects.filter(user=request.user).select_related('badge')
        earned_map = {ub.badge_id: ub for ub in earned_qs}
        ctx = {'earned_map': earned_map, 'request': request}
        data = BadgeCatalogSerializer(badges, many=True, context=ctx).data
        return Response({
            'count': len(data),
            'earned_count': len(earned_map),
            'results': data,
        })


class UserBadgeListView(generics.ListAPIView):
    """
    GET /api/users/me/badges/

    Daftar badge yang sudah di-earn user (untuk halaman profile).
    """
    permission_classes = [IsAuthenticated]
    serializer_class = UserBadgeSerializer
    pagination_class = None

    def get_queryset(self):
        return (
            UserBadge.objects.filter(user=self.request.user)
            .select_related('badge', 'earned_via_course__platform', 'earned_via_learning_path')
            .prefetch_related('earned_via_course__tags')
            .order_by('-earned_at')
        )


class LearningPathBadgesView(APIView):
    """
    GET /api/learning-paths/<uuid:pk>/badges/

    Badge yang earned VIA learning path tertentu (untuk dashboard di bawah
    progress keseluruhan path).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk, *args, **kwargs):
        path = get_object_or_404(LearningPath, pk=pk, user=request.user)
        qs = (
            UserBadge.objects.filter(user=request.user, earned_via_learning_path=path)
            .select_related('badge', 'earned_via_course__platform')
            .prefetch_related('earned_via_course__tags')
            .order_by('-earned_at')
        )
        data = UserBadgeSerializer(qs, many=True).data
        return Response({
            'learning_path_id': str(path.id),
            'count': len(data),
            'results': data,
        })
