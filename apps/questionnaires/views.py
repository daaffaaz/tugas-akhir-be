from rest_framework import generics
from rest_framework.permissions import AllowAny

from .models import Question
from .serializers import QuestionSerializer


class QuestionListView(generics.ListAPIView):
    """GET /api/questions/ — list all questionnaire questions in order."""

    queryset = Question.objects.all()
    serializer_class = QuestionSerializer
    permission_classes = [AllowAny]
