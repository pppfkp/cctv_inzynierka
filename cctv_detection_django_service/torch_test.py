import torch

device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
print(f'Running on device: {torch.cuda.get_device_name(device)}')

import cv2
CAMERA_LINK = "rtsp://192.168.0.107"

cap = cv2.VideoCapture(CAMERA_LINK)

ret, frame = cap.read()

while ret:
    ret, frame = cap.read()
    if (cv2.waitKey(1) & 0xFF == ord('q')):
        break

cap.release()
cv2.destroyAllWindows()