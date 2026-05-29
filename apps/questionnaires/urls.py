from django.urls import path

from .views import ComputeLevelView, QuestionListView, UserQuestionnaireView

urlpatterns = [
    path('questions/', QuestionListView.as_view(), name='questions-list'),
    path('users/questionnaire/', UserQuestionnaireView.as_view(), name='user-questionnaire'),
    path('users/compute-level/', ComputeLevelView.as_view(), name='compute-level'),
]
