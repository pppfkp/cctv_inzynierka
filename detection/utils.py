from threading import Lock, Thread
import cv2
import torch
import ultralytics

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
        
def generate_frames(cap):
    """Generate frames for the video feed with drawing."""
    while True:
        # Read frame from the camera
        frame = cap.read()

        # Example of drawing on the frame (e.g., drawing a rectangle and text)
        cv2.rectangle(frame, (50, 50), (200, 200), (0, 255, 0), 3)  # Draw green rectangle
        cv2.putText(frame, 'Hello World', (100, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)  # Add text

        # Encode the altered frame to JPEG format
        _, buffer = cv2.imencode('.jpg', frame)

        # Yield the frame in a format suitable for streaming
        yield (b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')