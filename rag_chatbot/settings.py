"""
Django settings for rag_chatbot project.
This file contains all the configuration variables for the Django application,
including database connections, installed apps, middleware, and security settings.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
# BASE_DIR is the absolute path to the folder containing manage.py.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from a .env file into the system's environment variables.
# This prevents hardcoding sensitive secrets (like API keys) in the source code.
load_dotenv(BASE_DIR / ".env")

# SECURITY WARNING: keep the secret key used in production secret!
# Django uses this key for cryptographic signing (like session cookies).
# [PRODUCTION SETUP]: Load SECRET_KEY securely from the .env file.
SECRET_KEY = os.environ.get("SECRET_KEY", "django-insecure-rag-chatbot-dev-key-change-in-production")

# SECURITY WARNING: don't run with debug turned on in production!
# If DEBUG is True, detailed stack traces are shown on errors (which is a huge security risk in prod).
# [PRODUCTION SETUP]: Determine DEBUG mode via .env file to prevent exposing error pages.
DEBUG = os.environ.get("DEBUG", "False").lower() in ["true", "1", "yes"]

# A list of strings representing the host/domain names that this Django site can serve.
# [PRODUCTION SETUP]: Load allowed hostnames dynamically from the .env file.
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "*").split(",")

# Application definition
# These are the apps that make up this Django project.
INSTALLED_APPS = [
    # Built-in Django apps
    "django.contrib.admin",
    "django.contrib.auth",          # Core authentication framework
    "django.contrib.contenttypes",
    "django.contrib.sessions",      # Handles user sessions
    "django.contrib.messages",      # Handles flash messages
    "django.contrib.staticfiles",   # Manages static files (CSS, JS, images)
    
    # Custom apps
    "chat",                         # Our RAG Chat application
]

# Middleware sits between requests and views, and between views and responses.
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # WhiteNoise is used to serve static files directly from Django in production (e.g. on Render)
    # [PRODUCTION SETUP]: Whitenoise middleware must be placed right after SecurityMiddleware to serve static files efficiently.
    "whitenoise.middleware.WhiteNoiseMiddleware",
    
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",                # Protects against Cross-Site Request Forgery
    "django.contrib.auth.middleware.AuthenticationMiddleware",  # Populates request.user
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# Tells Django where to look first for URL routing.
ROOT_URLCONF = "rag_chatbot.urls"

# Configures how Django finds and renders HTML templates.
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True, # Look inside each app's 'templates' folder automatically.
        "OPTIONS": {
            "context_processors": [
                # Context processors make certain variables available in all templates automatically.
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# The WSGI application object used by production web servers (like Gunicorn).
WSGI_APPLICATION = "rag_chatbot.wsgi.application"

# Database Configuration
# We are using SQLite for simplicity. Since ChromaDB handles the heavy vector data,
# SQLite is perfectly fine for just storing users and sessions.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# Password validation policies (omitted for simplicity in this project)
AUTH_PASSWORD_VALIDATORS = []

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images) settings
STATIC_URL = "static/"
# STATIC_ROOT is where all static files are copied to when running `manage.py collectstatic`.
# [PRODUCTION SETUP]: Define STATIC_ROOT where whitenoise/Django collects and serves all static assets during production.
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = []

# Media files are files uploaded by users (e.g. the PDFs).
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Session settings
SESSION_ENGINE = "django.contrib.sessions.backends.db" # Store sessions in the database
SESSION_COOKIE_AGE = 86400  # Sessions expire after 24 hours

# Limits the maximum size of uploaded files to 50 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024  
DATA_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024  

# Custom setting: Where ChromaDB should save its vector databases on disk.
CHROMA_DB_DIR = BASE_DIR / "chroma_stores"

# Default Groq API key (read from environment, but can be overridden by users in the UI).
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

# Hugging Face API token for cloud embeddings
HF_TOKEN = os.environ.get("HF_TOKEN", "")

# Authentication redirection settings
LOGIN_URL = "/auth/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/auth/login/"
