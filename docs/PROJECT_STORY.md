# TritonDefense — Project Story

Mobile surveillance for a military-themed autonomous-vehicle hackathon.  
Final code: [`app_final (2).zip`](../app_final%20(2).zip)

---

## Background

We wanted a camera post you could move without rewiring a site. The pitch was **CCTV on wheels**: an Elegoo robot car you drive in with a remote, park in a watch position, and use for live recon. The full write-up is in [`TRITON_MOBILE_SENTRY_REPORT.md`](TRITON_MOBILE_SENTRY_REPORT.md). It covers acoustic sensing, ultrasonic ranging, local recording, and cloud upload.

We did not get all of that working. The build we submitted focuses on live video, remote driving, and camera pan tracking.

---

## Final system

The stack is an **Arduino UNO Q** running vision and a web UI, plus the **Elegoo Smart Robot Car V4** MCU handling motors, IR input, and a pan servo.

- Live person detection (YOLO via App Lab) with a browser view at port 7000  
- IR remote control for forward, reverse, and turns  
- Optional tracking mode: the servo pans to keep a person in frame; the car does not drive itself  

Typical use: RC into position, flip tracking on when you want the camera to follow someone, RC back out when you are done. Translation stays on the operator. Only the camera mount moves on its own.

---

## Build history

**Vision.** We started with YOLOv5 on a laptop to tune detection. Moving that stack onto the UNO Q in App Lab was slow and awkward, so we switched to the built-in `video_object_detection` brick. Less flexibility on the model, but it actually ran on the board.

**Camera setup.** This took longer than expected. A USB webcam does not plug straight into the UNO Q—you need a powered USB-C hub (PD to the hub, data to the board, camera on USB-A). `/dev/video0` and `/dev/video1` on the board are GPU devices, not the webcam; ours showed up on `/dev/video2`. Until we fixed `VIDEO_DEVICE` in `app.yaml`, App Lab kept reporting no camera. With the hub attached, we also had to deploy over Wi‑Fi instead of USB.

**Remote and motors.** We skipped the IR library and decoded NEC-style pulses in the sketch so we knew exactly what the receiver was doing. Each button on our remote needed its hex code measured and pasted into firmware (`rc_map` helped). One button was annoying: the tracking toggle alternates between `0xF78` and `0x778` on each press, so we had to accept both or the toggle would miss every other click. Motors go through the TB6612; we mapped left/right groups explicitly and cut drive after ~200 ms with no IR input so the car does not keep rolling.

**Tracking.** YOLO gives bounding boxes, not person IDs. Our first pass used a PID loop over serial; on the integrated car we used something simpler—pick the highest-confidence person, re-match by nearest center each frame, ignore jumps that are too large, and pan in coarse zones. If the target drops out near the edge, the servo sweeps that way; if they drop out in the center, it holds. Servo updates are throttled so the Bridge link does not get spammed.

**Putting it together.** Vision runs in Python on the Linux side; timing-sensitive I/O runs in the sketch. Both can touch the hardware, so we added a short window where Python commands take priority after a servo move—except the tracking toggle, which has to work even while panning. The last step was merging sketch and Python into a single App Lab project (`app_final`) so we could load one zip and demo.

**What we dropped.** Audio never worked in the final build—no mic pipeline, no synced event log. Ultrasonic, clip recording, and cloud upload were also left out. Time went to getting video, drive, and pan stable for demo day.

---

## Problems worth naming

- **Webcam on UNO Q:** hub wiring, correct V4L2 device, Wi‑Fi deploy  
- **On-board inference:** App Lab brick instead of a full local YOLO install  
- **IR remote:** hand-decoded codes; dual values for the tracking button  
- **Follow logic:** no track IDs, so lock + re-association instead of a off-the-shelf tracker  
- **Shared control:** IR vs Python over Bridge; priority timing to avoid fighting  
- **Acoustic sensing:** planned in the report, not in the shipped app  

---

## Takeaway

Most of the schedule went to integration—hub, device paths, IR, two processors—not to new algorithms. The demo that held up was narrow: see people, drive the car yourself, let the servo follow when you turn that on. The concept report still describes where we would take it next; [`app_final (2).zip`](../app_final%20(2).zip) is what we actually ran.

---

See also: [`README.md`](../README.md)
