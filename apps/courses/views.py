from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics
from rest_framework.filters import OrderingFilter, SearchFilter

from .filters import CourseFilter
from .models import Course
from .serializers import CourseListSerializer


class CourseListView(generics.ListAPIView):
    """GET /api/courses/ — catalog with search, filters, pagination."""

    queryset = (
        Course.objects.filter(is_active=True)
        .select_related('platform')
        .prefetch_related('tags')
    )
    serializer_class = CourseListSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = CourseFilter
    search_fields = ['title', 'description']
    ordering_fields = ['title', 'price', 'rating', 'review_count', 'duration_hours', 'created_at']
    ordering = ['title']
