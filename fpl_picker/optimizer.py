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


def pick_team(players, budget=100.0, bench_weight=0.1, locked=(), excluded=()):
    """Pick the optimal legal squad from a list of scored Players.

    ``locked``/``excluded`` are collections of player ids to force in or out.
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

    for team_id in {p.team_id for p in pool}:
        prob += (
            pulp.lpSum(in_squad[p.id] for p in pool if p.team_id == team_id)
            <= MAX_PER_CLUB
        )

    for p in pool:
        prob += starter[p.id] <= in_squad[p.id]
        prob += captain[p.id] <= starter[p.id]
        if p.id in locked:
            prob += in_squad[p.id] == 1

    status = prob.solve(pulp.PULP_CBC_CMD(msg=False))
    if pulp.LpStatus[status] != "Optimal":
        raise ValueError(
            f"No legal squad found (solver status: {pulp.LpStatus[status]}). "
            "Check the budget and any --lock/--exclude constraints."
        )

    squad = [p for p in pool if in_squad[p.id].value() == 1]
    xi = [p for p in pool if starter[p.id].value() == 1]
    cap = next(p for p in pool if captain[p.id].value() == 1)
    vice = max((p for p in xi if p.id != cap.id), key=lambda p: p.score)

    bench = [p for p in squad if p not in xi]
    bench.sort(key=lambda p: (p.position != "GK", -p.score))

    return Selection(
        squad=squad,
        starting_xi=sorted(
            xi, key=lambda p: (["GK", "DEF", "MID", "FWD"].index(p.position), -p.score)
        ),
        bench=bench,
        captain=cap,
        vice_captain=vice,
        total_cost=round(sum(p.price for p in squad), 1),
        projected_points=round(sum(p.score for p in xi) + cap.score, 1),
    )
