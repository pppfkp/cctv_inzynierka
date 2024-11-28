from rest_framework import serializers
from .models import FaceEmbedding
from django.contrib.auth.models import User

class FaceEmbeddingSerializer(serializers.ModelSerializer):
    class Meta:
        model = FaceEmbedding
        fields = ['id', 'user', 'embedding', 'created_at']
        read_only_fields = ['created_at']

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']