# SPDX-License-Identifier: MPL-2.0
"""Object detection on UNO Q via App Lab VideoObjectDetection brick (USB webcam).

Pans a servo-mounted camera to follow a single person. Detections update a shared
target position; a background control loop (default 30 Hz) moves the servo with
proportional pan and deg/s smoothing so pan is not tied to the detection callback rate.
"""

import os
import threading
import time
from datetime import UTC, datetime

from arduino.app_bricks.video_objectdetection import VideoObjectDetection
from arduino.app_bricks.web_ui import WebUI
from arduino.app_utils import App, Bridge

APP_VERSION = "0.7.4"
CONFIDENCE = float(os.environ.get("TRITON_YOLO_CONF", "0.5"))

FRAME_WIDTH = int(os.environ.get("TRITON_FRAME_WIDTH", "640"))

SERVO_MIN = int(os.environ.get("TRITON_SERVO_MIN", "0"))
SERVO_MAX = int(os.environ.get("TRITON_SERVO_MAX", "180"))
SERVO_CENTER = (SERVO_MIN + SERVO_MAX) // 2
# Scales horizontal error [-1, 1] into pan offset from center (killerbot-style).
SERVO_GAIN = float(os.environ.get("TRITON_SERVO_GAIN", "0.44"))
# Extra gain when the target is far from frame center (more responsive, still smooth near center).
SERVO_GAIN_FAR = float(os.environ.get("TRITON_SERVO_GAIN_FAR", "0.58"))
SERVO_FAR_ERROR = float(os.environ.get("TRITON_SERVO_FAR_ERROR", "0.12"))
# No pan when |error| is below this fraction of frame half-width.
CENTER_DEADBAND = float(os.environ.get("TRITON_CENTER_DEADBAND", "0.03"))
SERVO_SIGN = 1 if os.environ.get("TRITON_SERVO_INVERT", "0") == "1" else -1

# Fast pan loop, decoupled from brick detection callbacks.
CONTROL_HZ = float(os.environ.get("TRITON_CONTROL_HZ", "40"))
MAX_DEG_PER_SEC = float(os.environ.get("TRITON_MAX_DEG_PER_SEC", "180"))
# Max pan speed when the servo is far from the desired angle (large catch-up moves).
BOOST_DEG_PER_SEC = float(os.environ.get("TRITON_BOOST_DEG_PER_SEC", "280"))
BOOST_ANGLE_ERROR_DEG = float(os.environ.get("TRITON_BOOST_ANGLE_ERROR_DEG", "10"))
# Lead the target using estimated horizontal velocity (compensates for slow detection).
PREDICT_SEC = float(os.environ.get("TRITON_PREDICT_SEC", "0.08"))
# Search sweep speed when the target leaves the frame (deg/s).
SWEEP_DEG_PER_SEC = float(os.environ.get("TRITON_SWEEP_DEG_PER_SEC", "30"))

MAX_MISSES = int(os.environ.get("TRITON_MAX_MISSES", "8"))
GATE_FRAC = float(os.environ.get("TRITON_GATE_FRAC", "0.25"))
# Zones used only to pick sweep direction after a lost lock.
ZONES = int(os.environ.get("TRITON_ZONES", "3"))

print(
    f"TritonDefense YOLO v{APP_VERSION} starting "
    f"(brick, control {CONTROL_HZ:.0f} Hz, gain {SERVO_GAIN})",
    flush=True,
)

ui = WebUI()
detection_stream = VideoObjectDetection(confidence=CONFIDENCE, debounce_sec=0.0)

_state_lock = threading.Lock()
# Updated from detection callbacks; read by the control thread.
_track = {
    "tracking_enabled": False,
    "drive_active": False,
    "target_cx": None,
    "prev_cx": None,
    "prev_cx_ts": 0.0,
    "zone": None,
    "misses": 0,
    "sweep_dir": 0,
}

# Servo angle owned by the control thread only.
_servo_angle = SERVO_CENTER


def _set_tracking(enabled):
    """Enable/disable tracking. Invoked by the MCU over the Bridge on IR toggle."""
    with _state_lock:
        _track["tracking_enabled"] = bool(enabled)
        if not _track["tracking_enabled"]:
            _track["target_cx"] = None
            _track["prev_cx"] = None
            _track["prev_cx_ts"] = 0.0
            _track["zone"] = None
            _track["misses"] = 0
            _track["sweep_dir"] = 0
    print(f"tracking {'enabled' if enabled else 'disabled'}", flush=True)


def _set_drive_active(active):
    """Pause servo Bridge traffic while IR is driving motors (MCU notifies)."""
    with _state_lock:
        _track["drive_active"] = bool(active)


def clamp(value, low, high):
    return max(low, min(high, value))


def _center_x(bbox):
    return (bbox[0] + bbox[2]) / 2.0


def _zone_for(cx):
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
    bbox, _conf = max(persons, key=lambda p: p[1])
    return bbox


def _associate(persons, locked_cx):
    bbox = min(persons, key=lambda p: abs(_center_x(p[0]) - locked_cx))[0]
    if abs(_center_x(bbox) - locked_cx) <= GATE_FRAC * FRAME_WIDTH:
        return bbox
    return None


