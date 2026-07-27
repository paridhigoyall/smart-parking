import streamlit as st

from lib import api_client, auth
from lib.api_client import ApiError

st.set_page_config(page_title="Vehicles — AirGuard AI", page_icon="🚗", layout="wide")
auth.require_login()

st.markdown("## 🚗 Vehicle Tracking")

tab_entry, tab_manage = st.tabs(["Gate Entry", "Manage Vehicles"])

with tab_entry:
    st.markdown("#### Log a vehicle entering the site")
    with st.form("entry_form"):
        plate = st.text_input("Plate number", placeholder="MH-01-AB-1234")
        vtype = st.selectbox("Vehicle type", ["car", "truck", "tanker", "forklift"])
        driver = st.text_input("Driver name (optional)")
        submitted = st.form_submit_button("Log entry")
    if submitted:
        if not plate:
            st.error("Plate number is required.")
        else:
            try:
                v = api_client.register_vehicle_entry(plate_number=plate, vehicle_type=vtype, driver_name=driver or None)
                st.success(f"Logged entry for {plate} (id: {v['id']}).")
            except ApiError as e:
                st.error(f"Failed: {e.detail}")

with tab_manage:
    try:
        vehicles = api_client.list_vehicles()
    except ApiError as e:
        st.error(f"Could not load vehicles: {e.detail}")
        vehicles = []

    try:
        areas = api_client.list_parking_areas()
        area_options = {f"{a['name']} ({a['code']})": a["id"] for a in areas}
    except ApiError:
        area_options = {}

    if not vehicles:
        st.info("No vehicles tracked yet.")
    for v in vehicles:
        with st.container(border=True):
            col1, col2, col3 = st.columns([2, 1, 1])
            col1.markdown(f"**{v['plate_number']}** ({v['vehicle_type']}) — status: `{v['status']}`")
            if v["status"] == "entered" and area_options:
                with col2:
                    target = st.selectbox("Park at", list(area_options.keys()), key=f"park_{v['id']}")
                    if st.button("Park", key=f"park_btn_{v['id']}"):
                        try:
                            api_client.park_vehicle(v["id"], area_options[target])
                            st.rerun()
                        except ApiError as e:
                            st.error(e.detail)
            if v["status"] in ("entered", "parked"):
                with col3:
                    if st.button("Exit site", key=f"exit_{v['id']}"):
                        try:
                            api_client.exit_vehicle(v["id"])
                            st.rerun()
                        except ApiError as e:
                            st.error(e.detail)
