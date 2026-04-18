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

# Optional: place pretrained weights in models/
# - YOLO: models/yolov8n.pt
# - SAM:  models/mobile_sam.pt

# Analyze a still image from Person 1's wound pipeline
python -m vision.cli assets/test_wound.jpg --pixels-per-cm 12

# Export the full Person 1 handoff artifacts
python scripts/run_wound_detection.py assets/test_wound.jpg --pixels-per-cm 12

# Run the same pipeline across a short video clip
python scripts/run_wound_detection_video.py assets/test_wound_video.avi --pixels-per-cm 12 --frame-stride 3

# Or run the hackathon demo UI
streamlit run ui/app.py
```

Primary integration for the hackathon is in-process Python, not HTTP.

The vision side now exposes Python helpers that can build `Suggestion`-compatible
objects without depending on the group-owned `schema.py`:

```python
from vision.integration import build_wound_suggestions, top_wound_suggestion
```

The FastAPI wrapper still exists in [vision/api.py](/Users/aaryansuri/Documents/New project/Aegis/vision/api.py), but it is now optional and should be treated as a demo/debug surface, not the primary mobile contract.

The wound analysis payload now also includes Person 4's triage-facing fields:

- `location_type`: `head`, `torso`, or `limb`
- `bleeding_detected`: alias of `bleeding`
- `overall_severity`: capped sum of wound severities
- `priority_suggestion`: `RED`, `YELLOW`, or `GREEN`

Example output:

```json
{
  "wounds_detected": true,
  "wound_count": 2,
  "overall_severity": 0.8,
  "priority_suggestion": "RED",
  "wounds": [
    {
      "location": { "x": 100, "y": 200, "width": 50, "height": 30 },
      "severity": 0.7,
      "type": "laceration",
      "location_type": "torso",
      "bleeding": true,
      "bleeding_detected": true,
      "size_cm2": 15.5,
      "confidence": 0.85,
      "mask_area_px": 1860,
      "notes": "type heuristic: laceration; estimated size: 15.5 cm^2; body region: torso; active bleeding signature"
    }
  ],
  "confidence": 0.85,
  "image_quality": 0.9
}
```

---

## Demo

Generate a synthetic casualty image for demos:

```bash
python scripts/generate_demo_assets.py
```

Then run either the image or video demo:

```bash
python scripts/run_wound_detection_video.py assets/test_wound_video.avi --pixels-per-cm 12 --frame-stride 3
streamlit run ui/app.py
```

The app supports:

- Image upload for quick teammate testing
- Camera capture for mobile/laptop demos
- Overlay rendering for wound boxes and severity
- Raw JSON output for downstream fusion and triage components

The video script produces:

- An annotated demo video
- A per-frame JSON timeline with wound detections
- A video-level summary for triage and presentation use

For the merge contract used by the other teammates, see `docs/person1_handoff.md`.

---

## Demo Mode

For rehearsals or as a safety net if any live pipeline is unavailable:

1. `streamlit run ui/app.py`
2. In the sidebar, set Demo Mode to `"Scripted MASCAL (90s)"`
3. Click `Play`

The dashboard will play a pre-recorded video and fire scripted suggestions,
voice commands, and a MEDEVAC trigger over a 90-second loop. Zero external
dependencies.

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
