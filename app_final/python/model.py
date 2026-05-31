# SPDX-License-Identifier: MPL-2.0
"""Self-hosted person detector backed by an Ultralytics YOLO model.

Loads ``yolo26s.pt`` with Ultralytics ``YOLO``, captures frames from a video
stream (USB webcam), runs inference, and returns bounding boxes for detected
people. This replaces the App Lab ``VideoObjectDetection`` brick so the model
weights and detection logic live inside the app.

The public entry point is :class:`PersonDetector`. Call :meth:`PersonDetector.detect`
once per loop iteration to get the people found in the latest frame as a list of
``(bbox_xyxy, confidence)`` pairs, which the main app forwards to the tracker and
the web UI.
"""

import os
import threading

import cv2
from ultralytics import YOLO

# COCO class index for "person"; yolo26s is COCO-trained.
PERSON_CLASS_ID = 0

# Weights file shipped alongside this module.
_DEFAULT_MODEL_PATH = os.path.join(os.path.dirname(__file__), "yolo26s.pt")

# UNO Q: /dev/video0-1 are GPU codecs. USB webcams are usually /dev/video2+.
_DEFAULT_VIDEO_DEVICE = os.environ.get("TRITON_VIDEO_DEVICE", "/dev/video2")


class PersonDetector:
    """Detect people in a video stream using an Ultralytics YOLO model."""

    def __init__(
        self,
        model_path=None,
        video_device=None,
        confidence=0.5,
        frame_width=640,
        frame_height=480,
    ):
        self.model = YOLO(
            model_path or os.environ.get("TRITON_MODEL_PATH", _DEFAULT_MODEL_PATH)
        )
        # Guarded because the confidence threshold can be updated from the web UI
        # on a different thread than the detection loop.
        self._lock = threading.Lock()
        self._confidence = float(confidence)
        # Latest annotated frame, shared with the video stream server (a separate
        # thread), so the camera is only ever opened once.
        self._frame_lock = threading.Lock()
        self._latest_frame = None
        self.capture = self._open_capture(video_device, frame_width, frame_height)

    @staticmethod
    def _open_capture(video_device, frame_width, frame_height):
        device = video_device if video_device is not None else _DEFAULT_VIDEO_DEVICE
        source = int(device) if str(device).isdigit() else device
        # Prefer the V4L2 backend on Linux; fall back to the default backend.
        capture = cv2.VideoCapture(source, cv2.CAP_V4L2)
        if not capture.isOpened():
            capture = cv2.VideoCapture(source)
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, frame_width)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, frame_height)
        return capture

    def is_open(self):
        return self.capture is not None and self.capture.isOpened()

    def set_confidence(self, confidence):
        """Update the detection confidence threshold (driven by the web UI)."""
        with self._lock:
            self._confidence = float(confidence)

    def detect(self):
        """Read one frame and return ``[(bbox_xyxy, confidence), ...]`` for people.

        ``bbox_xyxy`` is ``[x1, y1, x2, y2]`` in pixel coordinates. Returns an
        empty list when no frame is available or no person is detected.
        """
        if not self.is_open():
            return []
        ok, frame = self.capture.read()
        if not ok or frame is None:
            return []
        persons = self.detect_in_frame(frame)
        self._store_annotated(frame, persons)
        return persons

    def detect_in_frame(self, frame):
        """Run inference on a single BGR frame and return person detections."""
        with self._lock:
            conf = self._confidence
        results = self.model.predict(
            frame,
            conf=conf,
            classes=[PERSON_CLASS_ID],
            verbose=False,
        )
        persons = []
        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue
            for box in boxes:
                bbox_xyxy = [float(v) for v in box.xyxy[0].tolist()]
                confidence = float(box.conf[0])
                persons.append((bbox_xyxy, confidence))
        return persons

    def _store_annotated(self, frame, persons):
        """Draw person boxes on ``frame`` and publish it for the video stream."""
        for bbox, conf in persons:
            x1, y1, x2, y2 = (int(v) for v in bbox)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(
                frame,
                f"person {conf:.2f}",
                (x1, max(0, y1 - 6)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 0),
                1,
                cv2.LINE_AA,
            )
        with self._frame_lock:
            self._latest_frame = frame

    def get_latest_frame(self):
        """Return a copy of the latest annotated frame, or ``None`` if none yet."""
        with self._frame_lock:
            if self._latest_frame is None:
                return None
            return self._latest_frame.copy()

    def release(self):
        if self.capture is not None:
            self.capture.release()
