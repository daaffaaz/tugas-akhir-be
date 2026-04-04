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
    """GET /api/questions/ — list all questionnaire questions in order."""

    queryset = Question.objects.all()
    serializer_class = QuestionSerializer
    permission_classes = [AllowAny]


def _validate_answer_rows(rows: list[dict]) -> dict:
    """Validate full submission: one row per question, options must match options_json keys."""
    expected = Question.objects.count()
    if expected == 0:
        raise ValidationError('No questions configured. Run import_questions first.')
    if len(rows) != expected:
        raise ValidationError(
            {'detail': f'Expected exactly {expected} answers, got {len(rows)}.'},
        )

    qids = [r['question_id'] for r in rows]
    if len(set(qids)) != len(qids):
        raise ValidationError({'detail': 'Duplicate question_id in payload.'})

    questions = {q.id: q for q in Question.objects.filter(id__in=qids)}
    if len(questions) != expected:
        raise ValidationError({'detail': 'Invalid or incomplete set of question ids.'})

    for r in rows:
        q = questions[r['question_id']]
        opt = r['answer_option']
        if opt not in (q.options_json or {}):
            raise ValidationError(
                {'detail': f'Invalid answer_option {opt!r} for question order {q.order_number}.'},
            )
    return questions


class UserQuestionnaireView(APIView):
    """POST: full submit (32 answers). PATCH: partial answer updates."""

    permission_classes = [IsAuthenticated]

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
