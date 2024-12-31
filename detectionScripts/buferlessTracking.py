import argparse
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
from utils.trackingUtils import Args, TrackUpdate, cut_the_frame_from_bbox, detect_face, send_frame_for_recognition, open_camera

# python buferlessTracking.py --camera_link rtsp://192.168.0.150 --camera_id 1 --fps_tracking 10 --batch_size 100 --face_detection_model yolov10n-face.pt --person_detection_model yolo11n.pt --face_similarity_treshold 0.7 --face_detection_treshold 0.4 --person_detection_treshold 0.6

def parse_arguments():
    parser = argparse.ArgumentParser(description="Run detection and tracking on a specific camera.")
    parser.add_argument("--camera_link", type=str, required=True, help="Link to the camera (rstp, http, or local webcam index)")
    parser.add_argument("--camera_id", type=int, required=True, help="ID for the camera")
    parser.add_argument("--fps_tracking", type=int, required=True, help="FPS for performing tracking")
    parser.add_argument("--batch_size", type=int, required=True, help="Batch size of detections for saving in the database")
    parser.add_argument("--face_detection_model", type=str, required=True, help="Face detection model name")
    parser.add_argument("--person_detection_model", type=str, required=True, help="Person detection model name")
    parser.add_argument("--face_similarity_treshold", type=float, required=True, help="Face similarity treshold")
    parser.add_argument("--face_detection_treshold", type=float, required=True, help="Face detection treshold")
    parser.add_argument("--person_detection_treshold", type=float, required=True, help="Person detection treshold")

    return parser.parse_args()

# Example values that will be later overriten by values from the args
BATCH_SIZE = 100  # batch size for saving in db
REQUEST_LINK = "http://localhost:8000/face_recognition/api/recognize/"  # closest embedding request address
TRACKING_MODEL = "models/yolo11n.pt"  # model for tracking and getting bounding boxes
FACE_DETECTION_MODEL = "models/yolov10n-face.pt"  # model for detecting faces before sending them to recognition
CAMERA_ID = 0
CAMERA_LINK = 0  # link to the camera (rst or http) when number then it's just a local webcam
FACE_SIMILARITY_THRESHOLD = 0.7  # threshold for face recognition through API
CSV_FILE = "detection_log.csv"  # CSV file with detections (for testing)
FACE_DETECTION_THRESHOLD = 0.4  # threshold for detection before recognition
PERSON_DETECTION_THRESHOLD = 0.6  # threshold for detecting a whole person
FRAME_WIDTH = 1920
FRAME_HEIGHT = 1080
FPS = 10
SAVE_TO_CSV_FILE = False

# Draw bounding boxes and tracking data
def visualize_tracks(frame, tracks):
    for track in tracks:
        x, y, w, h = map(int, track.xywh)
        track_id = track.track_id
        cv2.rectangle(frame, (x - int(w / 2), y - int(h / 2)), (x + int(w / 2), y + int(h / 2)), (0, 255, 0), 2)
        cv2.putText(frame, f"TRACK_ID: {track_id} USER_ID: {track_user_ids.get(track_id)}", 
                    (x - int(w / 2), y - int(h / 2) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    cv2.imshow("Tracking", frame)

# Dictionary to hold STrack ID and associated face embeddings
track_user_ids = {}
# New dictionary to store last known position
last_position = {}  
# Batch for storing data
data_batch = []

# CSV file with detections
columns = ["camera_link", 'track_id', "user_id", "date", "time", "x_center", "y_center", "width", "height"]
pd.DataFrame(columns=columns).to_csv(CSV_FILE, index=False, mode='w')
botsort_args = Args()

async def main():
    # Load the YOLO model
    tracking_model = YOLO(f"models/{TRACKING_MODEL}", verbose=False).to('cuda')
    face_model = YOLO(f"models/{FACE_DETECTION_MODEL}", verbose=False).to('cuda')
    print(f"------------------------------------tracking model: {tracking_model.device}-----------------------------------------")
    tracker = BOTSORT(botsort_args)  # Initialize the BOTSORT tracker

    cap = open_camera(CAMERA_LINK, FRAME_WIDTH, FRAME_HEIGHT)
    last_save_time = time.time()  # Track the last time data was saved
    fps = FPS  # Target FPS for saving data
    time_per_frame = 1.0 / fps 

    async with aiohttp.ClientSession() as session:
        while True:
            frame = cap.read()
            if frame is None:
                print("Waiting for frames...")
                time.sleep(0.1)  # Add a small delay if no frame is available
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
                        tracker.update(filtered_boxes.cpu())
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
                            distance, detected_id, user_inside = await send_frame_for_recognition(face_cropped, session, REQUEST_LINK)

                            if distance is not None and distance < FACE_SIMILARITY_THRESHOLD and user_inside:
                                user_id = detected_id
                                track_user_ids[track.track_id] = user_id
                    else:
                        user_id = track_user_ids[track.track_id]

                    now = datetime.now()
                    detection_data = pd.DataFrame([{
                            user_id,
                            CAMERA_ID, 
                            track.track_id,
                            now.strftime("%Y-%m-%d %H:%M:%S"),
                            float(track.xywh[0]),
                            float(track.xywh[1]),
                            float(track.xywh[2]),
                            float(track.xywh[3]),
                    }])

                    if SAVE_TO_CSV_FILE:
                        detection_data.to_csv(CSV_FILE, mode='a', index=False, header=False)

                    try:
                        # Create detection data 
                        detection_data = (
                            user_id,                # Matches the first column: user_id
                            CAMERA_ID,              # Matches the second column: camera_id
                            track.track_id,         # Matches the third column: track_id
                            now.strftime("%Y-%m-%d %H:%M:%S"),  # Matches the fourth column: time
                            float(track.xywh[0]),   # Matches the fifth column: x_center
                            float(track.xywh[1]),   # Matches the sixth column: y_center
                            float(track.xywh[2]),   # Matches the seventh column: width
                            float(track.xywh[3]),   # Matches the eighth column: height
                        )


                        # Debug print to confirm order
                        print(f"Tuple for insertion: {detection_data}")

                        data_batch.append(detection_data)

                        if len(data_batch) >= BATCH_SIZE:
                            save_to_timescaledb(data_batch)
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
    # python buferlessTracking.py --camera_link rtsp://192.168.0.150 --camera_id 1 --fps_tracking 10 --batch_size 100 --face_detection_model yolov10n-face.pt --person_detection_model yolo11n.pt --face_similarity_treshold 0.7 --face_detection_treshold 0.4 --person_detection_treshold 0.6
    args = parse_arguments()
    
    CAMERA_LINK = args.camera_link    
    print(f"CAMERA LINK: {CAMERA_LINK}")
    BATCH_SIZE = args.batch_size
    TRACKING_MODEL = args.person_detection_model
    FACE_DETECTION_MODEL = args.face_detection_model
    CAMERA_ID = args.camera_id
    CAMERA_LINK = args.camera_link
    FACE_SIMILARITY_THRESHOLD = args.face_similarity_treshold
    FACE_DETECTION_THRESHOLD = args.face_detection_treshold
    PERSON_DETECTION_THRESHOLD = args.person_detection_treshold
    FPS = args.fps_tracking

    asyncio.run(main())