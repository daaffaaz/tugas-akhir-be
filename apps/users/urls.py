from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import AvatarUploadView, EmailTokenObtainPairView, GoogleLoginView, PreferencesView, ProfileView, RegisterView

urlpatterns = [
    path('auth/register/', RegisterView.as_view(), name='auth-register'),
    path('auth/login/', EmailTokenObtainPairView.as_view(), name='auth-login'),
    path('auth/google/', GoogleLoginView.as_view(), name='auth-google-login'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='auth-token-refresh'),
    path('users/profile/', ProfileView.as_view(), name='user-profile'),
    path('users/preferences/', PreferencesView.as_view(), name='user-preferences'),
    path('users/avatar/', AvatarUploadView.as_view(), name='user-avatar-upload'),
]
