#!/usr/bin/env python3
import os, requests, json, re, time
from dotenv import load_dotenv
from datetime import datetime, timedelta

# --- Setup ---
load_dotenv()
TM_API_KEY = os.getenv("TM_API_KEY")

VENUES = [
    "Madison Square Garden",
    "Barclays Center",
    "UBS Arena",
    "Forest Hills Stadium",
    "Kings Theatre",
    "Brooklyn Paramount",
    "Hammerstein Ballroom",
    "Radio City Music Hall",
    "Beacon Theatre",
    "Nassau Coliseum",
    "Jones Beach Theater",
    "PNC Bank Arts Center",
    "Yankee Stadium"
]

EXCLUDE_KEYWORDS = [
    "nba","nhl","mlb","nfl","football","basketball","baseball","hockey",
    "giants","jets","knicks","nets","rangers","islanders","college","st john",
    "tournament","series","vs","game","match","meet","championship",
    "comedy","theater","broadway","circus","family","spoken word","variety",
    "expo","conference","lecture","panel","seminar","gala",
    "suite","deposit","group","package","parking","tailgate","fee",
    "season","membership","psl","hospitality","voucher","upgrade",
    "promo","vip experience","press conference","test","internal"
]

CITY_BLACKLIST = ["miami", "boston", "chicago", "denver", "philadelphia", "dallas", "los angeles", "vegas"]

def normalize(t):
    return re.sub(r"[^a-z0-9 ]", "", str(t).lower().strip())

def looks_like_concert(name):
    name = normalize(name)
    if any(w in name for w in ["tour","live","concert","festival","band","music","show","performance"]):
        return True
    if len(name.split()) <= 6 and not any(x in name for x in EXCLUDE_KEYWORDS):
        return True
    return False

def get_all_nyc_events():
    start = datetime.today().strftime("%Y-%m-%dT00:00:00Z")
    end = (datetime.today() + timedelta(days=120)).strftime("%Y-%m-%dT00:00:00Z")

    all_events, page = [], 0
    while True:
        url = (
            f"https://app.ticketmaster.com/discovery/v2/events.json?"
            f"apikey={TM_API_KEY}&dmaId=345"
            f"&classificationName=Music"
            f"&startDateTime={start}&endDateTime={end}"
            f"&size=200&page={page}"
        )
        r = requests.get(url)
        if r.status_code != 200:
            print(f"⚠️ HTTP {r.status_code} on page {page}")
            break
        data = r.json().get("_embedded", {}).get("events", [])
        if not data:
            break
        all_events.extend(data)
        page += 1
        if page > 10:  # just in case
            break
        time.sleep(0.25)
    return all_events

def main():
    print("🎶 Collecting Ticketmaster NYC concerts...\n")
    events = get_all_nyc_events()
    print(f"Fetched {len(events)} raw NYC music events\n")

    filtered = []
    for e in events:
        name = e.get("name", "")
        venue_api = e["_embedded"]["venues"][0].get("name", "")
        v_api = normalize(venue_api)
        if not any(v.lower() in v_api for v in VENUES):
            continue
        if any(k in normalize(name) for k in EXCLUDE_KEYWORDS):
            continue
        if any(c in normalize(name) for c in CITY_BLACKLIST):
            continue
        if not looks_like_concert(name):
            continue

        filtered.append({
            "name": name.strip(),
            "venue": venue_api.strip(),
            "date": e["dates"]["start"].get("localDate"),
            "url": e.get("url", "N/A")
        })

    # Deduplicate
    seen, deduped = set(), []
    for ev in filtered:
        key = (ev["name"], ev["date"], ev["venue"])
        if key not in seen:
            seen.add(key)
            deduped.append(ev)

    # Summary
    print(f"✅ Total concerts found: {len(deduped)} across {len(VENUES)} venues\n")
    counts = {}
    for ev in deduped:
        v = ev["venue"]
        counts[v] = counts.get(v, 0) + 1
    for v, c in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"  • {v}: {c} concerts")

    os.makedirs("outputs", exist_ok=True)
    filename = f"outputs/events_{datetime.today().strftime('%Y-%m-%d')}.json"
    with open(filename, "w") as f:
        json.dump({
            "last_updated": datetime.now().isoformat(),
            "total_events": len(deduped),
            "venues_summary": counts,
            "events": deduped
        }, f, indent=2)
    print(f"\n🎟️ Saved {len(deduped)} events to {filename}\n")

if __name__ == "__main__":
    main()