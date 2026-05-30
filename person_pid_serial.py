import argparse
import time
from dataclasses import dataclass

import cv2
import torch

try:
    import serial
except ImportError:
    serial = None


PERSON_CLASS_ID = 0


@dataclass
class PIDController:
    kp: float
    ki: float
    kd: float
    output_limit: float
    integral_limit: float
    deadband_degrees: float

    integral: float = 0.0
    previous_error: float | None = None
    previous_time: float | None = None

    def update(self, error_degrees: float, now: float) -> float:
        if abs(error_degrees) < self.deadband_degrees:
            error_degrees = 0.0

        if self.previous_time is None:
            dt = 0.0
        else:
            dt = max(now - self.previous_time, 1e-6)

        if dt > 0:
            self.integral += error_degrees * dt
            self.integral = clamp(
                self.integral,
                -self.integral_limit,
                self.integral_limit,
            )

        if self.previous_error is None or dt == 0:
            derivative = 0.0
        else:
            derivative = (error_degrees - self.previous_error) / dt

        self.previous_error = error_degrees
        self.previous_time = now

        output = (
            self.kp * error_degrees
            + self.ki * self.integral
            + self.kd * derivative
        )
        return clamp(output, -self.output_limit, self.output_limit)

    def reset(self) -> None:
        self.integral = 0.0
        self.previous_error = None
        self.previous_time = None


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def find_largest_person(results):
    people = results.pred[0][results.pred[0][:, -1] == PERSON_CLASS_ID]
    if len(people) == 0:
        return None

    areas = (people[:, 2] - people[:, 0]) * (people[:, 3] - people[:, 1])
    largest_index = int(areas.argmax())
    return people[largest_index]


def open_serial(port: str, baud: int):
    if port.lower() == "none":
        return None

    if serial is None:
        raise RuntimeError(
            "pyserial is not installed. Install it with: pip install pyserial"
        )

    connection = serial.Serial(port, baud, timeout=0)
    time.sleep(2.0)
    return connection


def send_yaw_delta(connection, yaw_delta: float) -> None:
    message = f"YAW_DELTA:{yaw_delta:.2f}\n"
    if connection is None:
        print(message, end="")
        return

    connection.write(message.encode("ascii"))
    connection.flush()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Track the largest detected person and send PID yaw degree changes "
            "to an Arduino over serial."
        )
    )
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--serial-port", default="COM3")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--horizontal-fov", type=float, default=60.0)
    parser.add_argument("--send-hz", type=float, default=10.0)
    parser.add_argument("--kp", type=float, default=0.35)
    parser.add_argument("--ki", type=float, default=0.0)
    parser.add_argument("--kd", type=float, default=0.08)
    parser.add_argument("--max-step-degrees", type=float, default=8.0)
    parser.add_argument("--integral-limit", type=float, default=30.0)
    parser.add_argument("--deadband-degrees", type=float, default=1.5)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print serial messages instead of opening a serial port.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    model = torch.hub.load(
        "ultralytics/yolov5",
        "yolov5s",
        pretrained=True,
        trust_repo=True,
    )

    serial_connection = open_serial(
        "none" if args.dry_run else args.serial_port,
        args.baud,
    )
    pid = PIDController(
        kp=args.kp,
        ki=args.ki,
        kd=args.kd,
        output_limit=args.max_step_degrees,
        integral_limit=args.integral_limit,
        deadband_degrees=args.deadband_degrees,
    )

    cap = cv2.VideoCapture(args.camera)
    min_send_interval = 1.0 / args.send_hz
    last_send_at = 0.0

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_height, frame_width = frame.shape[:2]
            frame_center_x = frame_width / 2.0

            results = model(frame)
            target = find_largest_person(results)
            now = time.monotonic()

            yaw_delta = 0.0
            target_found = target is not None

            if target_found:
                x1, y1, x2, y2, confidence, _class_id = target.tolist()
                target_center_x = (x1 + x2) / 2.0
                pixel_error = target_center_x - frame_center_x
                error_degrees = (
                    pixel_error / frame_width
                ) * args.horizontal_fov
                yaw_delta = pid.update(error_degrees, now)

                cv2.rectangle(
                    frame,
                    (int(x1), int(y1)),
                    (int(x2), int(y2)),
                    (0, 255, 0),
                    2,
                )
                cv2.circle(
                    frame,
                    (int(target_center_x), int((y1 + y2) / 2.0)),
                    5,
                    (0, 255, 0),
                    -1,
                )
                cv2.putText(
                    frame,
                    f"person {confidence:.2f} error {error_degrees:.1f} deg",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 0),
                    2,
                )
            else:
                pid.reset()
                cv2.putText(
                    frame,
                    "no person",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 255),
                    2,
                )

            cv2.line(
                frame,
                (int(frame_center_x), 0),
                (int(frame_center_x), frame_height),
                (255, 255, 255),
                1,
            )
            cv2.imshow("Person PID Serial Tracking", frame)

            if now - last_send_at >= min_send_interval:
                send_yaw_delta(serial_connection, yaw_delta)
                last_send_at = now

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        cap.release()
        if serial_connection is not None:
            serial_connection.close()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
