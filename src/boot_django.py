# File sets up the django environment, used by other scripts that need to
# execute in Django land
import sys
from pathlib import Path
import django
from django.conf import settings

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

def boot_django():
    settings.configure(
        BASE_DIR=BASE_DIR,
        DEBUG=True,
        DATABASES={
            "default":{
                "ENGINE":"django.db.backends.sqlite3",
                "NAME": BASE_DIR / "db.sqlite3",
            }
        },
        INSTALLED_APPS=(
            "django.contrib.admin",
            "django.contrib.auth",
            "django.contrib.contenttypes",
            "django.contrib.sessions",
            "django.contrib.messages",
            "logq",
        ),
        MIDDLEWARE=[
            "django.middleware.security.SecurityMiddleware",
            "django.contrib.sessions.middleware.SessionMiddleware",
            "django.middleware.common.CommonMiddleware",
            "django.middleware.csrf.CsrfViewMiddleware",
            "django.contrib.auth.middleware.AuthenticationMiddleware",
            "django.contrib.messages.middleware.MessageMiddleware",
            "django.middleware.clickjacking.XFrameOptionsMiddleware",
        ],
        TEMPLATES=[
            {
                "BACKEND": "django.template.backends.django.DjangoTemplates",
                "DIRS": [],
                "APP_DIRS": True,
                "OPTIONS": {
                    "context_processors": [
                        "django.template.context_processors.debug",
                        "django.template.context_processors.request",
                        "django.contrib.auth.context_processors.auth",
                        "django.contrib.messages.context_processors.messages",
                    ],
                },
            },
        ],
        ROOT_URLCONF="logq.urls",
        TIME_ZONE="UTC",
        USE_TZ=True,
        SECRET_KEY="django-insecure-test-key-for-testing-only",
        ASYNC_LOGGING_CONFIG={
            "MAX_QUEUE_SIZE": 1000,
            "FLUSH_INTERVAL": 0.1,
            "AUTO_CLEANUP_INTERVAL": 1,  # 1 second for testing
            "CLEANUP_POLICIES": [
                {"days": 30, "level": "INFO", "enabled": True},
                {"days": 7, "level": "WARNING", "enabled": True},
                {"days": 1, "level": "ERROR", "enabled": True},
                {"days": 0, "level": "CRITICAL", "enabled": True},
            ],
            "DEFAULT_HANDLERS": []
        }

    )
    django.setup()