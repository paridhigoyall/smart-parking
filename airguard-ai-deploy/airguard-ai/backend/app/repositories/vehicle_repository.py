from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import VehicleStatus
from app.models.vehicle import Vehicle


class VehicleRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, vehicle_id: uuid.UUID) -> Vehicle | None:
        return self.db.get(Vehicle, vehicle_id)

    def get_active_by_plate(self, plate_number: str) -> Vehicle | None:
        """A vehicle that's entered the site and hasn't exited yet."""
        stmt = select(Vehicle).where(
            Vehicle.plate_number == plate_number, Vehicle.status != VehicleStatus.EXITED
        )
        return self.db.scalar(stmt)

    def list(
        self,
        *,
        parking_area_id: uuid.UUID | None = None,
        status: VehicleStatus | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Vehicle]:
        stmt = select(Vehicle)
        if parking_area_id is not None:
            stmt = stmt.where(Vehicle.parking_area_id == parking_area_id)
        if status is not None:
            stmt = stmt.where(Vehicle.status == status)
        stmt = stmt.order_by(Vehicle.entered_at.desc()).offset(skip).limit(limit)
        return list(self.db.scalars(stmt))

    def create_entry(self, *, plate_number: str, vehicle_type: str, driver_name: str | None) -> Vehicle:
        vehicle = Vehicle(
            plate_number=plate_number,
            vehicle_type=vehicle_type,
            driver_name=driver_name,
            status=VehicleStatus.ENTERED,
            entered_at=datetime.now(timezone.utc),
        )
        self.db.add(vehicle)
        self.db.commit()
        self.db.refresh(vehicle)
        return vehicle

    def mark_parked(self, vehicle: Vehicle, parking_area_id: uuid.UUID) -> Vehicle:
        vehicle.parking_area_id = parking_area_id
        vehicle.status = VehicleStatus.PARKED
        vehicle.parked_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(vehicle)
        return vehicle

    def mark_exited(self, vehicle: Vehicle) -> Vehicle:
        vehicle.status = VehicleStatus.EXITED
        vehicle.exited_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(vehicle)
        return vehicle
