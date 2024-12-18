from datetime import datetime
import cv2
from ultralytics import YOLO
import aiohttp
import asyncio
import time
from utils.trackingUtils import detect_face, send_frame_for_recognition
from utils.timescaleUtils import save_entry_to_db, set_user_inside_status
import logging

logging.basicConfig(level=logging.INFO)

FRAME_WIDTH = 1920
FRAME_HEIGHT = 1080
FACE_DETECTION_MODEL = "models/yolov10n-face.pt" 
FACE_DETECTION_THRESHOLD = 0.5
CAMERA_LINK = 0 
REQUEST_LINK = "http://localhost:8000/face_recognition/api/recognize/"  # closest embedding request address


def open_camera(link):
    cap = cv2.VideoCapture(link)
    if cap.isOpened():
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize buffering
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    return cap

face_model = YOLO(FACE_DETECTION_MODEL, verbose=False).to('cuda')

async def main():
    cap = open_camera(CAMERA_LINK)

    async with aiohttp.ClientSession() as session:
        while True:
            if not cap.isOpened():
                logging.error("Unable to open camera. Retrying in 5 seconds...")
                time.sleep(5)
                cap = open_camera(CAMERA_LINK)
                continue

            ret, frame = cap.read()

            if not ret:
                logging.error("Unable to retrieve frame. Retrying connection...")
                cap.release()
                time.sleep(2)
                cap = open_camera(CAMERA_LINK)
                continue

            # Detect faces
            result = detect_face(frame, face_model, FACE_DETECTION_THRESHOLD)

            # If a face was detected, draw a bounding box around it
            if result is not None:
                # result is the largest face detected, with `xywh` coordinates.
                x_center, y_center, w, h = result.xywh[0].cpu().numpy()

                # Convert center-based coordinates to top-left (x1, y1) and bottom-right (x2, y2)
                x1 = int(x_center - w / 2)
                y1 = int(y_center - h / 2)
                x2 = int(x_center + w / 2)
                y2 = int(y_center + h / 2)

                # Draw a rectangle around the detected face
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

            # Display frame
            cv2.imshow('Face Detection', frame)

            # Exit condition
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

            # Exit condition
            if cv2.waitKey(1) & 0xFF == ord('s'):
                distance, detected_id, user_inside = await send_frame_for_recognition(frame, session, REQUEST_LINK)
                
                if distance is not None and detected_id is not None:
                    if user_inside:
                        print("user is already inside")
                    else: 
                        print(f"distance: {distance} user_id: {detected_id} user_inside: {user_inside}")
                        save_entry_to_db((datetime.now().strftime("%Y-%m-%d %H:%M:%S"), detected_id))
                        set_user_inside_status(detected_id, True)


        # Release resources
        cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    asyncio.run(main())