import base64
import json
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
import cv2
from django.views.decorators.csrf import csrf_exempt
from .models import Camera, Boundary

def capture_camera_frame_for_boundaries_edit(request, camera_id):
    # Get the camera object
    camera = Camera.objects.get(id=camera_id)
    boundaries = Boundary.objects.filter(camera=camera)

    # Open the camera stream using OpenCV
    cap = cv2.VideoCapture(camera.link)

    if not cap.isOpened():
        return HttpResponse("Error: Could not open camera stream", status=500)

    # Read a single frame from the camera
    ret, frame = cap.read()

    # If the frame is successfully captured
    if ret:
        # Convert the frame to an image format that can be used in HTML
        ret, jpeg = cv2.imencode('.jpg', frame)
        if ret:
            # Convert the JPEG frame to bytes
            frame_bytes = jpeg.tobytes()

            # Encode the image bytes to base64
            encoded_image = base64.b64encode(frame_bytes).decode('utf-8')

            # Send the image as a response (or pass it to the template)
            return render(request, 'camera_calibration_form.html', {
                'camera': camera,
                'image_data': encoded_image,  # Pass the base64-encoded image
                'boundaries': boundaries  # Pass the list of boundaries
            })

    # Release the camera capture object
    cap.release()

    return HttpResponse("Error: Could not capture image", status=500)

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