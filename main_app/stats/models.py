from django.db import models
from django.contrib.auth.models import User 
from face_recognition.models import Recognition
from management.models import Camera
from pgvector.django import VectorField


class Detection(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='detections', null=True)
    camera = models.ForeignKey(Camera, on_delete=models.CASCADE, related_name='detections')
    track_id = models.BigIntegerField()
    time = models.DateTimeField()
    x = models.IntegerField(default=0)
    y = models.IntegerField(default=0)
    w = models.IntegerField(default=0)
    h = models.IntegerField(default=0)

class Entry(models.Model):
    user = models.ForeignKey(
        'auth.User',
        on_delete=models.CASCADE,
        related_name='entries'
    )
    recognition_in = models.ForeignKey(
        'face_recognition.Recognition',
        on_delete=models.CASCADE,
        related_name='entries_in',
        null=False
    )
    recognition_out = models.ForeignKey(
        'face_recognition.Recognition',
        on_delete=models.CASCADE,
        related_name='entries_out',
        null=True,
        blank=True,
        default=None
    )