def _lock_target(bbox):
    cx = _center_x(bbox)
    now = time.monotonic()
    with _state_lock:
        _track["prev_cx"] = _track["target_cx"]
        _track["prev_cx_ts"] = now
        _track["target_cx"] = cx
        _track["zone"] = _zone_for(cx)
        _track["misses"] = 0
        _track["sweep_dir"] = 0


def _handle_miss():
    with _state_lock:
        if _track["target_cx"] is not None:
            _track["misses"] += 1
            if _track["misses"] <= MAX_MISSES:
                return
            last_zone = _track["zone"]
            _track["target_cx"] = None
            _track["prev_cx"] = None
            _track["prev_cx_ts"] = 0.0
            _track["zone"] = None
            _track["misses"] = 0
            if last_zone == 0:
                _track["sweep_dir"] = -1
            elif last_zone == ZONES - 1:
                _track["sweep_dir"] = 1
            else:
                _track["sweep_dir"] = 0


def _update_tracking_state(persons):
    """Refresh target lock from detections; does not command the servo."""
    if not persons:
        _handle_miss()
        return

    with _state_lock:
        locked_cx = _track["target_cx"]

    if locked_cx is None:
        _lock_target(_acquire(persons))
        return

    matched = _associate(persons, locked_cx)
    if matched is None:
        _handle_miss()
        return
    _lock_target(matched)


def _predicted_cx(cx):
    """Extrapolate target x using the last detection delta (reduces brick latency)."""
    with _state_lock:
        prev_cx = _track["prev_cx"]
        prev_ts = _track["prev_cx_ts"]
    if prev_cx is None or prev_ts <= 0.0:
        return cx
    dt = time.monotonic() - prev_ts
    if dt <= 0.0:
        return cx
    velocity = (cx - prev_cx) / dt
    return clamp(cx + velocity * PREDICT_SEC, 0.0, float(FRAME_WIDTH))


def _effective_gain(error):
    abs_err = abs(error)
    if abs_err <= SERVO_FAR_ERROR:
        return SERVO_GAIN
    blend = clamp((abs_err - SERVO_FAR_ERROR) / max(SERVO_FAR_ERROR, 0.01), 0.0, 1.0)
    return SERVO_GAIN + (SERVO_GAIN_FAR - SERVO_GAIN) * blend


def _desired_angle_for_cx(cx):
    cx = _predicted_cx(cx)
    center = FRAME_WIDTH / 2.0
    error = (cx - center) / center
    if abs(error) < CENTER_DEADBAND:
        return _servo_angle
    gain = _effective_gain(error)
    offset_deg = error * 90.0 * gain * SERVO_SIGN
    return clamp(SERVO_CENTER + offset_deg, SERVO_MIN, SERVO_MAX)


def _send_servo(angle):
    global _servo_angle
    angle = int(clamp(angle, SERVO_MIN, SERVO_MAX))
    if angle == _servo_angle:
        return
    _servo_angle = angle
    try:
        Bridge.call("set_servo", angle)
    except Exception as exc:
        print(f"set_servo failed: {exc}", flush=True)


def _max_speed_for_angle_error(angle_error_deg):
    """Move faster when far from the goal; ease in when close (smooth but responsive)."""
    abs_err = abs(angle_error_deg)
    if abs_err >= BOOST_ANGLE_ERROR_DEG:
        return BOOST_DEG_PER_SEC
    if abs_err <= 3.0:
        return MAX_DEG_PER_SEC * 0.75
    t = (abs_err - 3.0) / max(BOOST_ANGLE_ERROR_DEG - 3.0, 1.0)
    return MAX_DEG_PER_SEC * (0.75 + 0.25 * t) + t * (BOOST_DEG_PER_SEC - MAX_DEG_PER_SEC)


def _step_servo_toward(desired, dt):
    angle_error = desired - _servo_angle
    max_delta = _max_speed_for_angle_error(angle_error) * dt
    delta = clamp(angle_error, -max_delta, max_delta)
    if abs(delta) < 0.35:
        return
    _send_servo(_servo_angle + delta)


def _control_loop():
    interval = 1.0 / CONTROL_HZ
    last_ts = time.monotonic()
    while True:
        time.sleep(interval)
        now = time.monotonic()
        dt = max(now - last_ts, interval * 0.5)
        last_ts = now

        with _state_lock:
            if not _track["tracking_enabled"] or _track["drive_active"]:
                continue
            cx = _track["target_cx"]
            sweep_dir = _track["sweep_dir"]

        if cx is not None:
            desired = _desired_angle_for_cx(cx)
        elif sweep_dir != 0:
            desired = _servo_angle + sweep_dir * SWEEP_DEG_PER_SEC * dt * SERVO_SIGN
            desired = clamp(desired, SERVO_MIN, SERVO_MAX)
        else:
            continue

        _step_servo_toward(desired, dt)


def _send_detections_to_ui(detections: dict):
    persons = _persons_with_bbox(detections)
    with _state_lock:
        tracking_on = _track["tracking_enabled"]
    if tracking_on:
        _update_tracking_state(persons)

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


_control_thread = threading.Thread(target=_control_loop, name="servo-control", daemon=True)
_control_thread.start()

detection_stream.on_detect_all(_send_detections_to_ui)

Bridge.provide("set_tracking", _set_tracking)
Bridge.provide("drive_active", _set_drive_active)

ui.on_message(
    "override_th",
    lambda _sid, threshold: detection_stream.override_threshold(threshold),
)

App.run()
