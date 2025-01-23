from django.db import models
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import User
from pgvector.django import VectorField
import logging

from .utils import restart_all_containers_logic, update_entry_app_thresholds

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
    photo = models.ImageField(upload_to='camera_reference_photos/', default='default.png')

    def __str__(self):
        return f"{self.name}: {self.link}"
    
# Signal handler for Camera changes
@receiver(post_save, sender=Camera)
@receiver(post_delete, sender=Camera)
def camera_changed(sender, instance, **kwargs):
    try:
        # Restart containers when Camera changes
        restart_all_containers_logic(hard=True)
        logging.info(f"Containers restarted due to Camera changes: {instance.name}")
    except Exception as e:
        logging.error(f"Error restarting containers after Camera change: {e}")
    
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

# Signal handler for Setting changes
@receiver(post_save, sender=Setting)
@receiver(post_delete, sender=Setting)
def setting_changed(sender, instance, **kwargs):
    try:
        # Implement only if setting si related to the detection
        # restart_all_containers_logic(hard=True)
        logging.info(f"Containers restarted due to Setting changes: {instance.key}")
    except Exception as e:
        logging.error(f"Error restarting containers after Setting change: {e}")

    try:
        # Only update for threshold settings
        threshold_settings = [
            'faceSimilarityTresholdEnterExit',
            'faceDetectionTresholdEnterExit'
        ]
        
        if instance.key in threshold_settings:
            update_entry_app_thresholds()
            logging.info(
                f"Entry app thresholds updated due to setting change: "
                f"{instance.key} = {instance.value}"
            )
    except Exception as e:
        logging.error(f"Error updating entry-app thresholds after setting change: {e}")    
    
class Zone(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.CharField(max_length=255, null=True)

    def __str__(self):
        return f"{self.name}"

class Boundary(models.Model):
    camera = models.ForeignKey(Camera, on_delete=models.CASCADE, related_name='boundaries')
    zone = models.ForeignKey(Zone, on_delete=models.CASCADE, related_name='boundaries')
    polygon = VectorField(dimensions=20)

    class Meta:
        verbose_name_plural = "Boundaries"

class CameraContainer(models.Model):
    camera = models.OneToOneField('Camera', on_delete=models.CASCADE, related_name='container')
    container_id = models.CharField(max_length=100)
    port = models.IntegerField()
    last_started = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'camera_containers'