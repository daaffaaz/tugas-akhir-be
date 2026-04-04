from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.courses.models import Course

from .models import LearningPath, LearningPathCourse
from .serializers import (
    LearningPathBulkUpdateSerializer,
    LearningPathCourseItemSerializer,
    LearningPathCreateSerializer,
    LearningPathDetailSerializer,
    LearningPathListSerializer,
)


class LearningPathListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            LearningPath.objects.filter(user=self.request.user)
            .annotate(
                total_courses=Count('path_courses', distinct=True),
                completed_courses=Count('path_courses', filter=Q(path_courses__is_completed=True)),
            )
            .order_by('-created_at')
        )

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return LearningPathCreateSerializer
        return LearningPathListSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class LearningPathDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = LearningPathDetailSerializer
    lookup_field = 'pk'

    def get_queryset(self):
        return (
            LearningPath.objects.filter(user=self.request.user)
            .prefetch_related(
                'path_courses__course__platform',
                'path_courses__course__tags',
            )
        )


class LearningPathBulkUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, pk, *args, **kwargs):
        path = get_object_or_404(LearningPath, pk=pk, user=request.user)
        serializer = LearningPathBulkUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        items = data['courses']

        positions = [c['position'] for c in items]
        if len(set(positions)) != len(positions):
            raise ValidationError({'courses': 'Duplicate position values are not allowed.'})

        course_ids = [c['course_id'] for c in items]
        if len(set(course_ids)) != len(course_ids):
            raise ValidationError({'courses': 'Duplicate course_id values are not allowed.'})

        valid_ids = set(
            Course.objects.filter(id__in=course_ids).values_list('id', flat=True),
        )
        missing = set(course_ids) - valid_ids
        if missing:
            raise ValidationError({'courses': f'Unknown course ids: {sorted(missing)}'})

        with transaction.atomic():
            if 'title' in data:
                path.title = (data['title'] or '')[:255]
                path.save(update_fields=['title', 'updated_at'])

            incoming = set(course_ids)
            LearningPathCourse.objects.filter(learning_path=path).exclude(course_id__in=incoming).delete()

            existing = {
                lpc.course_id: lpc
                for lpc in LearningPathCourse.objects.filter(learning_path=path)
            }

            for row in sorted(items, key=lambda x: x['position']):
                cid = row['course_id']
                pos = row['position']
                manual = row.get('is_manually_added', False)
                if cid in existing:
                    lpc = existing[cid]
                    lpc.position = pos
                    if manual:
                        lpc.is_manually_added = True
                    lpc.save(update_fields=['position', 'is_manually_added'])
                else:
                    LearningPathCourse.objects.create(
                        learning_path=path,
                        course_id=cid,
                        position=pos,
                        is_manually_added=manual,
                    )

        path.refresh_from_db()
        out = LearningPathDetailSerializer(path)
        return Response(out.data)


class LearningPathCourseToggleCompleteView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk, *args, **kwargs):
        lpc = get_object_or_404(
            LearningPathCourse.objects.select_related('learning_path', 'course__platform').prefetch_related(
                'course__tags'
            ),
            pk=pk,
        )
        if lpc.learning_path.user_id != request.user.id:
            return Response(status=status.HTTP_404_NOT_FOUND)

        lpc.is_completed = not lpc.is_completed
        lpc.completed_at = timezone.now() if lpc.is_completed else None
        lpc.save(update_fields=['is_completed', 'completed_at'])

        return Response(LearningPathCourseItemSerializer(lpc).data)
