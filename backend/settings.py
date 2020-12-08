"""
Django settings for backend project.
"""

import os

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

STATIC_ROOT = os.environ["STATIC_ROOT"]

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.2/howto/deployment/checklist/

SECRET_KEY = os.environ["SECRET_KEY"]

DEBUG = os.environ.get("DEBUG") == "TRUE"
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG


REST_FRAMEWORK = {
    "TEST_REQUEST_DEFAULT_FORMAT": "json",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.LimitOffsetPagination",
    "PAGE_SIZE": 15,
    "DATE_INPUT_FORMATS": ["iso-8601", r"%m/%d/%Y"],
}

ALLOWED_HOSTS = (
    [os.environ.get("ALLOWED_HOSTS")] if os.environ.get("ALLOWED_HOSTS") else []
)

USE_X_FORWARDED_HOST = os.environ.get("USE_X_FORWARDED_HOST") == "TRUE"

STATICFILES_DIRS = (os.path.join(BASE_DIR, "frontend"),)

MEDIA_ROOT = os.environ["MEDIA_ROOT"]
# media_url needs to match the nginx frontend's config for the internal/x-accel block.
MEDIA_URL = "media/"

WEBPACK_LOADER = {"DEFAULT": {"BUNDLE_DIR_NAME": "bundles/",}}


LOGIN_REDIRECT_URL = "/loginSuccess"

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "webpack_loader",
    "rest_framework",
    "django_q",
    "cleanslate",
    "grades",
    "ujs_search",
]


MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "csp.middleware.CSPMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

CSP_DEFAULT_SRC = ("'self'",)
CSP_STYLE_SRC = (
    "fonts.googleapis.com",
    "'unsafe-inline'",
)
CSP_FONT_SRC = ("fonts.gstatic.com",)
CSP_SCRIPT_SRC = (
    "'self'",
    "'unsafe-inline'",
    "'unsafe-eval'",
)
# CSP_INCLUDE_NONCE_IN=['script-src', 'style-src']


Q_CLUSTER = {
    "name": "DjangORM",
    "workers": 4,
    "timeout": 90,
    "retry": 120,
    "queue_limit": 50,
    "bulk": 10,
    "orm": "default",
}

ROOT_URLCONF = "backend.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": ["templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
            "libraries": {"replace_nonce": "backend.templatetags.replace_nonce",},
        },
    },
]

WSGI_APPLICATION = "backend.wsgi.application"


# Database
CSP_EXCLUDE_URL_PREFIXES = ("/admin",)

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ["PSQL_NAME"],
        "HOST": os.environ["PSQL_HOST"],
        "USER": os.environ["PSQL_USER"],
        "PASSWORD": os.environ["PSQL_PW"],
    },
}

# Password validation
# https://docs.djangoproject.com/en/2.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",},
]


# Internationalization
# https://docs.djangoproject.com/en/2.2/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.2/howto/static-files/

STATIC_URL = "/static/"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"level": "INFO", "class": "logging.StreamHandler",}},
    "loggers": {"": {"handlers": ["console"], "propogate": True, "level": "INFO",}},
}

