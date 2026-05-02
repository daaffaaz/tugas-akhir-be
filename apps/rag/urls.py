from django.urls import path

from apps.rag import views

urlpatterns = [
    # ── Learning Path Generate (existing) ────────────────────────────────────
    path('rag/generate-roadmap/', views.RAGRoadmapGenerateView.as_view(), name='rag-generate-roadmap'),

    # ── Learning Path List (existing) ─────────────────────────────────────────
    path('rag/learning-paths/', views.RAGLearningPathListView.as_view(), name='rag-learning-path-list'),

    # ── Learning Path Edit / Regenerate / Replace ─────────────────────────────
    path(
        'rag/learning-paths/<uuid:pk>/regenerate/',
        views.RAGLearningPathRegenerateView.as_view(),
        name='rag-learning-path-regenerate',
    ),
    # NOTE: /replace/ and /similar/ and /apply/ MUST come BEFORE /<uuid:course_id>/
    # Django URL dispatch is top-to-bottom, so longer/more-specific paths first.
    path(
        'rag/learning-paths/<uuid:pk>/courses/<uuid:course_id>/replace/',
        views.RAGLearningPathReplaceCourseView.as_view(),
        name='rag-learning-path-replace-course',
    ),
    path(
        'rag/learning-paths/<uuid:pk>/courses/<uuid:course_id>/apply/',
        views.RAGLearningPathApplyReplacementView.as_view(),
        name='rag-learning-path-apply-replacement',
    ),
    path(
        'rag/learning-paths/<uuid:pk>/courses/<uuid:course_id>/similar/',
        views.RAGLearningPathSimilarCoursesView.as_view(),
        name='rag-learning-path-similar-courses',
    ),
    path(
        'rag/learning-paths/<uuid:pk>/courses/<uuid:course_id>/',
        views.RAGLearningPathDeleteCourseView.as_view(),
        name='rag-learning-path-delete-course',
    ),
    path(
        'rag/learning-paths/<uuid:pk>/courses/add/',
        views.RAGLearningPathAddCourseView.as_view(),
        name='rag-learning-path-add-course',
    ),

    # ── Course Recommendations (existing) ─────────────────────────────────────
    path('rag/recommend/', views.RAGCourseRecommendView.as_view(), name='rag-recommend'),
    path('rag/recommendations/', views.RAGRecommendationListView.as_view(), name='rag-recommendation-list'),
]