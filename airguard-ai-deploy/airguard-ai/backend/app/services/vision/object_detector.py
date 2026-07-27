"""
Object detection via a pretrained YOLOv8n model (COCO weights, downloaded
once from Ultralytics' GitHub releases and cached locally).

This is genuinely real detection — not a placeholder — but it's honest to
say what it can and can't do: COCO's 80 classes include the vehicle and
person categories this module uses (car, truck, bus, motorcycle, bicycle,
person), which is exactly what's needed for vehicle-density and
unauthorized-parking checks. COCO has no "hard hat" or "safety vest"
class, so PPE compliance detection is NOT implemented here — that
genuinely requires a custom-trained model on labeled PPE imagery, which
this environment has neither the data nor the training infrastructure
for. Faking a PPE check that always returns "compliant" would be worse
than not having the feature at all, so it's left out rather than stubbed.

The model loads lazily on first use (not at import time) so the rest of
the API stays fast to start up when this module isn't being exercised.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from io import BytesIO

VEHICLE_CLASSES = {"car", "truck", "bus", "motorcycle", "bicycle"}
PERSON_CLASS = "person"


@dataclass
class DetectedObject:
    class_name: str
    confidence: float
    bbox: tuple[float, float, float, float]  # x1, y1, x2, y2 in pixel coords


@dataclass
class DetectionResult:
    objects: list[DetectedObject]
    vehicle_count: int
    person_count: int
    image_width: int
    image_height: int


@lru_cache(maxsize=1)
def _get_model():
    import os

    from ultralytics import YOLO

    from app.core.config import settings

    os.makedirs(settings.VISION_MODEL_DIR, exist_ok=True)
    weights_path = os.path.join(settings.VISION_MODEL_DIR, "yolov8n.pt")
    return YOLO(weights_path)


class ObjectDetector:
    def is_available(self) -> bool:
        try:
            import ultralytics  # noqa: F401

            return True
        except ImportError:
            return False

    def detect(self, image_bytes: bytes, confidence_threshold: float = 0.35) -> DetectionResult:
        from PIL import Image

        model = _get_model()
        image = Image.open(BytesIO(image_bytes)).convert("RGB")
        results = model(image, verbose=False, conf=confidence_threshold)

        objects: list[DetectedObject] = []
        for r in results:
            for box in r.boxes:
                class_name = model.names[int(box.cls[0])]
                confidence = float(box.conf[0])
                x1, y1, x2, y2 = [float(v) for v in box.xyxy[0]]
                objects.append(DetectedObject(class_name=class_name, confidence=confidence, bbox=(x1, y1, x2, y2)))

        vehicle_count = sum(1 for o in objects if o.class_name in VEHICLE_CLASSES)
        person_count = sum(1 for o in objects if o.class_name == PERSON_CLASS)

        return DetectionResult(
            objects=objects,
            vehicle_count=vehicle_count,
            person_count=person_count,
            image_width=image.width,
            image_height=image.height,
        )


object_detector = ObjectDetector()
