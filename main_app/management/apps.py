from django.apps import AppConfig
import docker
import logging


class ManagementConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'management'
    def ready(self):
        try:
            # Initialize Docker client
            client = docker.DockerClient(base_url='tcp://host.docker.internal:2375')
            
            # Example: List all containers
            containers = client.containers.list()
            for container in containers:
                logging.info(f"Container name: {container.name}")
        except docker.errors.DockerException as e:
            logging.error(f"Error connecting to Docker: {e}")