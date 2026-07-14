from flask import Flask, jsonify
import pandas as pd
import joblib

# Create Flask app
app = Flask(__name__)

# Load trained model
model = joblib.load("model.pkl")


@app.route("/recommend", methods=["GET"])
def recommend():

    data = {
        "Parking": ["A", "B", "C"],
        "CO": [150, 60, 90],
        "CO2": [1200, 500, 700],
        "NO2": [80, 20, 35],
        "O2": [19.5, 20.7, 20.5],
        "LPG": [110, 30, 40],
        "Smoke": [90, 20, 30],
        "Temp": [36, 30, 32],
        "Humidity": [70, 60, 65]
    }

    df = pd.DataFrame(data)

    features = df[['CO', 'CO2', 'NO2', 'O2', 'LPG', 'Smoke', 'Temp', 'Humidity']]

    df["Status"] = model.predict(features)

    priority = {"Safe": 3, "Moderate": 2, "Unsafe": 1}
    df["Score"] = df["Status"].map(priority)

    best = df.sort_values(by="Score", ascending=False).iloc[0]

    explanation = f"""
    Parking {best['Parking']} is recommended because it has comparatively lower harmful gas levels
    like CO, NO2 and Smoke. The air quality here is more suitable for parking vehicles safely.
    """

    return jsonify({
        "parking": best["Parking"],
        "status": best["Status"],
        "explanation": explanation
    })


if __name__ == "__main__":
    app.run(debug=True)