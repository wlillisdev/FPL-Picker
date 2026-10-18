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

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fpl_picker import api  # noqa: E402

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
    if not bootstrap.get("elements"):
        sys.exit("error: bootstrap-static came back without any players")

    os.makedirs(OUT_DIR, exist_ok=True)
    write_json(bootstrap, os.path.join(OUT_DIR, "bootstrap.json"))
    write_json(fixtures, os.path.join(OUT_DIR, "fixtures.json"))

    next_event = api.next_event_id(bootstrap)
    priced = [e["now_cost"] / 10.0 for e in bootstrap["elements"]]
    print(
        f"wrote {len(bootstrap['elements'])} players and {len(fixtures)} "
        f"fixtures to {OUT_DIR}"
    )
    print(
        f"next gameweek: {next_event} | price range "
        f"£{min(priced):.1f}m-£{max(priced):.1f}m"
    )


if __name__ == "__main__":
    main()
