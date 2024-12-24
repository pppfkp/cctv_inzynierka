from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from pgvector.django import VectorField

# Create your models here.
class TrackingSubject(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    is_inside = models.BooleanField(default=False)

@receiver(post_save, sender=User)
def create_tracking_subjects(sender, instance, created, **kwargs):
    if created:
        TrackingSubject.objects.create(user=instance)

class Camera(models.Model):
    link = models.CharField(max_length=500, unique=True)
    name = models.CharField(max_length=200, unique=True)
    enabled = models.BooleanField(default=True)
    transformation_matrix = VectorField(dimensions=9, null=True, blank=True)

    def __str__(self):
        return f"{self.name}: {self.link}"
    
class Setting(models.Model):
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField()
    description = models.TextField(blank=True, null=True)
    TYPE_CHOICES = [
        ('str', 'String'),
        ('int', 'Integer'),
        ('bool', 'Boolean'),
        ('float', 'Float'),
    ]
    data_type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='str')

    def __str__(self):
        return f"{self.key}: {self.value}"
    
class CalibrationPoint(models.Model):
    camera = models.ForeignKey(Camera, on_delete=models.CASCADE, related_name='calibration_points')
    canvas_x = models.FloatField()
    canvas_y = models.FloatField()
    camera_x = models.FloatField()
    camera_y = models.FloatField()

    def __str__(self):
        return f"Calibration for {self.camera.name} - Canvas ({self.canvas_x}, {self.canvas_y}), Camera ({self.camera_x}, {self.camera_y})"    