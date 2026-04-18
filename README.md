# AEGIS

**AI-Enhanced Guidance for Integrated Survival**

An edge-deployable AI copilot that extends one combat medic's perception
across dozens of casualties during Mass Casualty (MASCAL) events. AEGIS
fuses zero-shot vision, audio analysis, and voice interaction to support
SALT and TCCC triage decisions in disconnected, intermittent, low-bandwidth
(DIL) environments.

> *"The aegis — a shield of protection carried into the fiercest battles."*

---

## The Problem

Up to 24% of battlefield deaths are potentially survivable with faster,
more effective prehospital care. The bottleneck is not medical knowledge —
medics know what to do — but **perception at scale**: seeing every wound,
hearing every airway, and tracking every patient simultaneously in
conditions designed to overwhelm human senses.

In a MASCAL event, one or two medics must assess, treat, and evacuate
dozens of casualties under fire, in smoke, darkness, and deafening noise.
AEGIS is the perception layer that makes this possible.

---

## What It Does

AEGIS acts as a silent second set of eyes and ears for the medic:

- 🩸 **Wound detection & segmentation** — MobileSAM + Grounding DINO identify
  and measure wounds in real time, flagging active hemorrhage
- 🫁 **Respiratory monitoring** — Zero-shot CLAP audio classification detects
  stridor, gurgling, agonal breathing, and absent respirations
- 👥 **Casualty detection & tracking** — YOLOv8 + ByteTrack + DINOv2 re-ID
  maintain persistent identity for every casualty across chaotic scenes
- 🎙️ **Voice command interaction** — Whisper-powered hands-free updates let
  the medic keep both hands on the patient
- 🏷️ **SALT/TCCC triage decision support** — Rule-based engine aligned with
  doctrine, with full human-in-the-loop confirmation
- 📋 **9-line MEDEVAC request generation** — Structured evacuation requests
  generated from the casualty roster
- 🔒 **Fully offline operation** — No cloud, no network dependency, no data
  leaves the device

---

## System Architecture
┌─────────────────┐      ┌─────────────────┐
│  Webcam (RGB)   │      │   Microphone    │
└────────┬────────┘      └────────┬────────┘
         │                        │
         ▼                        ▼
┌─────────────────┐      ┌─────────────────┐
│ Vision Pipeline │      │ Audio Pipeline  │
│ - YOLOv8        │      │ - CLAP          │
│ - ByteTrack     │      │ - Resp rate     │
│ - MobileSAM     │      │ - Whisper       │
│ - Grounding DINO│      │                 │
│ - DINOv2 re-ID  │      │                 │
└────────┬────────┘      └────────┬────────┘
         │                        │
         └───────────┬────────────┘
                     ▼
         ┌──────────────────────┐
         │  Fusion & Triage     │
         │  Engine (SALT/TCCC)  │
         └──────────┬───────────┘
                    ▼
         ┌──────────────────────┐
         │  Casualty Database   │
         │  (SQLite, local)     │
         └──────────┬───────────┘
                    ▼
         ┌──────────────────────┐
         │  Tactical Dashboard  │
         └──────────────────────┘

See `docs/architecture.png` for the detailed system diagram.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Person detection & tracking | YOLOv8 + ByteTrack (Ultralytics) |
| Wound segmentation | MobileSAM / EfficientSAM |
| Open-vocabulary detection | Grounding DINO |
| Posture classification | YOLOv8-pose / MediaPipe |
| Re-identification | DINOv2 embeddings |
| Audio classification | CLAP (zero-shot) |
| Speech-to-text | Whisper |
| Database | SQLite (local, file-based) |
| UI | Streamlit |
| Edge target | NVIDIA Jetson Orin NX (20-40W) |

All models are zero-shot or pretrained. No custom training required.

---

## Quick Start

```bash
# Clone the repo
git clone https://github.com/<your-org>/aegis.git
cd aegis

# Set up environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Download model weights (one-time, ~3GB)
python scripts/download_models.py

# Launch the tactical dashboard
streamlit run ui/app.py
```

The dashboard opens at `http://localhost:8501`.

---

## Demo

Run the bundled scenario video through the full pipeline:

```bash
streamlit run ui/app.py -- --source assets/scenario_video.mp4
```

