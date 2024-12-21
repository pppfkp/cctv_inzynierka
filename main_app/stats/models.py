from django.db import models
from django.contrib.auth.models import User 
from management.models import Camera
from pgvector.django import VectorField

# Create your models here.
class Enter(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='enters')
    time = models.DateTimeField()

class Exit(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='exits')
    time = models.DateTimeField()

class Detection(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='detections', null=True)
    camera = models.ForeignKey(Camera, on_delete=models.CASCADE, related_name='detections')
    track_id = models.BigIntegerField()
    time = models.DateTimeField()
    xywh = VectorField(dimensions=4, null=False, blank=False)