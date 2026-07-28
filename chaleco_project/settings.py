"""
Django settings for chaleco_project project.
"""

import os
from pathlib import Path

# 1. RUTAS BASE
BASE_DIR = Path(__file__).resolve().parent.parent


# 2. SEGURIDAD
SECRET_KEY = 'django-insecure-tnmsl9vn90dfu467o5x(!ds75wov$r%0*o)yse-9ke1126hg%_'

DEBUG = True

ALLOWED_HOSTS = ['127.0.0.1', 'localhost', '192.168.1.8', 'chaleco-rojo.onrender.com', '*']


# 3. REGISTRO DE APLICACIONES
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'chaleco_app',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'chaleco_project.urls'


# 4. CONFIGURACIÓN DE TEMPLATES - ✅ CORREGIDO
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],  # ✅ VACÍO - Django busca en cada app automáticamente
        'APP_DIRS': True,  # ✅ CLAVE: Permite que Django encuentre templates en cada app
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

WSGI_APPLICATION = 'chaleco_project.wsgi.application'


# 5. BASE DE DATOS
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# 6. VALIDACIÓN DE CONTRASEÑAS
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


# 7. REGIONALIZACIÓN
LANGUAGE_CODE = 'es-ar'
TIME_ZONE = 'America/Argentina/Cordoba'
USE_I18N = True
USE_TZ = True


# 8. ARCHIVOS ESTÁTICOS Y MULTIMEDIA - ✅ CORREGIDO
STATIC_URL = '/static/'  # ✅ CON BARRA AL FINAL
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'