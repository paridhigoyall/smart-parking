import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.enums import AlertStatus, UserRole
from app.models.user import User
from app.repositories.alert_repository import AlertRepository
from app.repositories.notification_log_repository import NotificationLogRepository
from app.schemas.alert import AlertNotificationLogRead, AlertRead

router = APIRouter(prefix="/alerts", tags=["Alerts"])

_MANAGE_ROLES = (UserRole.ADMIN, UserRole.SAFETY_OFFICER, UserRole.FACTORY_MANAGER, UserRole.ENVIRONMENTAL_OFFICER)


@router.get("", response_model=list[AlertRead])
def list_alerts(
    parking_area_id: uuid.UUID | None = Query(default=None),
    status_filter: AlertStatus | None = Query(default=None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list:
    return AlertRepository(db).list(parking_area_id=parking_area_id, status=status_filter, skip=skip, limit=limit)


@router.post("/{alert_id}/acknowledge", response_model=AlertRead)
def acknowledge_alert(
    alert_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_MANAGE_ROLES)),
):
    repo = AlertRepository(db)
    alert = repo.get(alert_id)
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    if alert.status != AlertStatus.OPEN:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Alert is already {alert.status.value}")
    return repo.acknowledge(alert, current_user.id)


@router.post("/{alert_id}/resolve", response_model=AlertRead)
def resolve_alert(
    alert_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*_MANAGE_ROLES)),
):
    repo = AlertRepository(db)
    alert = repo.get(alert_id)
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    if alert.status == AlertStatus.RESOLVED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Alert is already resolved")
    return repo.resolve(alert)


@router.get("/{alert_id}/notifications", response_model=list[AlertNotificationLogRead])
def get_alert_notifications(
    alert_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list:
    """Delivery audit trail: who was notified, over which channel, and whether it succeeded."""
    repo = AlertRepository(db)
    if not repo.get(alert_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    return NotificationLogRepository(db).list_for_alert(alert_id)


@router.post("/{alert_id}/notify", status_code=status.HTTP_202_ACCEPTED)
def resend_alert_notifications(
    alert_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*_MANAGE_ROLES)),
):
    """Manually (re)trigger notification delivery for an alert — e.g. after
    fixing SMTP credentials, or to re-page someone who missed the first round."""
    repo = AlertRepository(db)
    alert = repo.get(alert_id)
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")

    from app.tasks.notification_tasks import dispatch_alert_notifications

    try:
        dispatch_alert_notifications.delay(str(alert.id))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Could not reach the notification queue: {exc}",
        ) from exc

    return {"detail": "Notification dispatch queued"}
