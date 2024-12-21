import json
import aiohttp
import cv2
import requests

# config values for BOTSORT
class Args:
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

class TrackUpdate:
    def __init__(self, xywh=None, conf=None, cls=None):
        self.xywh = xywh
        self.conf = conf
        self.cls = cls


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


def send_frame_for_recognition_sync(frame, request_link):
    try:
        # Encode the frame as JPEG
        _, img_encoded = cv2.imencode('.jpg', frame)
        img_bytes = img_encoded.tobytes()

        # Send the frame to the API
        response = requests.post(request_link, files={"file": ("frame.jpg", img_bytes, 'image/jpeg')})

        # Parse the JSON response and handle potential missing data
        data = json.loads(response.text)
        distance = data.get("distance", None)
        user_id = data.get("user_id", None)

        # Return distance and user_id, or None if not found
        return distance, user_id

    except (requests.RequestException, json.JSONDecodeError) as e:
        # Handle request or decoding errors
        print(f"Error sending frame for recognition: {e}")
        return None, None          
    

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
            data = await response.json()
            distance = data.get("distance", None)
            user_id = data.get("user_id", None)
            user_inside = data.get("user_inside")
            print(f"face recognition distance: {distance} user_id: {user_id}")
            return distance, user_id, user_inside
    except Exception as e:
        print(f"Error sending frame: {e}")
        return None, None, None    