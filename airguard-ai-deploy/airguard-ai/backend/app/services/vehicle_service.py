"""
Vehicle tracking service.

Owns the one piece of cross-entity consistency vehicle tracking needs:
parking_area.occupied_slots must go up exactly when a vehicle parks and
down exactly when a parked vehicle exits (or is reassigned to a different
area) — never on entry alone, and never double-counted.
"""
from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.models.enums import VehicleStatus
from app.models.vehicle import Vehicle
from app.repositories.parking_area_repository import ParkingAreaRepository
from app.repositories.vehicle_repository import VehicleRepository


class VehicleTrackingError(Exception):
    pass


class VehicleTrackingService:
    def __init__(self, db: Session):
        self.db = db
        self.vehicles = VehicleRepository(db)
        self.areas = ParkingAreaRepository(db)

    def register_entry(self, *, plate_number: str, vehicle_type: str, driver_name: str | None) -> Vehicle:
        existing = self.vehicles.get_active_by_plate(plate_number)
        if existing is not None:
            raise VehicleTrackingError(f"Vehicle {plate_number} is already on-site (status={existing.status.value})")
        return self.vehicles.create_entry(plate_number=plate_number, vehicle_type=vehicle_type, driver_name=driver_name)

    def park(self, vehicle_id: uuid.UUID, parking_area_id: uuid.UUID) -> Vehicle:
        vehicle = self.vehicles.get(vehicle_id)
        if vehicle is None:
            raise VehicleTrackingError("Vehicle not found")
        if vehicle.status == VehicleStatus.EXITED:
            raise VehicleTrackingError("Vehicle has already exited the site")

        area = self.areas.get(parking_area_id)
        if area is None:
            raise VehicleTrackingError("Parking area not found")
        if area.is_closed:
            raise VehicleTrackingError(f"{area.name} is closed to new entry")
        if area.occupied_slots >= area.capacity:
            raise VehicleTrackingError(f"{area.name} is at full capacity ({area.capacity} slots)")

        previous_area_id = vehicle.parking_area_id if vehicle.status == VehicleStatus.PARKED else None

        updated = self.vehicles.mark_parked(vehicle, parking_area_id)
        area.occupied_slots += 1
        self.db.commit()

        if previous_area_id and previous_area_id != parking_area_id:
            previous_area = self.areas.get(previous_area_id)
            if previous_area and previous_area.occupied_slots > 0:
                previous_area.occupied_slots -= 1
                self.db.commit()

        return updated

    def exit_site(self, vehicle_id: uuid.UUID) -> Vehicle:
        vehicle = self.vehicles.get(vehicle_id)
        if vehicle is None:
            raise VehicleTrackingError("Vehicle not found")
        if vehicle.status == VehicleStatus.EXITED:
            raise VehicleTrackingError("Vehicle has already exited")

        was_parked = vehicle.status == VehicleStatus.PARKED
        parked_area_id = vehicle.parking_area_id

        updated = self.vehicles.mark_exited(vehicle)

        if was_parked and parked_area_id:
            area = self.areas.get(parked_area_id)
            if area and area.occupied_slots > 0:
                area.occupied_slots -= 1
                self.db.commit()

        return updated
