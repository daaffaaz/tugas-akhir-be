from django.urls import path

from .views import BadgeListView, LearningPathBadgesView, UserBadgeListView

urlpatterns = [
    path('badges/', BadgeListView.as_view(), name='badge-catalog'),
    path('users/me/badges/', UserBadgeListView.as_view(), name='user-badges'),
    path(
        'learning-paths/<uuid:pk>/badges/',
        LearningPathBadgesView.as_view(),
        name='learning-path-badges',
    ),
]
