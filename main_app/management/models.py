from django.db import models
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import User
import logging
from django.core.exceptions import ValidationError

from .utils import restart_all_containers_logic

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
    default_value = models.TextField()  # New field for default value
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

    def clean(self):
        """
        Validate the value based on its data type
        """
        try:
            if self.data_type == 'int':
                int(self.value)
                int(self.default_value)
            elif self.data_type == 'float':
                float(self.value)
                float(self.default_value)
            elif self.data_type == 'bool':
                self.value = str(self.value).lower() in ['true', '1', 'yes']
                self.default_value = str(self.default_value).lower() in ['true', '1', 'yes']
        except ValueError:
            raise ValidationError(f"Invalid {self.get_data_type_display()} value")

    def reset_to_default(self):
        """
        Reset the current value to its default value
        """
        self.value = self.default_value
        self.save()

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

class CameraContainer(models.Model):
    camera = models.OneToOneField('Camera', on_delete=models.CASCADE, related_name='container')
    container_id = models.CharField(max_length=100)
    port = models.IntegerField()
    last_started = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'camera_containers'