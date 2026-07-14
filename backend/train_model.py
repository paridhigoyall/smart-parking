import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
import pickle

print("Loading Dataset...")

data = pd.read_csv("gas_parking_dataset.csv")

X = data[['CO','CO2','NO2','O2','LPG','Smoke','Temp','Humidity']]
y = data['Parking_Status']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

print("Training Model...")

model = RandomForestClassifier()

model.fit(X_train, y_train)

pred = model.predict(X_test)

accuracy = accuracy_score(y_test, pred)

pickle.dump(model, open("model.pkl", "wb"))

print("Model Trained Successfully")
print("Accuracy:", accuracy)
print("Model Saved as model.pkl")