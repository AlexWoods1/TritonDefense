# SPDX-License-Identifier: MPL-2.0
"""Object detection on UNO Q via a self-hosted Ultralytics YOLO model (USB webcam).

Captures frames from a USB webcam, runs ``yolo26s.pt`` through
:class:`model.PersonDetector` to find people, and streams per-frame person
detections to the web UI while feeding them to the servo controller, which pans
a servo-mounted camera to follow a single person. All servo and target-tracking
logic lives in ``servo_control``.
"""

import os
import time
from datetime import UTC, datetime

from arduino.app_bricks.web_ui import WebUI
from arduino.app_utils import App

from model import PersonDetector
from servo_control import _update_tracking
from video_stream import VideoStreamServer

APP_VERSION = "0.8.0"
CONFIDENCE = float(os.environ.get("TRITON_YOLO_CONF", "0.5"))
FRAME_WIDTH = int(os.environ.get("TRITON_FRAME_WIDTH", "640"))
FRAME_HEIGHT = int(os.environ.get("TRITON_FRAME_HEIGHT", "480"))
LOOP_DELAY_SECONDS = float(os.environ.get("TRITON_LOOP_DELAY", "0.04"))

# Live video feed served at http://<host>:4912/embed (web UI iframe target).
STREAM_PORT = int(os.environ.get("TRITON_STREAM_PORT", "4912"))
# Adjustable frame rate (FPS) for the live video stream.
STREAM_FPS = float(os.environ.get("TRITON_STREAM_FPS", "15"))

print(f"TritonDefense YOLO v{APP_VERSION} starting (Ultralytics yolo26s.pt, USB webcam)")

ui = WebUI()
detector = PersonDetector(
    confidence=CONFIDENCE,
    frame_width=FRAME_WIDTH,
    frame_height=FRAME_HEIGHT,
)
video_stream = VideoStreamServer(
    detector.get_latest_frame,
    port=STREAM_PORT,
    fps=STREAM_FPS,
)
video_stream.start()


def _send_detections_to_ui(persons):
    """Forward per-frame person detections to the tracker and the web UI.

    ``persons`` is the list of ``(bbox_xyxy, confidence)`` pairs returned by the
    model for the current frame.
    """
    _update_tracking(persons)

    for bbox, conf in persons:
        ui.send_message(
            "detection",
            message={
                "content": "person",
                "confidence": round(conf, 3),
                "bbox": [round(v, 1) for v in bbox],
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )


def loop():
    if not detector.is_open():
        print("Camera is not open. Check TRITON_VIDEO_DEVICE.", flush=True)
        time.sleep(1)
        return
    _send_detections_to_ui(detector.detect())
    time.sleep(LOOP_DELAY_SECONDS)


ui.on_message(
    "override_th",
    lambda _sid, threshold: detector.set_confidence(threshold),
)

App.run(user_loop=loop)
