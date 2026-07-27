from fastapi import APIRouter

from app.api.v1.endpoints import (
    alerts,
    analytics,
    auth,
    gas_readings,
    health,
    parking_areas,
    predictions,
    recommendations,
    routes,
    sensors,
    users,
    vehicles,
    weather,
)

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(parking_areas.router)
api_router.include_router(sensors.router)
api_router.include_router(gas_readings.router)
api_router.include_router(recommendations.router)
api_router.include_router(predictions.router)
api_router.include_router(alerts.router)
api_router.include_router(analytics.router)
api_router.include_router(vehicles.router)
api_router.include_router(routes.router)
api_router.include_router(weather.router)

try:
    from app.api.v1.endpoints import vision

    api_router.include_router(vision.router)
except ImportError:
    # requirements-vision.txt (ultralytics/opencv) not installed — every
    # other module works fine without it. Install it and restart to
    # enable /vision/*.
    pass

from app.api.v1.endpoints import ml

api_router.include_router(ml.router)

# NOTE: The digital twin visualization lives in the frontend
# (app/dashboard/twin) — nothing further to register here.
