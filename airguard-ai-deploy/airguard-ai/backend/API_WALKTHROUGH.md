# API Walkthrough

Every command below was actually run against a live instance while building
each module — this isn't a hypothetical usage example.

Set these once:

```bash
export API=http://localhost:8000/api/v1
```

## 1. Log in

```bash
TOKEN=$(curl -s -X POST $API/auth/login \
  -d "username=admin@airguard.ai&password=ChangeMe123!" \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
AUTH="Authorization: Bearer $TOKEN"
```

## 2. Create a parking area

```bash
curl -s -X POST $API/parking-areas -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"name":"Parking A","code":"PARK-A","capacity":50,"map_x":100,"map_y":200}'
```

Copy the returned `id` into `AREA_ID`.

## 3. Register a sensor on that area

```bash
curl -s -X POST $API/sensors -H "$AUTH" -H "Content-Type: application/json" \
  -d "{\"serial_number\":\"SN-001\",\"sensor_type\":\"co\",\"parking_area_id\":\"$AREA_ID\"}"
```

Copy the returned `id` into `SENSOR_ID`.

## 4. Ingest a gas reading

```bash
curl -s -X POST $API/gas-readings -H "$AUTH" -H "Content-Type: application/json" \
  -d "{\"sensor_id\":\"$SENSOR_ID\",\"co\":2,\"co2\":400,\"no2\":0.1,\"smoke\":10,\"pm25\":8,\"pm10\":15}"
```

Returns a full `RiskAssessmentRead` immediately — risk score, level,
exposure label, confidence, air quality score, and a per-gas breakdown.
Ingest a reading with `co` near or above 35 (the default unsafe threshold)
to see the risk level flip to `unsafe` and an alert get auto-created.

## 5. Check the live risk for an area

```bash
curl -s $API/parking-areas/$AREA_ID/risk -H "$AUTH"
```

## 6. Get a parking recommendation across all areas

Create 2-3 areas with different gas levels (step 2-4, repeated) to see this
do something interesting:

```bash
curl -s $API/recommendations/parking -H "$AUTH"
```

Returns a ranked list plus a plain-language explanation of the top choice,
e.g. *"Parking C is recommended because Carbon Monoxide levels are 63%
lower than Parking A..."*.

## 7. Get suggested safety actions for one area

```bash
curl -s $API/recommendations/actions/$AREA_ID -H "$AUTH"
```

## 8. Generate forecasts

Ingest a few readings for the same sensor over time (varying `recorded_at`)
so there's a trend to fit, then:

```bash
curl -s -X POST "$API/predictions/generate?parking_area_id=$AREA_ID" -H "$AUTH"
```

Returns predicted values for every gas at 5/15/30/60 minutes out, with
per-gas trend direction and confidence.

## 9. Get a chart-ready trend series

```bash
curl -s "$API/predictions/trend?parking_area_id=$AREA_ID&gas=co" -H "$AUTH"
```

Returns actual historical points followed by forecast points — this is
exactly what the frontend's trend chart consumes.

## 10. List and acknowledge alerts

```bash
curl -s $API/alerts -H "$AUTH"
curl -s -X POST $API/alerts/$ALERT_ID/acknowledge -H "$AUTH"
```

## 11. Register your phone/device for SMS & push alerts

```bash
curl -s -X PATCH $API/users/me -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"phone_number":"+15551234567","push_token":"your-fcm-device-token"}'
```

## 12. Check (and manually re-trigger) alert delivery

```bash
curl -s $API/alerts/$ALERT_ID/notifications -H "$AUTH"
curl -s -X POST $API/alerts/$ALERT_ID/notify -H "$AUTH"
```

Notification channels with no credentials configured show up as `skipped`
in the log, not `failed` — ingestion never blocks on delivery either way.

## 13. Check sensor health (predictive maintenance)

```bash
curl -s $API/sensors/$SENSOR_ID/health -H "$AUTH"
```

## 14. Log a maintenance event

```bash
curl -s -X POST $API/sensors/$SENSOR_ID/maintenance-logs -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"event_type":"calibration","notes":"Routine check","performed_by":"J. Diaz"}'
```

`calibration` and `battery_swap` event types have real side effects — they
reset the sensor's calibration timestamp / battery level, not just log an
entry. Check `GET /sensors/$SENSOR_ID/health` again afterward to see it
reflected.

## 15. Generate a historical analytics rollup

```bash
curl -s -X POST "$API/analytics/rollups/generate?parking_area_id=$AREA_ID&period_type=daily&period_start=$(date -u +%Y-%m-%d)" -H "$AUTH"
curl -s "$API/analytics/rollups?parking_area_id=$AREA_ID" -H "$AUTH"
```

## 16. Analyze a camera frame (requires `requirements-vision.txt`)

```bash
curl -s -X POST "$API/vision/analyze?parking_area_id=$AREA_ID" \
  -H "$AUTH" -F "file=@/path/to/frame.jpg;type=image/jpeg"
```

Returns detected vehicle/person counts (real YOLOv8 inference) and a
smoke/fire heuristic result. A high-confidence fire/smoke detection raises
a real alert through the same pipeline as a gas-threshold breach — check
`GET /alerts` afterward. History: `GET /vision/analyses?parking_area_id=$AREA_ID`.

## 17. Track a vehicle and get a safe route

```bash
curl -s -X POST $API/vehicles/entry -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"plate_number":"MH-01-AB-1234","vehicle_type":"car"}'
# copy the returned id into VEHICLE_ID
curl -s -X POST $API/vehicles/$VEHICLE_ID/park -H "$AUTH" -H "Content-Type: application/json" \
  -d "{\"parking_area_id\":\"$AREA_ID\"}"

curl -s "$API/routes/to/$AREA_ID" -H "$AUTH"
```
