#!/usr/bin/env python3
import os, requests, json
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()
TM_API_KEY = os.getenv("TM_API_KEY")

VENUES = [
    "Madison Square Garden",
    "Barclays Center",
    "UBS Arena",
    "Forest Hills Stadium",
    "Yankee Stadium",
    "Citi Field",
    "Kings Theatre",
    "Brooklyn Paramount",
    "Hammerstein Ballroom",
    "MetLife Stadium",
    "Radio City Music Hall",
    "Beacon Theatre",
    "Nassau Coliseum",
    "Jones Beach Theater",
    "PNC Bank Arts Center"
]

EXCLUDE_KEYWORDS = [
    "NBA", "NHL", "MLB", "NFL", "Baseball", "Hockey", "Basketball", "Football",
    "Giants", "Jets", "Knicks", "Nets", "Rangers", "Mets", "Yankees",
    "Rockette", "Tour Experience", "Seinfeld", "Seth Meyers", "St. Johns"
]

def get_events(city="New York"):
    start_date = datetime.today().strftime("%Y-%m-%dT00:00:00Z")
    end_date = (datetime.today() + timedelta(days=90)).strftime("%Y-%m-%dT00:00:00Z")

    url = (
        f"https://app.ticketmaster.com/discovery/v2/events.json"
        f"?apikey={TM_API_KEY}"
        f"&dmaId=345"
        f"&classificationName=Music"
        f"&startDateTime={start_date}"
        f"&endDateTime={end_date}"
        f"&size=200"
    )

    r = requests.get(url)
    print("Status code:", r.status_code)
    print("Response preview:", r.text[:300])

    data = r.json().get("_embedded", {}).get("events", [])
    print(f"Found {len(data)} total events")

    filtered = []

    for e in data:
        name = e["name"]
        venue = e["_embedded"]["venues"][0]["name"]
        print("Venue name from API:", venue)

        if (
            any(v.lower() in venue.lower() for v in VENUES)
            and not any(x.lower() in name.lower() for x in EXCLUDE_KEYWORDS)
        ):
            filtered.append({
                "name": name,
                "venue": venue,
                "date": e["dates"]["start"].get("localDate"),
                "url": e["url"]
            })

    print(f"Filtered down to {len(filtered)} matching venues")
    return filtered


if __name__ == "__main__":
    events = get_events()
    os.makedirs("outputs", exist_ok=True)
    filename = f"outputs/events_{datetime.today().strftime('%Y-%m-%d')}.json"

    with open(filename, "w") as f:
        json.dump(events, f, indent=2)

    print(f"✅ Saved {len(events)} events to {filename}")