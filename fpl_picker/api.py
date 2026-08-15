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


def fetch_data(timeout=30):
    """Fetch bootstrap-static and fixtures from the FPL API.

    Returns a dict with keys ``bootstrap`` and ``fixtures``.
    """
    bootstrap = requests.get(
        f"{BASE_URL}/bootstrap-static/", headers=HEADERS, timeout=timeout
    )
    bootstrap.raise_for_status()
    fixtures = requests.get(f"{BASE_URL}/fixtures/", headers=HEADERS, timeout=timeout)
    fixtures.raise_for_status()
    return {"bootstrap": bootstrap.json(), "fixtures": fixtures.json()}


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
