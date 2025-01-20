# urls.py
from django.contrib import admin
from django.urls import path
from face_recognition.views import extract_embedding_view, FindClosestEmbeddingView
from management.views import camera_streams_view, save_boundary_points, list_containers, start_detection_containers, restart_containers
from stats.views import DetectionSearchView
from django.conf import settings
from django.conf.urls.static import static
from management.views import home

urlpatterns = [
    path('', home, name='home'),
    path('admin/', admin.site.urls),
    path('restart_containers/', restart_containers, name='restart_containers'),
    path('face_recognition/extract_embedding/', extract_embedding_view, name='extract-embedding-view'),
    path('face_recognition/api/recognize/', FindClosestEmbeddingView.as_view()),
    path('save-boundary/<int:boundary_id>/', save_boundary_points, name='save_boundary'),
    path('list_containers/', list_containers, name='list_containers'),
    path('start_containers/', start_detection_containers, name='start_detection_containers'),
    path('camera-streams/', camera_streams_view, name='camera_streams'),
    path('detections/search/', DetectionSearchView.as_view(), name='detection_search'),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)