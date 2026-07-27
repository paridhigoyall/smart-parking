# Deploying AirGuard AI

Two paths, both using the same Docker images already built and tested
locally. Honest caveat up front: I built `render.yaml` against Render's
documented Blueprint spec, but couldn't actually deploy it from this
environment to confirm it end-to-end (render.com isn't reachable from
where this was built) — treat the first deploy as something to verify
against the checklist below, not something guaranteed flawless on the
first try. The Dockerfiles and startup commands it references **are**
the same ones already tested locally.

## Option A — Everything on Render (recommended)

One Blueprint (`render.yaml`) deploys Postgres, Redis, the backend API,
the Celery worker, and the Streamlit frontend together.

1. Push this repo to GitHub (see the git steps in the README if you
   haven't already).
2. In the Render dashboard: **New → Blueprint**, point it at your repo.
   Render reads `render.yaml` and shows you the 5 services it's about to
   create (`airguard-db`, `airguard-redis`, `airguard-backend`,
   `airguard-celery-worker`, `airguard-frontend`).
3. Before clicking deploy, Render will prompt you to fill in every
   `sync: false` env var. At minimum set, on **airguard-backend**:
   - `FIRST_SUPERUSER_EMAIL` / `FIRST_SUPERUSER_PASSWORD` — your real
     admin login, not the sample defaults from local dev
   - `BACKEND_CORS_ORIGINS` — leave blank for now, you'll come back to
     this in step 5
   - SMTP/Twilio/FCM/Weather keys — optional, leave blank to run with
     those channels/features harmlessly skipped
4. Deploy. `airguard-backend`'s Dockerfile already runs
   `alembic upgrade head` before starting uvicorn (see its `CMD`), so the
   database schema is created automatically on first boot — no separate
   migration step to remember.
5. Once `airguard-frontend` has deployed and you have its URL (something
   like `https://airguard-frontend.onrender.com`):
   - Go back to `airguard-backend`'s environment settings and set
     `BACKEND_CORS_ORIGINS` to that exact URL, then **manually redeploy**
     the backend (env var changes don't auto-restart on Render by default
     for this kind of change — check the dashboard).
   - Go to `airguard-frontend`'s environment settings and set
     `API_BASE_URL` to `https://<your-backend-service>.onrender.com/api/v1`
     (Render can't auto-wire this one — see the comment in `render.yaml`
     for why). No rebuild needed, Streamlit reads this at runtime.
6. Verify (see the checklist below) before considering it done.

**Free tier reality check:** Render's free web services spin down after
15 minutes of inactivity and take ~30-60 seconds to wake back up on the
next request. Fine for a portfolio/demo link you share occasionally, not
fine for something you need instantly responsive — upgrade the plan if
that matters for your use case.

**The computer vision module** (`requirements-vision.txt`, ~5-6GB with
PyTorch) will make `airguard-backend`'s build slow and may not fit
comfortably in a free-tier build. Leave it uninstalled (the default) for
your first deploy — `/vision/*` just won't be registered, everything else
works. Add it later on a paid plan if you specifically need to demo it.

## Option B — Backend on Render + Frontend on Streamlit Community Cloud

Worth doing specifically if you want a clean, free, permanent public link
to just the dashboard (Streamlit Cloud's free tier doesn't spin down the
same punishing way, and it's a recognizable, shareable URL for a
portfolio).

1. Deploy `airguard-backend`, `airguard-db`, `airguard-redis`, and
   `airguard-celery-worker` on Render as in Option A (everything except
   `airguard-frontend` — you can delete that service from `render.yaml`
   locally or just ignore it in the Blueprint).
2. Go to [share.streamlit.io](https://share.streamlit.io), sign in with
   GitHub, **New app**, point it at this repo with:
   - Main file path: `frontend/app.py`
3. In the app's **Settings → Secrets**, paste:
   ```toml
   API_BASE_URL = "https://<your-backend-service>.onrender.com/api/v1"
   ```
   (`frontend/lib/api_client.py` checks `st.secrets` specifically for
   this — Streamlit Cloud doesn't support plain environment variables the
   way Docker/Render do.)
4. Go back to the Render backend's `BACKEND_CORS_ORIGINS` and set it to
   your `*.streamlit.app` URL, then redeploy the backend.

## Post-deploy verification checklist

Don't skip this — a deploy that "looks done" in the dashboard isn't the
same as one that actually works:

- [ ] `curl https://<backend-url>/api/v1/health` returns
      `{"status":"ok", ..., "database":"ok"}`
- [ ] The frontend URL loads the login page (not a blank page or a
      connection-refused error)
- [ ] Logging in with your real admin credentials succeeds
- [ ] Creating a parking area and ingesting a gas reading works (Parking
      Areas page → Create Area, then Ingest Reading) — this exercises the
      full stack: frontend → backend → Postgres → risk engine → back
- [ ] Open the browser's dev tools Network tab and confirm there are no
      CORS errors — if requests are failing silently, this is almost
      always `BACKEND_CORS_ORIGINS` not matching the frontend's actual URL
      exactly (including `https://`, no trailing slash)
- [ ] `GET /api/v1/ml/model-info` returns real metrics (confirms the
      pre-trained model shipped correctly in the Docker build)

## Environment variables reference

Every variable `render.yaml` marks `sync: false` needs a value set
manually in the Render dashboard before or right after first deploy —
`backend/.env.example` has the full list with descriptions.

## Common issues

**"Could not reach the backend" on the login page** — `API_BASE_URL` is
wrong or the backend hasn't finished its cold start yet (free tier). Wait
30-60s and retry; if it persists, check the exact URL matches the
backend's actual Render URL including `/api/v1`.

**Login page loads but nothing else works / CORS errors in the console**
— `BACKEND_CORS_ORIGINS` on the backend doesn't match the frontend's URL
exactly. This has to be redeployed on the backend after you know the
frontend's real URL — it's a chicken-and-egg problem on first deploy,
which is why step 5 in Option A exists.

**Alerts get created but no email/SMS/push arrives** — either
`airguard-celery-worker` isn't running (check its logs in the Render
dashboard) or the SMTP/Twilio/FCM env vars aren't set. Both are
expected-safe: alerts still work, delivery is just skipped and logged as
such (`GET /alerts/{id}/notifications` will show `"status": "skipped"`).
