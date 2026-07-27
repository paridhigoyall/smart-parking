"""
Typed-ish API client for the FastAPI backend. Deliberately mirrors the
same endpoint set the Next.js frontend used (lib/api.ts in the previous
version) — this backend contract was already tested end-to-end, so the
client just needs to call it correctly, not rediscover it.
"""
from __future__ import annotations

import os
from typing import Any

import requests
import streamlit as st


def _resolve_api_base_url() -> str:
    """
    Streamlit Community Cloud doesn't let you set plain environment
    variables — config there goes through st.secrets instead. Docker /
    Render / running locally use a plain env var. Support both rather
    than forcing one deployment target.

    Broad except is deliberate here: st.secrets raises different
    exception types depending on context (StreamlitSecretNotFoundError
    when no secrets.toml exists at all, KeyError when the file exists but
    lacks this key) — this is a "try config source A, then B, then a sane
    default" fallback chain, not a place where swallowing errors hides a
    real bug.
    """
    if "API_BASE_URL" in os.environ:
        return os.environ["API_BASE_URL"]
    try:
        return st.secrets["API_BASE_URL"]
    except Exception:
        return "http://localhost:8000/api/v1"


API_BASE_URL = _resolve_api_base_url()
TIMEOUT = 15


class ApiError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"[{status_code}] {detail}")


def _headers() -> dict:
    token = st.session_state.get("token")
    return {"Authorization": f"Bearer {token}"} if token else {}


def _request(method: str, path: str, **kwargs) -> Any:
    url = f"{API_BASE_URL}{path}"
    try:
        resp = requests.request(method, url, headers=_headers(), timeout=TIMEOUT, **kwargs)
    except requests.exceptions.ConnectionError as exc:
        raise ApiError(0, f"Could not reach the backend at {API_BASE_URL}. Is it running?") from exc
    except requests.exceptions.Timeout as exc:
        raise ApiError(0, "Request to backend timed out.") from exc

    if not resp.ok:
        try:
            detail = resp.json().get("detail", resp.text)
        except ValueError:
            detail = resp.text
        raise ApiError(resp.status_code, str(detail))

    if resp.status_code == 204 or not resp.content:
        return None
    return resp.json()


# ---------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------
def login(email: str, password: str) -> str:
    try:
        resp = requests.post(
            f"{API_BASE_URL}/auth/login",
            data={"username": email, "password": password},
            timeout=TIMEOUT,
        )
    except requests.exceptions.ConnectionError as exc:
        raise ApiError(0, f"Could not reach the backend at {API_BASE_URL}. Is it running?") from exc
    except requests.exceptions.Timeout as exc:
        raise ApiError(0, "Request to backend timed out.") from exc

    if not resp.ok:
        try:
            detail = resp.json().get("detail", "Login failed")
        except ValueError:
            detail = "Login failed"
        raise ApiError(resp.status_code, detail)
    token = resp.json()["access_token"]
    st.session_state["token"] = token
    return token


def get_current_user() -> dict:
    return _request("GET", "/auth/me")


def update_my_profile(**fields) -> dict:
    return _request("PATCH", "/users/me", json=fields)


# ---------------------------------------------------------------------
# Parking areas
# ---------------------------------------------------------------------
def list_parking_areas() -> list[dict]:
    return _request("GET", "/parking-areas?limit=200")


def get_parking_area_risk(area_id: str) -> dict:
    return _request("GET", f"/parking-areas/{area_id}/risk")


def create_parking_area(**fields) -> dict:
    return _request("POST", "/parking-areas", json=fields)


# ---------------------------------------------------------------------
# Sensors & gas readings
# ---------------------------------------------------------------------
def list_sensors(parking_area_id: str | None = None) -> list[dict]:
    qs = f"?parking_area_id={parking_area_id}" if parking_area_id else ""
    return _request("GET", f"/sensors{qs}")


def create_sensor(**fields) -> dict:
    return _request("POST", "/sensors", json=fields)


def ingest_gas_reading(**fields) -> dict:
    return _request("POST", "/gas-readings", json=fields)


def get_latest_reading(parking_area_id: str) -> dict | None:
    try:
        return _request("GET", f"/gas-readings/latest?parking_area_id={parking_area_id}")
    except ApiError as e:
        if e.status_code == 404:
            return None
        raise


# ---------------------------------------------------------------------
# Recommendations & decision support
# ---------------------------------------------------------------------
def get_parking_recommendation() -> dict:
    return _request("GET", "/recommendations/parking?persist=false")


def get_suggested_actions(area_id: str) -> dict:
    return _request("GET", f"/recommendations/actions/{area_id}")


# ---------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------
def list_alerts(status: str | None = None) -> list[dict]:
    qs = f"?status={status}" if status else ""
    return _request("GET", f"/alerts{qs}")


def acknowledge_alert(alert_id: str) -> dict:
    return _request("POST", f"/alerts/{alert_id}/acknowledge")


# ---------------------------------------------------------------------
# Predictions / forecasting
# ---------------------------------------------------------------------
def generate_forecasts(area_id: str) -> list[dict]:
    return _request("POST", f"/predictions/generate?parking_area_id={area_id}")


def get_trend_chart(area_id: str, gas: str) -> dict:
    return _request("GET", f"/predictions/trend?parking_area_id={area_id}&gas={gas}")


# ---------------------------------------------------------------------
# Vehicles
# ---------------------------------------------------------------------
def list_vehicles(parking_area_id: str | None = None) -> list[dict]:
    qs = f"?parking_area_id={parking_area_id}" if parking_area_id else ""
    return _request("GET", f"/vehicles{qs}")


def register_vehicle_entry(**fields) -> dict:
    return _request("POST", "/vehicles/entry", json=fields)


def park_vehicle(vehicle_id: str, parking_area_id: str) -> dict:
    return _request("POST", f"/vehicles/{vehicle_id}/park", json={"parking_area_id": parking_area_id})


def exit_vehicle(vehicle_id: str) -> dict:
    return _request("POST", f"/vehicles/{vehicle_id}/exit")


# ---------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------
def get_safest_route(area_id: str) -> dict:
    return _request("GET", f"/routes/to/{area_id}")


# ---------------------------------------------------------------------
# ML classifier comparison
# ---------------------------------------------------------------------
def classify_gas_values(**gas_values) -> dict:
    return _request("POST", "/ml/classify", json=gas_values)


def get_model_info() -> dict:
    return _request("GET", "/ml/model-info")
