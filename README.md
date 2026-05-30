# TritonDefense

**CCTV on wheels** — a mobile surveillance node for contested reconnaissance, built for a military-themed autonomous-vehicle hackathon.

An **Elegoo robot car** acts as a relocatable sentry: **video** is the primary recon product, **acoustic** sensing flags impulsive events on a shared timeline, and **ultrasonic** ranging adds standoff distance. Operators use **remote control** for all driving; in watch mode the vehicle can **yaw to follow personnel** but does **not** move forward or backward on its own.

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

- [`docs/TRITON_MOBILE_SENTRY_REPORT.md`](docs/TRITON_MOBILE_SENTRY_REPORT.md) — CONOPS, architecture, CCTV/acoustic pipelines, dual-mode control, demo plan, BOM (document ID: **TD-COW-003**)

## Operating modes

1. **RC navigation** — operator controls translation and steering for deploy and exfil.
2. **Watch / tracking** — CCTV and acoustic recording active; optional **autonomous yaw** to keep targets in the camera FOV; drive motors locked for translation.

## Repository layout

```text
TritonDefense/
├── docs/
│   └── TRITON_MOBILE_SENTRY_REPORT.md   # System concept & hackathon spec
├── main.py                              # Python entry (tooling scaffold)
├── pyproject.toml
└── LICENSE
```

## Development

Python **3.12+** with [uv](https://github.com/astral-sh/uv) (see `.python-version`):

```bash
uv sync
uv run python main.py
```

Firmware and vision work for the Elegoo platform are described in the technical report; this repo currently holds project documentation and Python scaffolding.

## Mission summary

> TritonDefense deploys **CCTV on wheels**—an Elegoo unit that **holds in a contested area**, **records video recon**, **detects acoustic threats on a shared timeline**, and **turns to follow personnel** without self-driving; the operator **RCs** for navigation and **uploads** data when connectivity returns.

## License

See [LICENSE](LICENSE).
