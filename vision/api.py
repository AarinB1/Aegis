from __future__ import annotations

from io import BytesIO
from pathlib import Path
from uuid import uuid4

import cv2
import numpy as np
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image

from vision.contracts import MobileVisionResponse, WoundAnalysisResult
from vision.summary import summarize_analysis
from vision.wound_detection import WoundAnalyzer


app = FastAPI(title="AEGIS Wound Detection API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

analyzer = WoundAnalyzer(
    yolo_weights=str(Path("models") / "yolov8n.pt") if (Path("models") / "yolov8n.pt").exists() else None,
    sam_checkpoint=str(Path("models") / "mobile_sam.pt")
    if (Path("models") / "mobile_sam.pt").exists()
    else None,
)


@app.get("/health")
def healthcheck() -> dict:
    return {"status": "ok", "detection_mode": analyzer.detection_mode()}


def _decode_upload(data: bytes) -> np.ndarray:
    try:
        image = Image.open(BytesIO(data)).convert("RGB")
    except Exception as exc:
        raise ValueError("uploaded file is not a readable image") from exc
    rgb = np.array(image)
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


async def _run_analysis(file: UploadFile, pixels_per_cm: float | None) -> dict:
    try:
        payload = await file.read()
        image = _decode_upload(payload)
        return analyzer.analyze_image(image, pixels_per_cm=pixels_per_cm)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/analyze-image", response_model=WoundAnalysisResult)
async def analyze_image(
    file: UploadFile = File(...),
    pixels_per_cm: float | None = Form(default=None),
) -> WoundAnalysisResult:
    analysis = await _run_analysis(file, pixels_per_cm)
    return WoundAnalysisResult.model_validate(analysis)


@app.post("/v1/mobile/analyze", response_model=MobileVisionResponse)
async def analyze_mobile_image(
    file: UploadFile = File(...),
    casualty_id: str | None = Form(default=None),
    source_id: str | None = Form(default=None),
    pixels_per_cm: float | None = Form(default=None),
) -> MobileVisionResponse:
    analysis = await _run_analysis(file, pixels_per_cm)
    return MobileVisionResponse(
        request_id=str(uuid4()),
        casualty_id=casualty_id,
        source_id=source_id,
        analysis=WoundAnalysisResult.model_validate(analysis),
        summary=summarize_analysis(analysis, analyzer.detection_mode()),
    )
