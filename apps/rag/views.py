import logging
import uuid
from collections import defaultdict

from django.db import models, transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.courses.models import Course
from apps.learning_paths.models import CourseRecommendation, LearningPath, LearningPathCourse
from apps.learning_paths.serializers import LearningPathDetailSerializer
from apps.questionnaires.models import Question, UserQuestionnaireAnswer
from apps.users.models import UserPreferences

from .generator import generate_roadmap
from .recommend_generator import generate_recommendations
from .replace_generator import generate_replacement_explanations
from .retriever import retrieve_courses, retrieve_courses_for_replace
from .serializers import (
    CourseRecommendationListSerializer,
    CourseRecommendationUpdateSerializer,
    LearningPathAddCourseRequestSerializer,
    LearningPathApplyReplacementRequestSerializer,
    LearningPathReplaceCourseRequestSerializer,
    LearningPathRegenerateRequestSerializer,
    LearningPathReorderRequestSerializer,
    RAGGenerateRequestSerializer,
    RAGRecommendRequestSerializer,
)

logger = logging.getLogger(__name__)


def _build_user_profile(user, topic: str) -> dict:
    """
    Assemble a user profile dict from UserPreferences + UserQuestionnaireAnswer.
    Used as context for the RAG prompt.
    """
    try:
        prefs = user.preferences  # related_name='preferences' di UserPreferences FK
        profile = {
            'current_skills': [],
            'goals': [],
            'level': '',
            'budget': prefs.budget_idr if prefs.budget_idr else None,
            'weekly_hours': prefs.weekly_hours or None,
            'material_format': prefs.material_format or '',
            'theory_practice': prefs.theory_practice or '',
            'target_role': prefs.target_role or '',
            'main_goal': prefs.main_goal or '',
        }
    except (UserPreferences.DoesNotExist, AttributeError):
        profile = {
            'current_skills': [],
            'goals': [],
            'level': '',
            'budget': None,
            'weekly_hours': None,
            'material_format': '',
            'theory_practice': '',
            'target_role': '',
            'main_goal': '',
        }

    # Extract answers from questionnaire
    answers = (
        UserQuestionnaireAnswer.objects
        .filter(user=user)
        .select_related('question')
        .order_by('question__order_number')
    )

    # Build a readable summary of answers
    answer_lines = []
    for ans in answers:
        q = ans.question
        answer_lines.append(f"- {q.variable_key or q.question_text[:60]}: {ans.answer_option}")

    profile['_answers'] = answer_lines

    # Extract variable_key answers into structured profile
    for ans in answers:
        key = ans.question.variable_key
        if not key:
            continue
        val = ans.answer_option

        if key in ('current_skills', 'skills', 'current_skills_list'):
            profile.setdefault('current_skills', []).append(val)
        elif key in ('goals', 'target_skills', 'learning_goals'):
            profile.setdefault('goals', []).append(val)
        elif key in ('level', 'course_level', 'difficulty_preference'):
            profile['level'] = val
        elif key == 'budget_idr':
            try:
                profile['budget'] = int(val.replace(',', '').replace('IDR', '').strip())
            except (ValueError, AttributeError):
                pass
        elif key == 'weekly_hours':
            try:
                profile['weekly_hours'] = int(val)
            except (ValueError, AttributeError):
                pass

    return profile


