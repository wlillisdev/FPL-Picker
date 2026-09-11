"""Scouting: fixture runs and players about to strike form.

Two questions the squad optimizer never answers:
  1. Whose fixtures turn good over the next few gameweeks?
  2. Who is creating the chances that haven't become points yet?

The second is the researched edge (docs/research/07-edge-playbook.md): shot
and chance VOLUME predicts future returns, and ownership follows returns with
a 1-3 gameweek lag — so the buy window is the week the underlying numbers
turn, not the week the hauls print.
"""

from .api import next_event_id
from .scoring import POSITIONS, fixture_multipliers


def _f(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def fixture_runs(data, horizon=6):
    """Rank every team by fixture ease over the next `horizon` gameweeks.

    Uses the same multipliers as the scoring model, so doubles count twice
    and blanks count zero. Returns rows sorted easiest-first.
    """
    bootstrap = data["bootstrap"]
    fixtures = data["fixtures"]
    start = next_event_id(bootstrap)
    teams = {t["id"]: t for t in bootstrap["teams"]}

    opponents = {}
    for f in fixtures:
        event = f.get("event")
        if event is None or not (start <= event < start + horizon):
            continue
        h, a = f.get("team_h"), f.get("team_a")
        if h in teams and a in teams:
            opponents.setdefault(h, []).append((event, teams[a]["short_name"], "H"))
            opponents.setdefault(a, []).append((event, teams[h]["short_name"], "A"))

    rows = []
    for team in bootstrap["teams"]:
        mults = fixture_multipliers(fixtures, team["id"], start, horizon)
        run = sorted(opponents.get(team["id"], []))
        rows.append(
            {
                "team": team["short_name"],
                "team_id": team["id"],
                "ease": sum(mults),
                "fixtures": [f"{name}({venue})" for _, name, venue in run],
            }
        )
    rows.sort(key=lambda r: -r["ease"])
    return rows


def strike_candidates(data, players, horizon=6, max_ownership=100.0, min_minutes=180):
    """Players whose underlying numbers lead their output.

    Ranked by expected goal involvements per 90 (the volume signal that
    actually predicts), scaled by fixture ease over the horizon and by how
    reliably they play. `gap` shows season expected involvements minus actual
    goals+assists — context, not the ranking (finishing luck regresses, but
    the chances keep coming).
    """
    bootstrap = data["bootstrap"]
    ease = {r["team_id"]: r["ease"] for r in fixture_runs(data, horizon)}
    average_ease = sum(ease.values()) / len(ease) if ease else 1.0
    by_id = {p.id: p for p in players}

    finished = {}
    for f in data["fixtures"]:
        if f.get("finished"):
            for tid in (f.get("team_h"), f.get("team_a")):
                finished[tid] = finished.get(tid, 0) + 1

    rows = []
    for element in bootstrap["elements"]:
        position = POSITIONS.get(element["element_type"])
        if position is None or element.get("status") in ("i", "s", "u", "n"):
            continue
        minutes = element.get("minutes") or 0
        if minutes < min_minutes:
            continue
        ownership = _f(element.get("selected_by_percent"))
        if ownership > max_ownership:
            continue

        player = by_id.get(element["id"])
        if player is None:
            continue

        xgi90 = _f(element.get("expected_goal_involvements_per_90"))
        if xgi90 <= 0:
            continue
        games = finished.get(element["team"], 0)
        minutes_share = min(minutes / (90.0 * games), 1.0) if games else 0.0
        fixture_factor = (ease.get(element["team"], average_ease) / average_ease) if average_ease else 1.0

        gap = _f(element.get("expected_goal_involvements")) - (
            (element.get("goals_scored") or 0) + (element.get("assists") or 0)
        )

        starts = element.get("starts")
        start_share = (starts / games) if (starts is not None and games) else None
        # Minutes dominate: a great per-90 rate from a 25-minute cameo is
        # worth nothing. Squaring the share punishes rotation hard, and a
        # player who has started every game is untouched.
        reliability = minutes_share**2 if minutes_share else 0.0

        rows.append(
            {
                "player": player,
                "xgi90": xgi90,
                "minutes": minutes,
                "starts": starts,
                "start_share": start_share,
                "minutes_share": minutes_share,
                "fixture_factor": fixture_factor,
                "ownership": ownership,
                "gap": gap,
                "form": _f(element.get("form")),
                "points": element.get("total_points") or 0,
                "ppg": _f(element.get("points_per_game")),
                "score": xgi90 * fixture_factor * reliability,
            }
        )
    rows.sort(key=lambda r: -r["score"])
    return rows


def print_scout_report(data, players, horizon=6, max_ownership=100.0, limit=12):
    runs = fixture_runs(data, horizon)
    print(f"\n=== Fixture runs, next {horizon} gameweeks (easiest first) ===")
    for row in runs[:6]:
        print(f"  {row['team']:<4} {row['ease']:>5.2f}  {' '.join(row['fixtures'])}")
    print("  ...")
    for row in runs[-4:]:
        print(f"  {row['team']:<4} {row['ease']:>5.2f}  {' '.join(row['fixtures'])}")

    rows = strike_candidates(
        data, players, horizon=horizon, max_ownership=max_ownership
    )
    print(
        f"\n=== About to strike: chance volume leading output "
        f"(ownership <= {max_ownership:.0f}%) ==="
    )
    print(
        "  Ranked by expected involvements per 90 x fixture ease x minutes\n"
        "  reliability. CHECK THE MINS COLUMN FIRST: a great per-90 rate off\n"
        "  the bench is worth nothing, and a low-owned player with elite\n"
        "  numbers is usually low-owned because he does not start."
    )
    header = (
        f"  {'Player':<18} {'Pos':<4} {'Team':<5} {'Price':>6} {'Pts':>4} "
        f"{'PPG':>5} {'Form':>5} {'xGI/90':>7} {'Mins':>5} {'Starts':>7} "
        f"{'Own%':>6} {'Gap':>6}  Fixtures"
    )
    print(header)
    for row in rows[:limit]:
        p = row["player"]
        starts = "?" if row["starts"] is None else str(row["starts"])
        share = row["start_share"]
        starts_col = starts if share is None else f"{starts} ({share:.0%})"
        print(
            f"  {p.name:<18} {p.position:<4} {p.team:<5} £{p.price:>4.1f}m "
            f"{row['points']:>4} {row['ppg']:>5.1f} {row['form']:>5.1f} "
            f"{row['xgi90']:>7.2f} {row['minutes']:>5} {starts_col:>7} "
            f"{row['ownership']:>5.1f}% {row['gap']:>+6.1f}  {p.next_fixture}"
        )
