import streamlit as st

from lib import api_client, auth
from lib.api_client import ApiError
from lib.theme import SEVERITY_COLORS, gas_label

st.set_page_config(page_title="Alerts — AirGuard AI", page_icon="🚨", layout="wide")
auth.require_login()

st.markdown("## 🚨 Alerts")

status_filter = st.radio("Filter", ["All", "Open", "Acknowledged", "Resolved"], horizontal=True)

try:
    filt = None if status_filter == "All" else status_filter.lower()
    alerts = api_client.list_alerts(status=filt)
except ApiError as e:
    st.error(f"Could not load alerts: {e.detail}")
    alerts = []

open_count = sum(1 for a in alerts if a["status"] == "open")
st.metric("Open alerts (in this view)", open_count)

if not alerts:
    st.success("No alerts to show. All zones nominal.")

for alert in alerts:
    color = SEVERITY_COLORS.get(alert["severity"], "#8A7A63")
    with st.container(border=True):
        col1, col2 = st.columns([5, 1])
        with col1:
            st.markdown(
                f"<span style='color:{color}; font-weight:700;'>{alert['severity'].upper()}</span> — **{alert['title']}**",
                unsafe_allow_html=True,
            )
            st.write(alert["message"])
            meta = f"Status: {alert['status']} · Created: {alert['created_at']}"
            if alert.get("gas_type"):
                meta += f" · Gas: {gas_label(alert['gas_type'])}"
            st.caption(meta)
        with col2:
            if alert["status"] == "open":
                if st.button("Acknowledge", key=f"ack_{alert['id']}"):
                    try:
                        api_client.acknowledge_alert(alert["id"])
                        st.rerun()
                    except ApiError as e:
                        st.error(e.detail)
