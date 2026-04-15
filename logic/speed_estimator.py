"""
Module 3: Business Logic (Speeding)
----------------------------------
Maintains per-track state, estimates speed from warped motion,
applies EMA smoothing, caps unrealistic spikes, and marks violations.
"""

import math


class SpeedEstimator:
    def __init__(
        self,
        ema_alpha=0.2,
        max_speed_kmh=120.0,
        min_pixel_movement=1.5,
        speed_limit_kmh=20.0,
    ):
        self.ema_alpha = ema_alpha
        self.max_speed_kmh = max_speed_kmh
        self.min_pixel_movement = min_pixel_movement
        self.speed_limit_kmh = speed_limit_kmh

        self.track_positions = {}
        self.track_speeds_ema = {}
        self.track_labels = {}
        self.alerted_ids = set()

    def update(self, metadata_item, effective_fps):
        """
        Update speed state for one tracked object.

        Args:
            metadata_item: dict with track_id, bbox, warped_px and pixel/meter scales.
            effective_fps: fps used after frame skipping.

        Returns:
            dict with label, speed_kmh, and should_alert fields.
        """
        track_id = metadata_item["track_id"]
        wx, wy = metadata_item["warped_px"]

        speed_kmh = None
        should_alert = False

        if track_id in self.track_positions:
            prev_wx, prev_wy = self.track_positions[track_id]
            dx = wx - prev_wx
            dy = wy - prev_wy
            pixel_dist = math.sqrt(dx * dx + dy * dy)

            if pixel_dist > self.min_pixel_movement:
                dx_m = dx / metadata_item["pixels_per_meter_x"]
                dy_m = dy / metadata_item["pixels_per_meter_y"]
                dist_m = math.sqrt(dx_m ** 2 + dy_m ** 2)

                raw_speed = dist_m * effective_fps * 3.6

                if raw_speed > self.max_speed_kmh:
                    raw_speed = self.track_speeds_ema.get(track_id, 0.0)

                if track_id in self.track_speeds_ema:
                    smoothed = (
                        self.ema_alpha * raw_speed
                        + (1 - self.ema_alpha) * self.track_speeds_ema[track_id]
                    )
                else:
                    smoothed = raw_speed

                self.track_speeds_ema[track_id] = smoothed
                self.track_labels[track_id] = f"ID{track_id} | {int(smoothed)} km/h"
                speed_kmh = smoothed

                if smoothed > self.speed_limit_kmh and track_id not in self.alerted_ids:
                    should_alert = True
                    self.alerted_ids.add(track_id)

        self.track_positions[track_id] = (wx, wy)

        return {
            "track_id": track_id,
            "bbox": metadata_item["bbox"],
            "label": self.track_labels.get(track_id, f"ID{track_id} | -- km/h"),
            "speed_kmh": speed_kmh,
            "should_alert": should_alert,
        }

    def cleanup_lost_tracks(self, current_track_ids):
        """Remove state for tracks not present in current frame."""
        lost_ids = set(self.track_positions.keys()) - set(current_track_ids)
        for lost_id in lost_ids:
            self.track_positions.pop(lost_id, None)
            self.track_speeds_ema.pop(lost_id, None)
            self.track_labels.pop(lost_id, None)
            self.alerted_ids.discard(lost_id)
