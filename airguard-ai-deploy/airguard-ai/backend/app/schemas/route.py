import uuid

from pydantic import BaseModel


class RoutePoint(BaseModel):
    x: float
    y: float


class RouteRead(BaseModel):
    destination_area_id: uuid.UUID
    waypoints: list[RoutePoint]
    status: str  # "clear" | "detoured" | "hazard_unavoidable"
    avoided_hazards: list[str]
    total_distance: float
    notes: str
