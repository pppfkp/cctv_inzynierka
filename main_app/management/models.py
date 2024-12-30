from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from pgvector.django import VectorField
import numpy as np
import cv2

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
    
    def compute_transformation_matrix(self, camera_points, floorplan_points):
        """
        Compute the transformation matrix (homography) based on the given points.
        
        :param camera_points: List of (x, y) tuples for points in the camera view.
        :param floorplan_points: List of (x, y) tuples for corresponding points on the floorplan.
        :return: Transformation matrix as a list of 9 elements (flattened 3x3 matrix).
        """
        if len(camera_points) != len(floorplan_points) or len(camera_points) < 4:
            raise ValueError("At least 4 points are required for homography calculation.")
        
        # Convert points to numpy arrays
        pts1 = np.array(camera_points, dtype="float32")
        pts2 = np.array(floorplan_points, dtype="float32")

        # Compute the homography matrix
        matrix, _ = cv2.findHomography(pts1, pts2)

        # Flatten the matrix to store it as a 9-element vector
        return matrix.flatten().tolist()

    def save_transformation_matrix(self, camera_points, floorplan_points):
        """
        Calculate and save the transformation matrix when saving calibration points.
        """
        matrix = self.compute_transformation_matrix(camera_points, floorplan_points)
        self.transformation_matrix = matrix
        self.save()  # Save the camera object with the new transformation matrix
    
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
    
class Zone(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.CharField(max_length=255, null=True)

class Boundary(models.Model):
    camera = models.ForeignKey(Camera, on_delete=models.CASCADE, related_name='boundaries')
    zone = models.ForeignKey(Zone, on_delete=models.CASCADE, related_name='boundaries')
    polygon = VectorField(dimensions=20)

