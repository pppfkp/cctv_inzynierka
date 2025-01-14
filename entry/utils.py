import asyncio
import os
import cv2
from psycopg2 import pool
import torch
from ultralytics import YOLO
import aiohttp
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Environment variables
FACE_DETECTION_MODEL = "yolov10n-face.pt"
FACE_SIMILARITY_THRESHOLD = 2.0
FACE_DETECTION_THRESHOLD = 2.0
FACE_SIMILARITY_REQUEST_LINK = os.getenv("FACE_SIMILARITY_REQUEST_LINK")

# Database connection settings
DB_SETTINGS = {
    "host": os.getenv("PGVECTOR_DB_HOST"),
    "port": int(os.getenv("PGVECTOR_DB_PORT")),
    "dbname": os.getenv("PGVECTOR_DB_NAME"),
    "user": os.getenv("PGVECTOR_DB_USER"),
    "password": os.getenv("PGVECTOR_DB_PASSWORD"),
}

# Create a connection pool
DB_POOL = pool.SimpleConnectionPool(
    minconn=1,
    maxconn=10,
    **DB_SETTINGS
)

# Initialize YOLO model
face_model = YOLO(FACE_DETECTION_MODEL, verbose=False).to('cuda')

class DatabaseManager:
    @staticmethod
    def save_entry_to_db(entry):
        try:
            conn = DB_POOL.getconn()
            cursor = conn.cursor()
            
            insert_query = """
            INSERT INTO stats_enter (
                time, user_id
            ) VALUES (%s, %s)
            """
            
            cursor.execute(insert_query, entry)
            conn.commit()
            print(f"saved entry to db")
        except Exception as e:
            print(f"Error saving data to DB: {e}")
        finally:
            if cursor:
                cursor.close()
            if conn:
                DB_POOL.putconn(conn)

    @staticmethod
    def save_exit_to_db(exit):
        try:
            conn = DB_POOL.getconn()
            cursor = conn.cursor()
            
            insert_query = """
            INSERT INTO stats_exit (
                time, user_id
            ) VALUES (%s, %s)
            """
            
            cursor.execute(insert_query, exit)
            conn.commit()
            print(f"saved exit to db")
        except Exception as e:
            print(f"Error saving data to DB: {e}")
        finally:
            if cursor:
                cursor.close()
            if conn:
                DB_POOL.putconn(conn)

    @staticmethod
    def set_user_inside_status(user_id, status):
        """
        Update the is_inside field for a user's TrackingSubject to True or False.
        
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

class FaceRecognition:
    @staticmethod
    def test_cuda():
        device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
        print(device)

    @staticmethod
    async def send_frame_for_recognition(frame, session, request_link):
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
            async with session.post(request_link, data=form) as response:
                # Check for successful response (status code 200)
                if response.status == 200:
                    # Parse JSON response
                    data = await response.json()
                    distance = data.get("distance", None)
                    user_id = data.get("user_id", None)
                    user_inside = data.get("user_inside")
                    print(f"face recognition distance: {distance} user_id: {user_id}")
                    return distance, user_id, user_inside
                else:
                    print(f"Error: Server returned status code {response.status}")
                    html_content = await response.text()  # Get the raw HTML error page
                    print(html_content)
                    return None, None, None
        except Exception as e:
            print(f"Error sending frame: {e}")
            return None, None, None

    @staticmethod
    def detect_faces(frame):
        """
        Detect faces in a frame using the YOLO model.
        
        Args:
            frame: The image frame to process
            
        Returns:
            List of bounding boxes for detected faces
        """
        results = face_model.predict(frame, conf=FACE_DETECTION_THRESHOLD)
        boxes = []
        for result in results:
            for box in result.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                boxes.append((x1, y1, x2, y2))
        return boxes

    @staticmethod
    # Synchronous wrapper for send_frame_for_recognition
    def send_frame_for_recognition_sync(frame, request_link):
        async def run_async():
            async with aiohttp.ClientSession() as session:
                return await FaceRecognition.send_frame_for_recognition(frame, session, request_link)
        
        return asyncio.run(run_async())