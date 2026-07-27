import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DetectedObjectRead(BaseModel):
    class_name: str
    confidence: float
    bbox: list[float]


class CameraFrameAnalysisRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: uuid.UUID
    parking_area_id: uuid.UUID
    vehicle_count: int
    person_count: int
    detected_objects: list[DetectedObjectRead]
    registered_parked_count: int
    unauthorized_parking_suspected: bool
    smoke_detected: bool
    smoke_confidence: float
    fire_detected: bool
    fire_confidence: float
    alert_id: uuid.UUID | None
    model_name: str
    created_at: datetime
