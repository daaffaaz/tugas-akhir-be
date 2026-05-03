from .base import *  # noqa: F403, F401

DEBUG = False

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='', cast=Csv()) + [  # noqa: F405
    '.vercel.app',
    'ta-be-persona-learn.vercel.app',
]


CORS_ALLOWED_ORIGINS = [
    'https://ta-persona-learn.vercel.app',
    'https://ta-be-persona-learn.vercel.app',
]
CORS_ALLOW_ALL_ORIGINS = False

CSRF_TRUSTED_ORIGINS = [
    'https://ta-persona-learn.vercel.app',
]

SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Vercel terminates TLS; without this Django may think requests are HTTP and
# redirect or build wrong URLs, and some responses may not get CORS applied as expected.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# CorsMiddleware must stay before WhiteNoise (see django-cors-headers docs).
MIDDLEWARE.insert(2, 'whitenoise.middleware.WhiteNoiseMiddleware')  # noqa: F405

STATIC_ROOT = BASE_DIR / 'staticfiles'  # noqa: F405
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
