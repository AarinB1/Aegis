from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import cv2
import numpy as np
import streamlit as st
from PIL import Image

from vision.render import draw_wounds
from vision.wound_detection import WoundAnalyzer


st.set_page_config(page_title="AEGIS Wound Demo", page_icon="🩸", layout="wide")


@st.cache_resource
def load_analyzer(yolo_weights: Optional[str], sam_checkpoint: Optional[str]) -> WoundAnalyzer:
    return WoundAnalyzer(yolo_weights=yolo_weights, sam_checkpoint=sam_checkpoint)


def pil_to_bgr(image: Image.Image) -> np.ndarray:
    rgb = np.array(image.convert("RGB"))
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


def render_summary(result: Dict[str, Any]) -> None:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Wounds", result["wound_count"])
    col2.metric("Pipeline Confidence", f"{result['confidence']:.2f}")
    col3.metric("Image Quality", f"{result['image_quality']:.2f}")
    bleeding_count = sum(1 for wound in result["wounds"] if wound["bleeding"])
    col4.metric("Bleeding Flags", bleeding_count)


def main() -> None:
    st.title("AEGIS")
    st.caption("Hackathon MVP for automated wound detection, sizing, and bleeding assessment.")

    with st.sidebar:
        st.subheader("Model Inputs")
        use_default_models = st.toggle("Use default model paths", value=True)
        default_yolo = "models/yolov8n.pt" if use_default_models else ""
        default_sam = "models/mobile_sam.pt" if use_default_models else ""
        yolo_weights = st.text_input("YOLO weights", value=default_yolo)
        sam_checkpoint = st.text_input("SAM checkpoint", value=default_sam)
        pixels_per_cm = st.number_input(
            "Pixels per cm",
            min_value=1.0,
            max_value=100.0,
            value=12.0,
            step=0.5,
            help="Use a known scale when available; otherwise AEGIS estimates it.",
        )
        st.markdown(
            "If model files are missing, the app falls back to color- and contour-based wound proposals."
        )

    analyzer = load_analyzer(
        yolo_weights=yolo_weights if Path(yolo_weights).exists() else None,
        sam_checkpoint=sam_checkpoint if Path(sam_checkpoint).exists() else None,
    )

    tab_upload, tab_camera = st.tabs(["Upload Image", "Use Camera"])

    with tab_upload:
        uploaded = st.file_uploader("Choose a casualty image", type=["jpg", "jpeg", "png"])
        if uploaded is not None:
            image = Image.open(uploaded)
            process_image(analyzer, image, pixels_per_cm)

    with tab_camera:
        captured = st.camera_input("Capture casualty frame")
        if captured is not None:
            image = Image.open(captured)
            process_image(analyzer, image, pixels_per_cm)


def process_image(analyzer: WoundAnalyzer, image: Image.Image, pixels_per_cm: float) -> None:
    image_bgr = pil_to_bgr(image)
    result = analyzer.analyze_image(image_bgr, pixels_per_cm=pixels_per_cm)
    annotated = cv2.cvtColor(draw_wounds(image_bgr, result), cv2.COLOR_BGR2RGB)

    left, right = st.columns([1.2, 1.0])
    with left:
        st.image(annotated, caption="AEGIS wound overlay", use_container_width=True)
    with right:
        render_summary(result)
        st.subheader("Detected Wounds")
        if result["wounds"]:
            for index, wound in enumerate(result["wounds"], start=1):
                st.markdown(
                    f"**Wound {index}**  \n"
                    f"Type: `{wound['type']}`  \n"
                    f"Severity: `{wound['severity']:.2f}`  \n"
                    f"Bleeding: `{wound['bleeding']}`  \n"
                    f"Size: `{wound['size_cm2']:.2f} cm^2`  \n"
                    f"Confidence: `{wound['confidence']:.2f}`  \n"
                    f"Notes: {wound['notes']}"
                )
        else:
            st.info("No wound candidates found in this frame.")
        st.subheader("Raw JSON")
        st.json(result)


if __name__ == "__main__":
    main()
