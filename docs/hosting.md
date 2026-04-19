# Hosting AEGIS

## Recommended Production Split

- **Landing site:** host `landing/` on Vercel.
- **Dashboard + Python vision pipeline:** host the repo root on a Docker-capable Python host.

For this project, the most practical path is **Render**:

- Render Web Services can deploy from a Git repository or Docker image and expose a public URL.
- Render supports Docker-based services and can attach a persistent disk for runtime assets like model files.

Official references:

- [Render Web Services](https://render.com/docs/web-services)
- [Render Blueprint YAML Reference](https://render.com/docs/blueprint-spec)
- [Vercel Python Functions limits](https://vercel.com/docs/functions/limitations/)

## Why not Vercel for the Streamlit app?

Vercel is a strong fit for the static/public marketing site in `landing/`, but the existing AEGIS dashboard is a long-lived Streamlit server with Python state, OpenCV processing, and optional model files. That is better served by a Docker web service than by serverless functions.

## What is in this repo now?

The repo includes everything needed to host the Streamlit dashboard and demo-safe vision pipeline:

- `Dockerfile.streamlit`
- `render.yaml`
- `.streamlit/config.toml`

The Streamlit service starts with:

```bash
streamlit run ui/app.py --server.address 0.0.0.0 --server.port $PORT
```

## Deploying on Render

1. Push the repo to GitHub.
2. In Render, create a new **Blueprint** and point it at this repository.
3. Render will detect `render.yaml` and create the `aegis-dashboard` web service.
4. Once deployed, open the public `onrender.com` URL for the Streamlit dashboard.

## Model-backed vs heuristic mode

The hosted app works without model files by falling back to heuristic detection.

For stronger demo performance, attach a persistent disk and provide model paths via environment variables:

- `AEGIS_YOLO_WEIGHTS=/var/data/models/yolov8n.pt`
- `AEGIS_SAM_CHECKPOINT=/var/data/models/mobile_sam.pt`

If those files are not present, the app still runs in heuristic mode.

## Optional vision API

The repo also includes a Python API in `vision/api.py`. If you want a separate API service later, it can reuse the same model path environment variables:

- `AEGIS_YOLO_WEIGHTS`
- `AEGIS_SAM_CHECKPOINT`

## Demo expectation

For a hackathon/public demo, the safest hosted flow is:

- use the curated demo clips already committed under `assets/demo_videos/`
- let the Streamlit dashboard run the scripted demo scenarios
- treat model files as an optional upgrade for tighter multi-casualty detection
