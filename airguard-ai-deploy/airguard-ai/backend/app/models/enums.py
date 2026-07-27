"""
Shared enumerations used across ORM models and Pydantic schemas.
"""
import enum


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    SAFETY_OFFICER = "safety_officer"
    FACTORY_MANAGER = "factory_manager"
    SECURITY_GUARD = "security_guard"
    EMPLOYEE = "employee"
    ENVIRONMENTAL_OFFICER = "environmental_officer"


class RiskLevel(str, enum.Enum):
    SAFE = "safe"
    MODERATE = "moderate"
    UNSAFE = "unsafe"


class SensorType(str, enum.Enum):
    CO = "co"
    CO2 = "co2"
    NO2 = "no2"
    SO2 = "so2"
    NH3 = "nh3"
    H2S = "h2s"
    METHANE = "methane"
    LPG = "lpg"
    SMOKE = "smoke"
    PM25 = "pm25"
    PM10 = "pm10"
    TEMPERATURE = "temperature"
    HUMIDITY = "humidity"
    WIND_SPEED = "wind_speed"
    WIND_DIRECTION = "wind_direction"


class SensorStatus(str, enum.Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    FAULTY = "faulty"
    CALIBRATION_NEEDED = "calibration_needed"


class AlertSeverity(str, enum.Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertStatus(str, enum.Enum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


class AlertChannel(str, enum.Enum):
    DASHBOARD = "dashboard"
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"


class VehicleStatus(str, enum.Enum):
    ENTERED = "entered"
    PARKED = "parked"
    EXITED = "exited"


class RecommendationAction(str, enum.Enum):
    PARK_HERE = "park_here"
    OPEN_VENTILATION = "open_ventilation"
    DELAY_ENTRY = "delay_entry"
    CLOSE_PARKING = "close_parking"
    ACTIVATE_EXHAUST = "activate_exhaust"
    EVACUATE = "evacuate"