def _save_roadmap_to_db(user, topic: str, roadmap_dict: dict) -> LearningPath:
    """
    Save the generated roadmap dict into LearningPath + LearningPathCourse records.
    Returns the created LearningPath instance.
    """
    phases = roadmap_dict.get('phases', [])
    total_duration = roadmap_dict.get('total_duration_weeks', 0)
    title = roadmap_dict.get('roadmap_title') or f"Roadmap: {topic}"

    # Collect all course IDs from all phases
    course_positions = []  # list of (course_id, position, phase_number)
    position = 0
    for phase in phases:
        phase_num = phase.get('phase_number')
        for course_item in phase.get('courses', []):
            cid = course_item.get('course_id')
            if cid:
                position += 1
                course_positions.append((cid, position, phase_num))

    if not course_positions:
        raise ValueError("No valid courses in roadmap to save.")

    # Verify all course IDs exist
    course_ids = [cid for cid, _, __ in course_positions]
    valid_ids = set(str(c.id) for c in Course.objects.filter(id__in=course_ids))
    course_positions = [(cid, pos, pn) for cid, pos, pn in course_positions if cid in valid_ids]

    if not course_positions:
        raise ValueError("No valid course IDs found in database.")

    with transaction.atomic():
        learning_path = LearningPath.objects.create(
            user=user,
            title=title[:255],
            topic_input=topic[:500],
            description=roadmap_dict.get('overview', '')[:1000],
            is_saved=True,
            questionnaire_snapshot=roadmap_dict,
        )

        for course_id, pos, phase_num in course_positions:
            LearningPathCourse.objects.create(
                learning_path=learning_path,
                course_id=course_id,
                position=pos,
                phase_number=phase_num,
                is_manually_added=False,
            )

    return learning_path


