from django.urls import path
from . import views

urlpatterns = [
    path('', views.upload_video, name='upload_video'),
    path('media-select/', views.media_select, name='media_select'),
]
