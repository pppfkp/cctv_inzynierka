import base64
import json
import logging
import os
import socket
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
import cv2
from django.views.decorators.csrf import csrf_exempt
import docker
from django.apps import apps
from django.conf import settings
from .forms import SettingForm
from .utils import hard_restart_container_logic, restart_all_containers_logic, soft_restart_container_logic, start_all_containers_logic, stop_container_logic, start_container_logic, stop_all_containers_logic
from django.views.decorators.http import require_POST
from django.urls import reverse
from .forms import CameraForm
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.contrib.admin.views.decorators import staff_member_required

@staff_member_required(login_url='admin:login')    
def home(request):
    return render(request, 'custom_base.html')

# camera streams

@staff_member_required(login_url='admin:login')    
def camera_streams_view(request):
    server_host = request.get_host().split(':')[0] # Get the server asddresss relative to the client
    CameraContainer = apps.get_model('management', 'CameraContainer')

    # Fetch all camera containers
    containers = CameraContainer.objects.all()
    
    # Prepare video feed URLs
    streams = [
        {
            "camera_name": container.camera.name,
            "video_feed_url": f"http://{server_host}:{container.port}/video_feed"
        }
        for container in containers
    ]
    
    # Render the template with streams data
    return render(request, 'camera_streams.html', {'streams': streams})

@staff_member_required(login_url='admin:login')    
def camera_streams_raw_view(request):
    server_host = request.get_host().split(':')[0] # Get the server asddresss relative to the client
    CameraContainer = apps.get_model('management', 'CameraContainer')

    # Fetch all camera containers
    containers = CameraContainer.objects.all()
    
    # Prepare video feed URLs
    streams = [
        {
            "camera_id": container.camera.id,
            "camera_name": container.camera.name,
            "video_feed_url": f"http://{server_host}:{container.port}/video_feed_raw"
        }
        for container in containers
    ]
    
    # Render the template with streams data
    return render(request, 'camera_streams_raw.html', {'streams': streams})

# camera containers

@staff_member_required(login_url='admin:login')    
def containers_status_view(request):
    Setting = apps.get_model('management', 'Setting')
    CameraContainer = apps.get_model('management', 'CameraContainer')

    # Fetch only the needed settings once and store them as a dictionary
    setting_dict = {setting.key: setting.value for setting in Setting.objects.all()}
    
    try:
        # Initialize Docker client
        client = docker.DockerClient(
            base_url=setting_dict.get("dockerClientAddress", 'tcp://host.docker.internal:2375')
        )
        
        # Query all CameraContainer objects from the database
        camera_containers = CameraContainer.objects.select_related('camera').all()
        
        container_status_data = []
        
        for camera_container in camera_containers:
            try:
                # Fetch container details using Docker client
                container = client.containers.get(camera_container.container_id)
                
                container_status_data.append({
                    'camera_id': camera_container.camera.id,
                    'camera_name': camera_container.camera.name,
                    'container_id': camera_container.container_id,
                    'port': camera_container.port,
                    'last_started': camera_container.last_started,
                    'status': container.status
                })
            except docker.errors.NotFound:
                container_status_data.append({
                    'camera_id': camera_container.camera.id,
                    'camera_name': camera_container.camera.name,
                    'container_id': camera_container.container_id,
                    'port': camera_container.port,
                    'last_started': camera_container.last_started,
                    'status': 'not found'
                })
        
        return render(request, 'containers_status.html', {'camera_containers': container_status_data})
        
    except docker.errors.DockerException as e:
        return render(request, 'container_status.html', {
            'error': f"Error connecting to Docker: {e}",
            'camera_containers': []
        })
    
@staff_member_required(login_url='admin:login')    
@csrf_exempt
@require_POST
def start_container_view(request):
    """
    Starts a container for a given camera ID via POST request.
    """
    try:
        # Parse the JSON body
        data = json.loads(request.body)
        camera_id = data.get('camera_id')

        if not camera_id:
            return JsonResponse({'error': 'Camera ID not provided'}, status=400)

        result = start_container_logic(camera_id)
        if 'error' in result:
            return JsonResponse(result, status=500)

        return JsonResponse(result)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    
@staff_member_required(login_url='admin:login')    
@csrf_exempt
@require_POST
def stop_container_view(request):
    """
    Stops a container for a given camera ID via POST request.
    """
    try:
        # Parse the JSON body
        data = json.loads(request.body)
        camera_id = data.get('camera_id')

        if not camera_id:
            return JsonResponse({'error': 'Camera ID not provided'}, status=400)

        result = stop_container_logic(camera_id)
        if 'error' in result:
            return JsonResponse(result, status=500)

        return JsonResponse(result)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    
