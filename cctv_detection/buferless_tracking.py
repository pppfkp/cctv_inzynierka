import asyncio
import aiohttp
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
from utils.tracking_utils import Args, TrackUpdate, cut_the_frame_from_bbox, detect_face, send_frame_for_recognition

REQUEST_LINK = "http://localhost:8001/api/find-closest-embedding/" # closest embedding request address
TRACKING_MODEL = "models/yolo11n.pt" # model for tracking and getting bounding boxes
FACE_DETECTION_MODEL = "models/yolov10n-face.pt" # model for detecting faces before sending them to recognition
CAMERA_LINK = 0 # link to the camera (rst or http) when number then it's just a local webcam
FACE_SIMILARITY_THRESHOLD = 0.7 # treshold for face recognition through api
CSV_FILE = "detection_log.csv" # csv file with detections (for testing)
# TRACK_EVERY_N_FRAMES = 2 # if you don't want to perform detection every frame
FACE_DETECTION_THRESHOLD = 0.4 # treshold for detection before recognition
PERSON_DETECTION_THRESHOLD = 0.6 # treshold for detecting a whole person
FRAME_WIDTH = 1920
FRAME_HEIGHT = 1080

# Draw bounding boxes and tracking data
def visualize_tracks(frame, tracks):
    for track in tracks:
        # Extract the bounding box coordinates and track ID
        x, y, w, h = map(int, track.xywh)
        track_id = track.track_id

        # Draw the bounding box rectangle
        cv2.rectangle(frame, (x - int(w / 2), y - int(h / 2)), (x + int(w / 2), y + int(h / 2)), (0, 255, 0), 2)

        # Display the track ID
        cv2.putText(frame, f"TRACK_ID: {track_id} USER_ID: {track_user_ids.get(track_id)}", (x - int(w / 2), y - int(h / 2) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    # Show the frame with visualized tracks
    cv2.imshow("Tracking", frame)

# Function to open the camera connection
def open_camera(link):
    cap = cv2.VideoCapture(link)
    if cap.isOpened():
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize buffering
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    return cap


# Dictionary to hold STrack ID and associated face embeddings
track_user_ids = {}
last_position = {}  # New dictionary to store last known position

# csv file with detections
columns = ["camera_link", 'track_id', "user_id", "date", "time", "x_center", "y_center", "width", "height"]
pd.DataFrame(columns=columns).to_csv(CSV_FILE, index=False, mode='w')
args = Args()

# Load the YOLO model
tracking_model = YOLO(TRACKING_MODEL, verbose=False).to('cuda')
face_model = YOLO(FACE_DETECTION_MODEL, verbose=False).to('cuda')
print(f"------------------------------------tracking model: {tracking_model.device}-----------------------------------------")
tracker = BOTSORT(args)  # Initialize the BOTSORT tracker

async def main():
    # Initialize camera
    cap = open_camera(CAMERA_LINK)

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

            # correct frame
            # cv2.imshow('frame', frame) # just show the frame

            #  dete cting every n frames
            # frame_count += 1
            # if frame_count % TRACK_EVERY_N_FRAMES != 0:
            #     visualize_tracks(frame, tracker.tracked_stracks)
            #     continue

            result = tracking_model(frame)[0]

            # Filter detections to include only people
            person_indices = (result.boxes.cls == 0) & (result.boxes.conf > PERSON_DETECTION_THRESHOLD)

            filtered_boxes = result.boxes[person_indices]

            # Update tracker with filtered boxes
            if filtered_boxes.shape[0] > 1:
                try:
                    tracked = tracker.update(filtered_boxes.cpu())
                except IndexError:
                    print("index error")
            
            if filtered_boxes.shape[0] == 1:
                try:
                    box = filtered_boxes[0]
                    x_center, y_center, width, height = box.xywh[0].cpu().numpy()  # Extract the bounding box
                    conf = box.conf.cpu().numpy()[0]  # Confidence score
                    cls = box.cls.cpu().numpy()[0]  # Class label

                    track_update = TrackUpdate(box.xywh.cpu().numpy(), box.conf.cpu().numpy(), box.cls.cpu().numpy())
                    tracked = tracker.update(track_update)
                except IndexError:
                    print("index error")




            # Clean the tracking-user association table from lost tracks
            for track in tracker.removed_stracks:
                if track.track_id in track_user_ids:
                    track_user_ids.pop(track.track_id)

            

            for track in tracker.tracked_stracks:
                position = (float(track.xywh[0]), float(track.xywh[1]))

                # if the position hasn't changed do nothing- that has to do with tracks that are lost but not removed
                if track.track_id in last_position and last_position[track.track_id] == position: 
                    continue

                # Save current position in last_position
                last_position[track.track_id] = position

                if track.track_id not in track_user_ids:
                    user_id = None

                    cropped_frame = cut_the_frame_from_bbox(frame, track.xywh)
                    face = detect_face(cropped_frame, face_model, FACE_DETECTION_THRESHOLD)
                    
                    # if face was detected then perform the face recognition
                    if face is not None:
                        face_cropped = cut_the_frame_from_bbox(cropped_frame, face.xywh[0].cpu().numpy())
                        distance, detected_id = await send_frame_for_recognition(face_cropped, session, REQUEST_LINK)

                        # here insert logic for getting only the users that are currently inside
                        if distance is not None and distance < FACE_SIMILARITY_THRESHOLD:
                            user_id = detected_id
                            track_user_ids[track.track_id] = user_id
                else:
                    user_id = track_user_ids[track.track_id] # if face is already associated with track, just use the already given user_id

                now = datetime.now()
                detection_data = pd.DataFrame([{
                    "camera_link": CAMERA_LINK,
                    'track_id': track.track_id,
                    "user_id": user_id,
                    "date": now.strftime("%Y-%m-%d"),
                    "time": now.strftime("%H:%M:%S"),
                    "x_center": float(track.xywh[0]),
                    "y_center":  float(track.xywh[1]),
                    "width":  float(track.xywh[2]),
                    "height":  float(track.xywh[3]),
                }])

                detection_data.to_csv(CSV_FILE, mode='a', index=False, header=False)
                print("Saved")    

                

                

            visualize_tracks(frame, tracker.tracked_stracks)


            # Break the loop if 'q' is pressed
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

if __name__ == "__main__":
    asyncio.run(main())