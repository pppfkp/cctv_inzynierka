import base64
import json
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
import cv2
from django.views.decorators.csrf import csrf_exempt
from .models import Camera, Boundary

@csrf_exempt  # Disable CSRF for simplicity; ensure proper security in production
def save_boundary_points(request, boundary_id):
    if request.method == "POST":
        try:
            # Parse the JSON data from the request body
            data = json.loads(request.body)
            points = data.get('points', [])

            if not points or len(points) % 2 != 0:
                return JsonResponse({'error': 'Invalid points data'}, status=400)

            # Update the boundary's polygon field
            boundary = Boundary.objects.get(id=boundary_id)
            boundary.polygon = points  # Save the flattened array
            boundary.save()

            return JsonResponse({'message': 'Boundary points updated successfully'})
        except Boundary.DoesNotExist:
            return JsonResponse({'error': 'Boundary not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=405)