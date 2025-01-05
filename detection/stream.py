import time
import socket
import numpy as np
import cv2
from utils import StreamServer
from flask import Flask, Response

app = Flask(__name__)

# Create server instance
server = StreamServer()
server.wait_for_client()

@app.route('/video_feed')
def video_feed():
    def generate():
        while True:
            frame = server.receive_frame()
            if frame is not None:
                _, encoded_image = cv2.imencode(".jpg", frame)
                frame_bytes = encoded_image.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            else:
                time.sleep(0.1)

    return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
