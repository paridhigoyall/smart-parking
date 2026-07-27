"""
Shared color palette — brown/green/yellow as the primary theme, with red
kept as a deliberately rare, reserved signal for "unsafe" risk status
only. Mixing red into general UI chrome would dilute it as a danger
signal in a gas-safety platform, so every other accent in the app pulls
from the brown/green/yellow family instead.
"""

BROWN_DARK = "#211609"
BROWN = "#3A2A16"
BROWN_LIGHT = "#6B4F2E"
CREAM = "#F3E9D2"

GREEN = "#6B8E23"       # olive green — "safe"
YELLOW = "#E8B923"      # golden yellow — "moderate" / primary accent
RED = "#C0392B"         # reserved exclusively for "unsafe"
GREY = "#8A7A63"        # closed / unknown / no-data

RISK_COLORS = {
    "safe": GREEN,
    "moderate": YELLOW,
    "unsafe": RED,
    "unknown": GREY,
}

RISK_LABELS = {
    "safe": "Safe",
    "moderate": "Moderate",
    "unsafe": "Unsafe",
    "unknown": "Unknown",
}

SEVERITY_COLORS = {
    "info": YELLOW,
    "warning": "#D98324",   # amber-brown, between yellow and red
    "critical": RED,
}

GAS_DISPLAY_NAMES = {
    "co": "Carbon Monoxide",
    "co2": "Carbon Dioxide",
    "no2": "Nitrogen Dioxide",
    "so2": "Sulfur Dioxide",
    "nh3": "Ammonia",
    "h2s": "Hydrogen Sulfide",
    "methane": "Methane",
    "lpg": "LPG",
    "smoke": "Smoke",
    "pm25": "PM2.5",
    "pm10": "PM10",
}

PLOTLY_LAYOUT_DEFAULTS = dict(
    paper_bgcolor=BROWN_DARK,
    plot_bgcolor=BROWN,
    font=dict(color=CREAM),
    margin=dict(l=30, r=30, t=40, b=30),
)


def gas_label(gas: str) -> str:
    return GAS_DISPLAY_NAMES.get(gas, gas.upper())
