#!/usr/bin/env python3
"""
PeteSheet Collector v9.2 Balanced
==================================
Optimized for yield + precision:
 - Includes Music, Arts & Theatre, Undefined classifications
 - Keeps short event names (<8 words) unless clearly sports
 - Still excludes Knicks, Rangers, Nets, Islanders, Rockettes
 - Adds color-coded console telemetry and skip stats
"""

import os
import json
import re
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
import requests
from dotenv import load_dotenv

# --- Setup ---
load_dotenv()
TM_API_KEY = os.getenv("TM_API_KEY")

VENUES = [
    "Madison Square Garden",
    "The Theater at Madison Square Garden",
    "Hulu Theater at MSG"
    "Madison Square Garden Theater"
    "Barclays Center",
    "UBS Arena",
    "Forest Hills Stadium",
    "Kings Theatre",
    "Brooklyn Paramount",
    "Hammerstein Ballroom",
    "Radio City Music Hall",
    "Beacon Theatre",
    "Beacon Theater",
    "Nassau Coliseum",
    "Jones Beach Theater",
    "PNC Bank Arts Center",
    "Yankee Stadium",
    "Citi Field",
]

SPORT_KEYWORDS = [
    "nba","nhl","mlb","nfl","football","basketball","baseball","hockey",
    "giants","jets","knicks","nets","rangers","islanders","mets","yankees",
    "match","vs","tournament","championship","playoff", "john oliver", 
    "rockettes", "jerry seinfeld", "Cirque du Soleil"
]

CITY_BLACKLIST = [
    "miami","boston","chicago","denver","philadelphia","dallas",
    "los angeles","vegas"
]

def normalize(t:str)->str:
    return re.sub(r"[^a-z0-9 ]","",t.lower().strip())

def _tm_time_window(days_ahead:int=180)->Tuple[str,str]:
    start=datetime.today().strftime("%Y-%m-%dT00:00:00Z")
    end=(datetime.today()+timedelta(days=days_ahead)).strftime("%Y-%m-%dT00:00:00Z")
    return start,end

def get_all_nyc_events(max_pages:int=10,page_size:int=200)->List[Dict[str,Any]]:
    if not TM_API_KEY:
        raise RuntimeError("TM_API_KEY not set in .env")
    start,end=_tm_time_window()
    all_events=[]
    print("\033[94m🎶 Collecting Ticketmaster NYC events...\033[0m\n")
    for classification in ["Music","Arts & Theatre","Undefined", "Comedy"]:
        for page in range(max_pages):
            url=(f"https://app.ticketmaster.com/discovery/v2/events.json?"
                 f"apikey={TM_API_KEY}&dmaId=345&classificationName={classification}"
                 f"&startDateTime={start}&endDateTime={end}&size={page_size}&page={page}")
            r=requests.get(url,timeout=20)
            if r.status_code!=200: 
                print(f"\033[91m⚠️ HTTP {r.status_code} on page {page} ({classification})\033[0m")
                break
            ev=r.json().get("_embedded",{}).get("events",[])
            if not ev: break
            all_events.extend(ev)
            time.sleep(0.2)
    print(f"Fetched {len(all_events)} raw NYC events\n")
    return all_events

def looks_like_music_event(name:str)->bool:
    n=normalize(name)
    if any(w in n for w in ["concert","tour","band","live","music","orchestra","festival","tribute","ensemble","holiday","show"]):
        return True
    # allow short names if not sports
    if len(n.split())<=8 and not any(s in n for s in SPORT_KEYWORDS):
        return True
    return False

def filter_events(raw:List[Dict[str,Any]])->List[Dict[str,Any]]:
    norm_targets=[normalize(v) for v in VENUES]
    filtered=[];skipped_venue=skipped_sport=skipped_city=0
    for e in raw:
        name=e.get("name",""); venues=e.get("_embedded",{}).get("venues",[])
        if not venues: continue
        venue_name=venues[0].get("name","")
        v_norm=normalize(venue_name); n_norm=normalize(name)
        if not any(v in v_norm or v_norm in v for v in norm_targets):
            skipped_venue+=1; continue
        if any(s in n_norm for s in SPORT_KEYWORDS):
            skipped_sport+=1; continue
        if any(c in n_norm for c in CITY_BLACKLIST):
            skipped_city+=1; continue
        if not looks_like_music_event(name):
            continue
        date=e.get("dates",{}).get("start",{}).get("localDate")
        filtered.append({"name":name.strip(),"venue":venue_name.strip(),"date":date,"url":e.get("url","")})
    print(f"\033[92m✔️ Filtered {len(filtered)} events ({skipped_venue} venue skips, {skipped_sport} sports skips)\033[0m")
    return filtered

def sort_events(events:List[Dict[str,Any]]): 
    events.sort(key=lambda e:e.get("date") or "9999-12-31")

def dedupe_events(events:List[Dict[str,Any]])->List[Dict[str,Any]]:
    seen=set(); out=[]
    for e in events:
        key=(e["name"],e["date"],e["venue"])
        if key not in seen:
            seen.add(key); out.append(e)
    return out

def summarize(events:List[Dict[str,Any]]):
    counts={}
    for e in events: counts[e["venue"]]=counts.get(e["venue"],0)+1
    for v,c in sorted(counts.items(),key=lambda x:(-x[1],x[0])):
        print(f"  • {v}: {c} shows")
    return counts

def write_output(events:List[Dict[str,Any]])->str:
    os.makedirs("outputs",exist_ok=True)
    fname=f"outputs/events_{datetime.now().strftime('%Y-%m-%d')}.json"
    with open(fname,"w") as f: json.dump({"events":events},f,indent=2)
    print(f"\n🎟️ Saved {len(events)} events → {fname}")
    return fname

def main()->List[Dict[str,Any]]:
    raw=get_all_nyc_events()
    filtered=filter_events(raw)
    sort_events(filtered)
    deduped=dedupe_events(filtered)
    print(f"\n✅ Total concerts found: {len(deduped)} across {len(VENUES)} venues\n")
    summarize(deduped)
    write_output(deduped)
    return deduped

if __name__ == "__main__":
    try:
        events = main()
    except Exception as e:
        raise

    if events:
        try:
            from send_email_gmail import send_email_gmail
            run_date = datetime.now().strftime("%Y-%m-%d")
            send_email_gmail(events, run_date)
        except Exception as e:
            print(f"⚠️ Email skipped: {e}")
