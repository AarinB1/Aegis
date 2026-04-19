# AEGIS

**AI-Enhanced Guidance for Integrated Survival**

An edge-deployable AI copilot that extends one combat medic's perception
across dozens of casualties during Mass Casualty (MASCAL) events. AEGIS
fuses computer vision, audio analysis, and voice interaction to support
SALT and TCCC triage decisions in disconnected, intermittent,
low-bandwidth environments. The name Aegis is a greek word meaning 
a shield of protection in battles.

---

## The Problem

Up to 24% of battlefield deaths are potentially survivable with faster
prehospital care. The bottleneck isn't medical knowledge — every combat
medic knows what to do. The bottleneck is perception at scale: seeing
every wound, hearing every airway, and tracking every patient at the
same time, in conditions designed to overwhelm human senses.

In a MASCAL event, one or two medics have to assess, treat, and
evacuate dozens of casualties under fire, in smoke, darkness, and
deafening noise. We built AEGIS to be the perception layer that makes
this possible.

---

## What It Does

AEGIS acts as a second set of eyes and ears for the medic:

- **Wound detection & measurement** — MobileSAM and Grounding DINO
  identify wounds in real time, estimate their size, and flag active
  hemorrhage
- **Scene-level casualty prioritization** — the vision pipeline ranks
  everyone visible by bleeding burden, severity, and attention score
  so the medic can focus on the highest-risk patient first
- **Respiratory monitoring** — zero-shot CLAP audio classification
  detects stridor, gurgling, agonal breathing, and absent respirations
- **Casualty tracking** — YOLOv8 + ByteTrack + DINOv2 re-identification
  keep persistent identity on every casualty across chaotic scenes
- **Voice command interaction** — Whisper parses hands-free updates so
  the medic never has to put a patient down to touch a screen
- **SALT/TCCC triage decision support** — a rule-based engine aligned
  with doctrine, with full human-in-the-loop confirmation
- **Llama 3.2 clinical reasoning** — Meta's open-weight model runs
  locally to generate medic-readable justifications behind every
  triage suggestion
- **9-line MEDEVAC request generation** — structured evacuation
  requests draft themselves from the casualty roster
- **Fully offline** — no cloud, no network, no data leaves the device

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
│  SALT/TCCC + Llama   │
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
| Clinical reasoning | Meta Llama 3.2 (via Ollama, local) |
| Database | SQLite (local, file-based) |
| UI | Streamlit |
| Edge target | NVIDIA Jetson Orin NX (20–40 W) |

All models are zero-shot or pretrained. No custom training.

---

## Quick Start

```bash
# Clone the repo
git clone https://github.com/AarinB1/Aegis.git
cd Aegis

# Set up environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Optional: drop pretrained weights into models/
# - YOLO: models/yolov8n.pt
# - SAM:  models/mobile_sam.pt

# Optional: install Ollama and pull Llama 3.2 for triage reasoning
# https://ollama.ai
ollama pull llama3.2

# Analyze a still image
python -m vision.cli assets/test_wound.jpg --pixels-per-cm 12

# Run the full wound detection pipeline on a short video
python scripts/run_wound_detection_video.py assets/test_wound_video.avi --pixels-per-cm 12 --frame-stride 3

# Launch the dashboard
streamlit run ui/app.py

# Multi-casualty ranking across real DOD demo scenarios
python scripts/run_judge_demo.py hero --allow-builtin-yolo --skip-reel
python scripts/run_judge_demo.py indoor --allow-builtin-yolo --skip-reel
python scripts/run_judge_demo.py torso --allow-builtin-yolo --skip-reel
python scenario_ranker.py outputs/judge_demo/*/*_video_wounds.json
```

Primary integration is in-process Python, not HTTP. The FastAPI wrapper
in `vision/api.py` exists as a demo/debug surface, not the main contract.

The vision pipeline also exposes helpers that build `Suggestion`-compatible
objects without depending on the shared `schema.py`:

```python
from vision.integration import build_wound_suggestions, top_wound_suggestion
```

