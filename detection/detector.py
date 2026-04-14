"""
Module 1: Detection Engine
--------------------------

Simply run yolov8m model with ByteTrack to get vehicle detections + track IDs.

"""

from ultralytics import YOLO

# COCO classes : bicycle, car, motorbike, bus, truck
VEHICLE_CLASSES = {1, 2, 3, 5, 7}

class DetectionEngine:
    def __init__(self, model_path="yolov8m.pt", imgsz=1280, conf=0.25):
        self.model  = YOLO(model_path)
        self.imgsz  = imgsz
        self.conf   = conf

    def detect(self, frame):
        """
        Run detection + tracking on a single frame.

        Returns a list of dictionaries, each containing the track ID, bounding box, center coordinates, and class ID for each detected vehicle.
        """
        results = self.model.track(
            frame,
            imgsz=self.imgsz,
            conf=self.conf,
            persist=True,               
            tracker="bytetrack.yaml",
            verbose=False
        )[0]

        detections = []

        if results.boxes.id is None:
            return detections

        for box, track_id in zip(results.boxes, results.boxes.id):
            cls = int(box.cls[0])
            if cls not in VEHICLE_CLASSES:
                continue

            x1, y1, x2, y2 = map(int, box.xyxy[0])
            cx = (x1 + x2) // 2
            cy = (y1 + y2) // 2

            detections.append({
                "track_id": int(track_id),
                "bbox":     [x1, y1, x2, y2],
                "center":   [cx, cy],
                "class_id": cls
            })

        return detections
    
    
'''

# Just to test detection engine on video frames ...

import cv2

cap = cv2.VideoCapture("C:\\Users\\MEET\\Documents\\HV\\Input\\out.mp4")
engine = DetectionEngine()

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    detections = engine.detect(frame)

    for d in detections:
        x1, y1, x2, y2 = d["bbox"]
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

    cv2.imshow("output", frame)
    if cv2.waitKey(1) == 27:
        break

cap.release()
cv2.destroyAllWindows()

'''