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
