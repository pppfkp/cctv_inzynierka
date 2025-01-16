import base64
import json
import os
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
import cv2
from django.views.decorators.csrf import csrf_exempt
import docker
from django.apps import apps
from django.conf import settings
import logging
import requests


logger = logging.getLogger(__name__)


def update_entry_app_thresholds():
    """
    Send POST request to entry-app to update thresholds
    """
    try:
        entry_app_url = f"http://entry-app:5000"  
        response = requests.post(f"{entry_app_url}/update_thresholds")
        
        if response.status_code == 200:
            logging.info("Successfully updated thresholds in entry-app")
            logging.info(f"Response: {response.json()}")
        else:
            logging.error(f"Failed to update thresholds. Status code: {response.status_code}")
            logging.error(f"Response: {response.text}")
            
    except Exception as e:
        logging.error(f"Error updating thresholds in entry-app: {e}")
        raise

def start_detection_containers_logic():
    try:
        # Dynamically load models to avoid circular imports
        Setting = apps.get_model('management', 'Setting')
        Camera = apps.get_model('management', 'Camera')
        CameraContainer = apps.get_model('management', 'CameraContainer')

        # Fetch only the needed settings once and store them as a dictionary
        setting_dict = {setting.key: setting.value for setting in Setting.objects.all()}

        # Initialize Docker client
        client = docker.DockerClient(
            base_url=setting_dict.get("dockerClientAddress", 'tcp://host.docker.internal:2375')
        )

        # Fetch all cameras that are enabled
        cameras = Camera.objects.filter(enabled=True)
        base_port = int(setting_dict.get("dockerDetectionContainerBasePort", '5000'))

        for i, camera in enumerate(cameras):
            container_port = base_port + i

            # Prepare environment variables from settings
            environment = {
                'CAMERA_LINK': camera.link,
                'CAMERA_ID': str(camera.id),
                'BATCH_SIZE': setting_dict.get("batchSizeDetectionsSave", "100"),
                'TRACKING_MODEL': setting_dict.get("trackingModel", "yolo11n.pt"),
                'FACE_DETECTION_MODEL': setting_dict.get("faceDetectionModel", "yolov10n-face.pt"),
                'FACE_SIMILARITY_THRESHOLD': setting_dict.get("faceSimilarityTresholdTracking", "0.7"),
                'FACE_DETECTION_THRESHOLD': setting_dict.get("faceDetectionTresholdTracking", "0.4"),
                'PERSON_DETECTION_THRESHOLD': setting_dict.get("personDetectionTresholdTracking", "0.6"),
                'FACE_SIMILARITY_REQUEST_LINK': setting_dict.get(
                    "detectionContainerFaceSimilarirtyRequestLink",
                    "host.docker.internal:8000/face_recognition/api/recognize/"
                ),
                'FPS': setting_dict.get("fpsTracking", "10"),
                'PGVECTOR_DB_NAME': os.getenv('PGVECTOR_DB_NAME'),
                'PGVECTOR_DB_USER': os.getenv('PGVECTOR_DB_USER'),
                'PGVECTOR_DB_PASSWORD': os.getenv('PGVECTOR_DB_PASSWORD'),
                'PGVECTOR_DB_HOST': setting_dict.get("detectionContainerDbHost", 'host.docker.internal'),
                'PGVECTOR_DB_PORT': setting_dict.get("detectionContainerDbPort", '5432'),
            }

            container_config = {
                'image': setting_dict.get("detectionCOntainerImage", 'pppfkp15/flask-ultralytics-gpu:3.0'),
                'detach': True,
                'environment': environment,
                'network_mode': 'bridge',  # Adjust if necessary for inter-container communication
                'ports': {'5000/tcp': ('0.0.0.0', container_port)},
                'device_requests': [
                    docker.types.DeviceRequest(count=-1, capabilities=[['gpu']])
                ]
            }

            # Run container
            container = client.containers.run(**container_config)

            # Store or update container information for each camera
            CameraContainer.objects.update_or_create(
                camera=camera,
                defaults={
                    'container_id': container.id,
                    'port': container_port
                }
            )

        return {'message': 'Containers started successfully'}

    except docker.errors.DockerException as e:
        raise RuntimeError(f"Docker error: {e}")
    except Exception as e:
        raise RuntimeError(f"Unexpected error: {e}")
    

def restart_containers_logic():
    try:
        # Dynamically load models to avoid circular imports
        Setting = apps.get_model('management', 'Setting')
        Camera = apps.get_model('management', 'Camera')
        CameraContainer = apps.get_model('management', 'CameraContainer')

        # Fetch only the needed settings once and store them as a dictionary
        setting_dict = {setting.key: setting.value for setting in Setting.objects.all()}

        # Initialize Docker client
        client = docker.DockerClient(
            base_url=setting_dict.get("dockerClientAddress", 'tcp://host.docker.internal:2375')
        )
        container_records = CameraContainer.objects.all()

        # Clean up orphaned or outdated container records
        for container_record in container_records:
            try:
                # Check if camera still exists
                camera_exists = Camera.objects.filter(id=container_record.camera_id).exists()
                if not camera_exists:
                    # If the camera doesn't exist, delete the container record
                    try:
                        # Try to stop and remove the container if it exists
                        container = client.containers.get(container_record.container_id)
                        container.stop(timeout=10)
                        container.remove()
                    except docker.errors.NotFound:
                        pass  # Container already removed
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
                container_record.delete()

        # Start new containers
        return start_detection_containers_logic()

    except Exception as e:
        raise RuntimeError(f"Error restarting containers: {e}")
    
def stop_container_logic(camera_id):
    try:
        # Dynamically load models to avoid circular imports
        Setting = apps.get_model('app_name', 'Setting')
        CameraContainer = apps.get_model('app_name', 'CameraContainer')

        # Fetch only the needed settings once and store them as a dictionary
        setting_dict = {setting.key: setting.value for setting in Setting.objects.all()}

        # Initialize Docker client
        client = docker.DockerClient(
            base_url=setting_dict.get("dockerClientAddress", 'tcp://host.docker.internal:2375')
        )

        # Retrieve container record for the given camera ID
        container_record = CameraContainer.objects.get(camera_id=camera_id)

        try:
            # Stop and remove the container
            container = client.containers.get(container_record.container_id)
            container.stop(timeout=10)
            container.remove()
            container_record.delete()
            return {'message': f'Container for camera {camera_id} stopped successfully'}
        except docker.errors.NotFound:
            # Handle case where the container is not found but the record exists
            container_record.delete()
            return {'message': 'Container not found but record cleaned up'}

    except CameraContainer.DoesNotExist:
        return {'error': 'No container found for this camera', 'status': 404}
    except Exception as e:
        # Log unexpected errors
        return {'error': str(e), 'status': 500}