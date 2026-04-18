# Person 1 Vision Handoff

This branch owns the wound-photo pipeline for the hackathon MVP.

## Deliverable

Run one image through the vision pipeline and export both artifacts:

```bash
python3 scripts/run_wound_detection.py assets/test_wound.jpg --pixels-per-cm 12
```

Outputs are written to `outputs/`:

- `*_wounds.json` for mobile and triage integration
- `*_annotated.jpg` for demo screenshots and operator review

For short casualty clips:

```bash
python3 scripts/run_wound_detection_video.py assets/test_wound_video.avi --pixels-per-cm 12 --frame-stride 3
```

Video outputs are written to `outputs/`:

- `*_video_wounds.json` with per-frame analysis and a video-level summary
- `*_annotated.mp4` or `*_annotated.avi` depending on local codec support

## Primary Integration Path

Person 3's contract is in-process Python, not HTTP. The merge-safe integration
surface is in [vision/integration.py](/Users/aaryansuri/Documents/New project/Aegis/vision/integration.py).

Use these helpers:

```bash
from vision.integration import build_wound_suggestions, top_wound_suggestion
```

They return Python objects built from the current vision analysis without
touching the group-owned `schema.py`.

Expected usage pattern:

```python
analysis = analyzer.analyze_image(frame, pixels_per_cm=12)
suggestions = build_wound_suggestions("A1", analysis, Suggestion)
```

Each suggestion has:

- `source="vision"`
- `field="wound"`
- `proposed_value=DetectedWound(...)`
- `rationale="Detected bleeding laceration ..."`

`DetectedWound` is a local dataclass owned by vision. That avoids guessing the
group's shared `Wound` dataclass until Person 3 or the group publishes it.

## Optional API Wrapper

The FastAPI wrapper in [vision/api.py](/Users/aaryansuri/Documents/New project/Aegis/vision/api.py)
still works for debugging and demos, but it is no longer the primary mobile
contract.

## Vision Output Shape

Top-level fields:

- `wounds_detected`: boolean summary
- `wound_count`: number of wound candidates
- `wounds`: list of wound records
- `overall_severity`: capped sum of wound severities for Person 4's rubric
- `priority_suggestion`: `RED`, `YELLOW`, or `GREEN`
- `confidence`: pipeline-level confidence
- `image_quality`: simple camera/frame quality score

Per-wound fields:

- `location`: `x`, `y`, `width`, `height`
- `severity`: `0.0-1.0`
- `type`: `laceration`, `puncture`, `abrasion`, `bruise`, `burn`, `unknown`
- `location_type`: `head`, `torso`, or `limb`
- `bleeding`: `true/false`
- `bleeding_detected`: alias of `bleeding`
- `size_cm2`: estimated wound area
- `confidence`: wound-level confidence
- `mask_area_px`: segmented area in pixels
- `notes`: human-readable heuristic explanation

## Integration Notes

For Person 3 mobile:

- Call the analyzer directly and turn the result into `Suggestion` objects with `build_wound_suggestions`
- Use `location` to draw overlays on the camera frame
- The `DetectedWound` dataclass carries `bbox`, `severity`, `location_type`, `bleeding`, `size_cm2`, `confidence`, and `notes`
- For recorded demos, use `run_wound_detection_video.py` and replay the annotated output video
- If no weights are present, fallback heuristics still return detections

For Person 4 triage:

- The vision output now directly applies Person 4's wound severity rubric
- Use `priority_suggestion` as the immediate vision-side priority hint
- Start with `summary.max_wound_severity` and `overall_severity` as wound-risk signals
- Treat `bleeding=true` as a high-priority feature
- Use `analysis.wound_count` and `summary.total_visible_wound_area_cm2` as additive burden signals
- For videos, use the video-level `summary.max_wound_severity` and `summary.peak_total_visible_wound_area_cm2`
- Ignore `type` if uncertain; it is heuristic, not clinically validated

## Still Needed From The Team

To wire directly into `Casualty.wounds`, I still need the shared `Wound`
dataclass shape. I did not guess it.

## Model Behavior

- If `models/yolov8n.pt` exists, the pipeline uses YOLO person detection
- If `models/mobile_sam.pt` exists, the pipeline uses SAM refinement
- If either weight file is missing, the pipeline still runs using image heuristics
