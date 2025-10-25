#!/usr/bin/env python3
import os, requests, json
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()
TM_API_KEY = os.getenv("TM_API_KEY")

VENUES = [
    "Madison Square Garden",
    "Beacon Theatre",
    "Radio City Music Hall",
    "Barclays Center",
    "UBS Arena",
    "Jones Beach Theater",
    "PNC Bank Arts Center",
    "Forest Hills Stadium",
    "Nassau Coliseum",
    "Yankee Stadium",
    "Citi Field",
    "Pier 17",
    "Kings Theatre",
    "Metropolitan Opera House"
]

EXCLUDE_KEYWORDS = [
    "NBA", "NHL", "MLB", "Baseball", "Hockey", "Basketball", "Football",
    "Rockette", "Tour Experience", "Seinfeld", "Seth Meyers", 
]

def get_events(city="New York"):
    url = f"https://app.ticketmaster.com/discovery/v2/events.json?apikey={TM_API_KEY}&city={city}&size=200"
    r = requests.get(url)
    data = r.json().get("_embedded", {}).get("events", [])
    filtered = []
    for e in data:
        name = e["name"]
        venue = e["_embedded"]["venues"][0]["name"]
        if any(v in venue for v in VENUES) and not any(x.lower() in name.lower() for x in EXCLUDE_KEYWORDS):
            filtered.append({
                "name": name,
                "venue": venue,
                "date": e["dates"]["start"].get("localDate"),
                "url": e["url"]
            })
    return filtered

if __name__ == "__main__":
    events = get_events()
    os.makedirs("outputs", exist_ok=True)
    with open("outputs/events.json", "w") as f:
        json.dump(events, f, indent=2)

    print(f"Saved {len(events)} events to outputs/events.json")
