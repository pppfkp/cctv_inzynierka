import asyncio
import json
import os
import signal
import socket
import sys
from threading import Lock, Thread
import cv2
import numpy as np
from psycopg2 import pool
import requests
import torch
from ultralytics import YOLO
from ultralytics.trackers.bot_sort import BOTSORT
import aiohttp

CAMERA_LINK = os.getenv("CAMERA_LINK")
BATCH_SIZE = int(os.getenv("BATCH_SIZE"))
TRACKING_MODEL = os.getenv("TRACKING_MODEL")
FACE_DETECTION_MODEL = os.getenv("FACE_DETECTION_MODEL")
CAMERA_ID = int(os.getenv("CAMERA_ID"))
FACE_SIMILARITY_THRESHOLD = float(os.getenv("FACE_SIMILARITY_THRESHOLD"))
FACE_DETECTION_THRESHOLD = float(os.getenv("FACE_DETECTION_THRESHOLD"))
PERSON_DETECTION_THRESHOLD = float(os.getenv("PERSON_DETECTION_THRESHOLD"))
FACE_SIMILARITY_REQUEST_LINK =  os.getenv("FACE_SIMILARITY_REQUEST_LINK") # closest embedding request address
FACE_SIMILARITY_REQUEST_LINK =  "http://host.docker.internal:8000/face_recognition/api/recognize/"
FPS = int(os.getenv("FPS"))
TIME_PER_FRAME = 1.0 / FPS

# Database connection settings from .env
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

# config values for BOTSORT
class BotsortArgs:
    def __init__(self):
        self.track_high_thresh = 0.5  
        self.track_low_thresh = 0.1   
        self.new_track_thresh = 0.3   
        self.track_buffer = 30        
        self.match_thresh = 0.8       
        self.proximity_thresh = 0.8
        self.appearance_thresh = 0.8
        self.with_reid = True
        self.gmc_method = 'sparseOptFlow'
        self.fuse_score = True
        self.verbose = False

class TrackUpdate:
    def __init__(self, xywh=None, conf=None, cls=None):
        self.xywh = xywh
        self.conf = conf
        self.cls = cls

# Dictionary to hold STrack ID and associated face embeddings
track_user_ids = {}

# New dictionary to store last known position
last_position = {}  

# Batch for storing data
data_batch = []

tracking_model = YOLO(TRACKING_MODEL, verbose=False).to('cuda')
face_model = YOLO(FACE_DETECTION_MODEL, verbose=False).to('cuda')
tracker = BOTSORT(BotsortArgs())  # Initialize the BOTSORT tracker



def test_cuda():
    device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
    print(device)

class VideoStream:
    def __init__(self, link, frame_width, frame_height):
        self.stream = cv2.VideoCapture(link)
        self.lock = Lock()
        self.latest_frame = None
        self.stopped = False

        if self.stream.isOpened():
            self.stream.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize buffering
            self.stream.set(cv2.CAP_PROP_FRAME_WIDTH, frame_width)
            self.stream.set(cv2.CAP_PROP_FRAME_HEIGHT, frame_height)

    def start(self):
        Thread(target=self.update, args=(), daemon=True).start()
        return self

    def update(self):
        while not self.stopped:
            if self.stream.isOpened():
                ret, frame = self.stream.read()
                if ret:
                    with self.lock:
                        self.latest_frame = frame

    def read(self):
        with self.lock:
            return self.latest_frame

    def stop(self):
        self.stopped = True
        self.stream.release()

def open_camera(link, frame_width=640, frame_heigth=480):
    video_stream = VideoStream(link, frame_width, frame_heigth)
    video_stream.start()
    return video_stream

def cut_the_frame_from_bbox(frame, xywh):
    x, y, w, h = map(int, xywh)
    
    # Ensure the bounding box coordinates are within frame boundaries
    height, width = frame.shape[:2]
    x1 = max(0, x - int(w / 2))
    y1 = max(0, y - int(h / 2))
    x2 = min(width, x + int(w / 2))
    y2 = min(height, y + int(h / 2))
    
    # Extract the region of interest (ROI)
    roi = frame[y1:y2, x1:x2]

    return roi

def detect_face(img, face_model, threshold):
    # Run the face detection model
    result = face_model(img)
    
    largest_face = None
    max_area = 0

    # Iterate over all detected boxes
    for box in result[0].boxes:
        conf = box.conf.cpu().numpy()[0]
        if conf < threshold:
            continue

        # Calculate the area of the bounding box
        _, _, w, h = box.xywh[0].cpu().numpy()
        area = w * h

        # Update largest_face if this box has a larger area
        if area > max_area:
            max_area = area
            largest_face = box

    if largest_face:
        # print(f"Largest face box: {largest_face}")
        return largest_face
    else:
        print("No face detected above the threshold.")
        return None          
    
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

def generate_frames(cap):
    """Generate frames for the video feed."""
    while True:
        frame = cap.read()  # Read frame from the camera
        # Encode the frame to JPEG format
        _, buffer = cv2.imencode('.jpg', frame)
        # Yield the frame in a format suitable for streaming
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

