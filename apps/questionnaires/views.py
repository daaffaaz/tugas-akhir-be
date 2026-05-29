from django.db import transaction
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Question, UserQuestionnaireAnswer
from .serializers import (
    AnswerItemSerializer,
    QuestionSerializer,
    UserQuestionnaireAnswerSerializer,
)


class QuestionListView(generics.ListAPIView):
    """GET /api/questions/ — list active questionnaire questions in order."""

    queryset = Question.objects.filter(is_active=True)
    serializer_class = QuestionSerializer
    permission_classes = [AllowAny]


def _validate_answer_rows(rows: list[dict]) -> dict:
    """Validate full submission: one row per question, options must match options_json keys.

    Accepts:
      - 14 answers (new v14 flow)
      - 32 answers (old v32 flow, for users re-taking questionnaire)
    """
    active_qs = Question.objects.filter(is_active=True)
    total_qs = Question.objects.count()
    expected_active = active_qs.count()

    if len(rows) == expected_active:
        # New user flow — validate against active questions only
        questions = {q.id: q for q in active_qs}
    elif len(rows) == total_qs:
        # Old user re-take flow — validate against all questions
        questions = {q.id: q for q in Question.objects.all()}
    else:
        raise ValidationError(
            {'detail': f'Expected {expected_active} answers (new) or {total_qs} (old), got {len(rows)}.'},
        )

    # Check for duplicate question IDs
    qids = [r['question_id'] for r in rows]
    if len(set(qids)) != len(qids):
        raise ValidationError({'detail': 'Duplicate question_id in payload.'})

    # Ensure all submitted question IDs are valid
    if len(questions) != len(rows):
        raise ValidationError({'detail': 'Invalid or incomplete set of question ids.'})

    # Validate each answer_option against question's options_json
    for r in rows:
        q = questions[r['question_id']]
        opt = r['answer_option']
        if opt not in (q.options_json or {}):
            raise ValidationError(
                {'detail': f'Invalid answer_option {opt!r} for question order {q.order_number}.'},
            )
    return questions


class ComputeLevelView(APIView):
    """
    POST /api/questionnaires/compute-level/
    Compute learner level from 3-signal weighted scoring (Proposal v3).
    """

    permission_classes = [AllowAny]

    PROGRAMMING_FAMILIARITY_SCORES = {
        'A': 0.00, 'B': 0.25, 'C': 0.55, 'D': 1.00,
    }
    DOMAIN_COMFORT_SCORES = {
        'A': 0.00, 'B': 0.25, 'C': 0.40, 'D': 0.70, 'E': 1.00,
    }
    FORMAL_PREPARATION_SCORES = {
        'A': 0.00, 'B': 0.35, 'C': 0.60, 'D': 1.00,
    }
    LEVEL_WEIGHTS = {
        'programming_familiarity': 0.35,
        'domain_comfort':          0.40,
        'formal_preparation':      0.25,
    }
    LEVEL_BUCKETS = [
        (0.35, 'Beginner'),
        (0.55, 'Lower Intermediate'),
        (0.75, 'Intermediate'),
    ]
    LEVEL_FALLBACK = 'Advanced'

    SIGNAL_LABELS = {
        'programming_familiarity': {
            'A': 'Beginner', 'B': 'Beginner-Lower Intermediate',
            'C': 'Intermediate', 'D': 'Advanced',
        },
        'domain_comfort': {
            'A': 'Beginner', 'B': 'Beginner-Lower Intermediate',
            'C': 'Lower Intermediate', 'D': 'Intermediate-Upper Intermediate', 'E': 'Advanced',
        },
        'formal_preparation': {
            'A': 'Beginner', 'B': 'Lower Intermediate',
            'C': 'Intermediate', 'D': 'Advanced',
        },
    }

    def post(self, request):
        answers = request.data.get('answers', [])
        if not answers:
            return Response({'detail': 'No answers provided.'}, status=status.HTTP_400_BAD_REQUEST)

        answers_map = {
            a.get('variable_key'): a.get('answer_option')
            for a in answers
            if a.get('variable_key') and a.get('answer_option')
        }

        s1 = self.PROGRAMMING_FAMILIARITY_SCORES.get(
            answers_map.get('programming_familiarity', 'A'), 0.0
        )
        s2 = self.DOMAIN_COMFORT_SCORES.get(
            answers_map.get('domain_comfort', 'A'), 0.0
        )
        s3 = self.FORMAL_PREPARATION_SCORES.get(
            answers_map.get('formal_preparation', 'A'), 0.0
        )

        level_score = (
            s1 * self.LEVEL_WEIGHTS['programming_familiarity'] +
            s2 * self.LEVEL_WEIGHTS['domain_comfort'] +
            s3 * self.LEVEL_WEIGHTS['formal_preparation']
        )

        level = self.LEVEL_FALLBACK
        for threshold, label in self.LEVEL_BUCKETS:
            if level_score <= threshold:
                level = label
                break

        score_maps = {
            'programming_familiarity': self.PROGRAMMING_FAMILIARITY_SCORES,
            'domain_comfort':          self.DOMAIN_COMFORT_SCORES,
            'formal_preparation':      self.FORMAL_PREPARATION_SCORES,
        }

        signals = {}
        for key in ('programming_familiarity', 'domain_comfort', 'formal_preparation'):
            value = answers_map.get(key, 'A')
            signals[key] = {
                'value': value,
                'score': score_maps[key].get(value, 0.0),
                'label': self.SIGNAL_LABELS[key].get(value, 'Beginner'),
            }

        return Response({
            'level': level,
            'level_score': round(level_score, 2),
            'signals': signals,
        })