@staff_member_required(login_url='admin:login')    
@csrf_exempt
@require_POST
def soft_restart_container_view(request):
    """
    Soft restarts a container for a given camera ID via POST request.
    """
    try:
        # Parse the JSON body
        data = json.loads(request.body)
        camera_id = data.get('camera_id')

        if not camera_id:
            return JsonResponse({'error': 'Camera ID not provided'}, status=400)

        result = soft_restart_container_logic(camera_id)
        if 'error' in result:
            return JsonResponse(result, status=500)

        return JsonResponse(result)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    
@staff_member_required(login_url='admin:login')    
@csrf_exempt
@require_POST
def hard_restart_container_view(request):
    """
    Hard restarts a container for a given camera ID via POST request.
    """
    try:
        # Parse the JSON body
        data = json.loads(request.body)
        camera_id = data.get('camera_id')

        if not camera_id:
            return JsonResponse({'error': 'Camera ID not provided'}, status=400)

        result = hard_restart_container_logic(camera_id)
        if 'error' in result:
            return JsonResponse(result, status=500)

        return JsonResponse(result)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@staff_member_required(login_url='admin:login')    
@csrf_exempt
@require_POST
def soft_reset_all_containers_view(request):
    try:
        result = restart_all_containers_logic(hard_restart=False)
        if 'error' in result:
            return JsonResponse(result, status=500)
        return JsonResponse({'message': 'All containers soft restarted successfully.'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@staff_member_required(login_url='admin:login')    
@csrf_exempt
@require_POST
def hard_reset_all_containers_view(request):
    try:
        result = restart_all_containers_logic(hard_restart=True)
        if 'error' in result:
            return JsonResponse(result, status=500)
        return JsonResponse({'message': 'All containers hard restarted successfully.'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@staff_member_required(login_url='admin:login')    
@csrf_exempt
@require_POST
def start_all_containers_view(request):
    """
    View to start all existing containers that are not running.
    """
    try:
        result = start_all_containers_logic()
        if 'error' in result:
            return JsonResponse(result, status=500)
        return JsonResponse({'message': 'All containers started successfully.'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@staff_member_required(login_url='admin:login')    
@csrf_exempt
@require_POST
def stop_all_containers_view(request):
    """
    View to stop all running containers.
    """
    try:
        result = stop_all_containers_logic()
        if 'error' in result:
            return JsonResponse(result, status=500)
        return JsonResponse({'message': 'All containers stopped successfully.'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# settings

@staff_member_required(login_url='admin:login')    
def settings_view(request):
    Setting = apps.get_model('management', 'Setting')
    settings = Setting.objects.all()
    return render(request, 'settings.html', {'settings': settings})

@staff_member_required(login_url='admin:login')    
@csrf_exempt
@require_POST
def update_setting(request, setting_id):
    Setting = apps.get_model('management', 'Setting')
    setting = Setting.objects.get(id=setting_id)
    form = SettingForm(request.POST, instance=setting)
    
    if form.is_valid():
        form.save()
        return JsonResponse({
            'status': 'success', 
            'message': 'Setting updated successfully',
            'value': form.cleaned_data['value']
        })
    else:
        return JsonResponse({
            'status': 'error', 
            'message': form.errors['value'][0]
        }, status=400)

@staff_member_required(login_url='admin:login')    
@csrf_exempt
@require_POST
def reset_all_settings(request):
    try:
        Setting = apps.get_model('management', 'Setting')
        # Reset all settings to their default values
        settings = Setting.objects.all()
        for setting in settings:
            setting.reset_to_default()
        
        return JsonResponse({
            'status': 'success',
            'message': 'All settings reset to default values'
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)
    
#  cameras setup

@staff_member_required(login_url='admin:login')    
def cameras_setup_view(request):
    Camera = apps.get_model('management', 'Camera')
    cameras = Camera.objects.all()
    return render(request, 'cameras_setup.html', {'cameras': cameras})

@staff_member_required(login_url='admin:login')    
def add_camera_view(request):
    if request.method == 'POST':
        form = CameraForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('cameras_setup')
    else:
        form = CameraForm()
    return render(request, 'camera_add.html', {'form': form})

@staff_member_required(login_url='admin:login')    
def edit_camera_view(request, pk):
    Camera = apps.get_model('management', 'Camera')
    camera = get_object_or_404(Camera, pk=pk)
    if request.method == 'POST':
        form = CameraForm(request.POST, request.FILES, instance=camera)
        if form.is_valid():
            form.save()
            return redirect('cameras_setup')
    else:
        form = CameraForm(instance=camera)
    return render(request, 'camera_edit.html', {'form': form, 'camera': camera})

@staff_member_required(login_url='admin:login')    
def delete_camera_view(request, pk):
    Camera = apps.get_model('management', 'Camera')
    camera = get_object_or_404(Camera, pk=pk)
    if request.method == 'POST':
        camera.delete()
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})

# users management

@staff_member_required(login_url='admin:login')    
def users_list_view(request):
    User = apps.get_model('auth', 'User')
    users = User.objects.filter(is_superuser=False)
    
    return render(request, 'user_list.html', {'users': users})

@staff_member_required(login_url='admin:login')    
def edit_user_view(request, user_id):
    User = apps.get_model('auth', 'User')
    FaceEmbedding = apps.get_model('face_recognition', 'FaceEmbedding')
    user = get_object_or_404(User, id=user_id, is_superuser=False)
    
    
    if request.method == 'POST':
        try:
            # Update basic user info
            user.username = request.POST.get('username')
            user.first_name = request.POST.get('first_name')
            user.last_name = request.POST.get('last_name')
            user.email = request.POST.get('email')

            user.save()
            
            # Handle new face embedding upload
            new_embedding_file = request.FILES.get('new_embedding')
            if new_embedding_file:
                # Create and save new face embedding
                new_embedding = FaceEmbedding(
                    user=user,
                    photo=new_embedding_file,
                    # Assuming you'll generate embedding later via signal or separate process
                )
                new_embedding.save()
            
            return redirect('users_list')
        
        except Exception as e:
            return render(request, 'edit_user.html', {
                'user': user
            })
    
    return render(request, 'edit_user.html', {
        'user': user
    })

@staff_member_required(login_url='admin:login')    
@require_POST
def delete_user_view(request, user_id):
    User = apps.get_model('auth', 'User')
    
    try:
        user = get_object_or_404(User, id=user_id, is_superuser=False)
        user.delete()
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    
# face embeddings

@staff_member_required(login_url='admin:login')    
@require_POST
@csrf_exempt  # Only use this if you're not using CSRF token in your AJAX request
def delete_face_embedding_view(request, embedding_id):
    FaceEmbedding = apps.get_model('face_recognition', 'FaceEmbedding')
    
    try:
        # Fetch the embedding object or return 404 if not found
        embedding = get_object_or_404(FaceEmbedding, id=embedding_id)
        
        # Delete the photo file from storage if it exists
        if embedding.photo:
            try:
                default_storage.delete(embedding.photo.path)
            except Exception as file_error:
                # Log the file deletion error but continue to delete the database record
                print(f"Error deleting file: {file_error}")
        
        # Delete the embedding record
        embedding.delete()
        
        # Return success response
        return JsonResponse({'status': 'success'})
    
    except Exception as e:
        # Log the error for debugging
        print(f"Error deleting embedding: {e}")
        # Return error response
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    

@staff_member_required(login_url='admin:login')    
@require_POST
def add_face_embedding_view(request, user_id):
    FaceEmbedding = apps.get_model('face_recognition', 'FaceEmbedding')
    User = apps.get_model('auth', 'User')
    
    try:
        user = User.objects.get(id=user_id)
        
        # Handle multiple files upload
        if 'new_embeddings' in request.FILES:
            files = request.FILES.getlist('new_embeddings')
            for file in files:
                embedding = FaceEmbedding(user=user, photo=file)
                embedding.save()
        # Handle single file upload (from camera or single file)
        elif 'new_embedding' in request.FILES:
            file = request.FILES['new_embedding']
            embedding = FaceEmbedding(user=user, photo=file)
            embedding.save()
        else:
            return JsonResponse({'status': 'error', 'message': 'No files uploaded'}, status=400)
        
        return JsonResponse({
            'status': 'success',
            'message': 'Embedding(s) added successfully'
        })
    
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    
@staff_member_required(login_url='admin:login')    
def add_user_view(request):
    """Handles adding a new user."""
    User = apps.get_model('auth', 'User')
    if request.method == 'GET':
        return render(request, 'user_add.html')

    elif request.method == 'POST':
        # Extract data from the POST request
        username = request.POST.get('username')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')

        # Validate input
        if not username or not email:
            return JsonResponse({'status': 'error', 'message': 'Missing required fields.'}, status=400)

        if User.objects.filter(username=username).exists():
            return JsonResponse({'status': 'error', 'message': 'Username already exists.'}, status=400)

        try:
            # Create the new user
            user = User.objects.create(
                username=username,
                first_name=first_name,
                last_name=last_name,
                email=email,
            )

            user.save()  # Save the user to the database

            # Return success response
            return JsonResponse({'status': 'success', 'message': 'User added successfully.'})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    else:
        # Handle invalid HTTP methods
        return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)