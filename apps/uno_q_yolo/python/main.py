# SPDX-License-Identifier: MPL-2.0
"""Object detection on UNO Q via App Lab VideoObjectDetection brick (USB webcam)."""

import os
from datetime import UTC, datetime

from arduino.app_bricks.video_objectdetection import VideoObjectDetection
from arduino.app_bricks.web_ui import WebUI
from arduino.app_utils import App

APP_VERSION = "0.6.1"
CONFIDENCE = float(os.environ.get("TRITON_YOLO_CONF", "0.5"))

print(f"TritonDefense YOLO v{APP_VERSION} starting (App Lab brick, USB webcam)")

ui = WebUI()
detection_stream = VideoObjectDetection(confidence=CONFIDENCE, debounce_sec=0.0)


def _send_detections_to_ui(detections: dict):
    for label, items in detections.items():
        for item in items:
            bbox = item.get("bounding_box_xyxy")
            ui.send_message(
                "detection",
                message={
                    "content": label,
                    "confidence": round(float(item.get("confidence", 0)), 3),
                    "bbox": [round(v, 1) for v in bbox] if bbox else [],
                    "timestamp": datetime.now(UTC).isoformat(),
                },
            )


detection_stream.on_detect_all(_send_detections_to_ui)

ui.on_message(
    "override_th",
    lambda _sid, threshold: detection_stream.override_threshold(threshold),
)

App.run()
