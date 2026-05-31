# TritonDefense

**CCTV on wheels** — a mobile surveillance node for contested reconnaissance, built for a military-themed autonomous-vehicle hackathon.

An **Elegoo Smart Robot Car V4** carries an **Arduino UNO Q** with a USB webcam. **Live video** and **YOLO person detection** are the primary recon product. Operators **drive by IR remote**; optional **servo pan tracking** keeps a person in the camera FOV without autonomous translation.

## Shipped implementation

**Final application:** [`app_final (2).zip`](app_final%20(2).zip) (same layout as [`app_final/`](app_final/)).

| Capability | Status |
|------------|--------|
| Live CCTV + YOLO person detection (web UI) | **Working** |
| IR remote navigation (forward / back / left / right) | **Working** |
| Servo pan tracking (toggle via IR; yaw-only, no auto-drive) | **Working** |
| Acoustic impulse detect + A/V sync | **Not implemented** |
| Ultrasonic distance | **Not implemented** |
| Local recording, rolling buffer, cloud upload | **Not implemented** |
| Shot triangulation, thermal, IR sensing | Out of scope |
| Autonomous path planning | Out of scope |

Acoustic sensing was part of the original concept but is **not functional** in the shipped build — no microphone pipeline or audio event logging is present in the final app.

## Quick start

1. Import **`app_final (2).zip`** (or the `app_final/` folder) into **Arduino App Lab**.
2. Wire a **powered USB-C hub** on the UNO Q and attach a **UVC webcam** (see [`apps/uno_q_yolo/README.md`](apps/uno_q_yolo/README.md) for hub wiring).
3. Flash the **sketch** to the ELEGOO MCU; run the **Python** app on the UNO Q.
4. Open **`http://<uno-q-ip>:7000`** for live annotated video and detection telemetry.
5. Use the **IR remote** to drive; press the **tracking toggle** button (IR `0xF78` / `0x778`) to enable or disable person-follow panning.

## Operating modes

1. **RC navigation** — IR remote controls translation and steering on the Elegoo chassis.
2. **Watch / tracking** — YOLO detects persons; when tracking is toggled on, the **servo pans** to follow a locked target. Drive motors are not commanded by the tracker.

## Repository layout

```text
TritonDefense/
├── app_final/                    # Final App Lab app (mirror of app_final (2).zip)
│   ├── app.yaml
│   ├── python/main.py            # YOLO detection + target lock + servo pan
│   ├── sketch/sketch.ino         # ELEGOO IR RC + servo + Bridge
│   └── assets/index.html         # Web UI
├── app_final (2).zip             # Canonical final deliverable
├── apps/uno_q_yolo/              # Earlier YOLO-only prototype (no car integration)
├── docs/
│   └── TRITON_MOBILE_SENTRY_REPORT.md   # Original concept & hackathon spec
├── killerbot/                    # IR / motor development artifacts
├── main.py                       # Python tooling scaffold
├── pyproject.toml
└── LICENSE
```

## Documentation

- [`docs/PROJECT_STORY.md`](docs/PROJECT_STORY.md) — One-page hackathon narrative and issues we faced

Full original technical concept (~20 sections), including planned acoustic and ultrasonic subsystems:

- [`docs/TRITON_MOBILE_SENTRY_REPORT.md`](docs/TRITON_MOBILE_SENTRY_REPORT.md) — CONOPS, architecture, demo plan, BOM (document ID: **TD-COW-003**)

That report describes the **design intent**. See the capability table above for what the **final build** actually ships.

## Development

Python **3.12+** with [uv](https://github.com/astral-sh/uv) (see `.python-version`) for local tooling and experiments:

```bash
uv sync
uv run python from_site.py   # PC webcam YOLOv5 demo (dev reference)
```

Firmware and vision on the UNO Q run through **App Lab**, not this repo’s `main.py`.

## Mission summary

> TritonDefense deploys **CCTV on wheels**—an Elegoo unit with live **YOLO video recon** and **servo pan tracking** of personnel. The operator **RCs** for navigation; tracking **yaws the camera** without self-driving. Acoustic threat detection and cloud exfil remain **future work**; they are documented in the concept report but are **not in the final app**.

## License

See [LICENSE](LICENSE).
