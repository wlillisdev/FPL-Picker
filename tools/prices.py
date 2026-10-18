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
    stripped = unicodedata.normalize("NFKD", text.replace("ß", "ss"))
    return "".join(c for c in stripped if not unicodedata.combining(c)).lower()


def candidate_names(element):
    first = element.get("first_name", "")
    second = element.get("second_name", "")
    return {
        fold(element.get("web_name", "")),
        fold(second),
        fold(f"{first} {second}".strip()),
    }


def select(elements, wanted):
    """Pick one element per requested name, preferring the closest match.

    Substring matching alone is far too loose on a 700-player list: "Saka"
    also finds Sakamoto and Wan-Bissaka, which silently corrupts the squad
    total. So try exact name matches first and only fall back to a substring
    search for the names that found nothing.
    """
    if not wanted:
        return [e for e in elements if (e.get("starts") or 0) > 0], []

    chosen, missing = {}, []
    for want in wanted:
        exact = [e for e in elements if want in candidate_names(e)]
        partial = [
            e for e in elements if any(want in name for name in candidate_names(e))
        ]
        found = exact or partial
        if not found:
            missing.append(want)
            continue
        for element in found:
            chosen[element["id"]] = element
    return list(chosen.values()), missing


def main(argv):
    if not argv:
        sys.exit(__doc__)
    with open(argv[0]) as f:
        bootstrap = json.load(f)
    if "elements" not in bootstrap:
        sys.exit(f"error: {argv[0]} is not the bootstrap-static response")

    wanted = [fold(name) for name in argv[1:]]
    teams = {t["id"]: t["short_name"] for t in bootstrap["teams"]}

    rows, missing = select(bootstrap["elements"], wanted)
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
        if missing:
            print(f"warning: no player matched {', '.join(missing)}")
        if len(rows) > len(wanted):
            print(
                f"warning: asked for {len(wanted)} names but matched "
                f"{len(rows)} players, so the total is too high — narrow the "
                "ambiguous name to a full name"
            )


if __name__ == "__main__":
    main(sys.argv[1:])
