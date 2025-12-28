
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-your-secret-key-here'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = ['*']


# Application definition

INSTALLED_APPS = [
 
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'django.contrib.sitemaps',
    'dev_mode',
    'product',
    'accounts',
    'components',
    'cart',
    'schedule_purchase',
    'address',
    'orders',
    'discount',
    'user_orders',
    'customize',
    'cloudinary',
'cloudinary_storage',
    
  
]

SITE_ID = 1
DEFAULT_DOMAIN = "thinknshop.in"


MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',


]

ROOT_URLCONF =  'sketezo.urls'

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

WSGI_APPLICATION = 'sketezo.wsgi.application'



# # For Development Only
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / "db.sqlite3",
#     }
# }

# Production Only (Render PostgreSQL)
import dj_database_url

import dj_database_url

DATABASES = {
    'default': dj_database_url.config(
        default="postgresql://thinknshop_jdjq_user:gPFMloDQ99kMgGozwvqZMrE5VhDsOs4m@dpg-d4t7m9vdiees73atjfug-a.oregon-postgres.render.com/thinknshop_jdjq",
        conn_max_age=600,
        ssl_require=True,
    )
}






# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Asia/Kolkata'
USE_TZ = True


USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = 'static/'

# STATICFILES_DIRS is where Django looks for static files (e.g. your 'static' folder)
STATICFILES_DIRS = [
    BASE_DIR / 'static'
]

# STATIC_ROOT is where files are collected for production
STATIC_ROOT = BASE_DIR / "staticfiles"

# Using default storage for local development (DEBUG=True) to avoid issues with collectstatic
# The WhiteNoise storage is confusing Django in local dev
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"

STABILITY = 1

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        # Use default storage for local development
         "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
         "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True

EMAIL_HOST_USER = "thinknshopofficial@gmail.com"
EMAIL_HOST_PASSWORD = "cbydnvdqihkyuxmz"  # The App Password (no spaces)
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

# Media files (can stay, Cloudinary will ignore in prod)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Cloudinary credentials
from decouple import config

CLOUDINARY_STORAGE = {
    'CLOUD_NAME': config('CLOUDINARY_CLOUD_NAME'),
    'API_KEY': config('CLOUDINARY_API_KEY'),
    'API_SECRET': config('CLOUDINARY_API_SECRET'),
}




# # Razorpay Credentials For real payments
# for production 
RAZORPAY_KEY_ID = "rzp_live_RrSCite2n9vAim"
RAZORPAY_KEY_SECRET = "80NKumjOqpHSuDk8a4meYg7J"

# For Test - Development only 
# RAZORPAY_KEY_ID = "rzp_test_jJJrl2JogIrKeo"
# RAZORPAY_KEY_SECRET = "oqJBApRaO4rOYdd4cTcUc7m4"


# ==================== LOGGING CONFIGURATION ====================
import os

# Create logs directory
LOGS_DIR = BASE_DIR / 'logs'
if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'zippypost_file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': str(LOGS_DIR / 'zippypost.log'),
            'formatter': 'verbose',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'orders': {
            'handlers': ['zippypost_file', 'console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}