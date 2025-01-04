from flask import Flask, Response
import cv2
from utils import open_camera, generate_frames

# Initialize Flask app
app = Flask(__name__)

# Open the camera feed
cap = open_camera("http://192.168.0.156:5333/video")

@app.route('/video_feed')
def video_feed():
    """Video streaming route."""
    return Response(generate_frames(cap), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
