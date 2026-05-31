# TritonDefense YOLO — Arduino UNO Q

COCO object detection on a **USB webcam** using the App Lab **`video_object_detection`** brick (YOLOX Nano).

## Hardware (required wiring)

The UNO Q **cannot** use a USB webcam plugged directly into its USB-C port. You need a **powered USB-C hub**:

```
[5V PD power] ──► hub PD port
[UNO Q USB-C] ◄── hub USB-C data port (hub plugs into the board)
[USB webcam]  ──► hub USB-A port
```

- Hub **USB-C cable → UNO Q** (UNO Q is USB **host**)
- **Do not** plug the hub into your PC with the UNO Q on the hub — the board will not see the camera
- With a hub attached, connect App Lab via **Network** (Wi‑Fi), not USB

Tested webcams: Logitech C270, Brio series (others may work if UVC).

## Setup

1. Wire hub + webcam as above.
2. Import `apps/uno_q_yolo` or `apps/uno_q_yolo.zip`.
3. **Run** in App Lab (first run may need internet for the model container).

## Run

1. Open **`http://<uno-q-ip>:7000`**
2. Live annotated video comes from the brick on port **4912**
3. Adjust confidence with the slider

## "No webcam found" — fix

### 1. Check physical setup

- Powered hub connected **to UNO Q**, not to PC only
- Webcam LED on (if it has one)
- App Lab connected over **Network**

### 2. Find the camera device (SSH on UNO Q)

```bash
lsusb
# Look for your webcam, e.g. Logitech

v4l2-ctl --list-devices
# Find the UVC camera — note its /dev/videoN path (often video2 or video3)
```

`/dev/video0` and `/dev/video1` are **Venus GPU codecs** — not your webcam.

### 3. Set `VIDEO_DEVICE` in `app.yaml`

Default in this app is `/dev/video2`. If your camera is elsewhere, edit:

```yaml
- arduino:video_object_detection:
    model: yolox-object-detection
    variables:
      VIDEO_DEVICE: /dev/video3
```

Save, reload the app in App Lab, **Run** again.

### 4. Quick test

```bash
v4l2-ctl --device=/dev/video2 --info
# Should show "Video Capture" capability for a real webcam
```

## Tuning

| Variable | Default | Purpose |
|----------|---------|---------|
| `TRITON_YOLO_CONF` | `0.5` | Initial detection confidence |
| `VIDEO_DEVICE` | `/dev/video2` in `app.yaml` | V4L2 path for the brick |

## Model

`yolox-object-detection` — COCO 80 classes. For faces only, change model to `face-detection` in `app.yaml`.

## Next step — Elegoo car

Extend `sketch/sketch.ino` and use `Bridge` from `python/main.py` when a target (e.g. `person`) is off-center.
