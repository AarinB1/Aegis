from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

import cv2
import numpy as np

from vision.contracts import BoundingBox, WoundAnalysisResult, WoundRecord
from vision.demo_profiles import DemoVideoProfile, get_demo_profile_for_frame_shape
from vision.triage import calculate_overall_severity, calculate_priority_suggestion, calculate_wound_severity, infer_location_type

try:
    from ultralytics import YOLO
except Exception:  # pragma: no cover - optional dependency at runtime
    YOLO = None

try:
    from segment_anything import SamPredictor, sam_model_registry
except Exception:  # pragma: no cover - optional dependency at runtime
    SamPredictor = None
    sam_model_registry = {}


@dataclass
class CandidateRegion:
    bbox: Tuple[int, int, int, int]
    mask: np.ndarray
    area_px: int
    mean_bgr: Tuple[float, float, float]
    mean_hsv: Tuple[float, float, float]
    redness_ratio: float
    blood_ratio: float
    orange_ratio: float
    purple_ratio: float
    person_roi: Tuple[int, int, int, int]
    person_detected: bool


class WoundAnalyzer:
    def __init__(
        self,
        yolo_weights: Optional[str] = None,
        sam_type: str = "vit_b",
        sam_checkpoint: Optional[str] = None,
        fallback_pixels_per_cm: float = 12.0,
    ) -> None:
        self.fallback_pixels_per_cm = fallback_pixels_per_cm
        self.yolo_model = self._load_yolo(yolo_weights)
        self.sam_predictor = self._load_sam(sam_type, sam_checkpoint)
        self._last_person_detected = False
        self._last_demo_profile: DemoVideoProfile | None = None

    def analyze_image(
        self,
        image: np.ndarray,
        pixels_per_cm: Optional[float] = None,
    ) -> dict:
        if image is None or image.size == 0:
            raise ValueError("image must be a non-empty numpy array")

        bgr = self._ensure_bgr(image)
        demo_profile = get_demo_profile_for_frame_shape(bgr.shape[:2])
        self._last_demo_profile = demo_profile
        image_quality = self._estimate_image_quality(bgr)
        rois, person_detected = self._detect_person_rois_with_source(bgr)
        self._last_person_detected = person_detected
        candidate_regions: List[CandidateRegion] = []

        for roi in rois:
            x, y, w, h = roi
            person_crop = bgr[y : y + h, x : x + w]
            candidates = self._find_wound_candidates(person_crop)
            for candidate in candidates:
                refined_mask = self._refine_with_sam(person_crop, candidate)
                if refined_mask is not None:
                    candidate = self._rebuild_candidate(candidate, refined_mask)
                cx, cy, cw, ch = candidate.bbox
                candidate_regions.append(
                    CandidateRegion(
                        bbox=(x + cx, y + cy, cw, ch),
                        mask=self._place_mask(
                            refined_mask if refined_mask is not None else candidate.mask,
                            roi,
                            (bgr.shape[0], bgr.shape[1]),
                            candidate.bbox,
                        ),
                        area_px=candidate.area_px,
                        mean_bgr=candidate.mean_bgr,
                        mean_hsv=candidate.mean_hsv,
                        redness_ratio=candidate.redness_ratio,
                        blood_ratio=candidate.blood_ratio,
                        orange_ratio=candidate.orange_ratio,
                        purple_ratio=candidate.purple_ratio,
                        person_roi=roi,
                        person_detected=person_detected,
                    )
                )

        deduped_candidates = self._dedupe_candidates(candidate_regions)
        scale = pixels_per_cm or self._estimate_pixels_per_cm(bgr, rois, person_detected=person_detected)
        wounds = [self._candidate_to_wound(candidate, scale) for candidate in deduped_candidates]
        wounds = self._apply_demo_profile_filters(wounds, demo_profile)
        overall_severity = calculate_overall_severity(wounds)
        priority_suggestion = calculate_priority_suggestion(wounds)
        overall_confidence = self._aggregate_confidence(wounds, image_quality)

        result = WoundAnalysisResult(
            wounds_detected=bool(wounds),
            wound_count=len(wounds),
            wounds=wounds,
            overall_severity=overall_severity,
            priority_suggestion=priority_suggestion,
            confidence=overall_confidence,
            image_quality=image_quality,
        )
        return result.model_dump()

    def analyze_path(
        self,
        image_path: str | Path,
        pixels_per_cm: Optional[float] = None,
    ) -> dict:
        image = cv2.imread(str(image_path))
        if image is None:
            raise FileNotFoundError(f"unable to read image: {image_path}")
        return self.analyze_image(image, pixels_per_cm=pixels_per_cm)

    def detect_person_rois(self, image: np.ndarray) -> List[Tuple[int, int, int, int]]:
        bgr = self._ensure_bgr(image)
        rois, person_detected = self._detect_person_rois_with_source(bgr)
        self._last_person_detected = person_detected
        self._last_demo_profile = get_demo_profile_for_frame_shape(bgr.shape[:2])
        return rois

    def last_person_detection_reliable(self) -> bool:
        return self._last_person_detected

    def last_demo_profile(self) -> DemoVideoProfile | None:
        return self._last_demo_profile

    def detection_mode(self) -> str:
        if self.yolo_model is not None and self.sam_predictor is not None:
            return "yolo+sam"
        if self.yolo_model is not None:
            return "yolo+heuristic"
        if self.sam_predictor is not None:
            return "heuristic+sam"
        return "heuristic"

    def runtime_summary(self) -> dict[str, str]:
        return {
            "detection_mode": self.detection_mode(),
            "person_detection": "yolo" if self.yolo_model is not None else "full-frame heuristic",
            "wound_refinement": "sam" if self.sam_predictor is not None else "color/contour heuristic",
        }

    def runtime_warnings(self) -> list[str]:
        warnings: list[str] = []
        if self.yolo_model is None:
            warnings.append(
                "YOLO person detection is unavailable; multi-casualty ranking may be less reliable on unconstrained footage."
            )
        if self.sam_predictor is None:
            warnings.append(
                "SAM wound refinement is unavailable; wound extents rely on color and contour heuristics."
            )
        return warnings

    def _load_yolo(self, weights: Optional[str]) -> Optional[object]:
        if not weights or YOLO is None:
            return None
        if not Path(weights).exists():
            return None
        return YOLO(weights)

    def _load_sam(self, sam_type: str, checkpoint: Optional[str]) -> Optional[object]:
        if not checkpoint or SamPredictor is None:
            return None
        if not Path(checkpoint).exists():
            return None
        sam_model = sam_model_registry[sam_type](checkpoint=checkpoint)
        return SamPredictor(sam_model)

    def _ensure_bgr(self, image: np.ndarray) -> np.ndarray:
        if image.ndim == 2:
            return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        if image.shape[2] == 4:
            return cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
        return image.copy()

    def _estimate_image_quality(self, image: np.ndarray) -> float:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blur_score = min(cv2.Laplacian(gray, cv2.CV_64F).var() / 500.0, 1.0)
        brightness = gray.mean() / 255.0
        brightness_score = 1.0 - min(abs(brightness - 0.55) / 0.55, 1.0)
        return round(float(0.65 * blur_score + 0.35 * brightness_score), 3)

    def _detect_person_rois(self, image: np.ndarray) -> List[Tuple[int, int, int, int]]:
        rois, _ = self._detect_person_rois_with_source(image)
        return rois

    def _detect_person_rois_with_source(
        self,
        image: np.ndarray,
    ) -> Tuple[List[Tuple[int, int, int, int]], bool]:
        if self.yolo_model is None:
            h, w = image.shape[:2]
            return [(0, 0, w, h)], False

        predictions = self.yolo_model.predict(image, verbose=False, classes=[0])
        rois: List[Tuple[int, int, int, int]] = []
        for prediction in predictions:
            for box in getattr(prediction, "boxes", []):
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                rois.append(
                    (
                        int(max(x1, 0)),
                        int(max(y1, 0)),
                        int(max(x2 - x1, 1)),
                        int(max(y2 - y1, 1)),
                    )
                )

        if rois:
            rois = self._filter_candidate_person_rois(rois, image_shape=image.shape[:2])
            return rois, True
        h, w = image.shape[:2]
        return [(0, 0, w, h)], False

    def _filter_candidate_person_rois(
        self,
        rois: Sequence[Tuple[int, int, int, int]],
        *,
        image_shape: Tuple[int, int],
    ) -> List[Tuple[int, int, int, int]]:
        if len(rois) <= 2:
            return list(rois)

        scored = [
            (self._casualty_roi_score(roi, image_shape=image_shape), roi)
            for roi in rois
        ]
        scored.sort(key=lambda item: item[0], reverse=True)
        best_score = scored[0][0]
        keep = [
            roi
            for score, roi in scored
            if score >= max(0.22, best_score - 0.18)
        ]
        if not keep:
            keep = [scored[0][1]]
        return keep[:3]

    def _casualty_roi_score(
        self,
        roi: Tuple[int, int, int, int],
        *,
        image_shape: Tuple[int, int],
    ) -> float:
        image_height, image_width = image_shape
        x, y, w, h = roi
        image_area = max(image_height * image_width, 1)
        area_ratio = (w * h) / image_area
        aspect_ratio = w / max(h, 1)
        center_y = (y + (h / 2.0)) / max(image_height, 1)

        prone_score = min(max((aspect_ratio - 0.55) / 0.8, 0.0), 1.0)
        area_score = min(area_ratio / 0.12, 1.0)
        lower_frame_score = min(max((center_y - 0.2) / 0.55, 0.0), 1.0)
        return round((0.45 * prone_score) + (0.35 * area_score) + (0.2 * lower_frame_score), 3)

    def _find_wound_candidates(self, image: np.ndarray) -> List[CandidateRegion]:
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)

        lower_red_1 = np.array([0, 110, 40], dtype=np.uint8)
        upper_red_1 = np.array([12, 255, 255], dtype=np.uint8)
        lower_red_2 = np.array([165, 110, 40], dtype=np.uint8)
        upper_red_2 = np.array([180, 255, 255], dtype=np.uint8)
        red_mask = cv2.inRange(hsv, lower_red_1, upper_red_1) | cv2.inRange(
            hsv, lower_red_2, upper_red_2
        )
        blood_mask = red_mask

        a_channel = lab[:, :, 1]
        tissue_mask = cv2.threshold(a_channel, 138, 255, cv2.THRESH_BINARY)[1]

        burn_mask = cv2.inRange(
            hsv,
            np.array([5, 80, 70], dtype=np.uint8),
            np.array([25, 255, 255], dtype=np.uint8),
        )
        purple_mask = cv2.inRange(
            hsv,
            np.array([120, 35, 25], dtype=np.uint8),
            np.array([165, 255, 230], dtype=np.uint8),
        )

        blue_channel, green_channel, red_channel = cv2.split(image)
        red_excess = red_channel.astype(np.float32) - (
            (green_channel.astype(np.float32) + blue_channel.astype(np.float32)) / 2.0
        )
        local_red = red_excess - cv2.GaussianBlur(red_excess, (0, 0), sigmaX=11)
        contrast_mask = np.where((local_red > 5.0) | (red_excess > 70.0), 255, 0).astype(np.uint8)

        candidate_mask = cv2.bitwise_and(blood_mask, tissue_mask)
        candidate_mask = cv2.bitwise_and(candidate_mask, contrast_mask)
        blood_mask = cv2.bitwise_and(blood_mask, tissue_mask)
        burn_mask = cv2.bitwise_and(burn_mask, tissue_mask)
        purple_mask = cv2.bitwise_and(purple_mask, tissue_mask)

        kernel = np.ones((5, 5), np.uint8)
        cleaned = cv2.morphologyEx(candidate_mask, cv2.MORPH_OPEN, kernel)
        cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        image_area = image.shape[0] * image.shape[1]
        image_height, image_width = image.shape[:2]
        candidates: List[CandidateRegion] = []
        minimum_area = max(150, int(image_area * 0.0008))

        for contour in contours:
            area = cv2.contourArea(contour)
            if area < minimum_area:
                continue

            x, y, w, h = cv2.boundingRect(contour)
            border_touches = int(x <= 1) + int(y <= 1) + int(x + w >= image_width - 1) + int(
                y + h >= image_height - 1
            )
            if border_touches >= 2 and area >= image_area * 0.01:
                continue
            if border_touches >= 1 and area < 400:
                continue

            contour_mask = np.zeros(image.shape[:2], dtype=np.uint8)
            cv2.drawContours(contour_mask, [contour], -1, 255, thickness=cv2.FILLED)
            pixels = image[contour_mask > 0]
            hsv_pixels = hsv[contour_mask > 0]
            if pixels.size == 0:
                continue

            mask_index = contour_mask > 0
            redness_ratio = float(np.mean(pixels[:, 2] > (pixels[:, 1] + 18)))
            blood_ratio = float(np.mean(blood_mask[mask_index] > 0))
            orange_ratio = float(np.mean(burn_mask[mask_index] > 0))
            purple_ratio = float(np.mean(purple_mask[mask_index] > 0))
            mean_bgr = tuple(float(v) for v in pixels.mean(axis=0))
            mean_hsv = tuple(float(v) for v in hsv_pixels.mean(axis=0))

            candidates.append(
                CandidateRegion(
                    bbox=(x, y, w, h),
                    mask=contour_mask,
                    area_px=int(area),
                    mean_bgr=mean_bgr,
                    mean_hsv=mean_hsv,
                    redness_ratio=redness_ratio,
                    blood_ratio=blood_ratio,
                    orange_ratio=orange_ratio,
                    purple_ratio=purple_ratio,
                    person_roi=(0, 0, image.shape[1], image.shape[0]),
                    person_detected=False,
                )
            )

        candidates = [
            candidate
            for candidate in candidates
            if self._is_plausible_candidate(candidate, image_shape=(image_height, image_width))
        ]
        candidates.sort(key=lambda candidate: candidate.area_px, reverse=True)
        if candidates:
            largest_area = candidates[0].area_px
            minimum_significant_area = max(250, int(largest_area * 0.06))
            candidates = [
                candidate
                for candidate in candidates
                if candidate.area_px >= minimum_significant_area or candidate.area_px >= 900
            ]
        return candidates[:6]

    def _refine_with_sam(
        self,
        image: np.ndarray,
        candidate: CandidateRegion,
    ) -> Optional[np.ndarray]:
        if self.sam_predictor is None:
            return None

        x, y, w, h = candidate.bbox
        self.sam_predictor.set_image(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        input_box = np.array([x, y, x + w, y + h])
        masks, scores, _ = self.sam_predictor.predict(box=input_box, multimask_output=True)
        if masks is None or len(masks) == 0:
            return None

        best_index = int(np.argmax(scores))
        refined = (masks[best_index].astype(np.uint8)) * 255
        overlap = cv2.bitwise_and(refined, candidate.mask)
        if cv2.countNonZero(overlap) == 0:
            return None
        return overlap

    def _rebuild_candidate(self, candidate: CandidateRegion, mask: np.ndarray) -> CandidateRegion:
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return candidate

        contour = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(contour)
        area = int(cv2.contourArea(contour))
        return CandidateRegion(
            bbox=(x, y, w, h),
            mask=mask,
            area_px=area,
            mean_bgr=candidate.mean_bgr,
            mean_hsv=candidate.mean_hsv,
            redness_ratio=candidate.redness_ratio,
            blood_ratio=candidate.blood_ratio,
            orange_ratio=candidate.orange_ratio,
            purple_ratio=candidate.purple_ratio,
            person_roi=candidate.person_roi,
            person_detected=candidate.person_detected,
        )

    def _place_mask(
        self,
        mask: np.ndarray,
        roi: Tuple[int, int, int, int],
        image_shape: Tuple[int, int],
        bbox: Tuple[int, int, int, int],
    ) -> np.ndarray:
        full_mask = np.zeros(image_shape, dtype=np.uint8)
        rx, ry, rw, rh = roi
        cropped_mask = mask[:rh, :rw]
        full_mask[ry : ry + cropped_mask.shape[0], rx : rx + cropped_mask.shape[1]] = cropped_mask
        return full_mask

    def _estimate_pixels_per_cm(
        self,
        image: np.ndarray,
        rois: Sequence[Tuple[int, int, int, int]],
        *,
        person_detected: bool,
    ) -> float:
        if not rois or not person_detected:
            return self.fallback_pixels_per_cm

        _, _, _, tallest_person = max(rois, key=lambda roi: roi[3])
        estimated = tallest_person / 170.0
        return max(float(estimated), self.fallback_pixels_per_cm / 2)

    def _candidate_to_wound(self, candidate: CandidateRegion, pixels_per_cm: float) -> WoundRecord:
        x, y, w, h = candidate.bbox
        size_cm2 = round(candidate.area_px / max(pixels_per_cm**2, 1.0), 2)
        wound_type = self._classify_wound_type(candidate)
        bleeding = self._detect_bleeding(candidate, wound_type)
        location_type = infer_location_type(
            candidate.bbox,
            candidate.person_roi,
            person_detected=candidate.person_detected,
        )
        severity = calculate_wound_severity(
            size_cm2=size_cm2,
            bleeding_detected=bleeding,
            location_type=location_type,
            wound_type=wound_type,
        )
        confidence = self._score_confidence(candidate, bleeding)

        return WoundRecord(
            location=BoundingBox(x=x, y=y, width=w, height=h),
            severity=severity,
            type=wound_type,
            location_type=location_type,
            bleeding=bleeding,
            bleeding_detected=bleeding,
            size_cm2=size_cm2,
            confidence=confidence,
            mask_area_px=candidate.area_px,
            notes=self._build_notes(wound_type, bleeding, size_cm2, location_type),
        )

    def _is_plausible_candidate(
        self,
        candidate: CandidateRegion,
        *,
        image_shape: Tuple[int, int],
    ) -> bool:
        image_height, image_width = image_shape
        x, y, w, h = candidate.bbox
        bbox_area = max(w * h, 1)
        fill_ratio = candidate.area_px / bbox_area
        elongated_ratio = max(w / max(h, 1), h / max(w, 1))
        wound_type = self._classify_wound_type(candidate)
        touches_border = (
            x <= 1
            or y <= 1
            or (x + w) >= image_width - 1
            or (y + h) >= image_height - 1
        )

        # Suppress long, sparse fabric folds and straps that can appear red/orange
        # under harsh lighting but do not have wound-like coverage.
        if wound_type in {"burn", "laceration", "abrasion", "unknown"}:
            if fill_ratio < 0.24 and elongated_ratio > 1.9:
                return False
            if touches_border and fill_ratio < 0.24 and candidate.orange_ratio > 0.55:
                return False

        return True

    def _classify_wound_type(self, candidate: CandidateRegion) -> str:
        blue, green, red = candidate.mean_bgr
        hue, saturation, value = candidate.mean_hsv
        _, _, w, h = candidate.bbox
        aspect_ratio = w / max(h, 1)

        if candidate.orange_ratio >= 0.65 and aspect_ratio < 1.6 and candidate.area_px >= 1200:
            return "burn"
        if candidate.purple_ratio >= 0.18 and candidate.blood_ratio < 0.25:
            return "bruise"
        if candidate.blood_ratio >= 0.45 and aspect_ratio < 1.35 and candidate.area_px < 1800:
            return "puncture"
        if candidate.blood_ratio >= 0.28 and (aspect_ratio > 1.6 or candidate.area_px >= 1500):
            return "laceration"
        if candidate.blood_ratio >= 0.14 or candidate.redness_ratio >= 0.32:
            return "abrasion"
        if candidate.purple_ratio >= 0.1 or (green > red and blue > red):
            return "bruise"
        if candidate.orange_ratio >= 0.15 or (5 <= hue <= 25 and saturation >= 75 and value >= 70):
            return "burn"
        return "unknown"

    def _detect_bleeding(self, candidate: CandidateRegion, wound_type: str) -> bool:
        if wound_type == "bruise":
            return False
        if wound_type == "burn":
            return False
        return candidate.blood_ratio >= 0.2 or candidate.redness_ratio >= 0.4

    def _score_confidence(self, candidate: CandidateRegion, bleeding: bool) -> float:
        contour_density = min(candidate.area_px / 2500.0, 1.0)
        color_signal = min(
            max(candidate.blood_ratio, candidate.orange_ratio, candidate.purple_ratio) * 1.2,
            1.0,
        )
        bleeding_bonus = 0.1 if bleeding else 0.0
        confidence = 0.35 + 0.35 * contour_density + 0.2 * color_signal + bleeding_bonus
        return round(float(min(confidence, 0.99)), 3)

    def _build_notes(self, wound_type: str, bleeding: bool, size_cm2: float, location_type: str) -> str:
        notes = [
            f"type heuristic: {wound_type}",
            f"estimated size: {size_cm2} cm^2",
            f"body region: {location_type}",
        ]
        notes.append("active bleeding signature" if bleeding else "no strong bleeding signature")
        return "; ".join(notes)

    def _aggregate_confidence(self, wounds: Sequence[WoundRecord], image_quality: float) -> float:
        if not wounds:
            return round(float(0.3 * image_quality), 3)
        wound_confidence = sum(wound.confidence for wound in wounds) / len(wounds)
        return round(float(min(0.7 * wound_confidence + 0.3 * image_quality, 0.99)), 3)

    def _apply_demo_profile_filters(
        self,
        wounds: Sequence[WoundRecord],
        profile: DemoVideoProfile | None,
    ) -> List[WoundRecord]:
        wound_list = list(wounds)
        if not wound_list or profile is None:
            return wound_list

        if profile.wound_focus_roi is not None:
            focused = [
                wound for wound in wound_list if self._wound_intersects_roi(wound, profile.wound_focus_roi)
            ]
            if focused:
                wound_list = focused

        wound_list.sort(key=lambda wound: self._demo_wound_score(wound, profile), reverse=True)

        if profile.max_wounds is not None:
            wound_list = wound_list[: profile.max_wounds]

        return wound_list

    def _wound_intersects_roi(
        self,
        wound: WoundRecord,
        roi: Tuple[int, int, int, int],
    ) -> bool:
        rx, ry, rw, rh = roi
        wx = int(wound.location.x)
        wy = int(wound.location.y)
        ww = int(wound.location.width)
        wh = int(wound.location.height)
        inter_x1 = max(rx, wx)
        inter_y1 = max(ry, wy)
        inter_x2 = min(rx + rw, wx + ww)
        inter_y2 = min(ry + rh, wy + wh)
        return inter_x2 > inter_x1 and inter_y2 > inter_y1

    def _demo_wound_score(self, wound: WoundRecord, profile: DemoVideoProfile) -> float:
        score = (0.42 * wound.confidence) + (0.33 * wound.severity) + min(wound.size_cm2 / 60.0, 0.15)
        if wound.bleeding:
            score += 0.18
        if profile.wound_focus_roi is not None and self._wound_intersects_roi(wound, profile.wound_focus_roi):
            score += 0.2
        return round(score, 3)

    def _dedupe_candidates(self, candidates: Sequence[CandidateRegion]) -> List[CandidateRegion]:
        kept: List[CandidateRegion] = []
        for candidate in candidates:
            if all(self._iou(candidate.bbox, other.bbox) < 0.35 for other in kept):
                kept.append(candidate)
        return kept

    def _iou(self, box_a: Tuple[int, int, int, int], box_b: Tuple[int, int, int, int]) -> float:
        ax, ay, aw, ah = box_a
        bx, by, bw, bh = box_b

        inter_x1 = max(ax, bx)
        inter_y1 = max(ay, by)
        inter_x2 = min(ax + aw, bx + bw)
        inter_y2 = min(ay + ah, by + bh)

        if inter_x2 <= inter_x1 or inter_y2 <= inter_y1:
            return 0.0

        inter_area = (inter_x2 - inter_x1) * (inter_y2 - inter_y1)
        area_a = aw * ah
        area_b = bw * bh
        return inter_area / max(area_a + area_b - inter_area, 1)
