import pandas as pd
import pickle

# Load trained model
model = pickle.load(open("model.pkl", "rb"))

print("Model Loaded Successfully")

# Example parking gas data (3 parking zones in campus)
parking_data = {
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

# Convert to dataframe
df = pd.DataFrame(parking_data)

# Features used by ML model
features = df[['CO','CO2','NO2','O2','LPG','Smoke','Temp','Humidity']]

# Predict parking status
df["Status"] = model.predict(features)

# Ranking logic
priority = {
    "Safe": 3,
    "Moderate": 2,
    "Unsafe": 1
}

df["Score"] = df["Status"].map(priority)

# Select best parking
best_parking = df.sort_values(by="Score", ascending=False).iloc[0]

print("\nParking Analysis:")
print(df)

print("\nRecommended Parking Area:", best_parking["Parking"])
print("Condition:", best_parking["Status"])