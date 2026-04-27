from pathlib import Path
from decouple import config, Csv
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'csp',
    'manga.apps.MangaConfig',
    'accounts.apps.AccountsConfig',
]
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',                    
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'csp.middleware.CSPMiddleware',                                             
]
ROOT_URLCONF = 'scrollix.urls'
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]
WSGI_APPLICATION = 'scrollix.wsgi.application'
DATABASES = {
    'default': dj_database_url.config(
        default=config('DATABASE_URL', default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}"),
        conn_max_age=0,
        conn_health_checks=True,
    )
}
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = (
    'django.contrib.staticfiles.storage.StaticFilesStorage'
    if DEBUG else
    'whitenoise.storage.CompressedManifestStaticFilesStorage'
)
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'
ADMIN_URL = config('ADMIN_URL', default='scrollix-admin/')
USE_IMAGE_PROXY = config('USE_IMAGE_PROXY', default=False, cast=bool)
MANGADEX_API_BASE = config('MANGADEX_API_BASE', default='')
MANGADEX_API_CONNECT_TIMEOUT = config('MANGADEX_API_CONNECT_TIMEOUT', default=3.05, cast=float)
MANGADEX_API_READ_TIMEOUT = config('MANGADEX_API_READ_TIMEOUT', default=8.0, cast=float)
MANGADEX_HTTP_POOL_CONNECTIONS = config('MANGADEX_HTTP_POOL_CONNECTIONS', default=10, cast=int)
MANGADEX_HTTP_POOL_MAXSIZE = config('MANGADEX_HTTP_POOL_MAXSIZE', default=20, cast=int)
MANGADEX_API_MAX_RETRIES = config('MANGADEX_API_MAX_RETRIES', default=2, cast=int)
MANGADEX_API_BACKOFF_FACTOR = config('MANGADEX_API_BACKOFF_FACTOR', default=0.3, cast=float)
CACHE_TTL_MANGA = config('CACHE_TTL_MANGA', default=86400, cast=int)              
CACHE_TTL_CHAPTERS = config('CACHE_TTL_CHAPTERS', default=3600, cast=int)          
CONTENT_SECURITY_POLICY = {
    "DIRECTIVES": {
        "default-src": ["'self'"],
        "img-src": [
            "'self'",
            "data:",
            "https://uploads.mangadex.org",
            "https://*.mangadex.network",
            "https://*.mangadex.org",
        ],
        "style-src": [
            "'self'",
            "'unsafe-inline'",
            "https://fonts.googleapis.com",
        ],
        "font-src": [
            "'self'",
            "https://fonts.gstatic.com",
        ],
        "script-src": ["'self'"],
        "connect-src": [
            "'self'",
            "https://api.mangadex.org",
        ],
        "frame-ancestors": ["'none'"],
    }
}
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_HTTPONLY = True
CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', default='https://*.railway.app', cast=Csv())
CSRF_FAILURE_VIEW = 'scrollix.views.csrf_failure'
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'scrollix_cache',
        'TIMEOUT': CACHE_TTL_MANGA,
        'OPTIONS': {
            'MAX_ENTRIES': 2000,
        },
    }
}
