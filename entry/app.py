from flask import Flask, render_template, request, jsonify
import cv2
import numpy as np
from datetime import datetime
import base64
from utils import (
    DatabaseManager,
    FaceRecognition,
    FACE_SIMILARITY_THRESHOLD,
    FACE_SIMILARITY_REQUEST_LINK
)

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/entry')
def entry():
    return render_template('entry.html')

@app.route('/exit')
def exit():
    return render_template('exit.html')

@app.route('/recognize_entry', methods=['POST'])
def recognize_entry():
    try:
        # Get the image data from the request
        image_data = request.json['image'].split(',')[1]
        image_bytes = base64.b64decode(image_data)
        
        # Convert to numpy array
        nparr = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # Detect faces and process recognition
        distance, detected_id, user_inside = FaceRecognition.send_frame_for_recognition_sync(
            frame, 
            FACE_SIMILARITY_REQUEST_LINK
        )
        
        if distance is None or distance > FACE_SIMILARITY_THRESHOLD or detected_id is None:
            return jsonify({"status": "error", "message": "Not recognized"})
        else:
            if user_inside:
                return jsonify({
                    "status": "warning",
                    "message": f"User {detected_id} is already inside"
                })
            else:
                DatabaseManager.save_entry_to_db(
                    (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), detected_id)
                )
                DatabaseManager.set_user_inside_status(detected_id, True)
                return jsonify({
                    "status": "success",
                    "message": f"User {detected_id} entered (distance: {distance:.2f})"
                })
    except Exception as e:
        return jsonify({"status": "error", "message": f"Error processing image: {str(e)}"})

@app.route('/recognize_exit', methods=['POST'])
def recognize_exit():
    try:
        # Get the image data from the request
        image_data = request.json['image'].split(',')[1]
        image_bytes = base64.b64decode(image_data)
        
        # Convert to numpy array
        nparr = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # Detect faces and process recognition
        distance, detected_id, user_inside = FaceRecognition.send_frame_for_recognition_sync(
            frame, 
            FACE_SIMILARITY_REQUEST_LINK
        )
        
        if distance is None or distance > FACE_SIMILARITY_THRESHOLD or detected_id is None:
            return jsonify({"status": "error", "message": "Not recognized"})
        else:
            if user_inside:
                DatabaseManager.set_user_inside_status(detected_id, False)
                DatabaseManager.save_exit_to_db(
                    (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), detected_id)
                )
                return jsonify({
                    "status": "success",
                    "message": f"User {detected_id} left (distance: {distance:.2f})"
                })
            else:
                return jsonify({
                    "status": "warning",
                    "message": f"User {detected_id} is not inside"
                })
    except Exception as e:
        return jsonify({"status": "error", "message": f"Error processing image: {str(e)}"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)