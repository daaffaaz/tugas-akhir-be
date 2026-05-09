from .base import *  # noqa: F403, F401

DEBUG = False

# Supabase transaction pooler + Vercel serverless: never persist connections
# between requests — each request gets a fresh connection from the pool.
DATABASES['default']['CONN_MAX_AGE'] = 0  # noqa: F405

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='', cast=Csv()) + [  # noqa: F405
    '.vercel.app',
    'ta-be-persona-learn.vercel.app',
]


# Browser origins allowed to call this API (OAuth / credentialed fetch from local Next.js hits prod API).
_cors_fallback = (
    'https://ta-persona-learn.vercel.app',
    'https://ta-be-persona-learn.vercel.app',
    'http://localhost:3000',
    'http://127.0.0.1:3000',
)
_env_cors = config('CORS_ALLOWED_ORIGINS', default='', cast=Csv())
CORS_ALLOWED_ORIGINS = list(dict.fromkeys(list(_cors_fallback) + _env_cors))
CORS_ALLOW_ALL_ORIGINS = False

_csrf_fallback = (
    'https://ta-persona-learn.vercel.app',
    'http://localhost:3000',
    'http://127.0.0.1:3000',
)
_env_csrf = config('CSRF_TRUSTED_ORIGINS', default='', cast=Csv())
CSRF_TRUSTED_ORIGINS = list(dict.fromkeys(list(_csrf_fallback) + _env_csrf))

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
