from django.apps import AppConfig
from .model_loader import get_models


class FaceRecognitionApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'face_recognition_api'

    def ready(self):
        get_models()