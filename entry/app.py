import json
import os
from utils import DB_POOL
from flask import Flask, render_template, request, jsonify
import cv2
import numpy as np
from datetime import datetime
import base64
import requests
import aiohttp
import asyncio

# Environment and configuration
DJANGO_ENTRY_ENDPOINT = os.getenv("DJANGO_ENTRY_ENDPOINT")
DJANGO_EXIT_ENDPOINT = os.getenv("DJANGO_EXIT_ENDPOINT")
FACE_SIMILARITY_REQUEST_LINK = os.getenv("FACE_SIMILARITY_REQUEST_LINK")

# Thresholds (will be updated from database)
FACE_SIMILARITY_THRESHOLD = 2.0
FACE_DETECTION_THRESHOLD = 2.0

app = Flask(__name__)

class FaceRecognition:
    @staticmethod
    async def send_frame_for_recognition(frame, session):
        """
        Send frame to face recognition service and get user details asynchronously.
        
        Args:
            frame: Image frame to process
            session: Aiohttp client session
        
        Returns:
            Tuple of (distance, user_id, user_inside, recognition_id)
        """
        # Encode the frame to JPEG
        _, img_encoded = cv2.imencode('.jpg', frame)
        img_bytes = img_encoded.tobytes()

        # Prepare multipart form data
        form = aiohttp.FormData()
        form.add_field(
            name='file',
            value=img_bytes,
            filename='frame.jpg',
            content_type='image/jpeg'
        )

        try:
            async with session.post(FACE_SIMILARITY_REQUEST_LINK, data=form) as response:
                if response.status == 200:
                    data = await response.json()
                    return (
                        data.get("distance"),
                        data.get("user_id"),
                        data.get("user_inside"),
                        data.get("recognition_id")
                    )
                else:
                    print(f"Recognition service error: {response.status}")
                    return None, None, None, None
        except Exception as e:
            print(f"Error in face recognition: {e}")
            return None, None, None, None

    @staticmethod
    def send_frame_for_recognition_sync(frame, request_link):
        """
        Synchronous wrapper for async face recognition
        
        Args:
            frame: Image frame to process
            request_link: Face similarity service URL
        
        Returns:
            Tuple of (distance, user_id, user_inside, recognition_id)
        """
        async def run_async():
            async with aiohttp.ClientSession() as session:
                return await FaceRecognition.send_frame_for_recognition(frame, session)
        
        return asyncio.run(run_async())

class DatabaseManager:
    @staticmethod
    def set_user_inside_status(user_id, status):
        """
        Update the is_inside field for a user's TrackingSubject.
        
        Args:
            user_id (int): The ID of the user whose is_inside status needs to be updated.
            status (bool): The value to set for is_inside (True or False).
        """
        try:
            conn = DB_POOL.getconn()
            cursor = conn.cursor()
            
            update_query = """
            UPDATE management_trackingsubject
            SET is_inside = %s
            WHERE user_id = %s
            """
            
            cursor.execute(update_query, (status, user_id))
            conn.commit()
            print(f"Set is_inside for user_id {user_id} to {status}")
        except Exception as e:
            print(f"Error updating is_inside for user_id {user_id}: {e}")
        finally:
            if cursor:
                cursor.close()
            if conn:
                DB_POOL.putconn(conn)

    @staticmethod
    def get_threshold_settings():
        """
        Fetch threshold settings from the management_setting table.
        Returns a tuple of (face_similarity_threshold, face_detection_threshold)
        """
        try:
            conn = DB_POOL.getconn()
            cursor = conn.cursor()
            
            # Query for both threshold settings
            query = """
            SELECT key, value, data_type
            FROM management_setting
            WHERE key IN ('faceSimilarityTresholdEnterExit', 'faceDetectionTresholdEnterExit')
            """
            
            cursor.execute(query)
            settings = cursor.fetchall()
            
            # Initialize default values
            face_similarity = None
            face_detection = None
            
            # Process settings based on data type
            for key, value, data_type in settings:
                if key == 'faceSimilarityTresholdEnterExit':
                    face_similarity = float(value) if data_type == 'float' else None
                elif key == 'faceDetectionTresholdEnterExit':
                    face_detection = float(value) if data_type == 'float' else None
            
            return face_similarity, face_detection
            
        except Exception as e:
            print(f"Error fetching threshold settings: {e}")
            return None, None
        finally:
            if cursor:
                cursor.close()
            if conn:
                DB_POOL.putconn(conn)

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
        FACE_SIMILARITY_THRESHOLD, FACE_DETECTION_THRESHOLD = DatabaseManager.get_threshold_settings()
        # Get the image data from the request
        image_data = request.json['image'].split(',')[1]
        image_bytes = base64.b64decode(image_data)
        
        # Convert to numpy array
        nparr = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # Detect faces and process recognition
        distance, detected_id, user_inside, recognition_id = FaceRecognition.send_frame_for_recognition_sync(
            frame, 
            FACE_SIMILARITY_REQUEST_LINK
        )
        
        # Check recognition conditions
        if distance is None or distance > FACE_SIMILARITY_THRESHOLD or detected_id is None:
            return jsonify({"status": "error", "message": "Not recognized"})
        
        # Send to Django entry endpoint
        django_response = requests.post(DJANGO_ENTRY_ENDPOINT, json={
            "recognition_id": recognition_id,
            "user_id": detected_id
        })
        
        # Check Django response
        if django_response.status_code == 200:  
            return jsonify({
                "status": "success",
                "message": f"User {detected_id} entered (distance: {distance:.2f})"
            })
        else:
            error_data = json.loads(django_response.text)
            error_message = error_data['error'].strip("['']")

            return jsonify({
                "status": "error",
                "message": error_message
            })
    
    except Exception as e:
        return jsonify({"status": "error", "message": f"Error processing image: {str(e)}"})

@app.route('/recognize_exit', methods=['POST'])
def recognize_exit():
    try:
        FACE_SIMILARITY_THRESHOLD, FACE_DETECTION_THRESHOLD = DatabaseManager.get_threshold_settings()
        # Get the image data from the request
        image_data = request.json['image'].split(',')[1]
        image_bytes = base64.b64decode(image_data)
        
        # Convert to numpy array
        nparr = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # Detect faces and process recognition
        distance, detected_id, user_inside, recognition_id = FaceRecognition.send_frame_for_recognition_sync(
            frame, 
            FACE_SIMILARITY_REQUEST_LINK
        )
        
        # Check recognition conditions
        if distance is None or distance > FACE_SIMILARITY_THRESHOLD or detected_id is None:
            return jsonify({"status": "error", "message": "Not recognized"})
        
        # Check if user is inside
        if not user_inside:
            return jsonify({
                "status": "warning",
                "message": f"User {detected_id} is not inside"
            })
        
        # Send to Django exit endpoint
        django_response = requests.post(DJANGO_EXIT_ENDPOINT, json={
            "recognition_id": recognition_id,
            "user_id": detected_id
        })
        
        # Check Django response
        if django_response.status_code == 200:   
            return jsonify({
                "status": "success",
                "message": f"User {detected_id} left (distance: {distance:.2f})"
            })
        else:
            error_data = json.loads(django_response.text)
            error_message = error_data['error'].strip("['']")

            return jsonify({
                "status": "error",
                "message": error_message
            })
    
    except Exception as e:
        return jsonify({"status": "error", "message": f"Error processing image: {str(e)}"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)