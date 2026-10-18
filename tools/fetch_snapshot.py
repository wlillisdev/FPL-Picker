"""Fetch the FPL API and write it to data/ for offline use.

The FPL API refuses requests from a lot of hosts (PythonAnywhere free
accounts, cloud containers and CI runners behind policy proxies all get 403),
which leaves the only authoritative source of prices, ownership, minutes and
starts out of reach from the machines we actually work on. GitHub's hosted
runners are not behind such a proxy, so a scheduled workflow can fetch the
data and commit it; everywhere else then reads it with ``git pull``.

Run it by hand with::

    python tools/fetch_snapshot.py

and then use the files it writes::

    python -m fpl_picker --from-files data/bootstrap.json data/fixtures.json
    python tools/prices.py data/bootstrap.json Haaland Saka

JSON is written sorted and indented rather than minified. That costs disk but
makes each commit a small diff instead of a new multi-megabyte blob, which
matters when this runs on a schedule for a whole season.
"""

import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fpl_picker import api  # noqa: E402

# A full bootstrap carries every player in the game. Anything far below this
# is a truncated or error response, and overwriting a good snapshot with one
# is worse than having no new data at all.
MIN_PLAYERS = 400
MIN_FIXTURES = 300

OUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data"
)


def write_json(obj, path):
    with open(path, "w") as f:
        json.dump(obj, f, indent=1, sort_keys=True)
        f.write("\n")


def main():
    print("Fetching bootstrap-static and fixtures from the FPL API...")
    try:
        data = api.fetch_data()
    except Exception as exc:  # noqa: BLE001 - surface the reason in CI logs
        sys.exit(f"error: could not fetch the FPL API: {exc}")

    bootstrap, fixtures = data["bootstrap"], data["fixtures"]
    players = bootstrap.get("elements") or []
    if len(players) < MIN_PLAYERS or len(fixtures) < MIN_FIXTURES:
        sys.exit(
            f"error: implausible payload ({len(players)} players, "
            f"{len(fixtures)} fixtures) — keeping the previous snapshot"
        )

    os.makedirs(OUT_DIR, exist_ok=True)
    write_json(bootstrap, os.path.join(OUT_DIR, "bootstrap.json"))
    write_json(fixtures, os.path.join(OUT_DIR, "fixtures.json"))

    events = bootstrap.get("events") or []
    upcoming = next((e for e in events if e.get("is_next")), {})
    write_json(
        {
            "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "current_event": next(
                (e["id"] for e in events if e.get("is_current")), None
            ),
            "next_event": upcoming.get("id"),
            "next_deadline": upcoming.get("deadline_time"),
            "player_count": len(players),
            "fixture_count": len(fixtures),
            "source": api.BASE_URL,
        },
        os.path.join(OUT_DIR, "meta.json"),
    )

    priced = [e["now_cost"] / 10.0 for e in players]
    print(f"wrote {len(players)} players and {len(fixtures)} fixtures to {OUT_DIR}")
    print(
        f"next gameweek: {upcoming.get('id') or api.next_event_id(bootstrap)} "
        f"(deadline {upcoming.get('deadline_time') or 'unknown'}) | "
        f"price range £{min(priced):.1f}m-£{max(priced):.1f}m"
    )


if __name__ == "__main__":
    main()
