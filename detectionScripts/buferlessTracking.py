import asyncio
import aiohttp
from utils.timescaleUtils import save_to_timescaledb
import cv2
from ultralytics import YOLO
from ultralytics.trackers.bot_sort import BOTSORT, STrack
import json
import requests
import pandas as pd
from datetime import datetime
import torch
import numpy as np
import time
from utils.trackingUtils import Args, TrackUpdate, cut_the_frame_from_bbox, detect_face, send_frame_for_recognition

BATCH_SIZE = 100  # batch size for saving in timescaledb
REQUEST_LINK = "http://localhost:8000/face_recognition/api/recognize/"  # closest embedding request address
TRACKING_MODEL = "models/yolo11n.pt"  # model for tracking and getting bounding boxes
FACE_DETECTION_MODEL = "models/yolov10n-face.pt"  # model for detecting faces before sending them to recognition
CAMERA_LINK = 0  # link to the camera (rst or http) when number then it's just a local webcam
FACE_SIMILARITY_THRESHOLD = 0.7  # threshold for face recognition through API
CSV_FILE = "detection_log.csv"  # CSV file with detections (for testing)
FACE_DETECTION_THRESHOLD = 0.4  # threshold for detection before recognition
PERSON_DETECTION_THRESHOLD = 0.6  # threshold for detecting a whole person
FRAME_WIDTH = 1920
FRAME_HEIGHT = 1080
FPS = 10

# Draw bounding boxes and tracking data
def visualize_tracks(frame, tracks):
    for track in tracks:
        x, y, w, h = map(int, track.xywh)
        track_id = track.track_id
        cv2.rectangle(frame, (x - int(w / 2), y - int(h / 2)), (x + int(w / 2), y + int(h / 2)), (0, 255, 0), 2)
        cv2.putText(frame, f"TRACK_ID: {track_id} USER_ID: {track_user_ids.get(track_id)}", 
                    (x - int(w / 2), y - int(h / 2) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    cv2.imshow("Tracking", frame)

def open_camera(link):
    cap = cv2.VideoCapture(link)
    if cap.isOpened():
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize buffering
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    return cap


# Dictionary to hold STrack ID and associated face embeddings
track_user_ids = {}
# New dictionary to store last known position
last_position = {}  
# Batch for storing data
data_batch = []

# CSV file with detections
columns = ["camera_link", 'track_id', "user_id", "date", "time", "x_center", "y_center", "width", "height"]
pd.DataFrame(columns=columns).to_csv(CSV_FILE, index=False, mode='w')
args = Args()

# Load the YOLO model
tracking_model = YOLO(TRACKING_MODEL, verbose=False).to('cuda')
face_model = YOLO(FACE_DETECTION_MODEL, verbose=False).to('cuda')
print(f"------------------------------------tracking model: {tracking_model.device}-----------------------------------------")
tracker = BOTSORT(args)  # Initialize the BOTSORT tracker

async def main():
    cap = open_camera(CAMERA_LINK)
    last_save_time = time.time()  # Track the last time data was saved
    fps = FPS  # Target FPS for saving data
    time_per_frame = 1.0 / fps  # Time per frame for 15 FPS

    async with aiohttp.ClientSession() as session:
        while True:
            if not cap.isOpened():
                print("Error: Unable to open camera. Retrying in 5 seconds...")
                time.sleep(5)  # Wait before retrying
                cap = open_camera(CAMERA_LINK)  # Attempt to reconnect
                continue

            ret, frame = cap.read()

            if not ret:
                print("Error: Unable to retrieve frame. Retrying connection...")
                cap.release()
                time.sleep(2)  # Small delay before retrying
                cap = open_camera(CAMERA_LINK)  # Attempt to reconnect
                continue

            current_time = time.time()

            # If enough time has passed, process and save data
            if current_time - last_save_time >= time_per_frame:
                result = tracking_model(frame)[0]

                # Filter detections to include only people
                person_indices = (result.boxes.cls == 0) & (result.boxes.conf > PERSON_DETECTION_THRESHOLD)
                filtered_boxes = result.boxes[person_indices]

                if filtered_boxes.shape[0] > 1:
                    try:
                        tracked = tracker.update(filtered_boxes.cpu())
                    except IndexError:
                        print("index error")

                if filtered_boxes.shape[0] == 1:
                    try:
                        box = filtered_boxes[0]
                        track_update = TrackUpdate(box.xywh.cpu().numpy(), box.conf.cpu().numpy(), box.cls.cpu().numpy())
                        tracker.update(track_update)
                    except IndexError:
                        print("index error")

                for track in tracker.removed_stracks:
                    if track.track_id in track_user_ids:
                        track_user_ids.pop(track.track_id)

                for track in tracker.tracked_stracks:
                    position = (float(track.xywh[0]), float(track.xywh[1]))

                    if track.track_id in last_position and last_position[track.track_id] == position:
                        continue

                    last_position[track.track_id] = position

                    if track.track_id not in track_user_ids:
                        user_id = None
                        cropped_frame = cut_the_frame_from_bbox(frame, track.xywh)
                        face = detect_face(cropped_frame, face_model, FACE_DETECTION_THRESHOLD)

                        if face is not None:
                            face_cropped = cut_the_frame_from_bbox(cropped_frame, face.xywh[0].cpu().numpy())
                            distance, detected_id = await send_frame_for_recognition(face_cropped, session, REQUEST_LINK)

                            if distance is not None and distance < FACE_SIMILARITY_THRESHOLD:
                                user_id = detected_id
                                track_user_ids[track.track_id] = user_id
                    else:
                        user_id = track_user_ids[track.track_id]

                    now = datetime.now()
                    detection_data = pd.DataFrame([{
                        "camera_link": CAMERA_LINK,
                        'track_id': track.track_id,
                        "user_id": user_id,
                        "date": now.strftime("%Y-%m-%d"),
                        "time": now.strftime("%H:%M:%S"),
                        "x_center": float(track.xywh[0]),
                        "y_center": float(track.xywh[1]),
                        "width": float(track.xywh[2]),
                        "height": float(track.xywh[3]),
                    }])

                    detection_data.to_csv(CSV_FILE, mode='a', index=False, header=False)

                    try:
                        detection_data = (
                            CAMERA_LINK,
                            track.track_id,
                            user_id,
                            now.strftime("%Y-%m-%d"),
                            now.strftime("%H:%M:%S"),
                            float(track.xywh[0]),
                            float(track.xywh[1]),
                            float(track.xywh[2]),
                            float(track.xywh[3]),
                        )

                        data_batch.append(detection_data)

                        if len(data_batch) >= BATCH_SIZE:
                            # save_to_timescaledb(data_batch)
                            data_batch.clear()

                    except Exception as e:
                        print(f"Error in main loop: {e}")

                visualize_tracks(frame, tracker.tracked_stracks)
                last_save_time = current_time  # Update the last save time

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        if data_batch:
            save_to_timescaledb(data_batch)

if __name__ == "__main__":
    asyncio.run(main())