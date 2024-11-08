from django.shortcuts import render
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from .models import FaceEmbedding
from .serializers import FaceEmbeddingSerializer
from pgvector.django import L2Distance
import numpy as np
from PIL import Image
import io

class DeleteEmbeddingView(APIView):
    def delete(self, request, embedding_id):
        # Get user from request data
        user_id = request.data.get('user_id')
        if not user_id:
            return Response({"error": "No user ID provided"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        try:
            # Find the embedding by ID and ensure it belongs to the given user
            embedding = FaceEmbedding.objects.get(id=embedding_id, user=user)
            embedding.delete()

            return Response({"message": "Embedding deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
        except FaceEmbedding.DoesNotExist:
            return Response({"error": "Embedding not found or doesn't belong to this user"}, status=status.HTTP_404_NOT_FOUND)
        
class DeleteAllEmbeddingsView(APIView):
    def delete(self, request):
        # Get user from request data
        user_id = request.data.get('user_id')
        if not user_id:
            return Response({"error": "No user ID provided"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        # Delete all embeddings for this user
        deleted_count, _ = FaceEmbedding.objects.filter(user=user).delete()

        if deleted_count > 0:
            return Response({"message": f"{deleted_count} embeddings deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
        else:
            return Response({"error": "No embeddings found for this user"}, status=status.HTTP_404_NOT_FOUND)

class UploadEmbeddingView(APIView):
    def post(self, request):
        # Get the uploaded photo
        photo = request.FILES.get('file')
        if not photo:
            return Response({"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)

        # Extract the embedding from the photo
        embedding = extract_embedding(photo)
        
        if embedding is None:
            return Response({"error": "Could not extract embedding from photo"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Get user from request body (assuming the user ID is provided)
        user_id = request.data.get('user_id')
        if not user_id:
            return Response({"error": "No user ID provided"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        # Save the embedding to the database
        face_embedding = FaceEmbedding.objects.create(user=user, embedding=embedding)

        return Response(FaceEmbeddingSerializer(face_embedding).data, status=status.HTTP_201_CREATED)
    
class UploadBulkEmbeddingsView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        # Get the user from request data
        user_id = request.data.get('user_id')
        if not user_id:
            return Response({"error": "No user ID provided"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        # Expect a list of files in the request
        files = request.FILES.getlist('files')
        if not files:
            return Response({"error": "No files provided"}, status=status.HTTP_400_BAD_REQUEST)

        embeddings = []
        for photo in files:
            embedding = extract_embedding(photo)
            if embedding is None:
                continue
            embeddings.append(embedding)

        # Save all embeddings in bulk
        if embeddings:
            face_embeddings = [
                FaceEmbedding(user=user, embedding=embedding) for embedding in embeddings
            ]
            FaceEmbedding.objects.bulk_create(face_embeddings)

            return Response({"message": "Embeddings uploaded successfully"}, status=status.HTTP_201_CREATED)
        else:
            return Response({"error": "No valid embeddings extracted"}, status=status.HTTP_400_BAD_REQUEST)

class FindClosestEmbeddingView(APIView):
    def post(self, request):
        # get the photo
        photo = request.FILES.get('file') 
        if not photo:
            return Response({"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)

        # extract the embedding from the photo
        embedding = extract_embedding(photo)  # Implement this method

        if embedding is None:
            return Response({"error": "Could not extract embedding from photo"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # find the closest match taking advantage of the pg-vector built-in l2 distance
        closest_embedding = FaceEmbedding.objects.annotate(
            distance=L2Distance("embedding", embedding)
        ).order_by('distance').first()

        if closest_embedding:
            # Serialize the result
            result = {
                "user_id": closest_embedding.user.id,
                "user_name": closest_embedding.user.username,
                "embedding_id": closest_embedding.id,
                "created_at": closest_embedding.created_at,
                "distance": closest_embedding.distance,
            }
            return Response(result, status=status.HTTP_200_OK)
        else:
            return Response({"error": "No embeddings found"}, status=status.HTTP_404_NOT_FOUND)

def extract_embedding(photo):
    """
    Extracts an embedding from a photo.
    This function takes an image and returns a 512-dimensional vector.
    """
    try:
        image = Image.open(photo)
        # Perform image processing and extract the embedding vector
        embedding = np.random.rand(512).tolist()  # will replace later with actual logic
        return embedding
    except Exception as e:
        print(f"Error extracting embedding: {e}")
        return None
