import base64
import json
import cv2
from django.shortcuts import redirect, render
from django.http import HttpResponse
from django.conf import settings
import numpy as np
from io import BytesIO
from PIL import Image

# Your Camera model here
from .models import CalibrationPoint, Camera, Floorplan

def save_calibration_points(request, camera_id):
    if request.method == "POST":
        camera = Camera.objects.get(id=camera_id)
        points_data = json.loads(request.POST.get("points", "[]"))

        # Delete existing points for the camera
        CalibrationPoint.objects.filter(camera=camera).delete()

        # Save new points
        for point in points_data:
            CalibrationPoint.objects.create(
                camera=camera,
                canvas_x=point["canvas_x"],
                canvas_y=point["canvas_y"],
                camera_x=point["camera_x"],
                camera_y=point["camera_y"],
            )
        return redirect("capture_camera_frame", camera_id=camera.id)

def capture_camera_frame(request, camera_id):
    # Get the camera object
    camera = Camera.objects.get(id=camera_id)

    # Open the camera stream using OpenCV
    cap = cv2.VideoCapture(camera.link)

    if not cap.isOpened():
        return HttpResponse("Error: Could not open camera stream", status=500)
    
    # Fetch the global floorplan (assuming there is only one)
    floorplan = Floorplan.objects.first()  # Get the first and only floorplan

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
                'floorplan': floorplan,  # Pass the floorplan object
            })

    # Release the camera capture object
    cap.release()

    return HttpResponse("Error: Could not capture image", status=500)

