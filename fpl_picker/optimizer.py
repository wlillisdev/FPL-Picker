"""Squad optimization via integer linear programming.

One ILP simultaneously picks the 15-man squad, the starting XI, and the
captain, maximizing projected points under all FPL rules.
"""

from dataclasses import dataclass

import pulp

SQUAD_SHAPE = {"GK": 2, "DEF": 5, "MID": 5, "FWD": 3}
XI_MIN = {"GK": 1, "DEF": 3, "MID": 2, "FWD": 1}
XI_MAX = {"GK": 1, "DEF": 5, "MID": 5, "FWD": 3}
MAX_PER_CLUB = 3


@dataclass
class Selection:
    squad: list  # all 15 Players
    starting_xi: list
    bench: list  # ordered: GK first, then outfield by score desc
    captain: object
    vice_captain: object
    total_cost: float
    projected_points: float  # XI + captain double, over the horizon


def pick_team(
    players,
    budget=100.0,
    bench_weight=0.1,
    locked=(),
    excluded=(),
    current_ids=None,
    max_transfers=None,
    club_caps=None,
):
    """Pick the optimal legal squad from a list of scored Players.

    ``locked``/``excluded`` are collections of player ids to force in or out.
    When ``current_ids`` (an existing 15-man squad) and ``max_transfers`` are
    given, the solver may swap at most that many players out of the current
    squad — this is the transfer-planning mode.
    Raises ValueError if the problem is infeasible (e.g. budget too small).
    """
    locked = set(locked)
    excluded = set(excluded)
    pool = [p for p in players if p.id not in excluded]

    prob = pulp.LpProblem("fpl_picker", pulp.LpMaximize)
    in_squad = {p.id: pulp.LpVariable(f"squad_{p.id}", cat="Binary") for p in pool}
    starter = {p.id: pulp.LpVariable(f"start_{p.id}", cat="Binary") for p in pool}
    captain = {p.id: pulp.LpVariable(f"cap_{p.id}", cat="Binary") for p in pool}

    # Objective: starters at full value, captain counted double, bench at a
    # small weight so it still prefers playable cheap enablers.
    prob += pulp.lpSum(
        p.score * starter[p.id]
        + p.score * captain[p.id]
        + p.score * bench_weight * (in_squad[p.id] - starter[p.id])
        for p in pool
    )

    prob += pulp.lpSum(p.price * in_squad[p.id] for p in pool) <= budget
    prob += pulp.lpSum(starter.values()) == 11
    prob += pulp.lpSum(captain.values()) == 1

    for position, count in SQUAD_SHAPE.items():
        members = [p for p in pool if p.position == position]
        prob += pulp.lpSum(in_squad[p.id] for p in members) == count
        prob += pulp.lpSum(starter[p.id] for p in members) >= XI_MIN[position]
        prob += pulp.lpSum(starter[p.id] for p in members) <= XI_MAX[position]

    club_caps = club_caps or {}
    for team_id in {p.team_id for p in pool}:
        cap = min(MAX_PER_CLUB, club_caps.get(team_id, MAX_PER_CLUB))
        prob += (
            pulp.lpSum(in_squad[p.id] for p in pool if p.team_id == team_id)
            <= cap
        )

    for p in pool:
        prob += starter[p.id] <= in_squad[p.id]
        prob += captain[p.id] <= starter[p.id]
        if p.id in locked:
            prob += in_squad[p.id] == 1

    if current_ids is not None and max_transfers is not None:
        keep = [in_squad[pid] for pid in current_ids if pid in in_squad]
        prob += pulp.lpSum(keep) >= 15 - max_transfers

    status = prob.solve(pulp.PULP_CBC_CMD(msg=False))
    if pulp.LpStatus[status] != "Optimal":
        raise ValueError(
            f"No legal squad found (solver status: {pulp.LpStatus[status]}). "
            "Check the budget and any --lock/--exclude constraints."
        )

    squad = [p for p in pool if in_squad[p.id].value() == 1]
    return build_selection(squad)


def _lineup_metric(squad):
    """Next-GW projections drive lineups when available; horizon otherwise
    (synthetic/test players may not carry next_score)."""
    if any(p.next_score > 0 for p in squad):
        return lambda p: p.next_score
    return lambda p: p.score


def build_selection(squad):
    """Choose XI/captain/bench from a 15-man squad by NEXT-gameweek points.

    Squad composition and transfers are horizon decisions, but who starts
    this week is a fixture-specific decision — a player facing the league's
    best attack next match should be benchable even if his 5-week run is
    good, and a blank-gameweek player (next_score 0) benches automatically.
    Exact search over legal formations (1 GK, 3-5 DEF, 2-5 MID, 1-3 FWD).
    """
    metric = _lineup_metric(squad)
    by_pos = {pos: [] for pos in SQUAD_SHAPE}
    for p in squad:
        by_pos[p.position].append(p)
    for pos in by_pos:
        by_pos[pos].sort(key=metric, reverse=True)

    best_xi, best_value = None, None
    for n_def in range(XI_MIN["DEF"], XI_MAX["DEF"] + 1):
        for n_mid in range(XI_MIN["MID"], XI_MAX["MID"] + 1):
            n_fwd = 10 - n_def - n_mid
            if not (XI_MIN["FWD"] <= n_fwd <= XI_MAX["FWD"]):
                continue
            xi = (
                by_pos["GK"][:1]
                + by_pos["DEF"][:n_def]
                + by_pos["MID"][:n_mid]
                + by_pos["FWD"][:n_fwd]
            )
            value = sum(metric(p) for p in xi)
            if best_value is None or value > best_value:
                best_xi, best_value = xi, value

    xi = best_xi
    cap = max(xi, key=metric)
    vice = max((p for p in xi if p.id != cap.id), key=metric)
    bench = [p for p in squad if p not in xi]
    bench.sort(key=lambda p: (p.position != "GK", -metric(p)))

    return Selection(
        squad=squad,
        starting_xi=sorted(
            xi,
            key=lambda p: (["GK", "DEF", "MID", "FWD"].index(p.position), -metric(p)),
        ),
        bench=bench,
        captain=cap,
        vice_captain=vice,
        total_cost=round(sum(p.price for p in squad), 1),
        projected_points=round(sum(p.score for p in xi) + cap.score, 1),
    )
