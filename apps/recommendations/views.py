import logging

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import NextStepsResponseSerializer
from .services import get_next_steps_for_user

logger = logging.getLogger(__name__)


class NextStepsRecommendationView(APIView):
    """
    GET /api/recommendations/next-steps/

    Returns 2-4 career possibilities + 3-5 suggested courses per possibility,
    based on the courses the user has marked as completed in their learning paths.
    Empty list (200) when the user has no completed courses yet.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        logger.info(
            f"[next-steps] user={request.user.id} requesting next-steps"
        )
        payload = get_next_steps_for_user(request.user)
        serializer = NextStepsResponseSerializer(payload)
        return Response(serializer.data, status=status.HTTP_200_OK)
