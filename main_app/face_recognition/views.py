import base64
from django.utils import timezone
import os
import uuid
from django.shortcuts import render
from django.http import JsonResponse
from PIL import Image
from io import BytesIO
from django.conf import settings

from .models import FaceEmbedding, Recognition
from .utils import extract_embedding
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from pgvector.django import L2Distance
import logging

def extract_embedding_view(request):
    if request.method == "POST":
        try:
            # Get the Base64 image data from the form
            image_data = request.POST.get('image', None)
            if not image_data:
                return JsonResponse({"error": "No image data found."}, status=400)

            # Decode the Base64 image
            format, imgstr = image_data.split(';base64,') 
            image = Image.open(BytesIO(base64.b64decode(imgstr)))

            # Extract embedding
            embedding = extract_embedding(image)

            if embedding is None:
                return render(request, "extract_embedding.html", {"error": "No face detected in the image."})

            # Convert embedding to a string for display
            embedding_str = ", ".join([f"{x:.4f}" for x in embedding.tolist()])
            return render(request, "extract_embedding.html", {"embedding": embedding_str})

        except Exception as e:
            return render(request, "extract_embedding.html", {"error": f"An error occurred: {str(e)}"})

    # Render the initial template
    return render(request, "extract_embedding.html")

class FindClosestEmbeddingView(APIView):
    def post(self, request):
        # Get the photo
        photo = request.FILES.get('file') 
        if not photo:
            return Response({"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)

        # Extract the embedding and cropped face from the photo
        embedding, cropped_face = extract_embedding(photo)

        if embedding is None or cropped_face is None:
            return Response({"error": "Could not extract embedding from photo"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Create directory if it doesn't exist
        directory = os.path.join(settings.MEDIA_ROOT, "recognition_face_photos")
        if not os.path.exists(directory):
            os.makedirs(directory)

        # Save the cropped face as an image file
        normalized_face = (cropped_face + 1) / 2
        cropped_face_image = Image.fromarray((normalized_face * 255).permute(1, 2, 0).byte().numpy())
        cropped_face_filename = f"{uuid.uuid4().hex}.jpg"
        cropped_face_path = os.path.join(directory, cropped_face_filename)
        cropped_face_image.save(cropped_face_path)
        print(f"Image saved at {cropped_face_path}")

        # Find the closest match using pg-vector's L2 distance
        closest_embedding = FaceEmbedding.objects.annotate(
            distance=L2Distance("embedding", embedding)
        ).order_by('distance').first()

        # Prepare the recognition data
        if closest_embedding:
            user = closest_embedding.user
            distance = closest_embedding.distance
            # Save recognition data
            Recognition.objects.create(
                user=user,
                distance=distance,
                time=timezone.now(),
                photo=os.path.join("recognition_face_photos", cropped_face_filename)
            )
            result = {
                "user_id": user.id,
                "user_name": user.username,
                "user_inside": user.trackingsubject.is_inside,
                "embedding_id": closest_embedding.id,
                "distance": distance,
            }
            return Response(result, status=status.HTTP_200_OK)
        else:
            return Response({"error": "No embeddings found"}, status=status.HTTP_404_NOT_FOUND)
        
