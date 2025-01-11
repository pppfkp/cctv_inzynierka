import time
import socket
import numpy as np
import cv2
from utils import ImprovedStreamServer, StreamServer
from flask import Flask, Response

# Flask application
app = Flask(__name__)
server = ImprovedStreamServer()

@app.route('/video_feed')
def video_feed():
    def generate():
        while True:
            frame = server.get_frame()
            if frame is not None:
                _, encoded_image = cv2.imencode(".jpg", frame)
                frame_bytes = encoded_image.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            else:
                # Provide a default frame
                default_frame = np.zeros((480, 640, 3), dtype=np.uint8)
                _, encoded_image = cv2.imencode(".jpg", default_frame)
                frame_bytes = encoded_image.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                time.sleep(0.1)

    return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame")

if __name__ == '__main__':
    server.start_receiving()  # Start receiving frames in background thread
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
