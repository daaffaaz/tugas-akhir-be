import logging
import uuid
from collections import defaultdict

from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.courses.models import Course
from apps.learning_paths.models import LearningPath, LearningPathCourse
from apps.learning_paths.serializers import LearningPathDetailSerializer
from apps.questionnaires.models import Question, UserQuestionnaireAnswer
from apps.users.models import UserPreferences

from .generator import generate_roadmap
from .retriever import retrieve_courses
from .serializers import RAGGenerateRequestSerializer

logger = logging.getLogger(__name__)


def _build_user_profile(user, topic: str) -> dict:
    """
    Assemble a user profile dict from UserPreferences + UserQuestionnaireAnswer.
    Used as context for the RAG prompt.
    """
    try:
        prefs = user.userpreferences
        profile = {
            'current_skills': [],
            'goals': [],
            'level': '',
            'budget': int(prefs.budget_idr) if prefs.budget_idr else None,
            'weekly_hours': int(prefs.weekly_hours) if prefs.weekly_hours else None,
            'material_format': prefs.material_format or '',
            'theory_practice': prefs.theory_practice or '',
            'target_role': prefs.target_role or '',
            'main_goal': prefs.main_goal or '',
        }
    except UserPreferences.DoesNotExist:
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
    course_positions = []  # list of (course_id, position)
    position = 0
    for phase in phases:
        for course_item in phase.get('courses', []):
            cid = course_item.get('course_id')
            if cid:
                position += 1
                course_positions.append((cid, position))

    if not course_positions:
        raise ValueError("No valid courses in roadmap to save.")

    # Verify all course IDs exist
    course_ids = [cid for cid, _ in course_positions]
    valid_ids = set(str(c.id) for c in Course.objects.filter(id__in=course_ids))
    course_positions = [(cid, pos) for cid, pos in course_positions if cid in valid_ids]

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

        for course_id, pos in course_positions:
            LearningPathCourse.objects.create(
                learning_path=learning_path,
                course_id=course_id,
                position=pos,
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
                {'detail': 'No courses found matching your topic. Try a different query.'},
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