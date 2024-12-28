"""
URL configuration for main_app project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from face_recognition.views import extract_embedding_view, FindClosestEmbeddingView
from management.views import capture_camera_frame_for_boundaries_edit, save_boundary_points
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('face_recognition/extract_embedding/', extract_embedding_view, name='extract-embedding-view'),
    path('face_recognition/api/recognize/',FindClosestEmbeddingView.as_view()),
    path('camera/<int:camera_id>/edit-boundaries/', capture_camera_frame_for_boundaries_edit, name='edit_boundaries'),
    path('save-boundary/<int:boundary_id>/', save_boundary_points, name='save_boundary'),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)