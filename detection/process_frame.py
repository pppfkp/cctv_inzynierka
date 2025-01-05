import time
import aiohttp
import asyncio
import cv2
import numpy as np
import socket
from datetime import datetime
from utils import StreamClient, open_camera, CAMERA_LINK, TIME_PER_FRAME, tracking_model, PERSON_DETECTION_THRESHOLD, tracker, TrackUpdate, track_user_ids, last_position, cut_the_frame_from_bbox, detect_face, face_model, FACE_DETECTION_THRESHOLD, send_frame_for_recognition, FACE_SIMILARITY_REQUEST_LINK, FACE_SIMILARITY_THRESHOLD, CAMERA_ID, visualize_tracks

# Initialize camera feed
cap = open_camera(CAMERA_LINK)



# Frame dimensions
frame_width = 640
frame_height = 480
frame_shape = (frame_height, frame_width, 3)

async def main():
    last_save_time = time.time()

    # Initialize client
    client = StreamClient()
    if not await client.connect():
        return
    try:
        async with aiohttp.ClientSession() as session:
            while True:
                frame = cap.read()
                if frame is None:
                    print("Waiting for frames...")
                    time.sleep(0.1)
                    continue

                current_time = time.time()

                # Process the frame every TIME_PER_FRAME
                if current_time - last_save_time >= TIME_PER_FRAME:
                    result = tracking_model(frame)[0]

                    # Filter detections for people
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
                                distance, detected_id, user_inside = await send_frame_for_recognition(face_cropped, session, FACE_SIMILARITY_REQUEST_LINK)

                                if distance is not None and distance < FACE_SIMILARITY_THRESHOLD and user_inside:
                                    user_id = detected_id
                                    track_user_ids[track.track_id] = user_id
                        else:
                            user_id = track_user_ids[track.track_id]

                        try:
                            # Create detection data for shared memory
                            detection_data = (
                                user_id,
                                CAMERA_ID,
                                track.track_id,
                                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                float(track.xywh[0]),
                                float(track.xywh[1]),
                                float(track.xywh[2]),
                                float(track.xywh[3]),
                            )

                            # You can store detection_data to a database here if needed
                            print(detection_data)

                        except Exception as e:
                            print(f"Error in processing frame: {e}")

                    last_save_time = current_time  # Update the last save time

                    # Copy the frame to be visualized
                    processed_frame = visualize_tracks(frame, tracker.tracked_stracks, track_user_ids)
                
                    # Send the processed frame
                    if not client.send_frame(processed_frame):
                        print("Lost connection to server, attempting to reconnect...")
                        if await client.connect():
                            continue
                        else:
                            break
    except KeyboardInterrupt:
        print("\nShutting down client...")
    finally:
        client.cleanup()
        cap.release()

if __name__ == '__main__':
    asyncio.run(main())
