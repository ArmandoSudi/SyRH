"""Django settings for the SyRH backend (SIRH de l'ARPTC).

Configuration comes from environment variables, loaded from backend/.env in
development. See backend/.env.example for the expected keys.
"""

import sys
import tempfile
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    DJANGO_ALLOWED_HOSTS=(list, []),
)
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env("DJANGO_DEBUG")
ALLOWED_HOSTS = env("DJANGO_ALLOWED_HOSTS")
# Cookies travel over HTTPS only, except in development. A test server on the
# local network without HTTPS sets DJANGO_SECURE_COOKIES=False (see docs/deployment.md).
SECURE_COOKIES = env.bool("DJANGO_SECURE_COOKIES", default=not DEBUG)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    "rest_framework",
    "apps.accounts",
    "apps.core",
    "apps.audit",
    "apps.referentiels",
    "apps.agents",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
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

# PostgreSQL only: DATABASE_URL=postgres://user:password@host:port/name
DATABASES = {"default": env.db("DATABASE_URL")}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "accounts.User"

# Session cookie + CSRF, no token in the browser. The session cookie is hidden
# from JavaScript; the CSRF cookie is readable so the SPA can echo it back in
# the X-CSRFToken header. Both travel over HTTPS only (SECURE_COOKIES).
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = SECURE_COOKIES
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = SECURE_COOKIES

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# French first: no LocaleMiddleware, so every message (API validation errors
# included) is in French whatever language the browser asks for.
LANGUAGE_CODE = "fr"
TIME_ZONE = "Africa/Kinshasa"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Scanned supporting documents (document storage D7 to D9, D12). Every file is
# encrypted with Fernet before it reaches the disk, under a directory no URL
# serves; only the authenticated documents endpoints read it back. The first key
# encrypts, all of them decrypt (key rotation); system check core.E002 refuses to
# start without a valid one. A test run gets a throwaway key and directory.
TESTING = sys.argv[1:2] == ["test"]
SYRH_DOCUMENT_KEYS = env.list("SYRH_DOCUMENT_KEYS", default=[])
SYRH_DOCUMENT_ROOT = Path(env("SYRH_DOCUMENT_ROOT", default=str(BASE_DIR / "var" / "documents")))
if TESTING:
    from cryptography.fernet import Fernet

    SYRH_DOCUMENT_KEYS = [Fernet.generate_key().decode()]
    SYRH_DOCUMENT_ROOT = Path(tempfile.mkdtemp(prefix="syrh-documents-"))

# No request body above 50 Mo, the highest value of the size limit parameter (D12).
DATA_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024

MAILERS = {
    "default": {
        "BACKEND": "django.core.mail.backends.console.EmailBackend",
    },
}

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "apps.accounts.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}
