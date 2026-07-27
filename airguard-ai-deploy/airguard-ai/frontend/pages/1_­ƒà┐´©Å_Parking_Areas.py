import streamlit as st

from lib import api_client, auth
from lib.api_client import ApiError
from lib.theme import RISK_COLORS, RISK_LABELS, gas_label

st.set_page_config(page_title="Parking Areas — AirGuard AI", page_icon="🅿️", layout="wide")
auth.require_login()

st.markdown("## 🅿️ Parking Areas")

tab_overview, tab_create, tab_sensors, tab_ingest = st.tabs(
    ["Overview", "Create Area", "Sensors", "Ingest Reading"]
)

with tab_overview:
    try:
        areas = api_client.list_parking_areas()
    except ApiError as e:
        st.error(f"Could not load parking areas: {e.detail}")
        areas = []

    if not areas:
        st.info("No parking areas yet — create one in the **Create Area** tab.")
    for a in areas:
        level = a["current_risk_level"]
        color = RISK_COLORS.get(level, RISK_COLORS["unknown"])
        with st.expander(f"{a['name']} ({a['code']}) — {RISK_LABELS.get(level, level)}"):
            col1, col2, col3 = st.columns(3)
            col1.metric("Risk Score", f"{a['current_risk_score']:.0f}/100")
            col2.metric("Occupancy", f"{a['occupied_slots']}/{a['capacity']}")
            col3.metric("Status", "Closed" if a["is_closed"] else "Open")

            try:
                risk = api_client.get_parking_area_risk(a["id"])
                st.markdown(f"**Exposure:** {risk['exposure_label']} · **Confidence:** {risk['confidence_score']:.0f}% · **Air Quality:** {risk['air_quality_score']:.0f}/100")
                if risk.get("dominant_gas"):
                    st.markdown(f"**Dominant gas:** {gas_label(risk['dominant_gas'])}")
                if risk.get("factors"):
                    st.markdown("**Per-gas breakdown:**")
                    for f in risk["factors"][:6]:
                        st.progress(
                            min(1.0, f["percent_of_threshold"] / 100),
                            text=f"{gas_label(f['gas'])}: {f['value']:g} ({f['percent_of_threshold']:.0f}% of threshold)",
                        )
            except ApiError:
                st.caption("No sensor readings yet for this area.")

with tab_create:
    st.markdown("#### Register a new parking area")
    with st.form("create_area_form"):
        name = st.text_input("Name", placeholder="Parking A")
        code = st.text_input("Code", placeholder="PARK-A")
        capacity = st.number_input("Capacity", min_value=1, value=50)
        col1, col2 = st.columns(2)
        map_x = col1.number_input("Map X (0-1000)", min_value=0.0, max_value=1000.0, value=500.0)
        map_y = col2.number_input("Map Y (0-1000)", min_value=0.0, max_value=1000.0, value=500.0)
        submitted = st.form_submit_button("Create")
    if submitted:
        if not name or not code:
            st.error("Name and code are required.")
        else:
            try:
                api_client.create_parking_area(name=name, code=code, capacity=int(capacity), map_x=map_x, map_y=map_y)
                st.success(f"Created {name} ({code}).")
                st.rerun()
            except ApiError as e:
                st.error(f"Failed to create area: {e.detail}")

with tab_sensors:
    st.markdown("#### Register a sensor")
    try:
        areas = api_client.list_parking_areas()
    except ApiError:
        areas = []

    if not areas:
        st.info("Create a parking area first.")
    else:
        area_options = {f"{a['name']} ({a['code']})": a["id"] for a in areas}
        with st.form("create_sensor_form"):
            area_label = st.selectbox("Parking area", list(area_options.keys()))
            serial = st.text_input("Serial number", placeholder="SN-001")
            sensor_type = st.selectbox(
                "Sensor type",
                ["co", "co2", "no2", "so2", "nh3", "h2s", "methane", "lpg", "smoke", "pm25", "pm10"],
            )
            submitted = st.form_submit_button("Register sensor")
        if submitted:
            try:
                api_client.create_sensor(
                    serial_number=serial, sensor_type=sensor_type, parking_area_id=area_options[area_label]
                )
                st.success(f"Registered sensor {serial}.")
            except ApiError as e:
                st.error(f"Failed to register sensor: {e.detail}")

    st.markdown("---")
    st.markdown("#### Sensors on this site")
    try:
        sensors = api_client.list_sensors()
        if sensors:
            st.dataframe(
                [
                    {
                        "Serial": s["serial_number"],
                        "Type": s["sensor_type"],
                        "Status": s["status"],
                        "Battery": f"{s['battery_level']:.0f}%",
                        "Health": f"{s['health_score']:.0f}/100",
                    }
                    for s in sensors
                ],
                width='stretch',
                hide_index=True,
            )
        else:
            st.info("No sensors registered yet.")
    except ApiError as e:
        st.error(f"Could not load sensors: {e.detail}")

with tab_ingest:
    st.markdown("#### Manually ingest a gas reading")
    st.caption("Simulates a sensor gateway posting telemetry — useful for demoing without real hardware.")
    try:
        sensors = api_client.list_sensors()
    except ApiError:
        sensors = []

    if not sensors:
        st.info("Register a sensor first.")
    else:
        sensor_options = {f"{s['serial_number']} ({s['sensor_type']})": s["id"] for s in sensors}
        with st.form("ingest_form"):
            sensor_label = st.selectbox("Sensor", list(sensor_options.keys()))
            col1, col2, col3 = st.columns(3)
            co = col1.number_input("CO (ppm)", min_value=0.0, value=5.0)
            co2 = col2.number_input("CO2 (ppm)", min_value=0.0, value=450.0)
            smoke = col3.number_input("Smoke (ppm)", min_value=0.0, value=10.0)
            col4, col5 = st.columns(2)
            pm25 = col4.number_input("PM2.5 (µg/m³)", min_value=0.0, value=10.0)
            pm10 = col5.number_input("PM10 (µg/m³)", min_value=0.0, value=15.0)
            submitted = st.form_submit_button("Ingest reading")
        if submitted:
            try:
                result = api_client.ingest_gas_reading(
                    sensor_id=sensor_options[sensor_label], co=co, co2=co2, smoke=smoke, pm25=pm25, pm10=pm10
                )
                color = RISK_COLORS.get(result["risk_level"], "#8A7A63")
                st.markdown(
                    f"**Result:** <span style='color:{color}; font-weight:700;'>{RISK_LABELS.get(result['risk_level'], result['risk_level'])}</span> "
                    f"— risk score {result['risk_score']:.0f}/100",
                    unsafe_allow_html=True,
                )
            except ApiError as e:
                st.error(f"Ingestion failed: {e.detail}")