class UserQuestionnaireView(APIView):
    """GET: fetch answers. POST: full submit (14 or 32 answers). PATCH: partial answer updates."""

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        answers = UserQuestionnaireAnswer.objects.filter(user=request.user).select_related('question')
        return Response(UserQuestionnaireAnswerSerializer(answers, many=True).data)

    def post(self, request, *args, **kwargs):
        if request.user.questionnaire_completed_at:
            return Response(
                {'detail': 'Questionnaire already completed. Use PATCH to update specific answers.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = AnswerItemSerializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        rows = serializer.validated_data

        questions = _validate_answer_rows(rows)

        with transaction.atomic():
            UserQuestionnaireAnswer.objects.filter(user=request.user).delete()
            to_create = [
                UserQuestionnaireAnswer(
                    user=request.user,
                    question=questions[r['question_id']],
                    answer_option=r['answer_option'],
                )
                for r in rows
            ]
            UserQuestionnaireAnswer.objects.bulk_create(to_create)

            request.user.questionnaire_completed_at = timezone.now()
            request.user.save(update_fields=['questionnaire_completed_at', 'updated_at'])

        out = UserQuestionnaireAnswer.objects.filter(user=request.user).select_related('question')
        return Response(
            UserQuestionnaireAnswerSerializer(out, many=True).data,
            status=status.HTTP_201_CREATED,
        )

    def patch(self, request, *args, **kwargs):
        if not request.user.questionnaire_completed_at:
            return Response(
                {'detail': 'Complete the questionnaire via POST before using PATCH.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = AnswerItemSerializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        rows = serializer.validated_data
        if not rows:
            raise ValidationError({'detail': 'At least one answer update is required.'})

        qids = [r['question_id'] for r in rows]
        if len(set(qids)) != len(qids):
            raise ValidationError({'detail': 'Duplicate question_id in payload.'})

        questions = {q.id: q for q in Question.objects.filter(id__in=qids)}
        for r in rows:
            q = questions.get(r['question_id'])
            if q is None:
                raise ValidationError({'detail': f'Unknown question_id {r["question_id"]}.'})
            opt = r['answer_option']
            if opt not in (q.options_json or {}):
                raise ValidationError(
                    {'detail': f'Invalid answer_option {opt!r} for question order {q.order_number}.'},
                )

        with transaction.atomic():
            for r in rows:
                q = questions[r['question_id']]
                UserQuestionnaireAnswer.objects.update_or_create(
                    user=request.user,
                    question=q,
                    defaults={'answer_option': r['answer_option']},
                )

        updated = UserQuestionnaireAnswer.objects.filter(user=request.user, question_id__in=qids).select_related(
            'question'
        )
        return Response(UserQuestionnaireAnswerSerializer(updated, many=True).data)