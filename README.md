# 🚗 SPARK: Smart Parking Gas Monitoring System

## 📌 Overview

SPARK is an intelligent smart parking system that analyzes environmental gas levels (CO, CO2, NO2, O2, LPG, Smoke) and recommends the safest parking area within a university campus.  

The system combines Machine Learning and Generative AI to provide both prediction and explanation.

---

## 🎯 Objectives

- Detect harmful gas concentrations in parking zones
- Classify parking areas as Safe, Moderate, or Unsafe
- Recommend the best parking location
- Generate AI-based explanation for the recommendation

---

## 🧠 Technologies Used

### 🔹 Backend

- Python
- Flask
- Scikit-learn
- Pandas

### 🔹 Frontend

- React.js
- Axios
- CSS (Custom + Pastel UI)

### 🔹 AI

- Machine Learning (Random Forest Classifier)
- Generative AI (for explanation generation)

---

## 📊 Features

- 🚗 Smart Parking Recommendation

- 🌫 Gas Level Monitoring (CO, NO2, LPG, etc.)
- 🤖 AI-based Explanation
- 📍 Dashboard UI (Map-style layout)
- 🔄 Real-time Data Simulation

---

## 🗂 Project Structure

smart-parking-project/
│
├── backend/
│ ├── app.py
│ ├── train_model.py
│ ├── dataset_generator.py
│ ├── parking_recommendation.py
│ ├── genAI_explanation.py
│ └── model.pkl
│
├── data/
│ └── gas_parking_dataset.csv
│
├── frontend/
│ ├── src/
│ │ ├── pages/
│ │ │ ├── Login.jsx
│ │ │ └── Dashboard.jsx
│ │ ├── styles/
│ │ │ └── theme.css
│ │ ├── App.js
│ │ └── index.js
│ │
│ └── package.json
│
├── requirements.txt
└── README.md

---

## ⚙️ Installation & Setup

### 🔹 Backend Setup

```bash'
cd backend
pip install -r ../requirements.txt
python app.py

---

## ⚙️ Installation & Setup

### 🔹 Backend Setup

```bash
cd backend
pip install -r ../requirements.txt
python app.py
##frontend setup
cd frontend
npm install
npm start

#runs on
http://localhost:3000
#api endpoint
GET /recommend
Sample Response:
{
  "parking": "B",
  "status": "Moderate",
  "explanation": "Parking B is recommended because it has lower pollution levels..."
}
🧪 Machine Learning Model
Algorithm: Random Forest Classifier
Input Features:
CO
CO2
NO2
O2
LPG
Smoke
Temperature
Humidity
Output:
Safe
Moderate
Unsafe
🤖 Generative AI Role

Generative AI is used to:

Interpret model predictions
Generate human-readable explanations
Enhance decision transparency
🚀 Future Enhancements
📍 Google Maps Integration
📊 Real-time Graphs and Analytics
🔐 User Authentication with Email Verification
🌐 IoT Sensor Integration
📱 Mobile App Support
👩‍💻 Author

Paridhi Goyal

