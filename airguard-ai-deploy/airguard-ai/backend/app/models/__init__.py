"""
Import every model here so that `Base.metadata` is fully populated for
Alembic autogenerate and for `Base.metadata.create_all()` in tests.
"""
from app.db.base_class import Base  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.parking_area import ParkingArea  # noqa: F401
from app.models.sensor import Sensor  # noqa: F401
from app.models.gas_reading import GasReading  # noqa: F401
from app.models.prediction import Prediction  # noqa: F401
from app.models.alert import Alert  # noqa: F401
from app.models.recommendation import Recommendation  # noqa: F401
from app.models.vehicle import Vehicle  # noqa: F401
from app.models.maintenance_log import MaintenanceLog  # noqa: F401
from app.models.weather import WeatherRecord  # noqa: F401
from app.models.analytics import AnalyticsRollup  # noqa: F401
from app.models.audit_log import AuditLog  # noqa: F401
from app.models.alert_notification_log import AlertNotificationLog  # noqa: F401
from app.models.camera_frame_analysis import CameraFrameAnalysis  # noqa: F401

__all__ = [
    "Base",
    "User",
    "ParkingArea",
    "Sensor",
    "GasReading",
    "Prediction",
    "Alert",
    "Recommendation",
    "Vehicle",
    "MaintenanceLog",
    "WeatherRecord",
    "AnalyticsRollup",
    "AuditLog",
    "AlertNotificationLog",
    "CameraFrameAnalysis",
]
