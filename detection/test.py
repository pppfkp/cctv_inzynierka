from flask import Flask, Response
import cv2
from utils import open_camera, generate_frames, CAMERA_LINK
import os

# Initialize Flask app
app = Flask(__name__)

# Open the camera feed
cap = open_camera(CAMERA_LINK)

@app.route('/video_feed')
def video_feed():
    """Video streaming route."""
    return Response(generate_frames(cap), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
    

