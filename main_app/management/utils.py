import base64
import json
import os
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
import docker.errors
import cv2
from django.views.decorators.csrf import csrf_exempt
import docker
from django.apps import apps
from django.conf import settings
import logging
import requests


logger = logging.getLogger(__name__)

# containers

def get_container_env(camera_id):
    Camera = apps.get_model('management', 'Camera')

    setting_dict = get_settings()

    camera = Camera.objects.get(id=camera_id)

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

    return environment

def get_new_container_config(camera_id, container_port):
    setting_dict = get_settings()

    container_config = {
        'image': setting_dict.get("detectionContainerImage", 'pppfkp15/flask-ultralytics-gpu:4.0'),
        'detach': True,
        'environment': get_container_env(camera_id),
        'network_mode': 'bridge',  
        'ports': {'5000/tcp': container_port},  # Simplified port mapping
        'device_requests': [
            docker.types.DeviceRequest(count=-1, capabilities=[['gpu']])
        ]
    }

    return container_config

def get_settings():

    Setting = apps.get_model('management', 'Setting')

    # Fetch settings
    setting_dict = {setting.key: setting.value for setting in Setting.objects.all()}

    return setting_dict

def get_docker_client():

    setting_dict = get_settings()

    return docker.DockerClient(base_url=setting_dict.get("dockerClientAddress", 'tcp://host.docker.internal:2375'))

def start_container_logic(camera_id):
    """
    Logic to start a specific container. Create a new container if one doesn't exist.
    """
    try:
        client = get_docker_client()
        
        CameraContainer = apps.get_model('management', 'CameraContainer')

        # Retrieve or create a container record for the given camera ID
        container_record = CameraContainer.objects.get(camera_id=camera_id)

        try:
            # Check if the container exists
            container = client.containers.get(container_record.container_id)
            container.start()
        except docker.errors.NotFound:
            container_config= get_new_container_config(camera_id, container_record.port)

            # Extract the image and pass the rest of the config as keyword arguments
            image = container_config.pop('image')  # Remove 'image' from the config
            new_container = client.containers.run(image, **container_config)

            # Update the CameraContainer record
            container_record.container_id = new_container.id
            container_record.save()

        return {'message': f'Container for camera {camera_id} started successfully'}
    except Exception as e:
        return {'error': str(e), 'status': 500}
    
def stop_container_logic(camera_id):
    """
    Logic to stop a specific container. Stops the container if it's running.
    """
    try:
        client = get_docker_client()
        
        CameraContainer = apps.get_model('management', 'CameraContainer')

        # Retrieve the container record for the given camera ID
        container_record = CameraContainer.objects.get(camera_id=camera_id)

        try:
            # Check if the container exists
            container = client.containers.get(container_record.container_id)
            container.stop()
        except docker.errors.NotFound:
            return {'error': f'Container for camera {camera_id} not found', 'status': 404}

        return {'message': f'Container for camera {camera_id} stopped successfully'}
    except Exception as e:
        return {'error': str(e), 'status': 500}

def soft_restart_container_logic(camera_id):
    """
    Soft restart logic: Restart the container if it exists; otherwise, create a new one.
    """
    try:
        client = get_docker_client()
        
        CameraContainer = apps.get_model('management', 'CameraContainer')

        # Retrieve or create a container record for the given camera ID
        container_record = CameraContainer.objects.get(camera_id=camera_id)

        try:
            # Check if the container exists
            container = client.containers.get(container_record.container_id)
            container.restart()
            return {'message': f'Container for camera {camera_id} restarted successfully'}
        except docker.errors.NotFound:
            container_config= get_new_container_config(camera_id, container_record.port)

            # Extract the image and pass the rest of the config as keyword arguments
            image = container_config.pop('image')  # Remove 'image' from the config
            new_container = client.containers.run(image, **container_config)

            # Update the CameraContainer record
            container_record.container_id = new_container.id
            container_record.save()

            return {'message': f'Container for camera {camera_id} created and started successfully'}
    except Exception as e:
        return {'error': str(e), 'status': 500}

def hard_restart_container_logic(camera_id):
    """
    Hard restart logic: Always delete the existing container and create a new one.
    """
    try:
        client = get_docker_client()
        
        CameraContainer = apps.get_model('management', 'CameraContainer')

        # Retrieve the container record for the given camera ID
        container_record = CameraContainer.objects.get(camera_id=camera_id)

        # Try to stop and remove the existing container if it exists
        try:
            container = client.containers.get(container_record.container_id)
            container.stop()
            container.remove()
        except docker.errors.NotFound:
            pass  # Container doesn't exist, no need to remove it

        container_config= get_new_container_config(camera_id, container_record.port)

        # Extract the image and pass the rest of the config as keyword arguments
        image = container_config.pop('image')  # Remove 'image' from the config
        new_container = client.containers.run(image, **container_config)

        # Update the CameraContainer record
        container_record.container_id = new_container.id
        container_record.save()

        return {'message': f'Container for camera {camera_id} recreated and started successfully'}
    except Exception as e:
        return {'error': str(e), 'status': 500}

