#!/usr/bin/env python3
"""
NYC Ticketmaster collector (v9) — fetch → filter → sort → dedupe → summarize → save → (optional) email

- Chronological ordering by Ticketmaster localDate (YYYY-MM-DD)
- Non-fatal HTTP errors (logs and continues a few retries)
- Clear separation of steps and concise console telemetry
"""

import os
import json
import re
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple, Optional

import requests
from dotenv import load_dotenv

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
    "Yankee Stadium",
    "Citi Field",
]

EXCLUDE_KEYWORDS = [
    "nba", "nhl", "mlb", "nfl", "football", "basketball", "baseball", "hockey",
    "giants", "jets", "knicks", "nets", "rangers", "islanders", "college", "st john",
    "tournament", "series", "vs", "game", "match", "meet", "championship",
    "comedy", "theater", "broadway", "circus", "family", "spoken word", "variety",
    "expo", "conference", "lecture", "panel", "seminar", "gala",
    "suite", "deposit", "group", "package", "parking", "tailgate", "fee",
    "season", "membership", "psl", "hospitality", "voucher", "upgrade",
    "promo", "vip experience", "press conference", "test", "internal",
]

CITY_BLACKLIST = [
    "miami", "boston", "chicago", "denver", "philadelphia", "dallas",
    "los angeles", "vegas",
]


# ---------- Helpers ----------

def normalize(t: Any) -> str:
    return re.sub(r"[^a-z0-9 ]", "", str(t).lower().strip())


def looks_like_concert(name: str) -> bool:
    name_n = normalize(name)
    if any(w in name_n for w in ["tour", "live", "concert", "festival", "band", "music", "show", "performance"]):
        return True
    # Heuristic: short-ish titles that don't hit sports/exclude words
    if len(name_n.split()) <= 6 and not any(x in name_n for x in EXCLUDE_KEYWORDS):
        return True
    return False


def _tm_time_window(days_ahead: int = 120) -> Tuple[str, str]:
    start = datetime.today().strftime("%Y-%m-%dT00:00:00Z")
    end = (datetime.today() + timedelta(days=days_ahead)).strftime("%Y-%m-%dT00:00:00Z")
    return start, end


def get_all_nyc_events(max_pages: int = 10, page_size: int = 200) -> List[Dict[str, Any]]:
    """Fetch up to max_pages of 'Music' events for NYC DMA (345)."""
    if not TM_API_KEY:
        raise RuntimeError("TM_API_KEY is not set in environment")

    start, end = _tm_time_window()
    all_events: List[Dict[str, Any]] = []
    page = 0

    print("🎶 Collecting Ticketmaster NYC concerts...\n")

    while page < max_pages:
        url = (
            "https://app.ticketmaster.com/discovery/v2/events.json"
            f"?apikey={TM_API_KEY}"
            "&dmaId=345"
            "&classificationName=Music"
            f"&startDateTime={start}&endDateTime={end}"
            f"&size={page_size}&page={page}"
        )

        # Simple retry for transient errors
        attempt, last_status = 0, None
        while attempt < 3:
            resp = requests.get(url, timeout=20)
            last_status = resp.status_code
            if resp.status_code == 200:
                break
            attempt += 1
            print(f"⚠️ HTTP {resp.status_code} on page {page} (attempt {attempt}/3)")
            time.sleep(0.6 * attempt)

        if last_status != 200:
            # Non-200 after retries: stop pagination but keep what we have
            print(f"⚠️ Stopping at page {page} due to repeated HTTP {last_status}")
            break

        events = resp.json().get("_embedded", {}).get("events", [])
        if not events:
            # No more data
            break

        all_events.extend(events)
        page += 1
        time.sleep(0.25)  # be nice

    print(f"Fetched {len(all_events)} raw NYC music events\n")
    return all_events


