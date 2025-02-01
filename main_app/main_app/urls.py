# urls.py
from django.contrib import admin
from django.urls import path, include
from face_recognition.views import create_recognition_view, extract_embedding_view, FindClosestEmbeddingView
from management.views import add_camera_view, add_face_embedding_view, camera_streams_raw_view, containers_status_view, delete_camera_view, edit_camera_view, hard_reset_all_containers_view, hard_restart_container_view, soft_reset_all_containers_view, soft_restart_container_view, start_all_containers_view, start_container_view, stop_all_containers_view, stop_container_view
from stats.views import detections_view, entries_list_view, recognize_entry_view, recognize_exit_view
from django.conf import settings
from django.conf.urls.static import static
from management.views import home, camera_streams_view
from management.views import settings_view, update_setting, reset_all_settings
from management.views import cameras_setup_view
from management.views import users_list_view, delete_face_embedding_view, delete_user_view, edit_user_view, add_user_view
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import views as auth_views
from django.contrib.auth.views import LogoutView

def is_management(user):
    return user.is_staff 

# Combine login and group check
def management_required(view_func):
    decorated_view = login_required(user_passes_test(is_management)(view_func))
    return decorated_view

urlpatterns = [
    path('accounts/', include('django.contrib.auth.urls')),
    path('logout/', LogoutView.as_view(next_page='admin:login'), name='logout'),
    path('', management_required(home), name='home'),

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

    # users management
    path('users/', users_list_view, name='users_list'),
    path('users/edit/<int:user_id>/', edit_user_view, name='edit_user'),
    path('users/delete/<int:user_id>/', delete_user_view, name='delete_user'),
    path('users/delete-embedding/<int:embedding_id>/', delete_face_embedding_view, name='delete_face_embedding'),
    path('users/add-embedding/<int:user_id>/', add_face_embedding_view, name='add_face_embedding'),
    path('users/add/', add_user_view, name='add_user'),

    # stats
    path('entries/', entries_list_view, name='entries_list'),
    path('recognition/create/', create_recognition_view, name='create_recognition'),
    path('entry/recognize/', recognize_entry_view, name='recognize_entry'),
    path('exit/recognize/', recognize_exit_view, name='recognize_exit'),
    path('stats/detections/', detections_view, name='detections'),
    
    # face recognition
    path('face_recognition/extract_embedding/', extract_embedding_view, name='extract-embedding-view'),
    path('face_recognition/api/recognize/', FindClosestEmbeddingView.as_view()),

    # other
    path('admin/', admin.site.urls),

]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)