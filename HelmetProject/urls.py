from django.contrib import admin
from django.urls import path
from main import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.upload_video, name='upload_video'),
    path('media-select/', views.media_select, name='media_select')
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
