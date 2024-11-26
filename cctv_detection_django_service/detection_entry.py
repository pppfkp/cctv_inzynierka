import cv2

CAMERA_LINK = "rtsp://192.168.0.101"
# CAMERA_LINK = 0  # Uncomment this to use the default webcam

# Open the camera connection
cap = cv2.VideoCapture(CAMERA_LINK)

if not cap.isOpened():
    print("Error: Unable to open camera")
else:
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize buffering
    while True:
        ret, frame = cap.read()

        if not ret:
            print("Error: Unable to retrieve frame from camera")
            break

        cv2.imshow('frame', frame)

        # Break the loop if 'q' is pressed
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

# Release resources
cap.release()
cv2.destroyAllWindows()
