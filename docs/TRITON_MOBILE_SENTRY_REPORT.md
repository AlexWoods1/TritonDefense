# TritonDefense CCTV-on-Wheels
## Technical Concept Report — Mobile Video Surveillance with Acoustic Sensing for Contested Reconnaissance

**Document ID:** TD-COW-003  
**Version:** 3.0 (Hackathon Draft)  
**Classification:** Unclassified — Competition / Educational Use  
**Prepared for:** Military-Themed Autonomous Vehicle Hackathon  
**Organization:** TritonDefense  

---

## Implementation status (final build)

**Canonical code:** `app_final (2).zip` (same contents as `app_final/`).

| Planned capability (this report) | Final build |
|----------------------------------|-------------|
| Live CCTV + person tracking | **Shipped** — YOLO on UNO Q, servo pan, IR toggle |
| IR RC navigation (Elegoo V4) | **Shipped** |
| Acoustic impulse detect + A/V sync | **Not implemented** — no functional audio pipeline |
| Ultrasonic distance | **Not implemented** |
| Local recording / cloud upload | **Not implemented** |

The sections below describe **original design intent**. Where they mention acoustic sensing, ultrasonic ranging, or offline/cloud data management, treat those as **concept-only** unless marked shipped in the table above.

---

## Abstract

TritonDefense proposes **CCTV on wheels**: a **relocatable video sentry** on an **Elegoo robot car** for reconnaissance in **hostile, contested** areas. The platform behaves like a **mobile closed-circuit surveillance node**—**continuous or event-driven video** is the **primary recon product**, supported by **acoustic sensing** for **impulsive events** (e.g., simulated gunfire, bangs, sharp transients) that are **time-aligned** with the video record. An **ultrasonic sensor** provides **distance** to targets or obstacles in the watch sector.

The vehicle does **not** perform **shot triangulation** or use **thermal** or **infrared** sensing in this design. **Navigation** is **remote control (RC)** only. **Autonomous tracking mode** provides **yaw-only** follow of personnel—the chassis **does not translate on its own** during watch; only **steering** is autonomous.

Under optional **jamming**, video and acoustic data are **stored locally** and **uploaded to the cloud** after the operator **RCs** the unit back to connectivity. This report covers CONOPS, architecture, CCTV pipeline, acoustic subsystem, dual-mode control, data management, demonstration, and limitations.

---

## Table of Contents

