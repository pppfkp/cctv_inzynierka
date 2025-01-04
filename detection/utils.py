import os
from threading import Lock, Thread
import cv2
from psycopg2 import pool
import torch
from ultralytics import YOLO
from ultralytics.trackers.bot_sort import BOTSORT

CAMERA_LINK = os.getenv("CAMERA_LINK")
BATCH_SIZE = int(os.getenv("BATCH_SIZE"))
TRACKING_MODEL = os.getenv("TRACKING_MODEL")
FACE_DETECTION_MODEL = os.getenv("FACE_DETECTION_MODEL")
CAMERA_ID = int(os.getenv("CAMERA_ID"))
FACE_SIMILARITY_THRESHOLD = float(os.getenv("FACE_SIMILARITY_THRESHOLD"))
FACE_DETECTION_THRESHOLD = float(os.getenv("FACE_DETECTION_THRESHOLD"))
PERSON_DETECTION_THRESHOLD = float(os.getenv("PERSON_DETECTION_THRESHOLD"))
FACE_SIMILARITY_REQUEST_LINK =  os.getenv("FACE_SIMILARITY_REQUEST_LINK") # closest embedding request address
FPS = int(os.getenv("FPS"))

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

def generate_frames(cap):
    """Generate frames for the video feed."""
    while True:
        frame = cap.read()  # Read frame from the camera
        # Encode the frame to JPEG format
        _, buffer = cv2.imencode('.jpg', frame)
        # Yield the frame in a format suitable for streaming
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        
