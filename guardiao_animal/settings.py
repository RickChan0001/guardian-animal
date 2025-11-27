"""
Django settings for guardiao_animal project.

Configurado e otimizado para:
- Templates centralizados em /templates
- Arquivos estáticos em /static
- Uploads de mídia em /media
"""

from pathlib import Path
import os
from decouple import config, Csv
import pymysql
pymysql.install_as_MySQLdb()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY', default='django-insecure-j2e-wp_q5e2jcy7=jgr=hr%%z48*4u&p8+&=sj0%*+*h&g^avy')
DEBUG = config('DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='', cast=Csv())

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'tutores',
    'veterinarios',
    'widget_tweaks',
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

ROOT_URLCONF = 'guardiao_animal.urls'

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

WSGI_APPLICATION = 'guardiao_animal.wsgi.application'

# Configuração do banco de dados via variáveis de ambiente
DB_ENGINE = config('DB_ENGINE', default='django.db.backends.postgresql')
DB_NAME = config('DB_NAME', default='')
DB_USER = config('DB_USER', default='')
DB_PASSWORD = config('DB_PASSWORD', default='')
DB_HOST = config('DB_HOST', default='localhost')
DB_PORT = config('DB_PORT', default='5432')

# Configuração do banco de dados
# Se DB_NAME estiver vazio, usa SQLite (apenas para desenvolvimento local)
if not DB_NAME:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    # Configuração para banco de dados online (PostgreSQL ou MySQL)
    DATABASES = {
        'default': {
            'ENGINE': DB_ENGINE,
            'NAME': DB_NAME,
            'USER': DB_USER,
            'PASSWORD': DB_PASSWORD,
            'HOST': DB_HOST,
            'PORT': DB_PORT,
            'CONN_MAX_AGE': 600,  # Mantém conexões abertas por até 10 minutos
            'OPTIONS': {},
        }
    }
    
    # Opções específicas para PostgreSQL
    if 'postgresql' in DB_ENGINE or 'postgis' in DB_ENGINE:
        DATABASES['default']['OPTIONS'] = {
            'connect_timeout': 10,
            'options': '-c timezone=America/Sao_Paulo',
        }
        # Suporte para SSL se necessário
        if config('DB_SSLMODE', default='', cast=str):
            DATABASES['default']['OPTIONS']['sslmode'] = config('DB_SSLMODE')
    
    # Opções específicas para MySQL
    elif 'mysql' in DB_ENGINE:
        DATABASES['default']['OPTIONS'] = {
            'charset': 'utf8mb4',
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES', time_zone='-03:00'",
            'connect_timeout': 10,
        }
        # Suporte para SSL se necessário
        if config('DB_SSL_CA', default='', cast=str):
            DATABASES['default']['OPTIONS']['ssl'] = {
                'ca': config('DB_SSL_CA'),
            }

AUTH_USER_MODEL = 'tutores.CustomUser'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/tutores/painel/'
LOGOUT_REDIRECT_URL = '/'

LANGUAGE_CODE = 'pt-BR'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
