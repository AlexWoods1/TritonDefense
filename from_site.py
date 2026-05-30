import cv2
import torch

# 1. Load the YOLOv5 model
model = torch.hub.load(
    'ultralytics/yolov5', 'yolov5s', pretrained=True, trust_repo=True
)

# 2. Start the webcam
camera_dev_nr = 0
cap = cv2.VideoCapture(camera_dev_nr)

while True:
    # 3. Read a frame from the webcam
    ret, frame = cap.read()
    if not ret:
        break

    # 4. Perform object detection
    results = model(frame)

    # 5. Render the results on the frame
    frame = results.render()[0]

    # 6. Display the frame
    cv2.imshow('YOLOv5 Realtime Object Detection', frame)

    # 7. Break the loop if the user presses 'q'
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# 8. Clean up
cap.release()
cv2.destroyAllWindows()