The wound analysis payload includes the triage-facing fields the engine
consumes:

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
      "notes": "laceration; 15.5 cm²; torso; active bleeding"
    }
  ],
  "confidence": 0.85,
  "image_quality": 0.9
}
```

---

## How the Triage Engine Works

The triage engine is a two-layer system:

**Layer 1 — Rule-based SALT/TCCC scoring.** Deterministic, doctrine-aligned,
auditable. Bleeding adds points. Head wounds add more points. Unresponsive
patients auto-escalate. A score threshold maps to RED, YELLOW, or GREEN.

**Layer 2 — Llama 3.2 clinical reasoning.** The rule engine decides
priority. Llama only explains why. When the system flags a casualty as
RED, Llama generates two clinical bullets like *"Active arterial
hemorrhage — MARCH protocol M priority. Severe limb injury at 0.9
severity, indicating significant tissue damage."*

Critically: **the LLM cannot change the priority.** If Llama hallucinates,
the rule engine's decision stands. This is the responsible-use pattern we
think small open-weight models unlock — reasoning capability at the
tactical edge, without surrendering the hard decisions to an
uninterpretable black box.

The engine also never auto-assigns the **expectant** category. That
categorization is medic-only, enforced in code.

Public helpers for other subsystems:

```python
from triage_engine import get_priority, get_priority_and_reasoning

priority = get_priority(casualty)
# -> 'red' | 'yellow' | 'green'

