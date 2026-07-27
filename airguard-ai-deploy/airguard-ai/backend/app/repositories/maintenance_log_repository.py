from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.maintenance_log import MaintenanceLog


class MaintenanceLogRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self, *, sensor_id: uuid.UUID, event_type: str, notes: str | None, performed_by: str | None
    ) -> MaintenanceLog:
        log = MaintenanceLog(sensor_id=sensor_id, event_type=event_type, notes=notes, performed_by=performed_by)
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log

    def list_for_sensor(self, sensor_id: uuid.UUID, limit: int = 100) -> list[MaintenanceLog]:
        stmt = (
            select(MaintenanceLog)
            .where(MaintenanceLog.sensor_id == sensor_id)
            .order_by(MaintenanceLog.created_at.desc())
            .limit(limit)
        )
        return list(self.db.scalars(stmt))
