"""
Module 2: Metadata Bridge
--------------------------
Takes detections from the Detection Engine,
transforms pixel centers to bird's-eye (warped) coordinates
via homography, and returns metadata dicts.

"""

import cv2
import numpy as np


def order_points(pts):
    pts  = np.array(pts, dtype="float32")
    s    = pts.sum(axis=1)
    diff = np.diff(pts, axis=1)
    return np.array([
        pts[np.argmin(s)],
        pts[np.argmin(diff)],
        pts[np.argmax(s)],
        pts[np.argmax(diff)]
    ], dtype="float32")


def get_dst_size(pts):
    (tl, tr, br, bl) = pts
    widthA   = np.linalg.norm(br - bl)
    widthB   = np.linalg.norm(tr - tl)
    maxWidth = int(max(widthA, widthB))
    heightA  = np.linalg.norm(tr - br)
    heightB  = np.linalg.norm(tl - bl)
    maxHeight = int(max(heightA, heightB))
    return maxWidth, maxHeight


class MetadataBridge:
    def __init__(self, src_points, real_length_m, real_width_m):
        """
        Args:
            src_points     : 4 pixel coords of the road ROI in image space
            real_length_m  : real-world length of the ROI in metres
            real_width_m   : real-world width  of the ROI in metres
        """
        src_ordered = order_points(src_points)
        w, h        = get_dst_size(src_ordered)

        dst_points = np.array([
            [0,     0    ],
            [w - 1, 0    ],
            [w - 1, h - 1],
            [0,     h - 1]
        ], dtype=np.float32)

        self.H                  = cv2.getPerspectiveTransform(src_ordered, dst_points)
        self.src_ordered        = src_ordered
        self.warped_w           = w
        self.warped_h           = h
        self.pixels_per_meter_x = w / real_length_m
        self.pixels_per_meter_y = h / real_width_m

        print(f"[MetadataBridge] Warped size     : {w} x {h} px")
        print(f"[MetadataBridge] Scale X (length): {self.pixels_per_meter_x:.2f} px/m")
        print(f"[MetadataBridge] Scale Y (width) : {self.pixels_per_meter_y:.2f} px/m")

    def transform(self, detections):
        """
        Convert detections → standardized metadata with warped coords.
        """
        metadata = []

        for det in detections:
            cx, cy = det["center"]

            pt_img = np.array([[[cx, cy]]], dtype=np.float32)
            warped  = cv2.perspectiveTransform(pt_img, self.H)[0][0]
            wx, wy  = float(warped[0]), float(warped[1])

            metadata.append({
                "track_id":           det["track_id"],
                "bbox":               det["bbox"],
                "center_px":          [cx, cy],
                "warped_px":          [wx, wy],
                "pixels_per_meter_x": self.pixels_per_meter_x,
                "pixels_per_meter_y": self.pixels_per_meter_y
            })

        return metadata