def visualize_tracks(frame, tracks, track_user_ids):
    """Draw bounding boxes and tracking data."""
    for track in tracks:
        x, y, w, h = map(int, track.xywh)
        track_id = track.track_id
        cv2.rectangle(frame, (x - int(w / 2), y - int(h / 2)), (x + int(w / 2), y + int(h / 2)), (0, 255, 0), 2)
        cv2.putText(frame, f"TRACK_ID: {track_id} USER_ID: {track_user_ids.get(track_id)}", 
                    (x - int(w / 2), y - int(h / 2) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    return frame

class StreamClient:
    def __init__(self, server_host='localhost', server_port=12346):
        self.server_host = server_host
        self.server_port = server_port
        self.client_socket = None
        self.connected = False
        
    async def connect(self, retry_count=9999999, retry_delay=2):
        for attempt in range(retry_count):
            try:
                self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.client_socket.connect((self.server_host, self.server_port))
                self.connected = True
                print(f"Connected to server at {self.server_host}:{self.server_port}")
                return True
            except ConnectionRefusedError:
                print(f"Connection attempt {attempt + 1}/{retry_count} failed. Retrying in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
            except Exception as e:
                print(f"Unexpected error while connecting: {e}")
                if self.client_socket:
                    self.client_socket.close()
                await asyncio.sleep(retry_delay)
        
        print("Failed to connect to server after all attempts")
        return False

    def send_frame(self, frame):
        if not self.connected or not self.client_socket:
            return False
            
        try:
            # Encode the frame
            _, encoded_frame = cv2.imencode('.jpg', frame)
            frame_data = encoded_frame.tobytes()
            
            # Send frame size first
            size = len(frame_data)
            self.client_socket.sendall(size.to_bytes(4, byteorder='big'))
            
            # Then send the frame data
            self.client_socket.sendall(frame_data)
            return True
        except Exception as e:
            print(f"Error sending frame: {e}")
            self.connected = False
            return False

    def cleanup(self):
        if self.client_socket:
            self.client_socket.close()
            self.connected = False

class StreamServer:
    def __init__(self, host='localhost', port=12346):
        self.host = host
        self.port = port
        self.server_socket = None
        self.client_socket = None
        self.setup_socket()
        
        # Register cleanup on shutdown
        signal.signal(signal.SIGINT, self.cleanup)
        signal.signal(signal.SIGTERM, self.cleanup)

    def setup_socket(self):
        if self.server_socket:
            self.cleanup()
            
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Add socket reuse option
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(1)
            print(f"Server listening on {self.host}:{self.port}")
        except OSError as e:
            print(f"Failed to bind to port {self.port}: {e}")
            self.cleanup()
            sys.exit(1)

    def wait_for_client(self):
        print("Waiting for client connection...")
        try:
            self.client_socket, client_address = self.server_socket.accept()
            print(f"Client connected from {client_address}")
        except Exception as e:
            print(f"Error accepting client connection: {e}")
            self.cleanup()
            sys.exit(1)

    def cleanup(self, *args):
        print("\nCleaning up server resources...")
        if self.client_socket:
            self.client_socket.close()
        if self.server_socket:
            self.server_socket.close()
        sys.exit(0)

    def receive_frame(self):
        if not self.client_socket:
            return None
            
        try:
            # First receive the frame size
            size_data = self.client_socket.recv(4)
            if not size_data:
                return None
            
            frame_size = int.from_bytes(size_data, byteorder='big')
            
            # Then receive the actual frame data
            data = b""
            while len(data) < frame_size:
                packet = self.client_socket.recv(min(frame_size - len(data), 4096))
                if not packet:
                    return None
                data += packet

            # Decode the frame
            np_arr = np.frombuffer(data, dtype=np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            return frame
            
        except Exception as e:
            print(f"Error receiving frame: {e}")
            return None
        
def save_detections(data_batch):
    """
    Save a batch of detection data to the database.

    Args:
        data_batch (list): A list of tuples containing detection data to insert.
                           Each tuple should contain:
                           (user_id, camera_id, track_id, time, x_center, y_center, width, height)
    """
    try:
        conn = DB_POOL.getconn()
        cursor = conn.cursor()

        # Updated INSERT query to match the Detection model with track_id
        insert_query = """
        INSERT INTO stats_detection (
            user_id, camera_id, track_id, time, xywh
        ) VALUES (%s, %s, %s, %s, array[%s, %s, %s, %s])
        """

        # Transform data_batch to match the query's format
        transformed_batch = [
            (user_id, camera_id, track_id, time, x_center, y_center, width, height)
            for user_id, camera_id, track_id, time, x_center, y_center, width, height in data_batch
        ]

        cursor.executemany(insert_query, transformed_batch)
        conn.commit()
        print(f"{len(data_batch)} rows saved to DB")
    except Exception as e:
        print(f"Error saving data to DB: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            DB_POOL.putconn(conn)