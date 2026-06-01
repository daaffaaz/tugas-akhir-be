from django.urls import path

from .views import NextStepsRecommendationView

urlpatterns = [
    path(
        'recommendations/next-steps/',
        NextStepsRecommendationView.as_view(),
        name='recommendations-next-steps',
    ),
]
