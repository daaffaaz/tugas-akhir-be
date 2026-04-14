import os
import uuid

from django.contrib.auth import get_user_model
from django.core.files.storage import default_storage
from rest_framework import status
from rest_framework import generics
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import UserPreferences
from .serializers import (
    EmailTokenObtainPairSerializer,
    GoogleLoginSerializer,
    ProfileSerializer,
    ProfileUpdateSerializer,
    RegisterSerializer,
    UserPreferencesSerializer,
)

User = get_user_model()


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                'id': str(user.id),
                'email': user.email,
                'full_name': user.full_name,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            },
            status=status.HTTP_201_CREATED,
        )


class EmailTokenObtainPairView(TokenObtainPairView):
    serializer_class = EmailTokenObtainPairSerializer


class GoogleLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = GoogleLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token_info = serializer.validated_data['token_info']

        email = token_info['email'].lower()
        full_name = token_info.get('name', '')
        avatar_url = token_info.get('picture', '')

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'full_name': full_name,
                'avatar_url': avatar_url,
            },
        )

        # Keep profile in sync with Google claims.
        if not created:
            fields_to_update = []
            if full_name and user.full_name != full_name:
                user.full_name = full_name
                fields_to_update.append('full_name')
            if avatar_url and user.avatar_url != avatar_url:
                user.avatar_url = avatar_url
                fields_to_update.append('avatar_url')
            if fields_to_update:
                user.save(update_fields=fields_to_update)

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                'id': str(user.id),
                'email': user.email,
                'full_name': user.full_name,
                'avatar_url': user.avatar_url,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            },
            status=status.HTTP_200_OK,
        )


class ProfileView(APIView):
    """GET/PATCH /api/users/profile/ — view and update basic profile fields."""

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        return Response(ProfileSerializer(request.user).data)

    def patch(self, request, *args, **kwargs):
        serializer = ProfileUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(ProfileSerializer(request.user).data)


class PreferencesView(generics.RetrieveUpdateAPIView):
    serializer_class = UserPreferencesSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'patch']

    def get_object(self):
        obj, _ = UserPreferences.objects.get_or_create(user=self.request.user)
        return obj

    def update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return super().update(request, *args, **kwargs)


class AvatarUploadView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, *args, **kwargs):
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({'file': ['This field is required.']}, status=status.HTTP_400_BAD_REQUEST)

        ext = os.path.splitext(file_obj.name or '')[1].lower()
        if ext not in ('.jpg', '.jpeg', '.png', '.webp', '.gif'):
            return Response({'file': ['Unsupported file type.']}, status=status.HTTP_400_BAD_REQUEST)

        path = default_storage.save(f'avatars/{uuid.uuid4().hex}{ext}', file_obj)
        avatar_url = request.build_absolute_uri(default_storage.url(path))
        return Response({'avatar_url': avatar_url}, status=status.HTTP_200_OK)
