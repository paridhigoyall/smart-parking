from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.core.config import settings
from app.repositories.gas_reading_repository import GasReadingRepository
from app.repositories.parking_area_repository import ParkingAreaRepository
from app.services.risk_engine import risk_engine
from app.services.route_engine import Hazard, RouteEngine, RouteResult


class RouteError(Exception):
    pass


class RouteService:
    def __init__(self, db: Session):
        self.db = db
        self.areas = ParkingAreaRepository(db)
        self.readings = GasReadingRepository(db)
        self.engine = RouteEngine(hazard_buffer=settings.ROUTE_HAZARD_BUFFER)

    def route_to(
        self, destination_area_id: uuid.UUID, *, gate: tuple[float, float] | None = None
    ) -> RouteResult:
        destination = self.areas.get(destination_area_id)
        if destination is None:
            raise RouteError("Destination parking area not found")

        gate_point = gate or (settings.PLANT_GATE_X, settings.PLANT_GATE_Y)

        hazards: list[Hazard] = []
        for area in self.areas.list(limit=500):
            if area.id == destination_area_id:
                continue
            is_hazard = area.is_closed
            if not is_hazard:
                reading = self.readings.get_latest_for_area(area.id)
                if reading is not None:
                    assessment = risk_engine.classify(reading)
                    is_hazard = assessment.risk_level.value == "unsafe"
            if is_hazard:
                hazards.append(Hazard(name=area.name, point=(area.map_x, area.map_y)))

        return self.engine.plan_route(gate_point, (destination.map_x, destination.map_y), hazards)
