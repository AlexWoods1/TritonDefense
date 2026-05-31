import os
import time

import cv2
from arduino.app_utils import App, Bridge

CAMERA_SOURCE = os.getenv("KILLERBOT_CAMERA_SOURCE", "0")
FRAME_WIDTH = int(os.getenv("KILLERBOT_FRAME_WIDTH", "640"))
FRAME_HEIGHT = int(os.getenv("KILLERBOT_FRAME_HEIGHT", "480"))
LOOP_DELAY_SECONDS = float(os.getenv("KILLERBOT_LOOP_DELAY_SECONDS", "0.04"))

AUTO_DRIVE_ENABLED = os.getenv("KILLERBOT_AUTO_DRIVE", "1") == "1"
SERVO_GAIN = float(os.getenv("KILLERBOT_SERVO_GAIN", "0.28"))

MOTION_STOP = 0
MOTION_FORWARD = 1
MOTION_BACKWARD = 2
MOTION_LEFT = 3
MOTION_RIGHT = 4


def _open_camera():
    source = int(CAMERA_SOURCE) if CAMERA_SOURCE.isdigit() else CAMERA_SOURCE
    capture = cv2.VideoCapture(source, cv2.CAP_V4L2)
    if not capture.isOpened():
        capture = cv2.VideoCapture(source)

    capture.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    capture.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    return capture


camera = _open_camera()


def clamp(value, low, high):
    return max(low, min(high, int(value)))


def stop():
    try:
        Bridge.call("stop")
    except Exception as exc:
        print(f"Bridge stop failed: {exc}", flush=True)


def command_motion(motion):
    Bridge.call("set_motion", motion)


def command_servo(angle):
    angle = clamp(angle, 0, 180)
    Bridge.call("set_servo", angle)


def find_bright_target(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (7, 7), 0)
    _, mask = cv2.threshold(blurred, 220, 255, cv2.THRESH_BINARY)
    moments = cv2.moments(mask)

    if moments["m00"] == 0:
        return None

    cx = int(moments["m10"] / moments["m00"])
    cy = int(moments["m01"] / moments["m00"])
    return cx, cy


def loop():
    if not camera.isOpened():
        print("Camera is not open. Check KILLERBOT_CAMERA_SOURCE.", flush=True)
        stop()
        time.sleep(1)
        return

    ok, frame = camera.read()
    if not ok:
        print("Camera frame read failed.", flush=True)
        stop()
        time.sleep(0.25)
        return

    target = find_bright_target(frame)
    if target is None:
        stop()
        time.sleep(LOOP_DELAY_SECONDS)
        return

    _, width = frame.shape[:2]
    cx, _ = target
    center_x = width / 2.0
    error = (cx - center_x) / center_x

    servo_angle = clamp(90 + error * 90 * SERVO_GAIN, 30, 150)

    if error < -0.2:
        motion = MOTION_LEFT
    elif error > 0.2:
        motion = MOTION_RIGHT
    else:
        motion = MOTION_FORWARD

    try:
        command_servo(servo_angle)
        if AUTO_DRIVE_ENABLED:
            command_motion(motion)
    except Exception as exc:
        print(f"Bridge command failed: {exc}", flush=True)
        stop()

    time.sleep(LOOP_DELAY_SECONDS)


App.run(user_loop=loop)