1. [Introduction](#1-introduction)  
2. [Hackathon Context and Objectives](#2-hackathon-context-and-objectives)  
3. [Concept of Operations](#3-concept-of-operations)  
4. [System Architecture Overview](#4-system-architecture-overview)  
5. [Mobile Platform (Elegoo)](#5-mobile-platform-elegoo)  
6. [CCTV Video Surveillance Subsystem](#6-cctv-video-surveillance-subsystem)  
7. [Acoustic Sensing Subsystem](#7-acoustic-sensing-subsystem)  
8. [Ultrasonic Ranging Subsystem](#8-ultrasonic-ranging-subsystem)  
9. [Dual-Mode Control: RC Navigation and Autonomous Tracking](#9-dual-mode-control-rc-navigation-and-autonomous-tracking)  
10. [Data Management: Local Store and Cloud Upload](#10-data-management-local-store-and-cloud-upload)  
11. [Communications and Contested Environment Posture](#11-communications-and-contested-environment-posture)  
12. [Power, Mechanical, and Environmental Considerations](#12-power-mechanical-and-environmental-considerations)  
13. [Software Architecture (Arduino-Centric)](#13-software-architecture-arduino-centric)  
14. [Hackathon Demonstration Plan](#14-hackathon-demonstration-plan)  
15. [Threat Model, Assumptions, and Limitations](#15-threat-model-assumptions-and-limitations)  
16. [Comparison to Related Systems](#16-comparison-to-related-systems)  
17. [Development Plan, Schedule, and Risk Register](#17-development-plan-schedule-and-risk-register)  
18. [Future Work and Scaling Path](#18-future-work-and-scaling-path)  
19. [Conclusion](#19-conclusion)  
- [Appendix A: Event Record Schema (Draft)](#appendix-a-event-record-schema-draft)  
- [Appendix B: Bill of Materials (Indicative)](#appendix-b-bill-of-materials-indicative)  
- [Appendix C: Glossary](#appendix-c-glossary)  

---

## 1. Introduction

### 1.1 Purpose

Fixed **CCTV** covers installations well but cannot quickly **reposition** when the area of operations (AO) shifts. TritonDefense puts that capability **on wheels**: a **mobile surveillance post** that operators place by **RC**, then operate like a **field camera tower** with an **acoustic channel** for threat cues.

The **vehicle is the CCTV node**. **Video** is the main input; **acoustic** adds **ears** to the feed—detecting loud transients and tagging the timeline for review. **Ultrasonic** adds **standoff distance** in the watch direction.

### 1.2 Problem Statement

| Challenge | Operational impact | TritonDefense response |
|-----------|-------------------|------------------------|
| No persistent watch at a new choke point | Blind spots | **RC** reposition; deploy CCTV on wheels |
| Video without context | Missed gunfire cues | **Acoustic** impulse detect + timestamp sync |
| Range unknown from pixels alone | Weak threat assessment | **Ultrasonic** distance |
| Personnel cross FOV | Lost subject | **Yaw-only** auto-track in watch mode |
| Contested EM | No live stream | **Local A/V store** + cloud on return |
| Hackathon scope | Limited time | CCTV + acoustic slice; honest autonomy limits |

### 1.3 Scope

**In scope:**

- **CCTV on wheels** CONOPS: deploy, watch, record, exfil  
- Camera video capture, rolling buffer, event clips  
- **Acoustic** impulse detection and correlation with video timestamps  
- Ultrasonic distance (supplementary)  
- RC navigation; **turn-only** autonomous tracking in watch mode  
- Local logging and cloud upload  
- Hackathon demonstration  

**Out of scope (hackathon v1):**

- Thermal and infrared sensing  
- **Shot triangulation**, multi-vehicle TDOA, gunshot origin fusion  
- Autonomous path planning (deploy/return without operator)  
- Live-fire certification  
- Production EW-grade crypto  

### 1.4 Document Conventions

- **Shall** — hackathon reference requirement  
- **May** — optional enhancement  
- **TBD** — measured during integration  

---

## 2. Hackathon Context and Objectives

### 2.1 Event Framing

The project targets a **military-themed autonomous vehicle hackathon**. TritonDefense presents **CCTV on wheels** as a **surveillance-first** UGV: judges should see **recorded video recon** plus **acoustic marks** on the timeline, not only a tracking demo.

**Autonomy** is bounded: **RC** moves the node; **tracking mode** autonomously **yaws** toward personnel only.

### 2.2 Primary Objectives

1. **RC** the unit into a contested watch position.  
2. Operate as a **mobile CCTV** node: video watch + local recording.  
3. **Detect acoustic impulses** and log them **synchronized** with video timebase.  
4. **Measure distance** via ultrasonic when the watch sector is aligned.  
5. In **tracking mode**, **yaw** to follow personnel **without autonomous translation**.  
6. **Upload** video metadata, acoustic events, and clips to **cloud** after RC return.  

### 2.3 Success Criteria (Hackathon)

| Criterion | Metric (indicative) |
|-----------|---------------------|
| RC placement | Operator parks in hold zone |
| CCTV record | ≥ 30 s continuous or rolling buffer saved |
| Acoustic event | ≥ 1 impulse logged with timestamp during demo |
| A/V sync | Acoustic event within ±200 ms of video mark (TBD) |
| Turn-follow | Target kept in FOV ≥ 70% of 30 s trial (yaw only) |
| No auto drive | Drive motors off/locked in tracking mode |
| Cloud exfil | ≥ 1 successful upload bundle |

### 2.4 One-Line Mission Summary

> **TritonDefense** deploys **CCTV on wheels**—an **Elegoo** unit that **holds in a contested area**, **records video recon**, **detects acoustic threats on a shared timeline**, and **turns to follow personnel** without **self-driving**; the operator **RCs** for all **navigation** and **uploads** data when connectivity returns.

---

## 3. Concept of Operations

### 3.1 Phases of Employment

```
┌─────────────┐    ┌──────────────┐    ┌─────────────────────────┐    ┌──────────────┐
│  PLAN/LOAD  │───►│   DEPLOY     │───►│   WATCH (CCTV + AUDIO)  │───►│   EXFIL      │
│  (Friendly) │    │ (RC Mode)    │    │ (Tracking optional)     │    │ (RC Mode)    │
└─────────────┘    └──────────────┘    └─────────────────────────┘    └──────────────┘
      │                    │                        │                         │
   Format storage      Operator drives         Video + acoustic          RC to base;
   test mic/camera      to hold point           log locally               cloud upload
```

**Phase 1 — Plan and load:** Verify RC, camera, **microphone**, ultrasonic, storage. Set mission ID and clock epoch for **A/V sync**.

**Phase 2 — Deploy (RC):** Operator drives into the AO and parks at the watch point. No autonomous routing.

**Phase 3 — Watch (CCTV + acoustic):**  
- **Video:** rolling buffer and/or continuous segment recording (CCTV behavior).  
- **Acoustic:** monitor for impulses; on trigger, latch timestamp and optionally **ring-buffer pre-roll** clip.  
- **Tracking mode (optional):** yaw toward detected personnel; translation locked.  
- **Jamming narrative:** no live cloud stream; all A/V to local store.

**Phase 4 — Exfil (RC):** Operator drives to friendly Wi-Fi; system uploads bundles (events + clip references + range log).

### 3.2 Roles and Entities

| Entity | Role |
|--------|------|
| CCTV-on-wheels node | Video + acoustic + range sensor platform |
| Operator | RC, mode switch, safety |
| Cloud | Archive, timeline UI, playback |
| Demo threat | Walker in FOV + acoustic stimulus (speaker/clap) |

### 3.3 Watch Sector

```
     [Operator RC]
           │
           ▼
      ┌─────────┐
      │ Elegoo  │═══ camera (CCTV FOV) ═══► scene / personnel
      │  node   │
      └────┬────┘
           ├── microphone (acoustic)
           └── ultrasonic (range)
```

### 3.4 Rules of Engagement (Demo)

- Simulated threats only (walkers, speaker bangs).  
- E-stop on RC transmitter.  
- Tracking mode: **no autonomous forward/reverse**.  

---

## 4. System Architecture Overview

### 4.1 Logical Architecture

```
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │                    TRITON CCTV-ON-WHEELS (Elegoo)                            │
 │  ┌─────────────────────┐  ┌──────────────────┐  ┌────────────────────────┐ │
 │  │ CCTV / Camera       │  │ Acoustic         │  │ Ultrasonic (range)     │ │
 │  │ video + track       │  │ impulse detect   │  │                        │ │
 │  └──────────┬──────────┘  └────────┬─────────┘  └───────────┬────────────┘ │
 │             │                      │                        │              │
 │             └──────────────────────┼────────────────────────┘              │
 │                                    ▼                                         │
 │                         ┌─────────────────────┐                              │
 │                         │  A/V sync + event   │                              │
 │                         │  logger (SD)        │                              │
 │                         └──────────┬──────────┘                              │
 │  ┌─────────────────────┐           │         ┌──────────────────────────┐  │
 │  │ Mode supervisor     │◄──────────┴────────►│ RC receiver (navigate)   │  │
 │  │ RC | TRACKING       │                     └──────────────────────────┘  │
 │  └──────────┬──────────┘                                                    │
 │             ▼                                                               │
 │      ┌─────────────┐    ┌──────────────┐                                     │
 │      │ Yaw (track) │    │ Drive lock   │                                     │
 │      └─────────────┘    └──────────────┘                                     │
 └─────────────────────────────────────────────────────────────────────────────┘
                                    │ upload when link up
                         ┌──────────▼──────────┐
                         │ Cloud: CCTV archive │
                         │ + acoustic timeline │
                         └─────────────────────┘
```

### 4.2 Design Principles

1. **CCTV-first:** Video record is the primary recon deliverable.  
2. **Acoustic augmentation:** Ears on the timeline—not triangulation in v1.  
3. **Honest autonomy:** RC translates; tracking **yaws only**.  
4. **Synchronized evidence:** Acoustic events share a clock with video frames.  
5. **Jam-tolerant:** Store locally; upload after RC exfil.  

### 4.3 Explicit Non-Goals (v1)

| Non-goal | Note |
|----------|------|
| Shot triangulation | Acoustic = **detect + timestamp**, not multi-node TDOA |
| Thermal / IR | Not in BOM |
| Autonomous navigation | RC only |
| Live PTZ on a mast | PTZ emulated by **vehicle yaw** in tracking mode |

---

## 5. Mobile Platform (Elegoo)

### 5.1 Platform

**Elegoo Smart Robot Car**: chassis, motor drivers, kit **ultrasonic**, **Arduino-compatible** MCU. **Camera** and **microphone** mount forward on a short mast or deck bracket.

### 5.2 CCTV-on-Wheels Identity

| Fixed CCTV tower | TritonDefense CCTV on wheels |
|------------------|------------------------------|
| Fixed install | **RC reposition** |
| Wired backhaul | **Store-and-forward** under jamming |
| Separate audio rare | **Integrated acoustic channel** |
| PTZ motor | **Whole vehicle yaw** in tracking mode |

### 5.3 Mode Summary

| Mode | Translation | Yaw | CCTV | Acoustic |
|------|-------------|-----|------|----------|
| **RC navigation** | Operator | Operator | Optional preview | Optional monitor |
| **Watch / tracking** | **Locked** | Auto (track) or fixed | **Record** | **Active** |

### 5.4 Mechanical

- Camera and mic **forward-aligned**  
- Ultrasonic co-boresighted where possible  
- `TRACKING_MODE` → `v_forward = 0` enforced in firmware  

---

## 6. CCTV Video Surveillance Subsystem

### 6.1 Role

The **camera** delivers **CCTV-style** recon:

- Live view (when allowed—not during jamming demo)  
- **Continuous or rolling-buffer** recording  
- **Event clips** (person detected, acoustic trigger)  
- **Tracking** output for yaw controller (`bearing_error`)  

### 6.2 Recording Modes

| Mode | Behavior | Use |
|------|----------|-----|
| Rolling buffer | Last *N* seconds circular | Pre-roll on acoustic trigger |
| Segment record | Fixed-duration files | Whole watch phase |
| Event clip | Extract buffer on trigger | Efficient exfil |

### 6.3 Vision Processing (Hackathon Tiers)

| Tier | Hardware | Capability |
|------|----------|------------|
| A | Serial camera + Arduino | Motion-based CCTV; limited track |
| B | ESP32-CAM / Pi | Person detect + track + clip filenames |
| C | Pi + ML | Stable person class for demo |

**Recommendation:** Tier **B** for credible **CCTV on wheels** demo.

### 6.4 Tracking → Yaw

Exports: `target_present`, `bearing_error_deg`, `confidence`. Yaw PID drives error to zero; **drive translation locked**.

### 6.5 CCTV Data Products

| Product | Description |
|---------|-------------|
| `VIDEO_SEGMENT` | Mission video file or chunk index |
| `VIDEO_MARK` | Frame index at acoustic trigger |
| `TRACK_UPDATE` | Bearing / confidence timeline |
| Thumbnail / metadata | Optional for cloud gallery |

### 6.6 Environmental Limits

Low light, glare, and rain degrade CCTV; acoustic wind noise may rise—see Section 7.4.

---

## 7. Acoustic Sensing Subsystem

### 7.1 Role

**Acoustic sensing** gives the mobile CCTV node **surveillance audio**:

- Detect **impulsive sounds** (simulated gunshot, clap, metal strike)  
- Timestamp relative to **shared mission clock** with video  
- Optionally **trigger** ring-buffer **video clip** capture  
- Log peak amplitude, duration, optional frequency band energy  

**Not in v1:** bearing estimation, shooter localization, or multi-vehicle TDOA (**no shot triangulation**).

### 7.2 Sensor Layout

| Option | Hackathon fit |
|--------|---------------|
| Single electret mic + analog front-end | **Minimum** — detect + time |
| Dual mic (L/R) | Optional rough bearing hint (future) |
| MEMS I²S mic | Better SNR if companion board present |

**Recommendation:** One **forward-facing** mic near the camera; second mic optional for redundancy.

### 7.3 Signal Processing

1. High-pass (~200 Hz) to reduce wind/rumble during watch  
2. Envelope or energy detector with **adaptive threshold**  
3. On impulse: `ACOUSTIC_DETECT` event with `timestamp_ms`, `peak_db`, `snr_estimate`  
4. Notify video pipeline: `mark_frame` + optional `clip_request`  
5. During **tracking mode**, motors off → lower self-noise than driving  

### 7.4 Wind and False Alarms

| Source | Mitigation |
|--------|------------|
| Wind | Windscreen on mic; raise threshold in outdoor demo |
| Operator speech | Ignore band or push-to-talk narrative |
| Footsteps | Require sharp attack time constant |
| Echo | Demo layout away from hard walls |

### 7.5 Acoustic–Video Synchronization

Shared `mission_epoch_ms` set at watch start. Arduino or companion stamps both:

- Video frame index ↔ time  
- Acoustic ISR ↔ same monotonic clock  

**Target:** ±200 ms alignment for hackathon scoring (TBD in test).

### 7.6 Acoustic Data Products

| Event | Payload |
|-------|---------|
| `ACOUSTIC_DETECT` | time, peak, duration, optional clip_id |
| `ACOUSTIC_CLIP_LINK` | ties to `VIDEO_MARK` |

---

## 8. Ultrasonic Ranging Subsystem

### 8.1 Role

**Ultrasonic** provides **range (cm)** along the watch boresight—supplementary to CCTV, not a second primary sensor.

### 8.2 Fusion

When `target_present` and low `bearing_error`, tag range as `person_aligned`. On acoustic trigger, log **range at trigger time** for context (“threat at ~X m”).

### 8.3 Limits

Beam width, soft targets, multipath—median filter and alignment gating apply (see v2 rationale; unchanged).

---

## 9. Dual-Mode Control: RC Navigation and Autonomous Tracking

### 9.1 RC Navigation Mode

Operator controls **all translation and steering** for deploy and exfil. CCTV may **preview** locally; recording may start on deploy or at watch entry.

### 9.2 Autonomous Tracking Mode (Watch)

- **Yaw** follows personnel in FOV  
- **No autonomous forward/reverse** — CCTV stays at a fixed post while **panning via chassis**  
- **Acoustic** and **video** recording remain active  
- RC override returns instantly to full control  

### 9.3 State Machine

```
INIT → RC_NAVIGATION ⇄ WATCH_CCTV [+ optional TRACKING yaw] → RC exfil → UPLOAD → DONE
```

`WATCH_CCTV` = video record + acoustic monitor; tracking is a **sub-state** when enabled.

### 9.4 Safety

| Interlock | Action |
|-----------|--------|
| RC override | Exit tracking |
| E-stop | Motor off |
| Drive lock in watch | `v_forward = 0` |

---

## 10. Data Management: Local Store and Cloud Upload

### 10.1 Local Store (Contested Watch)

| Data type | Storage |
|-----------|---------|
| Video segments / clips | SD (companion or module) |
| Acoustic event log | SD via Arduino |
| Track + range timeline | SD JSON lines |
| Mission metadata | Header file per sortie |

**CCTV on wheels** implies **storage budget** planning: clip length × bitrate ≤ SD capacity (TBD).

### 10.2 Upload (Friendly Zone)

After RC return:

1. Package mission manifest (events + file list)  
2. HTTPS upload clips and logs  
3. Cloud builds **unified timeline**: video scrubber + acoustic markers + range  

### 10.3 Cloud UI (Hackathon)

- Playback with **acoustic spikes** on timeline  
- Export JSON/CSV for judges  
- No triangulation map in v1  

### 10.4 Recon Output Summary

| Output | Source |
|--------|--------|
| CCTV video / clips | Camera pipeline |
| Acoustic events | Microphone pipeline |
| Sync marks | A/V sync module |
| Range samples | Ultrasonic |
| Shot origin map | **N/A** |

---

## 11. Communications and Contested Environment Posture

### 11.1 Jamming Narrative

During watch, **no live CCTV stream** to cloud—mimics contested EM. Operators rely on **local record**; **exfil** happens after RC return.

### 11.2 RF Summary

| Phase | RF |
|-------|-----|
| Deploy / exfil | RC transmitter |
| Watch | RC override only; no cloud |
| Upload | Wi-Fi at base |

### 11.3 Future

Encrypted burst upload or mesh clip relay—out of v1 scope.

---

## 12. Power, Mechanical, and Environmental Considerations

### 12.1 Power

| Subsystem | Draw note |
|-----------|-----------|
| Camera companion | Dominant during record |
| Acoustic ADC | Low average |
| Yaw-only tracking | Lower than continuous drive |
| RC transit | Peak on motors |

**Target:** ≥ 20 min RC + ≥ 10 min watch record (TBD).

### 12.2 Acoustic Mechanical

Foam windscreen; mic isolated from chassis vibration; **motors off** during watch.

---

## 13. Software Architecture (Arduino-Centric)

### 13.1 Partition

| Board | Tasks |
|-------|--------|
| Arduino (Elegoo) | RC, modes, drive lock, ultrasonic, acoustic ISR/threshold, log, upload trigger |
| ESP32-CAM / Pi | CCTV capture, buffer, person track, clip files, time sync to Arduino |

### 13.2 Modules

| Module | Responsibility |
|--------|----------------|
| `rc_input.cpp` | RC decode, mode switch |
| `motor_drive.cpp` | RC drive; yaw; drive lock |
| `acoustic.cpp` | Impulse detect, timestamps |
| `vision_link.cpp` | Bearing error, clip commands |
| `av_sync.cpp` | Shared clock, mark frames |
| `ultrasonic.cpp` | Range filter |
| `cctv_record.cpp` | Buffer/segment (companion) |
| `log.cpp` / `upload.cpp` | SD + HTTPS |

### 13.3 Testing Hooks

- `SIM_AUDIO` — inject impulse  
- `SIM_MARK` — fake video frame mark  
- LED: amber = watch, blue = tracking, red = acoustic trigger  

---

## 14. Hackathon Demonstration Plan

### 14.1 Demo Script

1. **RC** unit to hold point; start **CCTV + acoustic** watch.  
2. Walker crosses FOV; optional **tracking mode** — vehicle **yaws**, does not drive away.  
3. **Bang** (speaker/clap); acoustic event appears on log; **video mark** saved.  
4. Ultrasonic logs range sample at trigger (if aligned).  
5. **RC** back to base; **cloud upload**.  
6. Judges play timeline: **video + acoustic spike** + range metadata.  

### 14.2 Talking Points

- **CCTV on wheels** = repositionable surveillance, not a fixed tower  
- **Acoustic** = synchronized threat cues on the reel  
- **Turn-only** autonomy = honest hackathon boundary  
- Future: triangulation, thermal, true PTZ (optional mention only)  

### 14.3 Failure Modes

| Failure | Mitigation |
|---------|------------|
| A/V desync | Common epoch; log PPS tick |
| Acoustic false trigger | Threshold tune; windscreen |
| SD full | Shorter clips; lower resolution |
| Drive creep | Drive lock test |

---

## 15. Threat Model, Assumptions, and Limitations

### 15.1 Assumptions

- Single primary walker in FOV for tracking demo  
- Simulated gunfire is **acoustic-only** (speaker)  
- Vehicle stationary in watch (no slope creep)  
- Companion board handles CCTV bitrate  

### 15.2 Capability Matrix

| Capability | v1 |
|------------|-----|
| Mobile CCTV record | Yes |
| Acoustic impulse + sync | Yes |
| Personnel yaw track | Yes |
| Ultrasonic range | Yes |
| Shot triangulation | No |
| Thermal / IR | No |
| Autonomous navigation | No |
| Night CCTV without light | Limited |

### 15.3 Safety

RC E-stop; no live fire; acoustic demo levels within venue limits.

---

## 16. Comparison to Related Systems

| System | Character | TritonDefense v3 |
|--------|-----------|------------------|
| Fixed CCTV + separate audio | Wired site security | **Integrated A/V on UGV** |
| Boomerang / ShotSpotter class | Fire **localization** | **Detect only**, no TDOA |
| Body-worn camera | Person-mounted | **Emplaced watch via wheels** |
| Thermal sentry | IR primary | **Visible CCTV** primary |

---

## 17. Development Plan, Schedule, and Risk Register

### 17.1 Work Packages

| WP | Deliverable |
|----|-------------|
| WP1 | RC + drive lock |
| WP2 | CCTV record + buffer |
| WP3 | Acoustic detect + sync |
| WP4 | Yaw tracking + ultrasonic |
| WP5 | Cloud timeline UI |
| WP6 | Full demo |

### 17.2 Timeline

| Week | Focus |
|------|-------|
| 1 | RC + CCTV record |
| 2 | Acoustic + sync marks |
| 3 | Tracking + fusion log |
| 4 | Cloud + rehearsal |

### 17.3 Risks

| ID | Risk | Mitigation |
|----|------|------------|
| R1 | SD bandwidth | Short clips, ESP32-CAM |
| R2 | A/V desync | Shared epoch test |
| R3 | Wind false triggers | Threshold + windscreen |
| R4 | Vision too slow | Pi companion |
| R5 | Drive creep | Interlock test |

---

## 18. Future Work and Scaling Path

1. **Multi-node acoustic TDOA** (shot localization) across several CCTV-on-wheels units  
2. **Live encrypted stream** when not jammed  
3. **Pan-tilt head** instead of whole-vehicle yaw  
4. Thermal overlay on CCTV (picture-in-picture)  
5. **Auto-translate** slow reposition to hold range band (new mode)  
6. On-device gunshot **classification** from acoustic fingerprint  

---

## 19. Conclusion

TritonDefense **CCTV on wheels** (v3) is a **video-first mobile surveillance** node on **Elegoo** hardware with an **acoustic channel** for **impulse detection** synchronized to the **CCTV timeline**. **Ultrasonic** ranging adds context; **RC** handles all translation; **tracking mode** provides **yaw-only** follow. The design fits a **hackathon** evidence story—judges review **what the camera saw** and **what the microphone caught**—without claiming **shot triangulation** or **thermal/IR** sensing in v1.

---

## Appendix A: Event Record Schema (Draft)

```json
{
  "schema_version": 3,
  "mission_id": "UUID",
  "vehicle_id": "COW-01",
  "event_type": "ACOUSTIC_DETECT",
  "timestamp_ms": 123456789,
  "mode": "WATCH_CCTV",
  "payload": {
    "peak_db": 72.5,
    "duration_ms": 45,
    "video_mark_frame": 1842,
    "clip_id": "clip_003.mp4",
    "range_cm": 210,
    "range_aligned": true
  },
  "crc16": "0xABCD"
}
```

**Event types:** `MODE_CHANGE`, `VIDEO_SEGMENT_START`, `VIDEO_MARK`, `ACOUSTIC_DETECT`, `TRACK_UPDATE`, `TRACK_LOST`, `RANGE_SAMPLE`, `MISSION_END`, `UPLOAD_COMPLETE`.

---

## Appendix B: Bill of Materials (Indicative)

| Item | Qty | Note |
|------|-----|------|
| Elegoo Smart Robot Car kit | 1+ | Chassis, ultrasonic, Arduino |
| Camera (ESP32-CAM or Pi Camera) | 1 | **CCTV** primary |
| Electret or MEMS microphone + amp | 1 | **Acoustic** |
| microSD | 1 | Video + logs |
| RC transmitter + receiver | 1 | Navigation |
| ESP32/Pi | 1 | Record + sync |
| Mic windscreen | 1 | Outdoor demo |

**Not in v1:** thermal, IR, multi-car TDOA harness.

---

## Appendix C: Glossary

| Term | Definition |
|------|------------|
| CCTV on wheels | Mobile video surveillance node on a UGV |
| COW | CCTV on wheels (internal shorthand) |
| Watch mode | Stationary record + acoustic monitor |
| Tracking mode | Yaw-only follow; no auto translation |
| A/V sync | Shared clock for video marks and acoustic events |
| Drive lock | Forward/reverse commands disabled |
| CONOPS | Concept of Operations |

---

*End of Report TD-COW-003*
