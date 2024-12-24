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
from face_recognition.views import FaceEmbeddingCreateView, FaceEmbeddingDetailView, UserEmbeddingsListView, extract_embedding_view, FindClosestEmbeddingView
from django.conf import settings
from django.conf.urls.static import static

from management.views import login_view, logout_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('face_recognition/extract_embedding/', extract_embedding_view, name='extract-embedding-view'),
    path('face_recognition/api/recognize/',FindClosestEmbeddingView.as_view()),
    path('users/<int:user_id>/embeddings/', UserEmbeddingsListView.as_view(), name='user-embeddings'),
    path('users/<int:user_id>/embeddings/add/', FaceEmbeddingCreateView.as_view(), name='add-embedding'),
    path('embeddings/<int:pk>/', FaceEmbeddingDetailView.as_view(), name='embedding-detail'),
    path('api/login/', login_view, name='login'),
    path('api/logout/', logout_view, name='logout'),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)