from django.urls import path

from .views import CourseListView, CourseDetailView

urlpatterns = [
    path('courses/', CourseListView.as_view(), name='courses-list'),
    path('courses/<uuid:pk>/', CourseDetailView.as_view(), name='course-detail'),
]
