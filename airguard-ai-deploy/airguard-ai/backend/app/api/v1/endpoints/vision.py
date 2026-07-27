import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.camera_frame_analysis_repository import CameraFrameAnalysisRepository
from app.schemas.vision import CameraFrameAnalysisRead
from app.services.vision.vision_service import VisionError, VisionService

router = APIRouter(prefix="/vision", tags=["Computer Vision"])

_MANAGE_ROLES = (UserRole.ADMIN, UserRole.SAFETY_OFFICER, UserRole.SECURITY_GUARD, UserRole.ENVIRONMENTAL_OFFICER)

_MAX_UPLOAD_BYTES = 15 * 1024 * 1024  # 15MB


@router.post("/analyze", response_model=CameraFrameAnalysisRead, status_code=status.HTTP_201_CREATED)
async def analyze_camera_frame(
    parking_area_id: uuid.UUID = Query(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*_MANAGE_ROLES)),
):
    """
    Upload a single camera frame (JPEG/PNG) for a parking area. Runs real
    YOLOv8 object detection (vehicle/person counts) and a classical
    smoke/fire color heuristic — see app/services/vision/ for the honest
    capability boundaries of each. A high-confidence fire/smoke detection
    raises a real alert through the same pipeline gas thresholds use.
    """
    if file.content_type not in ("image/jpeg", "image/png", "image/jpg"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only JPEG/PNG images are supported")

    image_bytes = await file.read()
    if len(image_bytes) > _MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Image exceeds 15MB limit")

    service = VisionService(db)
    try:
        return service.analyze_frame(parking_area_id, image_bytes)
    except VisionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Could not process image: {exc}") from exc


@router.get("/analyses", response_model=list[CameraFrameAnalysisRead])
def list_analyses(
    parking_area_id: uuid.UUID | None = Query(default=None),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list:
    return CameraFrameAnalysisRepository(db).list(parking_area_id=parking_area_id, limit=limit)
