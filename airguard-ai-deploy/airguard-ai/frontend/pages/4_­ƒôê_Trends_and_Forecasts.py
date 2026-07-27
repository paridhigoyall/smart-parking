import plotly.graph_objects as go
import streamlit as st

from lib import api_client, auth
from lib.api_client import ApiError
from lib.theme import GREEN, PLOTLY_LAYOUT_DEFAULTS, YELLOW, gas_label

st.set_page_config(page_title="Trends & Forecasts — AirGuard AI", page_icon="📈", layout="wide")
auth.require_login()

st.markdown("## 📈 Gas Trend & Forecast")
st.caption(
    "Per-gas linear-trend forecasting (5/15/30/60 minutes out) — confidence decays with how far "
    "the horizon extrapolates past the observed data window."
)

try:
    areas = api_client.list_parking_areas()
except ApiError as e:
    st.error(f"Could not load parking areas: {e.detail}")
    areas = []

if not areas:
    st.info("No parking areas yet.")
else:
    area_options = {f"{a['name']} ({a['code']})": a["id"] for a in areas}
    col1, col2 = st.columns([2, 1])
    area_label = col1.selectbox("Parking area", list(area_options.keys()))
    gas = col2.selectbox("Gas", ["co", "co2", "no2", "smoke", "pm25"], format_func=gas_label)
    area_id = area_options[area_label]

    col_a, col_b = st.columns(2)
    if col_a.button("Generate forecasts", width='stretch'):
        try:
            forecasts = api_client.generate_forecasts(area_id)
            st.success(f"Generated {len(forecasts)} forecasts.")
        except ApiError as e:
            st.error(f"Forecast generation failed: {e.detail}")

    if col_b.button("Refresh trend chart", width='stretch'):
        st.rerun()

    try:
        trend = api_client.get_trend_chart(area_id, gas)
        actual_x = [p["timestamp"] for p in trend["points"] if p["kind"] == "actual"]
        actual_y = [p["value"] for p in trend["points"] if p["kind"] == "actual"]
        forecast_x = [p["timestamp"] for p in trend["points"] if p["kind"] == "forecast"]
        forecast_y = [p["value"] for p in trend["points"] if p["kind"] == "forecast"]

        # Bridge the gap so the line is continuous at the "now" boundary
        if actual_x and forecast_x:
            forecast_x = [actual_x[-1]] + forecast_x
            forecast_y = [actual_y[-1]] + forecast_y

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=actual_x, y=actual_y, mode="lines+markers", name="Actual", line=dict(color=GREEN, width=3)))
        fig.add_trace(go.Scatter(x=forecast_x, y=forecast_y, mode="lines+markers", name="Forecast", line=dict(color=YELLOW, width=3, dash="dash")))
        fig.update_layout(
            height=380,
            title=f"{gas_label(gas)} ({trend['unit']})",
            legend=dict(orientation="h", y=1.1),
            **PLOTLY_LAYOUT_DEFAULTS,
        )
        st.plotly_chart(fig, width='stretch')
    except ApiError as e:
        st.warning(f"No trend data yet: {e.detail}. Ingest a few readings first (Parking Areas → Ingest Reading).")
