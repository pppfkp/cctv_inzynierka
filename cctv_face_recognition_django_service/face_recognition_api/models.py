from django.db import models
from pgvector.django import VectorField
from django.contrib.auth.models import User  

class FaceEmbedding(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='face_embeddings')
    embedding = VectorField(dimensions=512, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"FaceEmbedding for {self.user} created on {self.created_at}"

