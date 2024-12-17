from django.db import models
from pgvector.django import VectorField
from django.contrib.auth.models import User 

# Create your models here.
class FaceEmbedding(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='face_embeddings')
    embedding = VectorField(dimensions=512, null=False, blank=False)

    def __str__(self):
        return f"FaceEmbedding for {self.user}"
    
class Recognition(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recognitions')
    distance = models.FloatField()
    time = models.DateTimeField()

