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
from .utils import start_detection_containers_logic, restart_containers_logic, stop_container_logic

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
    server_host = request.get_host().split(':')[0]
    CameraContainer = apps.get_model('management', 'CameraContainer')
    # Fetch all camera containers
    containers = CameraContainer.objects.all()
    
    # Prepare video feed URLs
    streams = [
        {
            "camera_id": container.camera.id,
            "video_feed_url": f"http://{server_host}:{container.port}/video_feed"
        }
        for container in containers
    ]
    
    # Render the template with streams data
    return render(request, 'camera_streams.html', {'streams': streams})