from django.db import models
from pgvector.django import VectorField
from django.contrib.auth.models import User 
from timescale.db.models.models import TimescaleModel
from timescale.db.models.fields import TimescaleDateTimeField

# Create your models here.
class FaceEmbedding(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='face_embeddings')
    embedding = VectorField(dimensions=512, null=True, blank=True)

    def __str__(self):
        return f"FaceEmbedding for {self.user}: {self.embedding}"
    
class Recognition(TimescaleModel):
    user_id = models.IntegerField(null=True)
    distance = models.FloatField()
    time = TimescaleDateTimeField(interval = "1 second")

