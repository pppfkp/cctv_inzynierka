import cv2
import argparse
import tkinter as tk
from tkinter import ttk
from datetime import datetime
import requests
import threading
from ultralytics import YOLO
import PIL.Image, PIL.ImageTk
from utils.trackingUtils import send_frame_for_recognition_sync
from utils.timescaleUtils import save_entry_to_db, set_user_inside_status, save_exit_to_db

# python enter.py --camera_index 0 --face_detection_model models/yolov10n-face.pt --face_similarity_treshold 0.5 --face_detection_treshold 0.95

def parse_arguments():
    parser = argparse.ArgumentParser(description="Run detection and tracking on a specific camera.")
    parser.add_argument("--camera_index", type=int, required=True, help="Index of the camera (0 is default)")
    parser.add_argument("--face_detection_model", type=str, required=True, help="Face detection model name")
    parser.add_argument("--face_similarity_treshold", type=float, required=True, help="Face similarity treshold")
    parser.add_argument("--face_detection_treshold", type=float, required=True, help="Face detection treshold")

    return parser.parse_args()

args = parse_arguments()

CAMERA_LINK = args.camera_index
FACE_DETECTION_MODEL = args.face_detection_model
FACE_SIMILARITY_THRESHOLD = args.face_similarity_treshold
FACE_DETECTION_THRESHOLD = args.face_detection_treshold

# Constants
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
REQUEST_LINK = "http://localhost:8000/face_recognition/api/recognize/" 

# Initialize YOLO model (do this outside the loop)
try:
    face_model = YOLO(FACE_DETECTION_MODEL, verbose=False).to('cuda')
except Exception as e:
    print(f"Error loading YOLO model: {e}")
    exit()

def detect_faces(frame):
    results = face_model.predict(frame, conf=FACE_DETECTION_THRESHOLD)
    boxes = []
    for result in results:
        for box in result.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            boxes.append((x1, y1, x2, y2))
    return boxes

class App:
    def __init__(self, window, window_title, video_source=CAMERA_LINK):
        self.window = window
        self.window.title(window_title)
        self.video_source = video_source
        self.cap = cv2.VideoCapture(self.video_source)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
        self.session = requests.Session()

        self.canvas = tk.Canvas(window, width=FRAME_WIDTH, height=FRAME_HEIGHT)
        self.canvas.pack()

        # Recognize (entry) button
        self.btn_recognize_entry = ttk.Button(window, text="Recognize Entry", command=self.start_recognition_entry)
        self.btn_recognize_entry.pack()

        # Recognize (exit) button
        self.btn_recognize_exit = ttk.Button(window, text="Recognize Exit", command=self.start_recognition_exit)
        self.btn_recognize_exit.pack()

        self.status_label = ttk.Label(window, text="", foreground='black')
        self.status_label.pack()

        self.delay = 15  # milliseconds
        self.update()
        self.window.mainloop()

    def set_status(self, message, color):
        self.status_label.config(text=message, foreground=color)

    def update(self):
        ret, frame = self.cap.read()
        if ret:
            self.photo = PIL.ImageTk.PhotoImage(image=PIL.Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)))
            self.canvas.create_image(0, 0, image=self.photo, anchor=tk.NW)
        self.window.after(self.delay, self.update)

    def start_recognition_entry(self):
        threading.Thread(target=self.recognize_entry, daemon=True).start()

    def start_recognition_exit(self):
        threading.Thread(target=self.recognize_exit, daemon=True).start()

    def recognize_entry(self):
        ret, frame = self.cap.read()
        if ret:
            face_boxes = detect_faces(frame)
            for box in face_boxes:
                x1, y1, x2, y2 = box
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            distance, detected_id, user_inside = send_frame_for_recognition_sync(frame, REQUEST_LINK)
            if distance is None or detected_id is None:
                self.set_status("Not recognized", 'red')
            else:
                if user_inside:
                    self.set_status(f"User {detected_id} is already inside", 'orange')
                else:
                    self.set_status(f"User {detected_id} entered (distance: {distance:.2f})", 'green')
                    save_entry_to_db((datetime.now().strftime("%Y-%m-%d %H:%M:%S"), detected_id))
                    set_user_inside_status(detected_id, True)
        else:
            self.set_status("Error: Could not capture frame", 'red')

    def recognize_exit(self):
        ret, frame = self.cap.read()
        if ret:
            face_boxes = detect_faces(frame)
            for box in face_boxes:
                x1, y1, x2, y2 = box
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            distance, detected_id, user_inside = send_frame_for_recognition_sync(frame, REQUEST_LINK)
            if distance is None or detected_id is None:
                self.set_status("Not recognized", 'red')
            else:
                if user_inside:
                    self.set_status(f"User {detected_id} left (distance: {distance:.2f})", 'green')
                    set_user_inside_status(detected_id, False)
                    save_exit_to_db((datetime.now().strftime("%Y-%m-%d %H:%M:%S"), detected_id))
                else:
                    self.set_status(f"User {detected_id} is not inside", 'orange')
        else:
            self.set_status("Error: Could not capture frame", 'red')

App(tk.Tk(), "Entry and Exit App")