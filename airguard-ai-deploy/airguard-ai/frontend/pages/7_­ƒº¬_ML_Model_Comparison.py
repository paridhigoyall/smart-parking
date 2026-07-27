import plotly.graph_objects as go
import streamlit as st

from lib import api_client, auth
from lib.api_client import ApiError
from lib.theme import GREEN, PLOTLY_LAYOUT_DEFAULTS, RISK_COLORS, RISK_LABELS, YELLOW

st.set_page_config(page_title="ML Model Comparison — AirGuard AI", page_icon="🧪", layout="wide")
auth.require_login()

st.markdown("## 🧪 Rule Engine vs. Trained ML Model")
st.caption(
    "Every reading can be scored two independent ways: a transparent, threshold-based rule engine "
    "and a trained RandomForestClassifier. Enter hypothetical gas values below to see where they "
    "agree — and where they don't."
)

with st.form("classify_form"):
    st.markdown("#### Gas values")
    c1, c2, c3, c4 = st.columns(4)
    co = c1.number_input("CO (ppm)", min_value=0.0, value=5.0)
    co2 = c2.number_input("CO2 (ppm)", min_value=0.0, value=450.0)
    no2 = c3.number_input("NO2 (ppm)", min_value=0.0, value=0.2)
    h2s = c4.number_input("H2S (ppm)", min_value=0.0, value=0.0)
    c5, c6, c7 = st.columns(3)
    smoke = c5.number_input("Smoke (ppm)", min_value=0.0, value=10.0)
    pm25 = c6.number_input("PM2.5 (µg/m³)", min_value=0.0, value=10.0)
    pm10 = c7.number_input("PM10 (µg/m³)", min_value=0.0, value=15.0)
    submitted = st.form_submit_button("Classify with both models", width='stretch')

if submitted:
    try:
        result = api_client.classify_gas_values(co=co, co2=co2, no2=no2, h2s=h2s, smoke=smoke, pm25=pm25, pm10=pm10)
        rule = result["rule_engine"]
        ml = result.get("ml_model")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### 🟢 Rule-Based Risk Engine")
            level = rule["risk_level"]
            color = RISK_COLORS.get(level, "#8A7A63")
            st.markdown(f"**Prediction:** <span style='color:{color}; font-size:1.3em; font-weight:700;'>{RISK_LABELS.get(level, level)}</span>", unsafe_allow_html=True)
            st.metric("Risk score", f"{rule['risk_score']:.0f}/100")
            st.caption(f"Exposure: {rule['exposure_label']}")
            if rule.get("dominant_gas"):
                st.caption(f"Dominant gas: {rule['dominant_gas'].upper()}")

        with col2:
            st.markdown("### 🟡 Trained ML Classifier")
            if ml:
                level = ml["predicted_label"]
                color = RISK_COLORS.get(level, "#8A7A63")
                st.markdown(f"**Prediction:** <span style='color:{color}; font-size:1.3em; font-weight:700;'>{RISK_LABELS.get(level, level)}</span>", unsafe_allow_html=True)
                st.metric("Model confidence", f"{ml['model_confidence']*100:.1f}%")

                fig = go.Figure(
                    go.Bar(
                        x=list(ml["probabilities"].values()),
                        y=[RISK_LABELS.get(k, k) for k in ml["probabilities"].keys()],
                        orientation="h",
                        marker_color=[RISK_COLORS.get(k, "#8A7A63") for k in ml["probabilities"].keys()],
                    )
                )
                fig.update_layout(height=180, xaxis=dict(range=[0, 1], title="Probability"), **PLOTLY_LAYOUT_DEFAULTS)
                st.plotly_chart(fig, width='stretch')
            else:
                st.warning("ML model not available — train it first with `python -m app.ml.train_risk_classifier` on the backend.")

        if result.get("agree") is not None:
            if result["agree"]:
                st.success("✅ Both models agree on this reading.")
            else:
                st.warning("⚠️ The two models disagree on this reading — worth a second look.")
    except ApiError as e:
        st.error(f"Classification failed: {e.detail}")

st.markdown("---")
st.markdown("### 📊 Real Training Metrics")
st.caption("Not fabricated for display — this is what actually got written out the last time the model was trained.")
try:
    info = api_client.get_model_info()
    c1, c2, c3 = st.columns(3)
    c1.metric("Test Accuracy", f"{info['test_accuracy']*100:.1f}%")
    c2.metric("Training Samples", f"{info['n_samples']:,}")
    c3.metric("Injected Label Noise", f"{info['label_noise_rate']*100:.0f}%")

    st.markdown("**Feature importances** (should roughly track the rule engine's hand-set toxicity weights)")
    importances = info["feature_importances"]
    fig = go.Figure(
        go.Bar(
            x=list(importances.values()),
            y=[k.upper() for k in importances.keys()],
            orientation="h",
            marker_color=YELLOW,
        )
    )
    fig.update_layout(height=320, **PLOTLY_LAYOUT_DEFAULTS)
    st.plotly_chart(fig, width='stretch')

    st.caption(f"Trained at: {info['trained_at']}")
except ApiError as e:
    st.info(f"No training report available yet: {e.detail}")
