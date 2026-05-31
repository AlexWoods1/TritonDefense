import cv2
import torch
import time

# 1. Load the YOLOv5 model
model = torch.hub.load(
    'ultralytics/yolov5', 'yolov5s', pretrained=True, trust_repo=True
)

# 2. Configure camera pacing
IDLE_FPS = 2
ACTIVE_FPS = 15
ACTIVE_HOLD_SECONDS = 3
PERSON_CLASS_ID = 0

# 3. Start the webcam
camera_dev_nr = 0
cap = cv2.VideoCapture(camera_dev_nr)
last_person_seen_at = 0.0

while True:
    loop_started_at = time.monotonic()

    # 4. Read a frame from the webcam
    ret, frame = cap.read()
    if not ret:
        break

    # 5. Perform object detection
    results = model(frame)
    detected_classes = results.pred[0][:, -1].tolist()
    person_detected = PERSON_CLASS_ID in detected_classes
    if person_detected:
        last_person_seen_at = time.monotonic()

    active_mode = time.monotonic() - last_person_seen_at < ACTIVE_HOLD_SECONDS
    target_fps = ACTIVE_FPS if active_mode else IDLE_FPS
    frame_delay = 1.0 / target_fps

    # 6. Render the results on the frame
    frame = results.render()[0]
    mode = "ACTIVE" if active_mode else "IDLE"
    cv2.putText(
        frame,
        f"{mode} - {target_fps} FPS",
        (10, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (0, 255, 0) if mode == "ACTIVE" else (0, 255, 255),
        2,
    )

    # 7. Display the frame
    cv2.imshow('YOLOv5 Realtime Object Detection', frame)

    # 8. Break the loop if the user presses 'q'
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

    elapsed = time.monotonic() - loop_started_at
    if elapsed < frame_delay:
        time.sleep(frame_delay - elapsed)

# 9. Clean up
cap.release()
cv2.destroyAllWindows()
