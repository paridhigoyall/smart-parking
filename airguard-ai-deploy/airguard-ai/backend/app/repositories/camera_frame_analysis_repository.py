from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.camera_frame_analysis import CameraFrameAnalysis


class CameraFrameAnalysisRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, **fields) -> CameraFrameAnalysis:
        record = CameraFrameAnalysis(**fields)
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def list(self, *, parking_area_id: uuid.UUID | None = None, limit: int = 100) -> list[CameraFrameAnalysis]:
        stmt = select(CameraFrameAnalysis)
        if parking_area_id is not None:
            stmt = stmt.where(CameraFrameAnalysis.parking_area_id == parking_area_id)
        stmt = stmt.order_by(CameraFrameAnalysis.created_at.desc()).limit(limit)
        return list(self.db.scalars(stmt))
