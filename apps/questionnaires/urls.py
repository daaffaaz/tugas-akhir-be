from django.urls import path

from .views import QuestionListView

urlpatterns = [
    path('questions/', QuestionListView.as_view(), name='questions-list'),
]