class RAGRoadmapGenerateView(APIView):
    """
    POST /api/rag/generate-roadmap/
    Generates a personalized learning roadmap using RAG and saves it to the database.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = RAGGenerateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        topic = data['topic']
        level_pref = data.get('level') or request.data.get('level')
        budget_pref = data.get('budget_idr') or request.data.get('budget_idr')

        logger.info(f"[RAG] Generate roadmap for topic='{topic}' by user={request.user.id}")

        # Build user profile from DB
        user_profile = _build_user_profile(request.user, topic)

        # Override with request-level preferences if provided
        if level_pref:
            user_profile['level'] = level_pref
        if budget_pref:
            user_profile['budget'] = budget_pref

        # Retrieve relevant courses from FAISS
        courses, top_score = retrieve_courses(topic, user_profile)

        if not courses:
            return Response(
                {
                    'detail': (
                        'No courses found matching your topic. '
                        'The search index may not be built yet. '
                        'Contact support if this persists.'
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        logger.info(f"[RAG] Retrieved {len(courses)} courses, top_score={top_score:.3f}")

        # Generate roadmap via GPT-4o
        try:
            roadmap_dict, retrieval_info = generate_roadmap(
                topic=topic,
                user_profile=user_profile,
                courses_metadata=courses,
                top_score=top_score,
            )
        except Exception as e:
            logger.error(f"[RAG] Generation failed: {e}")
            return Response(
                {'detail': f'Roadmap generation failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Save to database
        try:
            learning_path = _save_roadmap_to_db(request.user, topic, roadmap_dict)
        except Exception as e:
            logger.error(f"[RAG] Failed to save roadmap to DB: {e}")
            return Response(
                {'detail': f'Failed to save roadmap: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Prefetch for serializer
        learning_path = (
            LearningPath.objects
            .filter(id=learning_path.id)
            .prefetch_related(
                'path_courses__course__platform',
                'path_courses__course__tags',
            )
            .first()
        )

        response_data = LearningPathDetailSerializer(learning_path).data
        response_data['_rag_meta'] = {
            'courses_retrieved': retrieval_info.get('courses_retrieved', len(courses)),
            'top_similarity_score': retrieval_info.get('top_similarity_score', top_score),
            'retrieval_method': retrieval_info.get('retrieval_method', 'semantic search'),
        }

        return Response(response_data, status=status.HTTP_201_CREATED)


# ─────────────────────────────────────────────────────────────────────────────
# Course Recommendation Views
# ─────────────────────────────────────────────────────────────────────────────

class RAGCourseRecommendView(APIView):
    """
    POST /api/rag/recommend/
    Generate personalized course recommendations (with AI explanations).

    Jika regenerate=True, wajib isi additional_context.
    Hasil regenerate akan menimpa record lama (update) dan increment regenerate_count.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = RAGRecommendRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        topic = data['topic']
        additional_context = data.get('additional_context', '')
        count = data.get('count', 5)
        regenerate = data.get('regenerate', False)

        logger.info(
            f"[RAG] Recommend count={count} topic='{topic}' "
            f"regenerate={regenerate} by user={request.user.id}"
        )

        # Build user profile from DB
        user_profile = _build_user_profile(request.user, topic)
        if additional_context:
            user_profile['additional_context'] = additional_context

        # Retrieve top courses from FAISS
        courses, top_score = retrieve_courses(topic, user_profile, top_k=max(count, 20))

        if not courses:
            return Response(
                {'detail': 'No courses found for this topic. Try a different query.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Limit to requested count
        courses = courses[:count]

        # Generate per-course AI explanations
        try:
            enriched = generate_recommendations(
                topic=topic,
                user_profile=user_profile,
                courses_metadata=courses,
            )
        except Exception as e:
            logger.warning(f"[RAG] AI explanation generation failed: {e}, falling back to raw courses")
            enriched = []
            for c in courses:
                result = dict(c)
                result['relevance_score'] = c.get('_score', 0.0)
                result['ai_explanation'] = 'Penjelasan tidak tersedia.'
                result['match_score'] = 0.5
                result['best_for'] = 'General learners'
                result['potential_gaps'] = ''
                enriched.append(result)

        # Save to DB (upsert — overwrite on regenerate)
        try:
            saved_recommendations = _save_recommendations_to_db(
                user=request.user,
                topic=topic,
                additional_context=additional_context,
                enriched_courses=enriched,
                regenerate=regenerate,
            )
        except Exception as e:
            logger.error(f"[RAG] Failed to save recommendations to DB: {e}")
            return Response(
                {'detail': f'Failed to save recommendations: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Build response
        response_data = {
            'recommendations': saved_recommendations,
            'topic': topic,
            'total_retrieved': len(enriched),
            'top_similarity_score': float(top_score),
            'regenerate': regenerate,
            'regenerate_count': max(
                (r.get('regenerate_count') or 0) for r in saved_recommendations
            ) if regenerate else 0,
        }

        return Response(response_data, status=status.HTTP_201_CREATED)


class RAGRecommendationListView(APIView):
    """
    GET  /api/rag/recommendations/  — list all saved recommendations for current user
    PATCH /api/rag/recommendations/{id}/ — update is_saved status
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        topic = request.query_params.get('topic', '')
        is_saved = request.query_params.get('is_saved')

        qs = (
            CourseRecommendation.objects
            .filter(user=request.user)
            .select_related('course__platform')
            .prefetch_related('course__tags')
        )

        if topic:
            qs = qs.filter(topic_input__icontains=topic)

        if is_saved is not None:
            qs = qs.filter(is_saved=is_saved.lower() == 'true')

        qs = qs.order_by('-created_at')

        # Simple pagination
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 10))
        start = (page - 1) * page_size
        end = start + page_size

        total = qs.count()
        items = qs[start:end]
        serializer = CourseRecommendationListSerializer(items, many=True)

        return Response({
            'results': serializer.data,
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': (total + page_size - 1) // page_size,
        })

    def patch(self, request, pk):
        serializer = CourseRecommendationUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            rec = CourseRecommendation.objects.get(pk=pk, user=request.user)
        except CourseRecommendation.DoesNotExist:
            return Response(
                {'detail': 'Recommendation not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        rec.is_saved = serializer.validized_data['is_saved']
        rec.save(update_fields=['is_saved'])

        return Response(CourseRecommendationListSerializer(rec).data)


class RAGLearningPathListView(APIView):
    """
    GET /api/rag/learning-paths/
    List all learning paths for the current user.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 10))
        start = (page - 1) * page_size
        end = start + page_size

        qs = (
            LearningPath.objects
            .filter(user=request.user)
            .prefetch_related('path_courses')
            .order_by('-created_at')
        )

        total = qs.count()
        items = qs[start:end]

        from apps.learning_paths.serializers import LearningPathListSerializer
        return Response({
            'results': LearningPathListSerializer(items, many=True).data,
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': (total + page_size - 1) // page_size,
        })


# ─────────────────────────────────────────────────────────────────────────────
# Learning Path Edit / Regenerate / Replace / Add / Delete Views
# ─────────────────────────────────────────────────────────────────────────────

class RAGLearningPathDetailView(APIView):
    """
    GET /api/rag/learning-paths/{id}/
    Fetch a single learning path with full RAG metadata.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        lp = (
            LearningPath.objects
            .filter(user=request.user, id=pk)
            .prefetch_related(
                'path_courses__course__platform',
                'path_courses__course__tags',
            )
            .first()
        )
        if not lp:
            return Response(
                {'detail': 'Learning path not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        response_data = LearningPathDetailSerializer(lp).data
        response_data['_rag_meta'] = {
            'regenerate_count': lp.regenerate_count,
            'regenerate_context': lp.regenerate_context or '',
            'courses_retrieved': len(lp.path_courses.all()),
        }
        return Response(response_data, status=status.HTTP_200_OK)


class RAGLearningPathRegenerateView(APIView):
    """
    POST /api/rag/learning-paths/{id}/regenerate/
    Regenerate ENTIRE learning path with additional context.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        serializer = LearningPathRegenerateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        lp = (
            LearningPath.objects
            .filter(user=request.user, id=pk)
            .first()
        )
        if not lp:
            return Response(
                {'detail': 'Learning path not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        additional_context = data.get('additional_context', '')

        logger.info(
            f"[RAG] Regenerate learning path {pk} by user={request.user.id}, "
            f"context='{additional_context[:80]}'"
        )

        # Build user profile
        user_profile = _build_user_profile(request.user, lp.topic_input)
        if additional_context:
            user_profile['additional_context'] = additional_context

        # Retrieve courses
        courses, top_score = retrieve_courses(lp.topic_input, user_profile, top_k=20)

        if not courses:
            return Response(
                {'detail': 'No courses found. Try a different topic.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Generate new roadmap
        try:
            roadmap_dict, retrieval_info = generate_roadmap(
                topic=lp.topic_input,
                user_profile=user_profile,
                courses_metadata=courses,
                top_score=top_score,
            )
        except Exception as e:
            logger.error(f"[RAG] Regenerate generation failed: {e}")
            return Response(
                {'detail': f'Regenerate failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Update learning path in DB
        try:
            with transaction.atomic():
                # Increment regenerate counter
                lp.regenerate_count = lp.regenerate_count + 1
                lp.regenerate_context = additional_context
                lp.questionnaire_snapshot = roadmap_dict
                lp.title = roadmap_dict.get('roadmap_title', lp.title)[:255]
                lp.description = roadmap_dict.get('overview', lp.description)[:1000]
                lp.save()

                # Preserve completed courses — mark them so they survive regenerate
                completed_ids = set(
                    str(c.course_id)
                    for c in lp.path_courses.filter(is_completed=True)
                )
                reg_version = lp.regenerate_count

                # Delete old LearningPathCourse records
                lp.path_courses.all().delete()

                # Rebuild LearningPathCourse records from new roadmap
                position = 0
                for phase in roadmap_dict.get('phases', []):
                    phase_num = phase.get('phase_number')
                    for course_item in phase.get('courses', []):
                        cid = course_item.get('course_id')
                        if not cid or not Course.objects.filter(id=cid).exists():
                            continue
                        position += 1
                        is_completed = cid in completed_ids
                        LearningPathCourse.objects.create(
                            learning_path=lp,
                            course_id=cid,
                            position=position,
                            phase_number=phase_num,
                            is_completed=is_completed,
                            is_manually_added=False,
                            regenerate_version=reg_version,
                        )

            # Reload with relations
            lp = (
                LearningPath.objects
                .filter(id=lp.id)
                .prefetch_related(
                    'path_courses__course__platform',
                    'path_courses__course__tags',
                )
                .first()
            )

        except Exception as e:
            logger.error(f"[RAG] Failed to save regenerated path: {e}")
            return Response(
                {'detail': f'Failed to save regenerated path: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        response_data = LearningPathDetailSerializer(lp).data
        response_data['_rag_meta'] = {
            'regenerate_count': lp.regenerate_count,
            'regenerate_context': lp.regenerate_context,
            'completed_courses_preserved': len(completed_ids),
            'courses_retrieved': len(courses),
            'top_similarity_score': float(top_score),
        }

        return Response(response_data, status=status.HTTP_200_OK)


class RAGLearningPathDeleteCourseView(APIView):
    """
    DELETE /api/rag/learning-paths/{id}/courses/{course_id}/
        Remove a course from a learning path. Positions are reindexed.

    PATCH /api/rag/learning-paths/{id}/courses/{course_id}/
        Apply a course replacement.
        Body: { "new_course_id": "...", "replacement_reason": "..." }
        (Supports frontend's existing PATCH call without needing /apply/ suffix)
    """
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk, course_id):
        """Apply course replacement — matches frontend PATCH /courses/{courseId}/"""
        serializer = LearningPathApplyReplacementRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        lp = LearningPath.objects.filter(user=request.user, id=pk).first()
        if not lp:
            return Response({'detail': 'Learning path not found.'}, status=status.HTTP_404_NOT_FOUND)

        item = lp.path_courses.filter(course_id=course_id).first()
        if not item:
            return Response({'detail': 'Course not found in this learning path.'}, status=status.HTTP_404_NOT_FOUND)

        new_course_id = data['new_course_id']
        replacement_reason = data.get('replacement_reason', '')

        try:
            new_course = Course.objects.get(id=new_course_id)
        except Course.DoesNotExist:
            return Response({'detail': 'Replacement course not found.'}, status=status.HTTP_404_NOT_FOUND)

        if lp.path_courses.filter(course_id=new_course_id).exists():
            return Response({'detail': 'Replacement course already exists in this learning path.'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            item.replaced_by = new_course
            item.replacement_reason = replacement_reason
            item.save(update_fields=['replaced_by', 'replacement_reason'])
            old_position = item.position
            item.delete()
            LearningPathCourse.objects.create(
                learning_path=lp,
                course_id=new_course_id,
                position=old_position,
                is_manually_added=True,
            )

        lp = (
            LearningPath.objects
            .filter(id=lp.id)
            .prefetch_related(
                'path_courses__course__platform',
                'path_courses__course__tags',
            )
            .first()
        )
        return Response({
            'detail': 'Course replaced successfully.',
            'learning_path': LearningPathDetailSerializer(lp).data,
        })

    def delete(self, request, pk, course_id):
        lp = LearningPath.objects.filter(user=request.user, id=pk).first()
        if not lp:
            return Response(
                {'detail': 'Learning path not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        item = lp.path_courses.filter(course_id=course_id).first()
        if not item:
            return Response(
                {'detail': 'Course not found in this learning path.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        deleted_position = item.position
        item.delete()

        # Reindex remaining courses
        for i, remaining in enumerate(
            lp.path_courses.order_by('position'), start=1
        ):
            if remaining.position != i:
                remaining.position = i
                remaining.save(update_fields=['position'])

        return Response(
            {'detail': 'Course removed from learning path.', 'position': deleted_position},
            status=status.HTTP_200_OK,
        )


class RAGLearningPathReorderView(APIView):
    """
    PATCH /api/rag/learning-paths/{id}/courses/reorder/
    Reorder courses in a learning path. Frontend sudah kirim urutan yang benar.
    """
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        serializer = LearningPathReorderRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        course_ids = serializer.validated_data['course_ids']

        lp = LearningPath.objects.filter(user=request.user, id=pk).first()
        if not lp:
            return Response(
                {'detail': 'Learning path not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Verify all course_ids exist in this learning path
        existing_ids = set(str(c.course_id) for c in lp.path_courses.all())
        ordered_ids = [str(cid) for cid in course_ids]

        missing = [cid for cid in ordered_ids if cid not in existing_ids]
        if missing:
            return Response(
                {'detail': f'Courses not found in this learning path: {missing}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Update positions based on frontend-provided order
        with transaction.atomic():
            for position, course_id in enumerate(ordered_ids, start=1):
                LearningPathCourse.objects.filter(
                    learning_path=lp,
                    course_id=course_id,
                ).update(position=position)

        # Reload with relations
        lp = (
            LearningPath.objects
            .filter(id=lp.id)
            .prefetch_related(
                'path_courses__course__platform',
                'path_courses__course__tags',
            )
            .first()
        )

        return Response(LearningPathDetailSerializer(lp).data)


class RAGLearningPathAddCourseView(APIView):
    """
    POST /api/rag/learning-paths/{id}/courses/add/
    Add a course to a learning path at a specific position or end.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        serializer = LearningPathAddCourseRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        lp = (
            LearningPath.objects
            .filter(user=request.user, id=pk)
            .first()
        )
        if not lp:
            return Response(
                {'detail': 'Learning path not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        course_id = data['course_id']
        phase_number = data.get('phase_number')
        position = data.get('position')

        # Verify course exists
        try:
            course = Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            return Response(
                {'detail': 'Course not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Check if course already in path
        if lp.path_courses.filter(course_id=course_id).exists():
            return Response(
                {'detail': 'Course already exists in this learning path.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate phase_number exists in this learning path
        if phase_number is not None:
            phase_exists = lp.path_courses.filter(phase_number=phase_number).exists()
            if not phase_exists:
                return Response(
                    {'detail': f'Phase {phase_number} not found in this learning path.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        with transaction.atomic():
            if phase_number is not None:
                # Insert at end of the specified phase
                last_in_phase = (
                    lp.path_courses.filter(phase_number=phase_number)
                    .order_by('-position')
                    .first()
                )
                new_position = last_in_phase.position + 1
                # Shift all courses after this phase down by 1
                lp.path_courses.filter(position__gte=new_position).update(
                    position=models.F('position') + 1
                )
            elif position is not None:
                # Insert at explicit position — shift existing courses down
                new_position = position
                lp.path_courses.filter(position__gte=new_position).update(
                    position=models.F('position') + 1
                )
            else:
                # Append at end
                last = lp.path_courses.order_by('-position').first()
                new_position = (last.position + 1) if last else 1

            LearningPathCourse.objects.create(
                learning_path=lp,
                course_id=course_id,
                position=new_position,
                phase_number=phase_number,
                is_manually_added=True,
            )

        # Reload with relations
        lp = (
            LearningPath.objects
            .filter(id=lp.id)
            .prefetch_related(
                'path_courses__course__platform',
                'path_courses__course__tags',
            )
            .first()
        )

        return Response(LearningPathDetailSerializer(lp).data, status=status.HTTP_200_OK)


class RAGLearningPathSimilarCoursesView(APIView):
    """
    GET /api/rag/learning-paths/{id}/courses/{course_id}/similar/
    Returns course candidates "similar" to a given course — for add/replace context.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk, course_id):
        lp = LearningPath.objects.filter(user=request.user, id=pk).first()
        if not lp:
            return Response(
                {'detail': 'Learning path not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        item = lp.path_courses.filter(course_id=course_id).first()
        if not item:
            return Response(
                {'detail': 'Course not found in this learning path.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        course = item.course
        topic = lp.topic_input or course.title

        # Get courses already in the path (to exclude)
        existing_ids = [str(c.course_id) for c in lp.path_courses.all()]

        # Retrieve similar courses from FAISS
        candidates, top_score = retrieve_courses_for_replace(
            replaced_course_id=str(course_id),
            topic=topic,
            user_profile=None,
            additional_context=None,
            exclude_ids=existing_ids,
            top_k=20,
        )

        # Build user profile for scoring
        user_profile = _build_user_profile(request.user, topic)

        # Build response
        from apps.rag.serializers import SimilarCourseSerializer
        from apps.rag.serializers import SimilarCoursesResponseSerializer

        course_results = []
        for c in candidates:
            meta = c.get('metadata', c)
            course_results.append({
                'course_id': c.get('course_id'),
                'title': meta.get('title', ''),
                'instructor': meta.get('instructor'),
                'platform': meta.get('platform', ''),
                'level': meta.get('level', ''),
                'rating': meta.get('rating'),
                'reviews_count': meta.get('reviews_count'),
                'price': meta.get('price'),
                'currency': meta.get('currency', 'IDR'),
                'duration': meta.get('duration', ''),
                'thumbnail_url': meta.get('thumbnail_url', ''),
                'url': meta.get('url', ''),
                'relevance_score': c.get('_score', 0.0),
                'faiss_score': c.get('_score', 0.0),
            })

        return Response({
            'original_course_id': str(course_id),
            'original_course_title': course.title,
            'topic': topic,
            'courses': course_results,
        })


class RAGLearningPathReplaceCourseView(APIView):
    """
    POST /api/rag/learning-paths/{id}/courses/{course_id}/replace/
    Find replacement candidates for a specific course, with AI explanations.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk, course_id):
        serializer = LearningPathReplaceCourseRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            lp = (
                LearningPath.objects
                .filter(user=request.user, id=pk)
                .first()
            )
        except LearningPath.DoesNotExist:
            return Response(
                {'detail': 'Learning path not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not lp:
            return Response(
                {'detail': 'Learning path not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        item = lp.path_courses.filter(course_id=course_id).first()
        if not item:
            return Response(
                {'detail': 'Course not found in this learning path.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        original_course = item.course
        additional_context = data.get('additional_context', '')
        topic = lp.topic_input or original_course.title

        # Get courses already in the path (to exclude)
        existing_ids = [str(c.course_id) for c in lp.path_courses.all()]

        # Build user profile
        user_profile = _build_user_profile(request.user, topic)
        if additional_context:
            user_profile['additional_context'] = additional_context

        # Retrieve replacement candidates
        count = data.get('count', 5)
        candidates, top_score = retrieve_courses_for_replace(
            replaced_course_id=str(course_id),
            topic=topic,
            user_profile=user_profile,
            additional_context=additional_context,
            exclude_ids=existing_ids,
            top_k=count + 10,  # Get extra so LLM can filter
        )

        # Limit to requested count
        candidates = candidates[:count]

        if not candidates:
            return Response(
                {'detail': 'No replacement candidates found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Generate AI explanations for replacements
        original_meta = {
            'course_id': str(original_course.id),
            'metadata': {
                'title': original_course.title,
                'instructor': original_course.instructor,
                'level': original_course.level,
                'platform': original_course.platform.name,
                'rating': float(original_course.rating) if original_course.rating else None,
                'price': float(original_course.price) if original_course.price else None,
                'currency': original_course.currency,
                'duration': original_course.duration,
                'thumbnail_url': original_course.thumbnail_url,
                'url': original_course.url,
                'description': original_course.description[:300],
                'what_you_learn': original_course.what_you_learn[:200],
                'tags': ', '.join(t.name for t in original_course.tags.all()),
            },
        }

        result = generate_replacement_explanations(
            topic=topic,
            user_profile=user_profile,
            original_course_metadata=original_meta,
            candidate_courses=candidates,
            additional_context=additional_context,
        )

        return Response({
            'original_course_id': str(course_id),
            'original_course_title': original_course.title,
            'replacement_reason_summary': result.get(
                'replacement_reason_summary', ''
            ),
            'candidates': result.get('candidates', []),
        })


class RAGLearningPathApplyReplacementView(APIView):
    """
    POST /api/rag/learning-paths/{id}/courses/{course_id}/apply/
    Apply a selected replacement course to the learning path.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk, course_id):
        serializer = LearningPathApplyReplacementRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            lp = (
                LearningPath.objects
                .filter(user=request.user, id=pk)
                .first()
            )
        except LearningPath.DoesNotExist:
            return Response(
                {'detail': 'Learning path not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not lp:
            return Response(
                {'detail': 'Learning path not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        item = lp.path_courses.filter(course_id=course_id).first()
        if not item:
            return Response(
                {'detail': 'Course not found in this learning path.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        new_course_id = data['new_course_id']
        replacement_reason = data.get('replacement_reason', '')

        # Verify new course exists and not already in path
        try:
            new_course = Course.objects.get(id=new_course_id)
        except Course.DoesNotExist:
            return Response(
                {'detail': 'Replacement course not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        if lp.path_courses.filter(course_id=new_course_id).exists():
            return Response(
                {'detail': 'Replacement course already exists in this learning path.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            # Record old course as replaced
            item.replaced_by = new_course
            item.replacement_reason = replacement_reason
            item.save(
                update_fields=[
                    'replaced_by', 'replacement_reason',
                ],
            )

            # Update the LearningPathCourse to point to new course
            # (delete old record, create new at same position)
            old_position = item.position
            item.delete()

            LearningPathCourse.objects.create(
                learning_path=lp,
                course_id=new_course_id,
                position=old_position,
                is_manually_added=True,
            )

        # Reload with relations
        lp = (
            LearningPath.objects
            .filter(id=lp.id)
            .prefetch_related(
                'path_courses__course__platform',
                'path_courses__course__tags',
            )
            .first()
        )

        return Response({
            'detail': 'Course replaced successfully.',
            'learning_path': LearningPathDetailSerializer(lp).data,
        })


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _save_recommendations_to_db(
    user,
    topic: str,
    additional_context: str,
    enriched_courses: list[dict],
    regenerate: bool = False,
) -> list[dict]:
    """
    Save/upsert CourseRecommendation records and return serialized data
    ready for response serialization.

    On regenerate=True: increment regenerate_count, preserve is_saved, overwrite
    ai_explanation & additional_context with new generation.
    """
    saved = []

    with transaction.atomic():
        for item in enriched_courses:
            course_id = item.get('course_id')
            if not course_id:
                continue

            if not Course.objects.filter(id=course_id).exists():
                continue

            if regenerate:
                # Preserve is_saved; increment regenerate_count
                existing = CourseRecommendation.objects.filter(
                    user=user,
                    course_id=course_id,
                    topic_input=topic,
                ).first()

                if existing:
                    existing.additional_context = additional_context
                    existing.relevance_score = item.get('relevance_score', 0.0)
                    existing.ai_explanation = item.get('ai_explanation', '')
                    existing.regenerate_count = existing.regenerate_count + 1
                    existing.save(
                        update_fields=[
                            'additional_context', 'relevance_score',
                            'ai_explanation', 'regenerate_count',
                        ],
                    )
                    rec = (
                        CourseRecommendation.objects
                        .filter(id=existing.id)
                        .select_related('course__platform')
                        .prefetch_related('course__tags')
                        .first()
                    )
                else:
                    # No existing record — create new one
                    rec = CourseRecommendation.objects.create(
                        user=user,
                        course_id=course_id,
                        topic_input=topic,
                        additional_context=additional_context,
                        relevance_score=item.get('relevance_score', 0.0),
                        ai_explanation=item.get('ai_explanation', ''),
                        regenerate_count=0,
                    )
                    rec = (
                        CourseRecommendation.objects
                        .filter(id=rec.id)
                        .select_related('course__platform')
                        .prefetch_related('course__tags')
                        .first()
                    )
            else:
                # Fresh recommendation — upsert as before (is_saved stays False)
                rec, _ = CourseRecommendation.objects.update_or_create(
                    user=user,
                    course_id=course_id,
                    topic_input=topic,
                    defaults={
                        'additional_context': additional_context,
                        'relevance_score': item.get('relevance_score', 0.0),
                        'ai_explanation': item.get('ai_explanation', ''),
                        'is_saved': False,
                        'regenerate_count': 0,
                    },
                )
                rec = (
                    CourseRecommendation.objects
                    .filter(id=rec.id)
                    .select_related('course__platform')
                    .prefetch_related('course__tags')
                    .first()
                )

            saved.append({
                'id': str(rec.id),
                # Store plain dict so REST Framework JSON renderer can serialize it
                'course_obj': {
                    'id': rec.course.id,
                    'title': rec.course.title,
                    'instructor': rec.course.instructor,
                    'rating': rec.course.rating,
                    'reviews_count': rec.course.reviews_count,
                    'price': rec.course.price,
                    'currency': rec.course.currency,
                    'level': rec.course.level,
                    'duration': rec.course.duration or '',
                    'video_hours': rec.course.video_hours,
                    'thumbnail_url': rec.course.thumbnail_url or '',
                    'url': rec.course.url or '',
                },
                'relevance_score': float(rec.relevance_score),
                'ai_explanation': rec.ai_explanation,
                'match_score': item.get('match_score', 0.5),
                'best_for': item.get('best_for', ''),
                'potential_gaps': item.get('potential_gaps', ''),
                'is_saved': rec.is_saved,
                'regenerate_count': rec.regenerate_count,
                'created_at': rec.created_at,
            })

    return saved