def restart_all_containers_logic(hard_restart=False):
    """
    Logic to restart containers, either in soft or hard mode.
    - In hard restart, containers are deleted and new containers are created for enabled cameras.
    - In soft restart, containers are just restarted without deletion.
    """    
    try:
        setting_dict = get_settings()
        client = get_docker_client()
        Camera = apps.get_model('management', 'Camera')
        CameraContainer = apps.get_model('management', 'CameraContainer')
        base_port = setting_dict.get('detectionContainersBasePort', 5000)

        camera_containers = CameraContainer.objects.all()

        if not hard_restart:
            for container_record in camera_containers:
                try:
                    container = client.containers.get(container_record.container_id)
                    container.restart()
                    logging.info(f"Container with id: {container_record.container_id} restarted.")
                except docker.errors.NotFound:
                    logging.warning(f"Container with id: {container_record.container_id} was not found.")
                except Exception as e:
                    logging.warning(f"Container with id: {container_record.container_id}- something went wrong during the soft restart: {e}")
        else:
            # Stop and remove all containers
            containers_to_delete = CameraContainer.objects.all()
            for container_record in containers_to_delete:
                try:
                    container = client.containers.get(container_record.container_id)
                    container.stop()
                    container.remove()
                    container_record.delete()
                    logging.info(f"Container for camera {container_record.camera.name} stopped and deleted.")
                except docker.errors.NotFound:
                    logging.warning(f"Container not found for camera {container_record.camera.name}. Skipping.")
                    container_record.delete()
                except Exception as e:
                    logging.error(f"Error stopping/removing container for camera {container_record.camera.name}: {e}")
            
            # Add a small delay to ensure ports are freed
            import time
            time.sleep(2)
            
            # Create new containers for all enabled cameras
            enabled_cameras = Camera.objects.filter(enabled=True)
            used_ports = set()
            
            def find_available_port(start_port):
                """Find the next available port starting from start_port."""
                import socket
                current_port = start_port
                while current_port < 65535:
                    if current_port in used_ports:
                        current_port += 1
                        continue
                    
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    try:
                        sock.bind(('', current_port))
                        sock.close()
                        return current_port
                    except OSError:
                        current_port += 1
                    finally:
                        sock.close()
                raise RuntimeError("No available ports found")
            
            for camera in enabled_cameras:
                try:
                    # Find an available port
                    container_port = find_available_port(base_port)
                    used_ports.add(container_port)
                    
                    container_config = get_new_container_config(camera.id, container_port)
                    
                    # Extract the image and pass the rest of the config as keyword arguments
                    image = container_config.pop('image')
                    
                    # Create the container
                    new_container = client.containers.run(image, **container_config)
                    
                    # Save the container info in the database
                    CameraContainer.objects.create(
                        camera=camera,
                        container_id=new_container.id,
                        port=container_port
                    )
                    
                    logging.info(f"New container created for camera {camera.name} at port {container_port}")
                        
                except Exception as e:
                    logging.error(f"Error creating container for camera {camera.name}: {e}")
                    # Release the port if container creation failed
                    used_ports.discard(container_port)
            
        return {'message': 'Containers restarted successfully'} 
    except Exception as e:
        logging.error(f"Error restarting containers: {e}")
        return {'error': str(e), 'status': 500}

def start_all_containers_logic():
    """
    Start all existing containers that are not currently running.
    """
    try:
        client = get_docker_client()
        CameraContainer = apps.get_model('management', 'CameraContainer')
        camera_containers = CameraContainer.objects.all()

        for container_record in camera_containers:
            try:
                container = client.containers.get(container_record.container_id)
                if container.status != 'running':  # Start only if not already running
                    container.start()
                    logging.info(f"Container with id: {container_record.container_id} started.")
                else:
                    logging.info(f"Container with id: {container_record.container_id} is already running.")
            except docker.errors.NotFound:
                logging.warning(f"Container with id: {container_record.container_id} not found. Skipping.")
            except Exception as e:
                logging.error(f"Error starting container with id: {container_record.container_id}: {e}")

        return {'message': 'All containers started successfully'}
    except Exception as e:
        logging.error(f"Error starting containers: {e}")
        return {'error': str(e), 'status': 500}

def stop_all_containers_logic():
    """
    Stop all running containers.
    """
    try:
        client = get_docker_client()
        CameraContainer = apps.get_model('management', 'CameraContainer')
        camera_containers = CameraContainer.objects.all()

        for container_record in camera_containers:
            try:
                container = client.containers.get(container_record.container_id)
                if container.status == 'running':  # Stop only if running
                    container.stop()
                    logging.info(f"Container with id: {container_record.container_id} stopped.")
                else:
                    logging.info(f"Container with id: {container_record.container_id} is not running.")
            except docker.errors.NotFound:
                logging.warning(f"Container with id: {container_record.container_id} not found. Skipping.")
            except Exception as e:
                logging.error(f"Error stopping container with id: {container_record.container_id}: {e}")

        return {'message': 'All containers stopped successfully'}
    except Exception as e:
        logging.error(f"Error stopping containers: {e}")
        return {'error': str(e), 'status': 500}

#  entries

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