from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Sequence


@dataclass
class Track:
    track_id: int
    alias: str
    bbox: tuple[int, int, int, int]
    last_seen_ts: float
    missed_frames: int = 0


class SimpleTracker:
    def __init__(
        self,
        *,
        iou_threshold: float = 0.25,
        max_missed_frames: int = 12,
        alias_prefix: str = "A",
    ) -> None:
        self.iou_threshold = iou_threshold
        self.max_missed_frames = max_missed_frames
        self.alias_prefix = alias_prefix
        self._next_track_id = 1
        self._active_tracks: list[Track] = []

    def update(
        self,
        detections: Sequence[tuple[int, int, int, int]],
        *,
        timestamp: float | None = None,
    ) -> list[Track]:
        now = timestamp if timestamp is not None else time.time()
        assignments: list[Track | None] = [None] * len(detections)
        available_tracks = list(range(len(self._active_tracks)))

        scored_pairs: list[tuple[float, int, int]] = []
        for detection_index, detection in enumerate(detections):
            for track_index in available_tracks:
                score = self._iou(self._active_tracks[track_index].bbox, detection)
                if score >= self.iou_threshold:
                    scored_pairs.append((score, detection_index, track_index))

        for _, detection_index, track_index in sorted(scored_pairs, reverse=True):
            if assignments[detection_index] is not None:
                continue
            track = self._active_tracks[track_index]
            if any(assigned is track for assigned in assignments if assigned is not None):
                continue
            track.bbox = detections[detection_index]
            track.last_seen_ts = now
            track.missed_frames = 0
            assignments[detection_index] = track

        assigned_track_ids = {assigned.track_id for assigned in assignments if assigned is not None}
        for track in self._active_tracks:
            if track.track_id not in assigned_track_ids:
                track.missed_frames += 1

        self._active_tracks = [
            track for track in self._active_tracks if track.missed_frames <= self.max_missed_frames
        ]

        for detection_index, detection in enumerate(detections):
            if assignments[detection_index] is None:
                new_track = Track(
                    track_id=self._next_track_id,
                    alias=f"{self.alias_prefix}{self._next_track_id}",
                    bbox=detection,
                    last_seen_ts=now,
                )
                self._next_track_id += 1
                self._active_tracks.append(new_track)
                assignments[detection_index] = new_track

        return [assignment for assignment in assignments if assignment is not None]

    def reset(self) -> None:
        self._next_track_id = 1
        self._active_tracks.clear()

    def _iou(
        self,
        box_a: tuple[int, int, int, int],
        box_b: tuple[int, int, int, int],
    ) -> float:
        ax1, ay1, ax2, ay2 = box_a
        bx1, by1, bx2, by2 = box_b

        inter_x1 = max(ax1, bx1)
        inter_y1 = max(ay1, by1)
        inter_x2 = min(ax2, bx2)
        inter_y2 = min(ay2, by2)

        if inter_x2 <= inter_x1 or inter_y2 <= inter_y1:
            return 0.0

        inter_area = (inter_x2 - inter_x1) * (inter_y2 - inter_y1)
        area_a = max((ax2 - ax1) * (ay2 - ay1), 1)
        area_b = max((bx2 - bx1) * (by2 - by1), 1)
        return inter_area / max(area_a + area_b - inter_area, 1)
