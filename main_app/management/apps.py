from django.apps import AppConfig
import docker
import logging



class ManagementConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'management'
    def ready(self):
        try:
            from .views import restart_containers

            restart_containers(None)
        except docker.errors.DockerException as e:
            logging.error(f"Error connecting to Docker: {e}")