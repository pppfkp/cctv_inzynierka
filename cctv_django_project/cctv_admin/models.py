from django.db import models
from pgvector.django import VectorField

class Camera(models.Model):
    link = models.CharField(max_length=500, unique=True)
    name = models.CharField(max_length=200, unique=True)
    enabled = models.BooleanField(default=True)
    transformation_matrix = VectorField(dimensions=9, null=True, blank=True)

    def __str__(self):
        return f"{self.name}: {self.link}"

class Setting(models.Model):
    setting_key = models.CharField(max_length=100, unique=True)
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

