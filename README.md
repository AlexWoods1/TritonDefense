# TritonDefense

**CCTV on wheels** — a mobile surveillance node for contested reconnaissance, built for a military-themed autonomous-vehicle hackathon.

An **Elegoo robot car** acts as a relocatable sentry: **video** is the primary recon product, **acoustic** sensing flags impulsive events on a shared timeline, and **ultrasonic** ranging adds standoff distance. Operators use **remote control** for all driving; in watch mode the vehicle can **yaw to follow personnel** but does **not** move forward or backward on its own.

## Implementation status

| Component | Status |
|-----------|--------|
| UNO Q object detection app (`apps/uno_q_yolo`) | **Live** — single App Lab project, USB webcam, YOLOX COCO |
| Browser CCTV UI (`http://<uno-q-ip>:7000`) | **Live** |
| MCU Bridge stub (`sketch/sketch.ino`) | **Stub** — ready for motor/yaw integration |
| Elegoo RC, drive lock, ultrasonic, acoustic | Planned |
| Yaw tracking from detections | Planned |
| SD logging + cloud upload timeline | Planned |

See [`docs/TRITON_MOBILE_SENTRY_REPORT.md`](docs/TRITON_MOBILE_SENTRY_REPORT.md) (TD-COW-003 v3.1) for the full concept and architecture.

## Concept

| Capability | v1 (hackathon) |
|------------|----------------|
| Mobile CCTV (record, clips, rolling buffer) | Yes |
| Acoustic impulse detect + A/V sync | Yes |
| Ultrasonic distance | Yes |
| RC navigation + yaw-only tracking | Yes |
| Shot triangulation, thermal, IR | Out of scope |
| Autonomous path planning | Out of scope |

Under a contested-EM story, video and logs are **stored locally** during watch and **uploaded to the cloud** after the operator drives the unit back to connectivity.

## Documentation

Full technical concept report (~20 sections):

- [`docs/TRITON_MOBILE_SENTRY_REPORT.md`](docs/TRITON_MOBILE_SENTRY_REPORT.md) — CONOPS, architecture, CCTV/acoustic pipelines, dual-mode control, demo plan, BOM (**TD-COW-003 v3.1**)
- [`apps/uno_q_yolo/README.md`](apps/uno_q_yolo/README.md) — UNO Q hub wiring, `VIDEO_DEVICE`, run and troubleshoot steps

## Operating modes

1. **RC navigation** — operator controls translation and steering for deploy and exfil.
2. **Watch / tracking** — CCTV and acoustic recording active; optional **autonomous yaw** to keep targets in the camera FOV; drive motors locked for translation.

## Repository layout

```text
TritonDefense/
├── apps/uno_q_yolo/          # Single Arduino UNO Q App Lab app (import this)
│   ├── app.yaml              # App manifest + video_object_detection brick
│   ├── python/main.py        # Detection UI bridge (no pip deps)
│   ├── sketch/sketch.ino     # MCU Bridge link
│   └── assets/index.html     # Browser UI
├── apps/uno_q_yolo.zip       # Same app, ready to import into App Lab
├── docs/
│   └── TRITON_MOBILE_SENTRY_REPORT.md
├── from_site.py              # PC-only YOLOv5 webcam demo (dev reference)
├── main.py
└── pyproject.toml
```

## Arduino UNO Q (single app)

Object detection runs as **one App Lab project** — no separate scripts, weights, or pip installs on the board.

| File | Purpose |
|------|---------|
| `app.yaml` | App manifest + `video_object_detection` and `web_ui` bricks |
| `python/main.py` | Forwards detections to the browser UI |
| `sketch/sketch.ino` | MCU Bridge link (future Elegoo motor control) |
| `assets/index.html` | Live video + detection panel |

**Quick start**

1. Import **`apps/uno_q_yolo`** or **`apps/uno_q_yolo.zip`** in [Arduino App Lab](https://docs.arduino.cc/software/app-lab/).
2. Wire a **USB webcam** through a **powered USB-C hub** (required — see [`apps/uno_q_yolo/README.md`](apps/uno_q_yolo/README.md)).
3. Connect App Lab to the UNO Q over **Network** (Wi‑Fi), not USB, when the hub is attached.
4. Click **Run**, then open **`http://<uno-q-ip>:7000`**.

Inference uses the built-in **`video_object_detection`** brick (`yolox-object-detection`, COCO 80 classes). Annotated video streams on port **4912**. Adjust confidence with the browser slider.

**PC development only:** `from_site.py` runs YOLOv5 on a laptop webcam for off-board tuning. It is not part of the board app.

## Development

Python **3.12+** with [uv](https://github.com/astral-sh/uv) (see `.python-version`):

```bash
uv sync
uv run python from_site.py   # PC webcam YOLOv5 demo (dev reference)
```

**Next integration step:** send person bearing from `python/main.py` over Bridge to `sketch/sketch.ino` for Elegoo yaw-only tracking in watch mode.

## Mission summary

> TritonDefense deploys **CCTV on wheels**—an Elegoo unit that **holds in a contested area**, **records video recon**, **detects acoustic threats on a shared timeline**, and **turns to follow personnel** without self-driving; the operator **RCs** for navigation and **uploads** data when connectivity returns.

## License

See [LICENSE](LICENSE).
