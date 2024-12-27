import cv2
import tkinter as tk
from tkinter import ttk
from datetime import datetime
import requests
import threading
from ultralytics import YOLO
import PIL.Image, PIL.ImageTk
from utils.trackingUtils import send_frame_for_recognition_sync
from utils.timescaleUtils import save_exit_to_db, set_user_inside_status

# Constants
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
FACE_DETECTION_MODEL = "models/yolov10n-face.pt" 
FACE_DETECTION_THRESHOLD = 0.5
CAMERA_LINK = 0
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
    def __init__(self, window, window_title, video_source=0):
        self.window = window
        self.window.title(window_title)
        self.video_source = video_source
        self.cap = cv2.VideoCapture(self.video_source)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
        self.session = requests.Session()

        self.canvas = tk.Canvas(window, width=FRAME_WIDTH, height=FRAME_HEIGHT)
        self.canvas.pack()

        self.btn_recognize = ttk.Button(window, text="Recognize", command=self.start_recognition)
        self.btn_recognize.pack()

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

    def start_recognition(self):
        threading.Thread(target=self.recognize, daemon=True).start()

    def recognize(self):
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

App(tk.Tk(), "Exit App")