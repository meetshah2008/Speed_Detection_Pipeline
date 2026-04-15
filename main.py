import cv2
import numpy as np
import os
from pathlib import Path
from dotenv import load_dotenv

from detection.detector import DetectionEngine
from metadata.bridge import MetadataBridge
from logic.speed_estimator import SpeedEstimator
from api.handler import APIHandler


# =========================
# PATH CONFIG
# =========================
PROJECT_DIR = Path(__file__).resolve().parent
ROOT_DIR = PROJECT_DIR.parent

load_dotenv(PROJECT_DIR / ".env")


def _env_str(name, default):
    value = os.getenv(name)
    return value if value not in (None, "") else default


def _env_int(name, default):
    value = os.getenv(name)
    if value in (None, ""):
        return default
    return int(value)


def _env_float(name, default):
    value = os.getenv(name)
    if value in (None, ""):
        return default
    return float(value)


def _env_path(name, default):
    raw_path = _env_str(name, str(default))
    p = Path(raw_path)
    if not p.is_absolute():
        p = (PROJECT_DIR / p).resolve()
    return str(p)


MODEL_PATH = _env_path("MODEL_PATH", ROOT_DIR / "yolov8l.pt")
VIDEO_PATH = _env_path("VIDEO_PATH", ROOT_DIR / "Input" / "out.mp4")
OUTPUT_PATH = _env_path("OUTPUT_PATH", ROOT_DIR / "Output" / "speed_annotated_submission.mp4")

# =========================
# FRAME / PROCESSING CONFIG
# =========================
FRAME_WIDTH = _env_int("FRAME_WIDTH", 900)
FRAME_HEIGHT = _env_int("FRAME_HEIGHT", 600)
TARGET_FPS = _env_int("TARGET_FPS", 5)

# =========================
# ROAD / HOMOGRAPHY CONFIG
# =========================
SRC_POINTS = np.array(
    [
    (467, 274),   # Point 1 (top-left)
    (786, 368),   # Point 2 (top-right)
    (769, 495),   # Point 3 (bottom-right)
    (435, 375)    # Point 4 (bottom-left)
],
    dtype=np.float32,
)
REAL_ROAD_WIDTH_METERS = 6.0
REAL_ROAD_LENGTH_METERS = 16.5

# =========================
# SPEED / API CONFIG
# =========================
EMA_ALPHA = _env_float("EMA_ALPHA", 0.2)
MAX_SPEED_KMH = _env_float("MAX_SPEED_KMH", 120.0)
SPEED_LIMIT_KMH = _env_float("SPEED_LIMIT_KMH", 20.0)
MIN_PIXEL_MOVEMENT = _env_float("MIN_PIXEL_MOVEMENT", 1.5)

API_URL = _env_str("API_URL", "http://localhost:8000/speed")
API_TIMEOUT_SEC = _env_float("API_TIMEOUT_SEC", 1.0)


def draw_reference_overlay(frame, src_ordered):
    pt1 = tuple(map(int, src_ordered[0]))
    pt2 = tuple(map(int, src_ordered[1]))
    pt3 = tuple(map(int, src_ordered[2]))
    pt4 = tuple(map(int, src_ordered[3]))

    quad_pts = src_ordered.astype(np.int32).reshape((-1, 1, 2))
    cv2.polylines(frame, [quad_pts], isClosed=True, color=(0, 165, 255), thickness=2)

    cv2.line(frame, pt1, pt4, (0, 0, 255), 3)
    cv2.circle(frame, pt1, 6, (0, 0, 255), -1)
    cv2.circle(frame, pt4, 6, (0, 0, 255), -1)
    mid_w_x = (pt1[0] + pt4[0]) // 2
    mid_w_y = (pt1[1] + pt4[1]) // 2
    cv2.putText(
        frame,
        "6.0 m (W)",
        (mid_w_x - 50, mid_w_y - 10),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (0, 0, 255),
        2,
    )

    cv2.line(frame, pt1, pt2, (0, 255, 0), 3)
    cv2.circle(frame, pt1, 6, (0, 255, 0), -1)
    cv2.circle(frame, pt2, 6, (0, 255, 0), -1)
    mid_l_x = (pt1[0] + pt2[0]) // 2
    mid_l_y = (pt1[1] + pt2[1]) // 2
    cv2.putText(
        frame,
        "16.5 m (L)",
        (mid_l_x - 50, mid_l_y - 10),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (0, 255, 0),
        2,
    )


def run_pipeline():
    detector = DetectionEngine(model_path=MODEL_PATH, imgsz=1280, conf=0.25)
    bridge = MetadataBridge(
        src_points=SRC_POINTS,
        real_length_m=REAL_ROAD_LENGTH_METERS,
        real_width_m=REAL_ROAD_WIDTH_METERS,
    )
    estimator = SpeedEstimator(
        ema_alpha=EMA_ALPHA,
        max_speed_kmh=MAX_SPEED_KMH,
        min_pixel_movement=MIN_PIXEL_MOVEMENT,
        speed_limit_kmh=SPEED_LIMIT_KMH,
    )
    api_handler = APIHandler(api_url=API_URL, timeout=API_TIMEOUT_SEC)

    cap = cv2.VideoCapture(VIDEO_PATH)
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    if fps <= 0:
        raise RuntimeError("Unable to read video FPS. Check VIDEO_PATH.")

    frame_skip = max(1, round(fps / TARGET_FPS))
    effective_fps = fps / frame_skip

    print(f"[INFO] Video FPS       : {fps}")
    print(f"[INFO] Frame skip      : {frame_skip} (process 1 in every {frame_skip} frames)")
    print(f"[INFO] Effective FPS   : {effective_fps:.2f} fps (used in speed calc)")

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(
        OUTPUT_PATH,
        fourcc,
        effective_fps,
        (FRAME_WIDTH, FRAME_HEIGHT),
    )

    frame_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_idx += 1
        if (frame_idx - 1) % frame_skip != 0:
            continue

        print(f"\r[INFO] Processing frame {frame_idx}/{total_frames}", end="")

        frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))
        draw_reference_overlay(frame, bridge.src_ordered)

        detections = detector.detect(frame)
        metadata_items = bridge.transform(detections)

        current_track_ids = set()
        for item in metadata_items:
            current_track_ids.add(item["track_id"])
            speed_info = estimator.update(item, effective_fps)

            x1, y1, x2, y2 = speed_info["bbox"]
            label = speed_info["label"]

            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 255), 2)
            cv2.putText(
                frame,
                label,
                (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 255),
                2,
            )

            if speed_info["should_alert"] and speed_info["speed_kmh"] is not None:
                api_handler.send_alert(speed_info["track_id"], speed_info["speed_kmh"])

        estimator.cleanup_lost_tracks(current_track_ids)

        writer.write(frame)
        cv2.imshow("Speed Detection", frame)
        if cv2.waitKey(1) & 0xFF == 27:
            break

    cap.release()
    writer.release()
    cv2.destroyAllWindows()
    print(f"\n[INFO] Saved annotated video to: {OUTPUT_PATH}")


if __name__ == "__main__":
    run_pipeline()
