from django.http import JsonResponse
from rest_framework_simplejwt.authentication import JWTAuthentication


class QuestionnaireCompletionMiddleware:
    """
    Block authenticated users who have not completed the questionnaire
    from protected API routes. JWT is resolved here so this runs before DRF.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self._jwt_auth = JWTAuthentication()

    def __call__(self, request):
        path = request.path.rstrip('/') or '/'

        if not path.startswith('/api'):
            return self.get_response(request)

        # Public API prefixes
        if path.startswith('/api/auth'):
            return self.get_response(request)

        user = None
        try:
            auth = self._jwt_auth.authenticate(request)
            if auth:
                user, _ = auth
        except Exception:
            user = None

        if not user or not getattr(user, 'is_authenticated', False):
            return self.get_response(request)

        if user.questionnaire_completed_at:
            return self.get_response(request)

        method = request.method.upper()
        if method == 'GET' and path == '/api/questions':
            return self.get_response(request)
        if method == 'POST' and path == '/api/users/questionnaire':
            return self.get_response(request)
        if path in ('/api/users/profile', '/api/users/preferences', '/api/users/avatar'):
            return self.get_response(request)

        return JsonResponse(
            {'detail': 'Complete the onboarding questionnaire before accessing this resource.'},
            status=403,
        )
