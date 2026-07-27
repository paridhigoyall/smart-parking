<div align="center">

# 🛡️ AirGuard AI
### AI-Powered Industrial Parking & Environmental Safety Platform

*Full-stack platform that predicts, explains, and acts on industrial gas hazards in real time*

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](.)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](.)
[![Streamlit](https://img.shields.io/badge/Streamlit-frontend-FF4B4B?logo=streamlit&logoColor=white)](.)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)](.)
[![scikit--learn](https://img.shields.io/badge/scikit--learn-RandomForest-F7931E?logo=scikitlearn&logoColor=white)](.)

</div>

---

## The problem

Industrial sites with hazardous gas exposure (refineries, chemical plants,
warehouses) traditionally treat "parking" and "safety monitoring" as two
separate, disconnected systems. AirGuard AI unifies them: it doesn't just
show which parking spaces are free — it monitors real-time air quality,
predicts which zones are dangerous, explains *why* in plain language, and
recommends the safest option.

## What I built

A complete, working full-stack system — not a notebook or a mockup —
spanning backend, frontend, ML, and infrastructure:

| Layer | What's there |
|---|---|
| **Backend** | FastAPI, 60+ REST endpoints, JWT + role-based access control (6 roles), 13-table PostgreSQL schema across 4 real Alembic migrations |
| **AI / ML** | A transparent rule-based risk engine *and* a trained `RandomForestClassifier` (92.6% test accuracy) running side by side, an explainable recommendation engine, a linear-regression gas-trend forecaster, real YOLOv8 object detection, and a classical OpenCV smoke/fire heuristic |
| **Frontend** | Streamlit dashboard (brown/green/yellow industrial theme) with a live plant map, risk gauges, trend charts, and a live 3D digital twin (Plotly) |
| **Infra** | Docker Compose, Celery + Redis for async alert delivery (real SMTP/Twilio-shaped/FCM-shaped notification providers), a full delivery audit trail |

## What makes it worth a second look

- **Explainable, not a black box** — recommendations read like *"Parking C
  is recommended because Carbon Monoxide levels are 63% lower than Parking
  A..."*, generated from the same numbers the engine computed
- **Two classifiers, compared live** — `POST /ml/classify` runs the rule
  engine and the trained model on the same input and flags when they
  disagree, which is itself a useful signal
- **Real geometry, not a lookup table** — the route-recommendation feature
  computes actual 2D vector-geometry hazard avoidance around unsafe zones,
  unit-tested against known coordinates
- **Everything tested against a live system** — every module was run
  against a real PostgreSQL database, a real local SMTP server, and mock
  REST endpoints standing in for Twilio/FCM during development, not just
  written and assumed correct

## Tech stack

**Backend:** Python, FastAPI, SQLAlchemy, Alembic, PostgreSQL, Redis, Celery, scikit-learn, OpenCV, Ultralytics YOLOv8, JWT
**Frontend:** Python, Streamlit, Plotly
**Infra:** Docker, Docker Compose

## Try it

```bash
git clone <this-repo>
cd airguard-ai
cp backend/.env.example backend/.env
docker compose up --build db redis backend celery_worker frontend
```

Dashboard: `http://localhost:8501` · API docs: `http://localhost:8000/api/v1/docs`

Full setup, architecture diagrams, and a module-by-module breakdown are in [`README.md`](README.md). Deployment instructions (Render + optional free Streamlit Cloud frontend) are in [`DEPLOYMENT.md`](DEPLOYMENT.md).

---

<div align="center">
<sub>Built as a full-stack + AI/ML portfolio project. Every module listed as "done" was actually run and tested, not just written.</sub>
</div>
