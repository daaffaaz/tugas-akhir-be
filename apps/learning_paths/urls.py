from django.urls import path

from .views import (
    LearningPathBulkUpdateView,
    LearningPathCourseToggleCompleteView,
    LearningPathDetailView,
    LearningPathListCreateView,
)

urlpatterns = [
    path('learning-paths/', LearningPathListCreateView.as_view(), name='learning-paths-list'),
    path(
        'learning-paths/<uuid:pk>/bulk-update/',
        LearningPathBulkUpdateView.as_view(),
        name='learning-paths-bulk-update',
    ),
    path('learning-paths/<uuid:pk>/', LearningPathDetailView.as_view(), name='learning-paths-detail'),
    path(
        'learning-paths/courses/<uuid:pk>/toggle-complete/',
        LearningPathCourseToggleCompleteView.as_view(),
        name='learning-path-course-toggle',
    ),
]
