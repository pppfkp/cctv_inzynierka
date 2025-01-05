import base64
import json
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
import cv2
from django.views.decorators.csrf import csrf_exempt
from .models import Camera, Boundary, CameraContainer
import docker

@csrf_exempt  # Disable CSRF for simplicity; ensure proper security in production
def save_boundary_points(request, boundary_id):
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
    try:
        client = docker.DockerClient(base_url='tcp://host.docker.internal:2375')
        cameras = Camera.objects.filter(enabled=True)
        base_port = 5000
        
        for i, camera in enumerate(cameras):
            container_port = base_port + i
            
            # Prepare environment variables for each camera
            environment = {
                'CAMERA_LINK': camera.link,
                'CAMERA_ID': str(camera.id),
                'BATCH_SIZE': '100',
                'TRACKING_MODEL': 'yolo11n.pt',
                'FACE_DETECTION_MODEL': 'yolov10n-face.pt',
                'FACE_SIMILARITY_THRESHOLD': '0.7',
                'FACE_DETECTION_THRESHOLD': '0.4',
                'PERSON_DETECTION_THRESHOLD': '0.6',
                'FACE_SIMILARITY_REQUEST_LINK': 'host.docker.internal:8000/face_recognition/api/recognize/',
                'FPS': '10',
                'PGVECTOR_DB_NAME': 'management',
                'PGVECTOR_DB_USER': 'pppfkp',
                'PGVECTOR_DB_PASSWORD': 'pppfkp123$',
                'PGVECTOR_DB_HOST': 'host.docker.internal',
                'PGVECTOR_DB_PORT': '5432'
            }
            
            container_config = {
                'image': 'pppfkp15/flask-ultralytics-gpu:2.0',
                'detach': True,
                'environment': environment,
                'network_mode': 'bridge',
                'ports': {'5000/tcp': ('0.0.0.0', container_port)},
                'device_requests': [
                    docker.types.DeviceRequest(count=-1, capabilities=[['gpu']])
                ]
            }
            
            container = client.containers.run(**container_config)
            
            # Store or update container information
            CameraContainer.objects.update_or_create(
                camera=camera,
                defaults={
                    'container_id': container.id,
                    'port': container_port
                }
            )
            
            
        return JsonResponse({'message': 'Containers started successfully'})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    
def restart_containers(request):
    try:
        client = docker.DockerClient(base_url='tcp://host.docker.internal:2375')
        container_records = CameraContainer.objects.all()
        
        # First clean up any orphaned records
        for container_record in container_records:
            try:
                # Check if camera still exists
                camera_exists = Camera.objects.filter(id=container_record.camera_id).exists()
                if not camera_exists:
                    # If camera doesn't exist, delete the container record
                    try:
                        # Try to stop and remove container if it exists
                        container = client.containers.get(container_record.container_id)
                        container.stop(timeout=10)
                        container.remove()
                    except docker.errors.NotFound:
                        pass  # Container already gone, which is fine
                    container_record.delete()
                    continue

                # Camera exists, proceed with normal container operations
                container = client.containers.get(container_record.container_id)
                container.stop(timeout=10)
                container.remove()
                container_record.delete()
                
            except docker.errors.NotFound:
                # Container not found, just delete the record
                container_record.delete()
            except Exception as e:
                # Log any other errors but continue with other containers
                print(f"Error handling container {container_record.container_id}: {e}")
                # Still delete the record to maintain consistency
                container_record.delete()

        # Start new containers
        return start_detection_containers(request)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def stop_container(request, camera_id):
    try:
        client = docker.DockerClient(base_url='tcp://host.docker.internal:2375')
        container_record = CameraContainer.objects.get(camera_id=camera_id)
        
        try:
            container = client.containers.get(container_record.container_id)
            container.stop(timeout=10)
            container.remove()
            container_record.delete()
            return JsonResponse({'message': f'Container for camera {camera_id} stopped successfully'})
        except docker.errors.NotFound:
            container_record.delete()
            return JsonResponse({'message': 'Container not found but record cleaned up'})
            
    except CameraContainer.DoesNotExist:
        return JsonResponse({'error': 'No container found for this camera'}, status=404)
    except Exception as e:
        # logger.error(f"Error stopping container: {e}")
        return JsonResponse({'error': str(e)}, status=500)