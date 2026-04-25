# Django Deployment Configuration
# Add this to your settings.py for production

import os
from pathlib import Path

# ============================================
# SECURITY SETTINGS FOR PRODUCTION
# ============================================

# IMPORTANT: Change these for your production environment
# Set DEBUG to False in production
DEBUG = os.getenv('DEBUG', 'False') == 'True'

# Replace with your domain name(s)
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# Generate a new SECRET_KEY and keep it secret!
# Keep the same SECRET_KEY across all your production servers
SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-change-this-in-production')

# ============================================
# HTTPS & SECURITY
# ============================================

# Enable HTTPS in production
SECURE_SSL_REDIRECT = os.getenv('SECURE_SSL_REDIRECT', 'False') == 'True'

# HSTS (HTTP Strict Transport Security)
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Cookie security
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True

# X-Frame-Options (prevents clickjacking)
X_FRAME_OPTIONS = 'DENY'

# ============================================
# DATABASE CONFIGURATION
# ============================================

# Use PostgreSQL in production (recommended)
# Install: pip install psycopg2-binary
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'tahfeed_db'),
        'USER': os.getenv('DB_USER', 'tahfeed_user'),
        'PASSWORD': os.getenv('DB_PASSWORD', 'your-db-password'),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
        'CONN_MAX_AGE': 600,  # Connection pooling
    }
}

# ============================================
# STATIC & MEDIA FILES
# ============================================

# Ensure STATIC_URL is absolute on production
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Media files for uploads
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# ============================================
# LOGGING
# ============================================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs/django_errors.log'),
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}

# ============================================
# EMAIL CONFIGURATION
# ============================================

# For sending notifications, password resets, etc.
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = os.getenv('EMAIL_PORT', 587)
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', 'your-email@gmail.com')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', 'your-app-password')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'noreply@tahfeed.com')

# ============================================
# CACHING
# ============================================

# Use Redis for caching (optional but recommended)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/1'),
    }
}

# ============================================
# ROOT URL AND SETTINGS
# ============================================

ROOT_URLCONF = 'myproject.urls'
WSGI_APPLICATION = 'myproject.wsgi.application'

# Allowed file uploads
MAX_UPLOAD_SIZE = 5242880  # 5MB
