from django.db import models
from .utils import extract_embedding
from pgvector.django import VectorField
from django.contrib.auth.models import User 
from django.dispatch import receiver
from django.db.models.signals import pre_save
from django.core.exceptions import ValidationError
import numpy as np

# Create your models here.
class FaceEmbedding(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='face_embeddings')
    embedding = VectorField(dimensions=512, null=False, blank=False)
    photo = models.ImageField(upload_to='face_photos/', null=False, blank=False)

    def __str__(self):
        return f"FaceEmbedding for {self.user}"
    
class Recognition(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recognitions', null=True)
    distance = models.FloatField()
    time = models.DateTimeField()
    photo =  models.ImageField(upload_to='recognition_face_photos/', null=True, blank=False)
    
@receiver(pre_save, sender=FaceEmbedding)
def process_face_embedding(sender, instance, **kwargs):
    """
    Signal to process face embedding before saving the model.
    
    - Extracts embedding from photo if photo is new or changed
    - Validates face detection
    - Converts embedding to list for storage
    - Stores confidence score
    """
    # Check if this is a new instance or if photo has changed
    if not instance.pk or instance.photo != sender.objects.get(pk=instance.pk).photo:
        # Ensure photo exists
        if not instance.photo:
            raise ValidationError("Photo is required for face embedding.")
        
        # Extract embedding and confidence
        embedding, confidence = extract_embedding(instance.photo)
        
        # Validate embedding and confidence
        if embedding is None or confidence is None:
            raise ValidationError("No face detected or error during embedding extraction. Please upload a valid face photo.")
        
        # Convert to list if it's a numpy array
        if isinstance(embedding, np.ndarray):
            embedding = embedding.tolist()
        
        # Set the embedding and confidence
        instance.embedding = embedding