"""Fetch data from the official FPL API (no auth required)."""

import json

import requests

BASE_URL = "https://fantasy.premierleague.com/api"
# The FPL API rejects requests from non-browser user agents on some hosts
# (403), so present a normal browser UA.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}


def fetch_data(timeout=30, with_history=False, min_minutes=1):
    """Fetch bootstrap-static and fixtures from the FPL API.

    Returns a dict with keys ``bootstrap`` and ``fixtures`` — plus
    ``history`` (per-player per-match logs, needed by the OpenFPL engine)
    when ``with_history`` is set. History means one API call per player with
    at least ``min_minutes`` season minutes, so expect a few minutes runtime.
    """
    bootstrap = requests.get(
        f"{BASE_URL}/bootstrap-static/", headers=HEADERS, timeout=timeout
    )
    bootstrap.raise_for_status()
    fixtures = requests.get(f"{BASE_URL}/fixtures/", headers=HEADERS, timeout=timeout)
    fixtures.raise_for_status()
    data = {"bootstrap": bootstrap.json(), "fixtures": fixtures.json()}
    if with_history:
        data["history"] = fetch_history(data["bootstrap"], timeout=timeout, min_minutes=min_minutes)
    return data


def fetch_history(bootstrap, timeout=30, min_minutes=1):
    """Fetch per-match history for every (played) player via element-summary."""
    import time

    history = {}
    targets = [
        e for e in bootstrap["elements"] if (e.get("minutes") or 0) >= min_minutes
    ]
    for i, element in enumerate(targets):
        resp = requests.get(
            f"{BASE_URL}/element-summary/{element['id']}/",
            headers=HEADERS,
            timeout=timeout,
        )
        if resp.status_code == 200:
            history[str(element["id"])] = resp.json().get("history", [])
        if i % 50 == 49:
            print(f"  fetched history for {i + 1}/{len(targets)} players...")
        time.sleep(0.05)
    return history


def load_data(path):
    """Load a previously saved API snapshot from a JSON file."""
    with open(path) as f:
        data = json.load(f)
    if "bootstrap" not in data or "fixtures" not in data:
        raise ValueError(f"{path} is not an FPL-Picker data snapshot")
    return data


def save_data(data, path):
    """Save an API snapshot to a JSON file for offline use."""
    with open(path, "w") as f:
        json.dump(data, f)


def fetch_team(entry_id, bootstrap, timeout=30):
    """Fetch a manager's public team by entry (team) ID.

    Returns a dict with keys ``entry`` (manager metadata), ``picks`` (list of
    15 element ids), ``bank`` (in £m), and ``event`` (the gameweek the picks
    are from). Public pick data only exists for gameweeks whose deadline has
    passed; before that the FPL API returns 404.
    """
    entry = requests.get(f"{BASE_URL}/entry/{entry_id}/", headers=HEADERS, timeout=timeout)
    if entry.status_code == 404:
        raise ValueError(f"No FPL team found with ID {entry_id}")
    entry.raise_for_status()
    entry = entry.json()

    # Use the current gameweek if one is underway/finished, else the previous.
    event = None
    for e in bootstrap["events"]:
        if e.get("is_current"):
            event = e["id"]
    if event is None:
        finished = [e["id"] for e in bootstrap["events"] if e.get("finished")]
        event = max(finished) if finished else None
    if event is None:
        raise ValueError(
            "The season hasn't started yet, so FPL doesn't publish any team "
            "picks. Until the first deadline passes, use --lock to tell the "
            "picker which players you already have."
        )

    picks = requests.get(
        f"{BASE_URL}/entry/{entry_id}/event/{event}/picks/",
        headers=HEADERS,
        timeout=timeout,
    )
    if picks.status_code == 404:
        raise ValueError(
            f"Team {entry_id} has no public picks for GW{event} yet. Picks "
            "become public once the gameweek deadline passes."
        )
    picks.raise_for_status()
    picks = picks.json()

    bank = (picks.get("entry_history") or {}).get("bank")
    if bank is None:
        bank = entry.get("last_deadline_bank") or 0
    return {
        "entry": entry,
        "picks": [p["element"] for p in picks["picks"]],
        "bank": bank / 10.0,
        "event": event,
    }


def next_event_id(bootstrap):
    """Return the id of the next (upcoming) gameweek."""
    for event in bootstrap["events"]:
        if event.get("is_next"):
            return event["id"]
    # Fall back to the current gameweek (mid-GW) or the first one.
    for event in bootstrap["events"]:
        if event.get("is_current"):
            return event["id"]
    return bootstrap["events"][0]["id"]
