from django.urls import path

from apps.rag import views

urlpatterns = [
    # Learning Path (existing)
    path('rag/generate-roadmap/', views.RAGRoadmapGenerateView.as_view(), name='rag-generate-roadmap'),
    # Course Recommendations (new)
    path('rag/recommend/', views.RAGCourseRecommendView.as_view(), name='rag-recommend'),
    path('rag/recommendations/', views.RAGRecommendationListView.as_view(), name='rag-recommendation-list'),
]