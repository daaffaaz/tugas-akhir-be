import logging

from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.badges.serializers import BadgeSerializer
from apps.badges.services import evaluate_course_for_badges
from apps.courses.models import Course
from apps.rag.views import _generate_roadmap_for_user

from .models import LearningPath, LearningPathCourse
from .serializers import (
    GenerateFromCareerRequestSerializer,
    LearningPathBulkUpdateSerializer,
    LearningPathCourseItemSerializer,
    LearningPathCreateSerializer,
    LearningPathDetailSerializer,
    LearningPathListSerializer,
    UserGlobalProgressSerializer,
)

logger = logging.getLogger(__name__)


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
                phase = row.get('phase_number')
                if cid in existing:
                    lpc = existing[cid]
                    lpc.position = pos
                    lpc.phase_number = phase
                    if manual:
                        lpc.is_manually_added = True
                    lpc.save(update_fields=['position', 'is_manually_added', 'phase_number'])
                else:
                    LearningPathCourse.objects.create(
                        learning_path=path,
                        course_id=cid,
                        position=pos,
                        is_manually_added=manual,
                        phase_number=phase,
                    )

        path.refresh_from_db()
        out = LearningPathDetailSerializer(path)
        return Response(out.data)


class UserGlobalProgressView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        paths = (
            LearningPath.objects.filter(user=request.user)
            .annotate(
                total_courses=Count('path_courses', distinct=True),
                completed_courses=Count(
                    'path_courses',
                    filter=Q(path_courses__is_completed=True),
                ),
            )
            .order_by('-created_at')
        )

        total_courses = sum(p.total_courses for p in paths)
        total_completed = sum(p.completed_courses for p in paths)

        completed_paths = sum(
            1 for p in paths if p.total_courses > 0 and p.completed_courses == p.total_courses
        )
        in_progress_paths = sum(
            1 for p in paths if 0 < p.completed_courses < p.total_courses
        )
        not_started_paths = sum(
            1 for p in paths if p.completed_courses == 0
        )

        overall_pct = 0.0
        if total_courses:
            overall_pct = round(100.0 * total_completed / total_courses, 2)

        data = {
            'total_learning_paths': paths.count(),
            'total_courses': total_courses,
            'total_completed_courses': total_completed,
            'overall_progress_percentage': overall_pct,
            'completed_paths': completed_paths,
            'in_progress_paths': in_progress_paths,
            'not_started_paths': not_started_paths,
            'learning_paths': paths,
        }

        return Response(UserGlobalProgressSerializer(data).data)


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

        badge_payload = {'awarded': [], 'already_owned': []}
        if lpc.is_completed:
            result = evaluate_course_for_badges(
                user=request.user,
                course=lpc.course,
                learning_path=lpc.learning_path,
            )
            badge_payload = {
                'awarded': BadgeSerializer(result['awarded'], many=True).data,
                'already_owned': BadgeSerializer(result['already_owned'], many=True).data,
            }

        data = LearningPathCourseItemSerializer(lpc).data
        data['badges'] = badge_payload
        return Response(data)


class GenerateFromCareerView(APIView):
    """
    POST /api/learning-paths/generate-from-career/

    Body: { "career_focus": "Data Analyst", "based_on_courses": ["uuid", ...] (opsional) }

    Creates a new learning path whose topic is the chosen career. Internally reuses
    the same RAG pipeline as POST /api/rag/generate-roadmap/.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = GenerateFromCareerRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        career_focus = data['career_focus']

        logger.info(
            f"[career] Generate learning path from career='{career_focus}' "
            f"by user={request.user.id}"
        )

        extra_context = f"User ingin fokus ke karier: {career_focus}."

        try:
            learning_path, retrieval_info, courses, top_score = (
                _generate_roadmap_for_user(
                    user=request.user,
                    topic=career_focus,
                    level_pref=None,
                    budget_pref=None,
                    extra_context=extra_context,
                )
            )
        except ValueError as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            logger.error(f"[career] Generation/save failed: {e}")
            return Response(
                {'detail': f'Generation failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        response_data = LearningPathDetailSerializer(learning_path).data
        response_data['_rag_meta'] = {
            'courses_retrieved': retrieval_info.get('courses_retrieved', len(courses)),
            'top_similarity_score': retrieval_info.get('top_similarity_score', top_score),
            'retrieval_method': retrieval_info.get('retrieval_method', 'semantic search'),
            'career_focus': career_focus,
            'source': 'generate-from-career',
        }
        return Response(response_data, status=status.HTTP_201_CREATED)
