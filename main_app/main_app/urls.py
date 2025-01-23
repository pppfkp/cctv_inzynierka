# urls.py
from django.contrib import admin
from django.urls import path
from face_recognition.views import extract_embedding_view, FindClosestEmbeddingView
from management.views import add_camera_view, camera_streams_raw_view, containers_status_view, delete_camera_view, edit_camera_view, hard_reset_all_containers_view, hard_restart_container_view, soft_reset_all_containers_view, soft_restart_container_view, start_all_containers_view, start_container_view, stop_all_containers_view, stop_container_view
from stats.views import DetectionSearchView
from django.conf import settings
from django.conf.urls.static import static
from management.views import home, camera_streams_view
from management.views import save_boundary_points
from management.views import settings_view, update_setting, reset_all_settings
from management.views import cameras_setup_view
urlpatterns = [
    path('', home, name='home'),

    # camera containers
    path('containers/status/', containers_status_view, name='containers_status'),
    path('start-container/', start_container_view, name='start_container'),
    path('stop-container/', stop_container_view, name='stop_container'),
    path('soft-restart-container/', soft_restart_container_view, name='soft_restart_container'),
    path('hard-restart-container/', hard_restart_container_view, name='hard_restart_container'),
    path('soft-reset-all/', soft_reset_all_containers_view, name='soft_reset_all_containers'),
    path('hard-reset-all/', hard_reset_all_containers_view, name='hard_reset_all_containers'),
    path('start-all-containers/', start_all_containers_view, name='start_all_containers'),
    path('stop-all-containers/', stop_all_containers_view, name='stop_all_containers'),

    # settings
    path('settings/', settings_view, name='settings'),
    path('update-setting/<int:setting_id>/', update_setting, name='update_setting'),
    path('reset-all-settings/', reset_all_settings, name='reset_all_settings'),

    # cameras_setup
    path('cameras_setup/', cameras_setup_view, name='cameras_setup'),
    path('add-camera/', add_camera_view, name='add_camera'),
    path('edit-camera/<int:pk>/', edit_camera_view, name='edit_camera'),
    path('delete-camera/<int:pk>/', delete_camera_view, name='delete_camera'),

    # cameras_streaming
    path('camera-streams/', camera_streams_view, name='camera_streams'),
    path('camera-streams-raw/', camera_streams_raw_view, name='camera_streams_raw'),

    #other
    path('admin/', admin.site.urls),
    path('face_recognition/extract_embedding/', extract_embedding_view, name='extract-embedding-view'),
    path('face_recognition/api/recognize/', FindClosestEmbeddingView.as_view()),
    path('save-boundary/<int:boundary_id>/', save_boundary_points, name='save_boundary'),
    
    path('detections/search/', DetectionSearchView.as_view(), name='detection_search'),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)