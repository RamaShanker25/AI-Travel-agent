import os, json
import pandas as pd
from datetime import datetime, timedelta, timezone
import httpx

BASE = os.path.join(os.path.dirname(__file__), "data")
LOC = pd.read_csv(os.path.join(BASE, "locations.csv"))
ACT = pd.read_csv(os.path.join(BASE, "activities.csv"))
ACCOM = pd.read_csv(os.path.join(BASE, "accommodations.csv"))
TRANS = pd.read_csv(os.path.join(BASE, "transports.csv"))

def load_data_snapshot(max_locations: int = 8) -> str:
    sample = LOC.head(max_locations)[["id", "name", "type", "state", "top_activities"]]
    return sample.to_json(orient="records", force_ascii=False, indent=2)

async def tool_get_weather(location_id: int, start_date: str, end_date: str):
    API_KEY = os.getenv("OPENWEATHER_API_KEY", "")
    loc = LOC[LOC["id"] == int(location_id)].iloc[0]
    lat, lon = float(loc["latitude"]), float(loc["longitude"])
    if API_KEY:
        url = "https://api.openweathermap.org/data/2.5/onecall"
        params = {"lat": lat, "lon": lon, "exclude": "minutely,daily,alerts", "units": "metric", "appid": API_KEY}
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(url, params=params)
            if r.status_code != 200:
                return {"error": r.text}
            data = r.json()
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date) + timedelta(days=1)
        relevant = []
        for h in data.get("hourly", []):
            t = datetime.fromtimestamp(h["dt"], tz=timezone.utc)
            if start <= t <= end:
                relevant.append(h)
        avg_temp = sum(h.get("temp", 0) for h in relevant) / len(relevant) if relevant else None
        rain_hours = len([h for h in relevant if any(w.get("main", "").lower() in ("rain","snow") for w in h.get("weather", []))])
        return {"summary": {"avg_temp": round(avg_temp, 1) if avg_temp is not None else None, "rain_hours": rain_hours}, "details": relevant}
    else:
        return {"summary": {"avg_temp": 18, "rain_hours": 0}, "details": []}

async def tool_generate_itinerary(args: dict):
    dest_id = int(args["destination_id"])
    sdate = datetime.fromisoformat(args["start_date"])
    edate = datetime.fromisoformat(args["end_date"])
    days = max(1, (edate.date() - sdate.date()).days + 1)
    dest_row = LOC[LOC["id"] == dest_id].iloc[0].to_dict()

    accoms = ACCOM[(ACCOM["city_id"] == dest_id) & (ACCOM["category"].str.lower() == args["budget_tier"].lower())].to_dict(orient="records")
    accoms = accoms[:6]

    acts = ACT[ACT["location_id"] == dest_id].to_dict(orient="records")
    itinerary = {"destination": dest_row, "accommodations": accoms, "days": []}
    for d in range(days):
        day_date = (sdate + timedelta(days=d)).date().isoformat()
        chosen = acts[d*3:(d*3)+3] if len(acts) > (d*3) else acts[:3]
        activities = []
        for a in chosen:
            activities.append({
                "activity_name": a["activity_name"],
                "must_see_place": a.get("must_see_place", ""),
                "duration_mins": int(a["typical_duration_mins"]),
                "estimated_cost_inr": int(a["estimated_cost_inr"])
            })
        itinerary["days"].append({"date": day_date, "activities": activities})
    itinerary["weather_summary"] = {"avg_temp": None, "rain_hours": None}
    return itinerary
