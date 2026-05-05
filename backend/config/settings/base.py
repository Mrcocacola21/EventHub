import os
from datetime import timedelta
from pathlib import Path

from celery.schedules import crontab
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent

load_dotenv(BASE_DIR / ".env")


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: list[str] | None = None) -> list[str]:
    value = os.getenv(name)
    if not value:
        return default or []
    return [item.strip() for item in value.split(",") if item.strip()]


SECRET_KEY = os.getenv("SECRET_KEY", "change-me")
DEBUG = env_bool("DEBUG", False)
ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", ["localhost", "127.0.0.1"])

INSTALLED_APPS = [
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "channels",
    "rest_framework",
    "rest_framework_simplejwt",
    "drf_spectacular",
    "django_filters",
    "corsheaders",
    "django_celery_beat",
    "apps.users.apps.UsersConfig",
    "apps.events.apps.EventsConfig",
    "apps.tickets.apps.TicketsConfig",
    "apps.bookings.apps.BookingsConfig",
    "apps.tournaments.apps.TournamentsConfig",
    "apps.reviews.apps.ReviewsConfig",
    "apps.notifications.apps.NotificationsConfig",
    "apps.audit.apps.AuditConfig",
    "apps.common",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "apps.audit.middleware.RequestIDMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "UserAttributeSimilarityValidator"
        ),
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DATABASE_NAME", "eventhub"),
        "USER": os.getenv("DATABASE_USER", "eventhub_user"),
        "PASSWORD": os.getenv("DATABASE_PASSWORD", "eventhub_password"),
        "HOST": os.getenv("DATABASE_HOST", "localhost"),
        "PORT": os.getenv("DATABASE_PORT", "5432"),
    }
}

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "EventHub API",
    "DESCRIPTION": (
        "Production-ready API for events, ticket booking, QR validation, "
        "PDF tickets, tournaments, reviews, notifications and real-time features."
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SCHEMA_PATH_PREFIX": "/api/",
    "TAGS": [
        {"name": "Health", "description": "Service health checks."},
        {"name": "Auth", "description": "JWT registration, login and token refresh."},
        {"name": "Users", "description": "Current user and profile endpoints."},
        {
            "name": "Events",
            "description": "Event categories, event management and public browsing.",
        },
        {"name": "Tickets", "description": "Ticket types and availability."},
        {
            "name": "Bookings",
            "description": (
                "Atomic ticket booking, cancellation, QR validation and PDF download."
            ),
        },
        {
            "name": "Tournaments",
            "description": (
                "Tournament registration, bracket generation and match results."
            ),
        },
        {"name": "Reviews", "description": "Event reviews and rating aggregation."},
        {"name": "Notifications", "description": "Persistent user notifications."},
    ],
    "ENUM_NAME_OVERRIDES": {
        "BookingStatusEnum": "apps.bookings.models.Booking.Status",
        "EventStatusEnum": "apps.events.models.Event.Status",
        "TournamentStatusEnum": "apps.tournaments.models.Tournament.Status",
        "ParticipantStatusEnum": "apps.tournaments.models.Participant.Status",
        "MatchStatusEnum": "apps.tournaments.models.Match.Status",
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "AUTH_HEADER_TYPES": ("Bearer",),
}

CORS_ALLOWED_ORIGINS = env_list(
    "CORS_ALLOWED_ORIGINS",
    ["http://localhost:5173", "http://127.0.0.1:5173"],
)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CACHE_URL = os.getenv("CACHE_URL", os.getenv("REDIS_URL", "redis://localhost:6379/1"))
CHANNEL_REDIS_URL = os.getenv(
    "CHANNEL_REDIS_URL",
    os.getenv("REDIS_URL", "redis://localhost:6379/2"),
)

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": CACHE_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
        "KEY_PREFIX": "eventhub",
    }
}

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [CHANNEL_REDIS_URL],
        },
    },
}

CELERY_BROKER_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60
CELERY_BEAT_SCHEDULE = {
    "expire-pending-bookings": {
        "task": "apps.bookings.tasks.expire_pending_bookings",
        "schedule": crontab(minute="*/5"),
    },
    "send-event-reminders": {
        "task": "apps.events.tasks.send_event_reminders",
        "schedule": crontab(minute=0, hour="*/1"),
    },
    "cleanup-old-notifications": {
        "task": "apps.notifications.tasks.cleanup_old_notifications",
        "schedule": crontab(minute=0, hour=3),
    },
}

EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend",
)
EMAIL_HOST = os.getenv("EMAIL_HOST", "")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
DEFAULT_FROM_EMAIL = os.getenv(
    "DEFAULT_FROM_EMAIL",
    "EventHub <noreply@eventhub.local>",
)

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "users.User"
