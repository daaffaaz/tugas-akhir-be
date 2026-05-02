from django.urls import path

from apps.rag import views

urlpatterns = [
    path('rag/generate-roadmap/', views.RAGRoadmapGenerateView.as_view(), name='rag-generate-roadmap'),
]