def filter_events(raw_events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Filter to target venues, exclude non-concert content, and shape fields."""
    target_norm = [normalize(v) for v in VENUES]
    filtered: List[Dict[str, Any]] = []

    for e in raw_events:
        name = e.get("name", "") or ""
        venues_emb = e.get("_embedded", {}).get("venues", []) or []
        if not venues_emb:
            continue

        venue_api = (venues_emb[0].get("name") or "").strip()
        v_api_norm = normalize(venue_api)

        # Venue allow-list
        if not any(v in v_api_norm for v in target_norm):
            continue

        # Keyword excludes
        n_norm = normalize(name)
        if any(k in n_norm for k in EXCLUDE_KEYWORDS):
            continue
        if any(c in n_norm for c in CITY_BLACKLIST):
            continue

        # Concert-ish heuristic
        if not looks_like_concert(name):
            continue

        # Dates
        date_str = (e.get("dates", {}).get("start", {}) or {}).get("localDate")
        url = e.get("url", "N/A")

        filtered.append({
            "name": name.strip(),
            "venue": venue_api,
            "date": date_str,   # YYYY-MM-DD
            "url": url,
        })

    return filtered


def _parse_evt_date(evt: Dict[str, Any]) -> datetime:
    """Parse YYYY-MM-DD; push bad/missing to bottom by returning datetime.max."""
    raw = evt.get("date")
    if not raw:
        return datetime.max
    try:
        return datetime.strptime(raw, "%Y-%m-%d")
    except Exception:
        return datetime.max


def sort_events(events: List[Dict[str, Any]]) -> None:
    """Sort in place ascending by local date."""
    events.sort(key=_parse_evt_date)


def dedupe_events(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen, out = set(), []
    for ev in events:
        key = (ev.get("name"), ev.get("date"), ev.get("venue"))
        if key in seen:
            continue
        seen.add(key)
        out.append(ev)
    return out


def summarize_by_venue(events: List[Dict[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for ev in events:
        v = ev.get("venue", "Unknown")
        counts[v] = counts.get(v, 0) + 1
    return counts


def write_output(events: List[Dict[str, Any]]) -> str:
    os.makedirs("outputs", exist_ok=True)
    fname = f"outputs/events_{datetime.today().strftime('%Y-%m-%d')}.json"
    with open(fname, "w") as f:
        json.dump({
            "last_updated": datetime.now().isoformat(),
            "total_events": len(events),
            "venues_summary": summarize_by_venue(events),
            "events": events,
        }, f, indent=2)
    return fname


# ---------- Main ----------

def main() -> List[Dict[str, Any]]:
    # 1) Fetch
    raw = get_all_nyc_events()

    # 2) Filter/shape
    filtered = filter_events(raw)

    # 3) Sort (chronological)
    sort_events(filtered)

    # Quick telemetry for ordering
    if filtered:
        first = _parse_evt_date(filtered[0]).date() if filtered[0].get("date") else "N/A"
        last = _parse_evt_date(filtered[-1]).date() if filtered[-1].get("date") else "N/A"
        print(f"📅 Sorted {len(filtered)} events chronologically: {first} → {last}")

    # 4) Dedupe
    deduped = dedupe_events(filtered)

    # 5) Summary
    print(f"\n✅ Total concerts found: {len(deduped)} across {len(VENUES)} venues\n")
    counts = summarize_by_venue(deduped)
    for v, c in sorted(counts.items(), key=lambda x: (-x[1], x[0])):
        print(f"  • {v}: {c} concerts")

    # 6) Persist
    out_path = write_output(deduped)
    print(f"\n🎟️ Saved {len(deduped)} events to {out_path}\n")

    return deduped


if __name__ == "__main__":
    try:
        events = main()
    except Exception as ex:
        # Keep a concise error but don't hide the exception during development
        raise

    # Optional: email handoff if your sender is wired up
    if events:
        try:
            # Keep your existing signature: send_email_dynamic(events, run_date)
            from send_email import send_email_dynamic  # type: ignore
            run_date = datetime.now().strftime("%Y-%m-%d")
            send_email_dynamic(events, run_date)
        except ImportError:
            # Sender not present; skip silently
            pass
        except Exception as e:
            # Don't fail the collector if email step errors
            print(f"⚠️ Email step failed: {e}")