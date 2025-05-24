import os
from pathlib import Path

# Thư mục gốc dự án
BASE_DIR = Path(__file__).resolve().parent.parent

# SECRET_KEY - bạn nên tạo riêng cho dự án của bạn
SECRET_KEY = 'django-insecure-3p1o^&$k#f@!m0v-8#z!9u_!x@7v5e^c^1q4z=hj)a@2r_#y*6'

# DEBUG True cho môi trường dev
DEBUG = True

ALLOWED_HOSTS = []

# Các app được cài đặt (đảm bảo có admin, auth, sessions, messages, staticfiles)
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Các app khác của bạn...
]

# Middleware chuẩn cho Django, đúng thứ tự
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',            # bắt buộc
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',         # bắt buộc
    'django.contrib.messages.middleware.MessageMiddleware',            # bắt buộc
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'HelmetProject.urls'

# Cấu hình Template Engine cho admin và các template khác
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'main' / 'templates'],  # ← dùng đường dẫn tương đối
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

WSGI_APPLICATION = 'HelmetProject.wsgi.application'

# Database ví dụ SQLite (thay đổi nếu bạn dùng DB khác)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Các cấu hình bảo mật (mặc định tạm)
AUTH_PASSWORD_VALIDATORS = []

# Ngôn ngữ và múi giờ
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# URL cho static files
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')

# Cấu hình media files (ảnh, file upload)
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

MEDIA_BOUNDING_BOX_URL = '/media-bounding-box/'
MEDIA_BOUNDING_BOX_ROOT = os.path.join(BASE_DIR, 'media-bounding-box')

# Kích thước file upload tối đa (nếu cần)
# DATA_UPLOAD_MAX_MEMORY_SIZE = 2621440  # 2.5 MB (ví dụ)

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
