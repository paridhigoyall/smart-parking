import streamlit as st

from lib import api_client, auth
from lib.api_client import ApiError
from lib.theme import RISK_COLORS, RISK_LABELS

st.set_page_config(page_title="AI Recommendations — AirGuard AI", page_icon="🤖", layout="wide")
auth.require_login()

st.markdown("## 🤖 AI Parking Recommendation")
st.caption(
    "Ranks every open parking area by live risk and explains the top choice in plain language — "
    "generated from the same numbers the risk engine computed, not templated text."
)

try:
    rec = api_client.get_parking_recommendation()
except ApiError as e:
    st.warning(f"No recommendation available yet: {e.detail}")
    rec = None

if rec and rec.get("top_choice_area_name"):
    st.success(f"**Recommended: {rec['top_choice_area_name']}**")
    st.markdown(f"> {rec['explanation']}")

    st.markdown("#### Full ranking")
    for r in rec["ranked_areas"]:
        level = r["assessment"]["risk_level"]
        color = RISK_COLORS.get(level, "#8A7A63")
        st.markdown(
            f"**#{r['rank']}** {r['parking_area_name']} ({r['parking_area_code']}) — "
            f"<span style='color:{color}; font-weight:600;'>{RISK_LABELS.get(level, level)}</span> "
            f"· risk {r['assessment']['risk_score']:.0f}/100 · air quality {r['assessment']['air_quality_score']:.0f}/100",
            unsafe_allow_html=True,
        )

st.markdown("---")
st.markdown("### 🧭 Suggested Actions for a Specific Area")
try:
    areas = api_client.list_parking_areas()
except ApiError:
    areas = []

if areas:
    area_options = {f"{a['name']} ({a['code']})": a["id"] for a in areas}
    selected = st.selectbox("Choose a parking area", list(area_options.keys()))
    if st.button("Get suggested actions"):
        try:
            support = api_client.get_suggested_actions(area_options[selected])
            level = support["risk_level"]
            color = RISK_COLORS.get(level, "#8A7A63")
            st.markdown(
                f"Current risk level: <span style='color:{color}; font-weight:700;'>{RISK_LABELS.get(level, level)}</span>",
                unsafe_allow_html=True,
            )
            for s in support["suggestions"]:
                st.info(f"**{s['action'].replace('_', ' ').title()}** — {s['reason']}")
        except ApiError as e:
            st.error(f"Could not get suggestions: {e.detail}")
else:
    st.info("No parking areas yet.")
