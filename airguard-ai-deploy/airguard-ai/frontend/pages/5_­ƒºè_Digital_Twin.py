import plotly.graph_objects as go
import streamlit as st

from lib import api_client, auth
from lib.api_client import ApiError
from lib.theme import BROWN_DARK, CREAM, RISK_COLORS

st.set_page_config(page_title="Digital Twin — AirGuard AI", page_icon="🧊", layout="wide")
auth.require_login()

st.markdown("## 🧊 Digital Twin (Prototype)")
st.caption(
    "A real, live-data-driven 3D scene — each parking area is a colored, risk-height-scaled bar on "
    "the same map coordinates the 2D plant map uses. This is a simplified block representation, "
    "**not** a CAD-accurate industrial model — a production twin would ingest a real facility "
    "CAD/BIM model and a real gas-dispersion simulation instead."
)

try:
    areas = api_client.list_parking_areas()
except ApiError as e:
    st.error(f"Could not load parking areas: {e.detail}")
    areas = []

if not areas:
    st.info("No parking areas yet.")
else:
    xs, ys, zs, colors, texts = [], [], [], [], []
    for a in areas:
        height = 0.3 if a["is_closed"] else 0.5 + (a["current_risk_score"] / 100) * 3.0
        color = "#8A7A63" if a["is_closed"] else RISK_COLORS.get(a["current_risk_level"], RISK_COLORS["unknown"])
        xs.append(a["map_x"])
        ys.append(a["map_y"])
        zs.append(height)
        colors.append(color)
        texts.append(f"{a['name']} ({a['code']})<br>Risk: {a['current_risk_score']:.0f}/100<br>Occupancy: {a['occupied_slots']}/{a['capacity']}")

    fig = go.Figure()

    # A bar per parking area, drawn as a vertical line + marker so plain
    # Scatter3d can stand in for extruded "blocks" without needing a mesh
    # library — genuinely 3D and orbit-able, just geometrically simple.
    for x, y, z, color, text in zip(xs, ys, zs, colors, texts):
        fig.add_trace(
            go.Scatter3d(
                x=[x, x], y=[y, y], z=[0, z],
                mode="lines",
                line=dict(color=color, width=22),
                hoverinfo="skip",
                showlegend=False,
            )
        )
        fig.add_trace(
            go.Scatter3d(
                x=[x], y=[y], z=[z],
                mode="markers+text",
                marker=dict(size=8, color=color, line=dict(color=CREAM, width=1)),
                text=[text.split("<br>")[0]],
                textposition="top center",
                textfont=dict(color=CREAM, size=11),
                hovertext=[text],
                hoverinfo="text",
                showlegend=False,
            )
        )

    fig.update_layout(
        height=650,
        paper_bgcolor=BROWN_DARK,
        font=dict(color=CREAM),
        scene=dict(
            xaxis=dict(range=[0, 1000], backgroundcolor=BROWN_DARK, gridcolor="#4A3820", title="Site X"),
            yaxis=dict(range=[0, 1000], backgroundcolor=BROWN_DARK, gridcolor="#4A3820", title="Site Y"),
            zaxis=dict(range=[0, 4], backgroundcolor=BROWN_DARK, gridcolor="#4A3820", title="Risk height"),
            camera=dict(eye=dict(x=1.4, y=1.4, z=0.9)),
        ),
        margin=dict(l=0, r=0, t=10, b=0),
    )
    st.plotly_chart(fig, width='stretch')
    st.caption("Drag to orbit · scroll to zoom · hover a bar for details")
