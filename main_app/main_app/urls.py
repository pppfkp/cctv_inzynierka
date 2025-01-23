# urls.py
from django.contrib import admin
from django.urls import path
from face_recognition.views import extract_embedding_view, FindClosestEmbeddingView
from management.views import camera_streams_view, hard_reset_all_containers_view, hard_restart_container_view, save_boundary_points, list_containers, soft_reset_all_containers_view, soft_restart_container_view, start_all_containers_view, start_detection_containers, restart_containers, stop_all_containers_view
from stats.views import DetectionSearchView
from django.conf import settings
from django.conf.urls.static import static
from management.views import home, containers_status_view, start_container_view, stop_container_view

urlpatterns = [
    path('containers/status/', containers_status_view, name='containers_status'),
    path('start-container/', start_container_view, name='start_container'),
    path('stop-container/', stop_container_view, name='stop_container'),
    path('soft-restart-container/', soft_restart_container_view, name='soft_restart_container'),
    path('hard-restart-container/', hard_restart_container_view, name='hard_restart_container'),
    path('soft-reset-all/', soft_reset_all_containers_view, name='soft_reset_all_containers'),
    path('hard-reset-all/', hard_reset_all_containers_view, name='hard_reset_all_containers'),
    path('start-all-containers/', start_all_containers_view, name='start_all_containers'),
    path('stop-all-containers/', stop_all_containers_view, name='stop_all_containers'),
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