from django.apps import AppConfig
import logging
import time
from django.db import connection
import docker

class ManagementConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'management'

    def ready(self):
        # Ensure Docker interaction happens only after app initialization
        self.restart_containers()

    def restart_containers(self):
        try:
            from .utils import restart_all_containers_logic
            # restart_all_containers_logic(hard_restart=True)
        except docker.errors.DockerException as e:
            logging.error(f"Error connecting to Docker: {e}")
        except Exception as ex:
            logging.error(f"Error in restarting containers: {ex}")