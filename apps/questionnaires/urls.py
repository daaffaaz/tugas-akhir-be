from django.urls import path

from .views import QuestionListView, UserQuestionnaireView

urlpatterns = [
    path('questions/', QuestionListView.as_view(), name='questions-list'),
    path('users/questionnaire/', UserQuestionnaireView.as_view(), name='user-questionnaire'),
]
