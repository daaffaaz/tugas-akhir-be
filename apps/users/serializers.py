from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.conf import settings
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import UserPreferences

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ('email', 'password', 'password_confirm', 'full_name')

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({'password_confirm': 'Passwords do not match.'})
        validate_password(attrs['password'])
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            'id',
            'email',
            'full_name',
            'avatar_url',
            'questionnaire_completed_at',
            'created_at',
        )
        read_only_fields = fields


class ProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('full_name', 'avatar_url')


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Login with email + password (JWT obtain pair)."""

    username_field = User.USERNAME_FIELD

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Use email validation instead of plain CharField
        self.fields[self.username_field] = serializers.EmailField(write_only=True)


class GoogleLoginSerializer(serializers.Serializer):
    id_token = serializers.CharField()

    def validate(self, attrs):
        raw_token = attrs['id_token']
        client_id = settings.GOOGLE_OAUTH_CLIENT_ID
        if not client_id:
            raise serializers.ValidationError(
                {'detail': 'GOOGLE_OAUTH_CLIENT_ID is not configured.'},
            )

        try:
            token_info = id_token.verify_oauth2_token(
                raw_token,
                google_requests.Request(),
                client_id,
            )
        except Exception as exc:
            raise serializers.ValidationError({'id_token': 'Invalid Google ID token.'}) from exc

        if token_info.get('iss') not in ('accounts.google.com', 'https://accounts.google.com'):
            raise serializers.ValidationError({'id_token': 'Invalid token issuer.'})

        email = token_info.get('email')
        if not email:
            raise serializers.ValidationError({'id_token': 'Email not available in Google token.'})

        attrs['token_info'] = token_info
        return attrs


class UserPreferencesSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPreferences
        exclude = ('id', 'user', 'created_at', 'updated_at')

    def validate_cli_level(self, value):
        if value is None:
            return value
        if value not in (0, 1, 2, 3):
            raise serializers.ValidationError('cli_level must be one of: 0, 1, 2, 3.')
        return value

    def validate_logic_level(self, value):
        if value is None:
            return value
        if value not in (0, 1, 2, 3):
            raise serializers.ValidationError('logic_level must be one of: 0, 1, 2, 3.')
        return value

    def to_representation(self, instance):
        data = super().to_representation(instance)
        for key, value in data.items():
            if value == '':
                data[key] = None
        return data
