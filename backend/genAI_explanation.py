# import pandas as pd

# print("Starting Generative AI Explanation Module...\n")

# # Example output from ML parking recommendation
# data = {
#     "Parking": ["A", "B", "C"],
#     "CO": [150, 60, 90],
#     "NO2": [80, 20, 35],
#     "CO2": [1200, 500, 700],
#     "Status": ["Unsafe", "Safe", "Moderate"]
# }

# df = pd.DataFrame(data)

# # Priority ranking
# priority = {
#     "Safe": 3,
#     "Moderate": 2,
#     "Unsafe": 1
# }

# df["Score"] = df["Status"].map(priority)

# # Find best parking
# best_parking = df.sort_values(by="Score", ascending=False).iloc[0]

# print("Parking Analysis:")
# print(df)

# print("\nRecommended Parking:", best_parking["Parking"])

# # Generate AI-style explanation
# explanation = f"""
# AI Explanation:

# Parking Area {best_parking['Parking']} is recommended because it has the lowest
# pollution levels among the available parking zones.

# The carbon monoxide (CO) level is {best_parking['CO']} ppm and the nitrogen dioxide
# (NO2) level is {best_parking['NO2']} ppm, which indicates better air quality
# compared to other parking areas.

# Therefore, Parking Area {best_parking['Parking']} provides a safer environment
# for vehicles and pedestrians.
# """

# print(explanation)
import pandas as pd

print("Starting Generative AI Explanation Module...\n")

# Example output from ML parking recommendation
data = {
    "Parking": ["A", "B", "C"],
    "CO": [150, 60, 90],
    "NO2": [80, 20, 35],
    "CO2": [1200, 500, 700],
    "Status": ["Unsafe", "Safe", "Moderate"]
}

df = pd.DataFrame(data)

# Priority ranking
priority = {
    "Safe": 3,
    "Moderate": 2,
    "Unsafe": 1
}

df["Score"] = df["Status"].map(priority)

# Find best parking
best_parking = df.sort_values(by="Score", ascending=False).iloc[0]

print("Parking Analysis:")
print(df)

print("\nRecommended Parking:", best_parking["Parking"])

# Generate AI-style explanation
explanation = f"""
AI Explanation:

Parking Area {best_parking['Parking']} is recommended because it has the lowest
pollution levels among the available parking zones.

The carbon monoxide (CO) level is {best_parking['CO']} ppm and the nitrogen dioxide
(NO2) level is {best_parking['NO2']} ppm, which indicates better air quality
compared to other parking areas.

Therefore, Parking Area {best_parking['Parking']} provides a safer environment
for vehicles and pedestrians.
"""

print(explanation)