import plotly.graph_objects as go
import streamlit as st

from lib import api_client, auth
from lib.api_client import ApiError
from lib.theme import BROWN, BROWN_DARK, CREAM, PLOTLY_LAYOUT_DEFAULTS, RISK_COLORS, RISK_LABELS

st.set_page_config(page_title="AirGuard AI", page_icon="🛡️", layout="wide")


def render_login():
    st.markdown(
        f"<h1 style='text-align:center; color:{CREAM};'>🛡️ AirGuard AI</h1>"
        f"<p style='text-align:center; color:{CREAM}; opacity:0.7;'>"
        "Industrial Parking &amp; Environmental Safety Platform</p>",
        unsafe_allow_html=True,
    )
    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        with st.form("login_form"):
            email = st.text_input("Email", value="admin@airguard.ai")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign in", width='stretch')
        if submitted:
            ok, error = auth.do_login(email, password)
            if ok:
                st.rerun()
            else:
                st.error(error or "Login failed")
        st.caption("Default admin account is seeded from `FIRST_SUPERUSER_EMAIL` on first backend boot.")


def risk_gauge(score: float, level: str, title: str = "Site-Wide Risk"):
    color = RISK_COLORS.get(level, RISK_COLORS["unknown"])
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=score,
            title={"text": title, "font": {"color": CREAM, "size": 16}},
            number={"suffix": " / 100", "font": {"color": color, "size": 30}},
            gauge={
                "axis": {"range": [0, 100], "tickcolor": CREAM},
                "bar": {"color": color},
                "bgcolor": BROWN,
                "borderwidth": 1,
                "bordercolor": CREAM,
                "steps": [
                    {"range": [0, 40], "color": "rgba(107,142,35,0.25)"},
                    {"range": [40, 70], "color": "rgba(232,185,35,0.25)"},
                    {"range": [70, 100], "color": "rgba(192,57,43,0.25)"},
                ],
            },
        )
    )
    fig.update_layout(height=260, **PLOTLY_LAYOUT_DEFAULTS)
    return fig


def render_dashboard():
    user = auth.current_user()
    top_left, top_right = st.columns([4, 1])
    with top_left:
        st.markdown("### 🛡️ AirGuard AI — Command Center")
        st.caption(f"Logged in as **{user.get('full_name', '')}** ({user.get('role', '')})")
    with top_right:
        if st.button("Log out", width='stretch'):
            auth.do_logout()
            st.rerun()

    try:
        areas = api_client.list_parking_areas()
    except ApiError as e:
        st.error(f"Could not load parking areas: {e.detail}")
        st.info("Is the backend running and reachable at the configured API_BASE_URL?")
        return

    try:
        alerts = api_client.list_alerts()
    except ApiError:
        alerts = []

    open_areas = [a for a in areas if not a["is_closed"]]
    avg_risk = sum(a["current_risk_score"] for a in open_areas) / len(open_areas) if open_areas else 0.0
    unsafe_count = sum(1 for a in areas if a["current_risk_level"] == "unsafe")
    safe_count = sum(1 for a in areas if a["current_risk_level"] == "safe")
    open_alerts = sum(1 for a in alerts if a["status"] == "open")
    overall_level = "unsafe" if unsafe_count > 0 else ("moderate" if avg_risk >= 40 else "safe")

    stat_cols = st.columns(4)
    stat_cols[0].metric("Avg Risk Score", f"{avg_risk:.0f}/100")
    stat_cols[1].metric("Safe Zones", f"{safe_count}/{len(areas)}")
    stat_cols[2].metric("Unsafe Zones", f"{unsafe_count}")
    stat_cols[3].metric("Open Alerts", f"{open_alerts}")

    gauge_col, map_col = st.columns([1, 2])
    with gauge_col:
        st.plotly_chart(risk_gauge(avg_risk, overall_level), width='stretch')

    with map_col:
        st.markdown("**Plant Map** — zones colored by live risk")
        if areas:
            fig = go.Figure()
            for a in areas:
                color = "#8A7A63" if a["is_closed"] else RISK_COLORS.get(a["current_risk_level"], RISK_COLORS["unknown"])
                fig.add_trace(
                    go.Scatter(
                        x=[a["map_x"]],
                        y=[a["map_y"]],
                        mode="markers+text",
                        marker=dict(size=34, color=color, line=dict(width=2, color=CREAM)),
                        text=[a["code"]],
                        textposition="middle center",
                        textfont=dict(color=BROWN_DARK, size=10, family="Arial Black"),
                        name=a["name"],
                        hovertext=f"{a['name']} — {a['current_risk_score']:.0f}/100",
                        hoverinfo="text",
                    )
                )
            fig.update_layout(
                height=300,
                showlegend=False,
                xaxis=dict(range=[0, 1000], visible=False),
                yaxis=dict(range=[0, 1000], visible=False),
                **PLOTLY_LAYOUT_DEFAULTS,
            )
            st.plotly_chart(fig, width='stretch')
        else:
            st.info("No parking areas configured yet — add one from the Parking Areas page.")

    st.markdown("---")
    st.markdown("#### Parking Areas")
    if not areas:
        st.info("No parking areas yet.")
    else:
        cards_per_row = 3
        for i in range(0, len(areas), cards_per_row):
            row_areas = areas[i : i + cards_per_row]
            cols = st.columns(cards_per_row)
            for col, a in zip(cols, row_areas):
                level = a["current_risk_level"]
                color = RISK_COLORS.get(level, RISK_COLORS["unknown"])
                with col:
                    st.markdown(
                        f"""
                        <div style="background:{BROWN}; border:1px solid {color}; border-radius:10px; padding:14px; margin-bottom:10px;">
                          <div style="display:flex; justify-content:space-between;">
                            <b style="color:{CREAM};">{a['name']}</b>
                            <span style="color:{color}; font-weight:600;">{RISK_LABELS.get(level, level)}</span>
                          </div>
                          <div style="color:{CREAM}; opacity:0.7; font-size:0.85em;">{a['code']}</div>
                          <div style="color:{CREAM}; margin-top:8px;">
                            Risk score: <b style="color:{color};">{a['current_risk_score']:.0f}/100</b><br/>
                            Occupancy: {a['occupied_slots']}/{a['capacity']}
                          </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

    st.markdown("---")
    st.caption(
        "Use the sidebar to explore Parking Areas, Alerts, AI Recommendations, "
        "Trends &amp; Forecasts, Vehicles, the Digital Twin, and the ML Model Comparison."
    )


if not auth.is_logged_in():
    render_login()
else:
    render_dashboard()
