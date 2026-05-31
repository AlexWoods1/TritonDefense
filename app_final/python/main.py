# SPDX-License-Identifier: MPL-2.0
"""Object detection on UNO Q via App Lab VideoObjectDetection brick (USB webcam).

Pans a servo-mounted camera to follow a single person. Detections arrive per
frame with no persistent IDs, so identity is maintained here: a target is
locked by confidence, re-associated each frame by nearest bounding-box center,
and re-acquired when lost. On loss the camera holds if the target was last seen
near the center, or sweeps toward the edge it vanished off of to search.
"""

import os
import time
from datetime import UTC, datetime

from arduino.app_bricks.video_objectdetection import VideoObjectDetection
from arduino.app_bricks.web_ui import WebUI
from arduino.app_utils import App, Bridge

APP_VERSION = "0.7.1"
CONFIDENCE = float(os.environ.get("TRITON_YOLO_CONF", "0.5"))

# Capture width in pixels; bounding boxes are reported in this coordinate space.
FRAME_WIDTH = int(os.environ.get("TRITON_FRAME_WIDTH", "640"))

# Number of vertical columns the frame is split into for steering. 3 = left /
# center / right thirds; the center column holds, the outer columns pan/sweep.
ZONES = int(os.environ.get("TRITON_ZONES", "3"))

# Servo travel and panning behavior (servo: 0..180, 90 = centered).
SERVO_MIN = int(os.environ.get("TRITON_SERVO_MIN", "0"))
SERVO_MAX = int(os.environ.get("TRITON_SERVO_MAX", "180"))
SERVO_CENTER = (SERVO_MIN + SERVO_MAX) // 2
# Degrees of pan per zone of horizontal offset from center while tracking.
SERVO_STEP = int(os.environ.get("TRITON_SERVO_STEP", "8"))
# Degrees of pan per frame while sweeping to search after an edge loss.
SWEEP_STEP = int(os.environ.get("TRITON_SWEEP_STEP", "4"))
# +1: person on the right pans the servo toward higher angles. Flip if mirrored.
SERVO_SIGN = 1 if os.environ.get("TRITON_SERVO_INVERT", "0") == "1" else -1

# Frames a locked target may be missing before the lock is dropped.
MAX_MISSES = int(os.environ.get("TRITON_MAX_MISSES", "8"))
# Max allowed center jump between frames, as a fraction of frame width, to be
# considered the same person. Keeps the lock from snapping onto a stranger.
GATE_FRAC = float(os.environ.get("TRITON_GATE_FRAC", "0.25"))

# Minimum seconds between servo commands to avoid overwhelming the serial link.
MIN_SERVO_INTERVAL = float(os.environ.get("TRITON_SERVO_MIN_INTERVAL", "0.05"))

print(f"TritonDefense YOLO v{APP_VERSION} starting (App Lab brick, USB webcam)")

ui = WebUI()
detection_stream = VideoObjectDetection(confidence=CONFIDENCE, debounce_sec=0.0)

# Servo state.
servo_angle = SERVO_CENTER
_last_servo_ts = 0.0

# Target-lock state. cx is the last known bounding-box center in pixels.
lock = {"cx": None, "zone": None, "misses": 0}
# Active sweep direction while searching after an edge loss (-1 left, +1 right, 0 idle).
sweep_dir = 0
# Whether person tracking is active. Toggled from the MCU via an IR command.
# Starts disabled; press the bound remote button (IR 0xF78) to enable.
tracking_enabled = False


def _set_tracking(enabled):
    """Enable/disable tracking. Invoked by the MCU over the Bridge on IR toggle."""
    global tracking_enabled, sweep_dir
    tracking_enabled = bool(enabled)
    if not tracking_enabled:
        lock["cx"] = None
        lock["zone"] = None
        lock["misses"] = 0
        sweep_dir = 0
    print(f"tracking {'enabled' if tracking_enabled else 'disabled'}", flush=True)


def clamp(value, low, high):
    return max(low, min(high, value))


def command_servo(angle):
    """Send an absolute servo angle, rate-limited and only when it changes."""
    global servo_angle, _last_servo_ts
    angle = int(clamp(angle, SERVO_MIN, SERVO_MAX))
    now = time.monotonic()
    if angle == servo_angle:
        return
    if now - _last_servo_ts < MIN_SERVO_INTERVAL:
        return
    servo_angle = angle
    _last_servo_ts = now
    try:
        Bridge.call("set_servo", angle)
    except Exception as exc:
        print(f"set_servo failed: {exc}", flush=True)


def _center_x(bbox):
    return (bbox[0] + bbox[2]) / 2.0


def _zone_for(cx):
    """Map a center x to a vertical column: 0 (left) .. ZONES - 1 (right)."""
    return int(clamp(cx / FRAME_WIDTH * ZONES, 0, ZONES - 1))


def _persons_with_bbox(detections):
    items = detections.get("person", [])
    out = []
    for item in items:
        bbox = item.get("bounding_box_xyxy")
        if bbox and len(bbox) == 4:
            out.append((bbox, float(item.get("confidence", 0.0))))
    return out


def _acquire(persons):
    """Lock onto the highest-confidence person."""
    bbox, _conf = max(persons, key=lambda p: p[1])
    return bbox


def _associate(persons):
    """Match the locked target to the nearest center within the gate, else None."""
    bbox = min(persons, key=lambda p: abs(_center_x(p[0]) - lock["cx"]))[0]
    if abs(_center_x(bbox) - lock["cx"]) <= GATE_FRAC * FRAME_WIDTH:
        return bbox
    return None


def _track_to(bbox):
    """Update the lock from a matched bbox and pan toward it."""
    global sweep_dir
    cx = _center_x(bbox)
    zone = _zone_for(cx)
    lock["cx"] = cx
    lock["zone"] = zone
    lock["misses"] = 0
    sweep_dir = 0
    # Signed offset from the center column; the center column (offset 0) holds.
    offset = zone - ZONES // 2
    command_servo(servo_angle + offset * SERVO_STEP * SERVO_SIGN)


def _handle_miss():
    """Advance the miss counter and decide hold-vs-sweep when the lock expires."""
    global sweep_dir
    if lock["cx"] is None:
        if sweep_dir != 0:
            command_servo(servo_angle + sweep_dir * SWEEP_STEP * SERVO_SIGN)
        return

    lock["misses"] += 1
    if lock["misses"] <= MAX_MISSES:
        return

    last_zone = lock["zone"]
    lock["cx"] = None
    lock["zone"] = None
    lock["misses"] = 0
    if last_zone == 0:
        sweep_dir = -1  # vanished off the left edge -> sweep left
    elif last_zone == ZONES - 1:
        sweep_dir = 1  # vanished off the right edge -> sweep right
    else:
        sweep_dir = 0  # vanished near center -> hold and wait


def _update_tracking(persons):
    if not persons:
        _handle_miss()
        return

    if lock["cx"] is None:
        _track_to(_acquire(persons))
        return

    matched = _associate(persons)
    if matched is None:
        _handle_miss()
        return
    _track_to(matched)


def _send_detections_to_ui(detections: dict):
    persons = _persons_with_bbox(detections)
    if tracking_enabled:
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


detection_stream.on_detect_all(_send_detections_to_ui)

Bridge.provide("set_tracking", _set_tracking)

ui.on_message(
    "override_th",
    lambda _sid, threshold: detection_stream.override_threshold(threshold),
)

App.run()
