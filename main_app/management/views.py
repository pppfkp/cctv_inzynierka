import base64
import json
import socket
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
import cv2
from django.views.decorators.csrf import csrf_exempt
import docker
from django.apps import apps
from django.conf import settings
from .utils import hard_restart_container_logic, restart_all_containers_logic, soft_restart_container_logic, start_all_containers_logic, start_container_logic, stop_all_containers_logic
from django.views.decorators.http import require_POST
from .utils import start_detection_containers_logic, restart_containers_logic, stop_container_logic

def home(request):
    return render(request, 'custom_base.html')

@csrf_exempt  # Disable CSRF for simplicity; ensure proper security in production
def save_boundary_points(request, boundary_id):
    Boundary = apps.get_model('management', 'Boundary')
    if request.method == "POST":
        try:
            # Parse the JSON data from the request body
            data = json.loads(request.body)
            points = data.get('points', [])

            if not points or len(points) % 2 != 0:
                return JsonResponse({'error': 'Invalid points data'}, status=400)

            # Update the boundary's polygon field
            boundary = Boundary.objects.get(id=boundary_id)
            boundary.polygon = points  # Save the flattened array
            boundary.save()

            return JsonResponse({'message': 'Boundary points updated successfully'})
        except Boundary.DoesNotExist:
            return JsonResponse({'error': 'Boundary not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=405)

def list_containers(request):
    try:
        # Initialize Docker client
        client = docker.DockerClient(base_url='tcp://host.docker.internal:2375')
        
        # List all containers
        containers = client.containers.list()

        # Collect container names and statuses
        container_data = [{
            'name': container.name,
            'status': container.status
        } for container in containers]
        
        return JsonResponse({'containers': container_data})
    except docker.errors.DockerException as e:
        return JsonResponse({'error': f"Error connecting to Docker: {e}"}, status=500)
    

def start_detection_containers(request):
    """
    Django view to start detection containers.
    """
    try:
        result = start_detection_containers_logic()
        return JsonResponse({'message': result['message']})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def restart_containers(request):
    """
    Django view to restart containers.
    """
    try:
        result = restart_containers_logic()
        return JsonResponse({'message': result['message']})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def stop_container(request, camera_id):
    """
    Django view to stop a container by camera ID.
    """
    try:
        result = stop_container_logic(camera_id=camera_id)
        if 'error' in result:
            return JsonResponse({'error': result['error']}, status=result.get('status', 500))
        return JsonResponse({'message': result['message']})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    
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