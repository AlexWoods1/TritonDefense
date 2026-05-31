# killerbot

Arduino UNO Q App Lab project for an RC car.

## Files

- `sketch/sketch.ino`: runs on the UNO Q MCU. It reads the IR receiver, controls the ELEGOO left/right motor groups, controls the servo, and exposes Bridge methods for Python.
- `python/main.py`: runs on the UNO Q Linux side. It opens the camera with OpenCV and sends forward/left/right/stop commands to the sketch over Bridge.
- `python/requirements.txt`: asks App Lab to install OpenCV for Python.

## Default Pin Map

- TB6612 STBY: D3
- Right motor group PWM/direction, ELEGOO group A: D5/D7
- Left motor group PWM/direction, ELEGOO group B: D6/D8
- IR receiver input: D9
- Servo signal: D10

Update the constants at the top of `sketch/sketch.ino` if your wiring differs.

## IR Command Codes

Run `rc_map` first, then copy the printed raw values into these constants in `sketch/sketch.ino`:

- `IR_CODE_FORWARD`
- `IR_CODE_BACKWARD`
- `IR_CODE_LEFT`
- `IR_CODE_RIGHT`
- `IR_CODE_STOP`

The current defaults come from `../input_codes.txt`:

- Forward: `0xB78`
- Backward: `0xE78`
- Left: `0xD38`
- Right: `0xA38`
- Stop/OK: `0xB38`

The sketch does not require the `IRremote` or `Servo` libraries. It uses the same relaxed ELEGOO IR timing decoder as `../rc_cmd_read.ino`: wait for an 8-10 ms start LOW, read HIGH pulse widths as bits, and store bits least-significant-bit first. It also generates the servo control pulse with `digitalWrite()` / `delayMicroseconds()`.

The motor mapping is:

- Forward: left and right motor groups forward.
- Backward: left and right motor groups backward.
- Left: left group backward, right group forward.
- Right: left group forward, right group backward.

## Python to Sketch Bridge API

The sketch exposes these methods:

- `set_motion(motion)`: `0` stop, `1` forward, `2` backward, `3` left, `4` right.
- `set_motor_groups(left, right, speed)`: directions are `-1`, `0`, or `1`; speed is `0..255`.
- `set_motor_outputs(m1, m2, m3, m4)`: compatibility wrapper; motors 1 and 3 map to the left group, motors 2 and 4 map to the right group.
- `set_servo(angle)`: servo angle, `0..180`.
- `stop()`: stop all four motors.

The sketch accepts IR control when Python has not sent a command for 300 ms.

## Debug Output

Open the App Lab Serial Monitor while the sketch is running. The sketch prints:

- every decoded IR signal as `signature12=... mapped_motion=...`
- every motor write, including STBY, PWM pins, direction pins, speed, and left/right group direction
- Python Bridge commands such as `set_motion`, `set_motor_groups`, `set_motor_outputs`, `set_servo`, and `stop`

## ESP32-S3-WROOM-1 Camera Source

`ESP32-S3-WROOM-1` identifies the ESP32-S3 module, not the camera transport by itself. The Python code supports either:

- a Linux video device, for example `/dev/video0`, configured as `KILLERBOT_CAMERA_SOURCE=0`
- an HTTP/MJPEG stream from ESP32 firmware, configured as `KILLERBOT_CAMERA_SOURCE=http://<esp32-ip>:81/stream`

If your ESP32-S3 camera firmware serves a different URL, set `KILLERBOT_CAMERA_SOURCE` to that URL.

## Runtime Settings

Optional environment variables:

- `KILLERBOT_CAMERA_SOURCE`: default `0`
- `KILLERBOT_FRAME_WIDTH`: default `640`
- `KILLERBOT_FRAME_HEIGHT`: default `480`
- `KILLERBOT_AUTO_DRIVE`: default `1`; set `0` to only move the servo from vision.
 
