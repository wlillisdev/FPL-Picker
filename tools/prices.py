"""Print exact FPL prices and stats for named players from a bootstrap file.

The FPL API blocks some hosts (PythonAnywhere free accounts, cloud servers),
so download the bootstrap response by hand in a browser:

    https://fantasy.premierleague.com/api/bootstrap-static/

then run:

    python tools/prices.py bootstrap.json Tzolakis Leno Tarkowski ...

With no names it prints every player who has started at least once, so you
can pipe it into grep. Names are matched case-insensitively against the FPL
web name, the full name, and the surname, so "Gonzalo", "Garcia" and
"Muharemovic" all work without accents.
"""

import json
import sys
import unicodedata

POSITIONS = {1: "GK", 2: "DEF", 3: "MID", 4: "FWD"}


def fold(text):
    """Lowercase and strip accents so 'Muharemović' matches 'muharemovic'."""
    stripped = unicodedata.normalize("NFKD", text)
    return "".join(c for c in stripped if not unicodedata.combining(c)).lower()


def candidate_names(element):
    first = element.get("first_name", "")
    second = element.get("second_name", "")
    return {
        fold(element.get("web_name", "")),
        fold(second),
        fold(f"{first} {second}".strip()),
    }


def matches(element, wanted):
    if not wanted:
        return (element.get("starts") or 0) > 0
    names = candidate_names(element)
    return any(w in name for w in wanted for name in names if name)


def main(argv):
    if not argv:
        sys.exit(__doc__)
    with open(argv[0]) as f:
        bootstrap = json.load(f)
    if "elements" not in bootstrap:
        sys.exit(f"error: {argv[0]} is not the bootstrap-static response")

    wanted = [fold(name) for name in argv[1:]]
    teams = {t["id"]: t["short_name"] for t in bootstrap["teams"]}

    rows = [e for e in bootstrap["elements"] if matches(e, wanted)]
    rows.sort(key=lambda e: -e["now_cost"])

    header = (
        f"{'Player':18} {'Club':5} {'Pos':4} {'Price':>6} {'Pts':>4} "
        f"{'Mins':>5} {'Starts':>6} {'Own%':>6} {'Flag':>5}"
    )
    print(header)
    print("-" * len(header))
    total = 0
    for e in rows:
        chance = e.get("chance_of_playing_next_round")
        flag = "-" if chance is None or chance == 100 else f"{chance}%"
        total += e["now_cost"]
        print(
            f"{e['web_name']:18} {teams[e['team']]:5} "
            f"{POSITIONS[e['element_type']]:4} "
            f"{e['now_cost'] / 10:6.1f} {e['total_points']:4} "
            f"{e['minutes']:5} {e.get('starts') or 0:6} "
            f"{e['selected_by_percent']:>6} {flag:>5}"
        )

    if wanted:
        print("-" * len(header))
        print(f"{len(rows)} players, total {total / 10:.1f}m")
        if len(rows) != len(wanted):
            print(
                f"warning: asked for {len(wanted)} names but matched "
                f"{len(rows)} players — check for duplicates or typos"
            )


if __name__ == "__main__":
    main(sys.argv[1:])
