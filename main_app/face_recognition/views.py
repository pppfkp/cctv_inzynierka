import base64
from django.shortcuts import render
from django.http import JsonResponse
from PIL import Image
from io import BytesIO

from .models import FaceEmbedding
from .utils import extract_embedding
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from pgvector.django import L2Distance

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
                "distance": closest_embedding.distance,
            }
            return Response(result, status=status.HTTP_200_OK)
        else:
            return Response({"error": "No embeddings found"}, status=status.HTTP_404_NOT_FOUND)