from rest_framework import serializers
from .models import FaceEmbedding

class FaceEmbeddingSerializer(serializers.ModelSerializer):
    class Meta:
        model = FaceEmbedding
        fields = ['id', 'user', 'embedding', 'created_at']
        read_only_fields = ['created_at']