priority, reasoning = get_priority_and_reasoning(casualty)
# -> ('red', 'Active bleeding, severe tissue damage...')
```

---

## Demo Mode

For rehearsal or as a safety net if any live pipeline is unavailable:

1. `streamlit run ui/app.py`
2. In the sidebar, set Demo Mode to `"Scripted MASCAL (90s)"`
3. Click `Play`

The dashboard plays a pre-recorded video and fires scripted suggestions,
voice commands, and a MEDEVAC trigger over a 90-second loop. Zero external
dependencies.

---

## Tactical Map

Open `Tactical Map` from the left sidebar after launching the dashboard.
The app uses a native multi-page layout with `Dashboard` and
`Tactical Map` views.

The Tactical Map is a stylized overhead scene rendered as a live SVG:
a fixed combat medic at center, casualty markers colored by triage, live
counts in the header, hover tooltips, and a selection line from medic
to the currently selected casualty.

The right-side panel updates by selection:

- **No selection** — prompt to click a casualty
- **Medic** — quick handoff card with a link back to the dashboard
- **Casualty** — identity, triage, live vision suggestions, wound
  summaries, intervention history, and a status footer showing the
  casualty's live/dead indicator plus MARCH completion

### Tactical Map v2 / Simulation Mode

The sidebar exposes three scenario states:

- `Off`
- `Scripted MASCAL (90s)`
- `Simulation (mixed)`

`Scripted MASCAL (90s)` keeps the timed rehearsal flow. `Simulation
(mixed)` resets shared state, seeds three baseline casualties, then
layers simulation casualties on top for a denser static instrument view.

The Tactical Map v2 renders as a three-column instrument:

- **Left:** SVG overhead with faint terrain contours, grid, compound
  outline, quadrant labels, drifting medics, coverage radii, casualty
  markers, and assignment lines to the nearest medic
- **Middle:** detail panel that switches between casualty drill-down
  and medic POV depending on selection
- **Right:** live priority queue that ranks the roster continuously

Selection behavior:

- **Casualty** — identity, triage, last-seen time, queue rank, vision
  findings, wound summaries, real audio playback when a clip exists,
  diagnosis text, interventions, and triage rationale from the engine
- **Medic** — live shared frame, casualties inside that medic's zone,
  and the current top-ranked patient in that zone

The priority queue uses the `rank_roster` helper from `scenario_ranker`
each refresh, with a local triage/confidence fallback if ranking fails.
The top-ranked row is highlighted in gold, and the same casualty gets
a persistent gold reticle on the map.

Audio playback uses Streamlit's native audio widget. Diagnosis text
comes from `simulation.casualties`.

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

Safeguards, enforced in code:

- Every AI suggestion requires explicit medic confirmation
- Expectant (black) categorization **cannot** be AI-assigned — medic only
- Llama 3.2 cannot override the rule engine's priority — it only
  explains decisions
- Full audit log of every suggestion and decision, stored locally in
  SQLite with timestamps and provenance
- Confidence scores shown on every AI-derived field
- Manual override: disable AI suggestions entirely with one toggle
- Known limitations documented in `docs/model_card.md`

The system never makes life-or-death decisions. It surfaces information
faster so the medic can.

---

## Edge Deployment

AEGIS runs on tactical edge hardware with no network dependency:

| Hardware | Target FPS | Power |
|---|---|---|
| NVIDIA Jetson Orin NX | 15–30 | 20–40 W |
| Laptop (GPU) | 30+ | Reference |
| Laptop (CPU only) | 5–10 | Fallback |

Benchmarks in `benchmark/results.md`.

---

## Project Structure
Aegis/
├── requirements.txt           # Pinned dependencies
├── schema.py                  # Shared dataclasses (Casualty, Wound, etc.)
├── triage_engine.py           # SALT/TCCC rule engine + Llama reasoning
├── llm_integration.py         # Ollama / Llama 3.2 wrapper
├── scenario_ranker.py         # Multi-casualty ranking across scenes
├── shared/state.py            # AppState singleton (integration spine)
├── vision/                    # Vision pipeline (YOLO + SAM + tracking)
├── audio/                     # Audio pipeline (CLAP + Whisper)
├── simulation/                # Scenario seeding & simulation casualties
├── ui/                        # Streamlit dashboard + Tactical Map
├── scripts/                   # Demo runners & data seeding
├── tests/                     # Test suites per subsystem
├── assets/                    # Demo videos, audio samples
└── docs/                      # Architecture, model card, ethics

---

## Roadmap Beyond the MVP

What we'd build with more time and resources:

- **Casualty beacons** — disposable BLE/accelerometer tags for
  persistent identity across the scene
- **UAS overwatch** — tethered drone for top-down SALT global sort
- **Mesh networking** — LoRa/goTenna-class store-and-forward for
  multi-medic coordination
- **Fine-tuned models** — partnership with USAISR/DHA for validated
  combat wound datasets
- **Multimodal fusion** — thermal and IR for smoke and darkness,
  pulse oximetry integration
- **Federated learning** — continuous model improvement without data
  leaving the unit
- **Clinical validation** — IRB-reviewed field trials with SOCOM medic
  cohorts

---

## Hackathon Context

Built in 24 hours for **Critical Ops: DC National Security Hackathon**,
Meta Challenge #15.

This is a proof-of-concept demonstrating the perception layer.
Production deployment would require clinical validation, IRB review,
hardware ruggedization, and partnership with military medical research
institutions.

---

## Team

| Role | Name |
|---|---|
| Vision pipeline | Aaryan Suri |
| Audio pipeline | Neal |
| Triage engine & MEDEVAC | Ansh Bhatia |
| UI, integration & demo | Aarin |

---

## Acknowledgments

AEGIS builds on work from many open-source projects:

- **Meta** for Llama 3.2, Segment Anything, DINOv2, and MobileSAM
- **Ultralytics** for YOLOv8 and ByteTrack integration
- **IDEA-Research** for Grounding DINO
- **LAION** for CLAP
- **OpenAI** for Whisper
- **Ollama** for making Llama runnable offline at the edge
- The **TCCC Committee** and the **SALT Triage Working Group** for
  the doctrine this system supports

---

## License

MIT — see `LICENSE`.

YOLOv8 (Ultralytics) is AGPL-3.0. Production deployment should
consider swapping to a permissively-licensed detector such as RT-DETR
or YOLOX.

---

## Contact

Questions or interested in contributing? Open an issue on the repo.

---