Or use a live webcam:

```bash
streamlit run ui/app.py -- --source 0
```

To prove offline operation during a live demo:
```bash
# Disconnect from wifi — AEGIS continues running
```

---

## Voice Commands

Hold spacebar to speak. Supported commands:

| Command | Action |
|---|---|
| `"Red tag [ID]"` | Set casualty to IMMEDIATE |
| `"Yellow tag [ID]"` | Set casualty to DELAYED |
| `"Green tag [ID]"` | Set casualty to MINIMAL |
| `"Tourniquet on [location]"` | Log tourniquet intervention |
| `"Airway clear [ID]"` | Mark airway as managed |
| `"Pulse present [ID]"` | Confirm circulation |
| `"Note [text]"` | Add freeform note |
| `"MEDEVAC [ID]"` | Generate 9-line request |

---

## Ethics & Safety

**AEGIS is perception augmentation, not autonomous triage.**

Core safeguards, enforced in code:

- ✅ Every AI suggestion requires explicit medic confirmation
- ✅ Expectant (black) categorization **cannot** be AI-assigned — medic only
- ✅ Full audit log of every suggestion and decision, stored locally
- ✅ Confidence scores shown on every AI-derived field
- ✅ Manual override mode: disable AI suggestions entirely with one toggle
- ✅ Known limitations documented in `docs/model_card.md`

The system never makes life-or-death decisions. It surfaces information
faster so the medic can.

---

## Edge Deployment

AEGIS is designed to run on tactical edge hardware with no network dependency:

| Hardware | Target FPS | Power |
|---|---|---|
| NVIDIA Jetson Orin NX | 15-30 | 20-40W |
| Laptop (GPU) | 30+ | Reference |
| Laptop (CPU only) | 5-10 | Fallback |

Benchmark results in `benchmark/results.md`.

---

## Project Structure
aegis/
├── schema.py              # Shared Casualty data model
├── requirements.txt       # Pinned dependencies
├── vision/                # Vision pipeline
├── audio/                 # Audio pipeline
├── fusion/                # Triage decision engine
├── data/                  # Database & MEDEVAC generator
├── ui/                    # Streamlit dashboard
├── benchmark/             # Edge deployment benchmarks
├── assets/                # Scenario video, audio samples
└── docs/                  # Architecture, model card, ethics

---

## Roadmap Beyond the MVP

What we'd build with more time and resources:

- **Casualty beacons** — disposable BLE/accelerometer tags for persistent
  identity across the scene
- **UAS overwatch** — tethered drone for top-down SALT global sort
- **Mesh networking** — LoRa/goTenna-class store-and-forward for multi-medic
  coordination
- **Fine-tuned models** — partnership with USAISR/DHA for validated combat
  wound datasets
- **Multimodal fusion** — thermal + IR for smoke/darkness; pulse oximetry
  integration
- **Federated learning** — continuous model improvement without data leaving
  the unit
- **Clinical validation** — IRB-reviewed field trials with SOCOM medic cohorts

---

## Hackathon Context

Built in [X] hours by a team of 4 for [event name].

This is a proof-of-concept demonstrating the perception layer. Production
deployment would require clinical validation, IRB review, hardware
ruggedization, and partnership with military medical research institutions.

---

## Team

| Role | Name |
|---|---|
| Vision pipeline | [Name] |
| Audio pipeline | [Name] |
| Fusion & data layer | [Name] |
| UI & integration | [Name] |

---

## Acknowledgments

AEGIS builds on the work of many open-source projects:

- Meta AI for Segment Anything, DINOv2, and MobileSAM
- Ultralytics for YOLOv8 and ByteTrack integration
- IDEA-Research for Grounding DINO
- LAION for CLAP
- OpenAI for Whisper
- The TCCC Committee and SALT Triage Working Group for the doctrine this
  system supports

---

## License

MIT License — see `LICENSE` for details.

Note: YOLOv8 (Ultralytics) is AGPL-3.0. Production deployment should
consider swapping to a permissively-licensed detector such as RT-DETR or
YOLOX.

---

## Contact

Questions or interested in contributing? Open an issue or reach the team at
[email/contact].

---

*AEGIS: A shield of perception for those who shield others.*
