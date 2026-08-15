"""Transfer planning and squad rating for an existing team.

Reuses the squad MILP with a "keep at least 15 - N current players"
constraint, solved for N = 0..max_transfers, with point hits priced in per
the strategy rules (a hit must clear 4 points plus a risk margin over the
horizon to be recommended).
"""

from dataclasses import dataclass

from .optimizer import pick_team

HIT_COST = 4
# A paid transfer must beat its cost by this margin before we recommend it
# (see docs/research/02-winning-strategies.md rule 2).
HIT_MARGIN = 2.0


@dataclass
class TransferPlan:
    n_transfers: int
    players_out: list
    players_in: list
    selection: object  # Selection for the resulting squad
    gross_points: float  # projected points of the resulting squad
    hit_cost: int
    net_gain: float  # vs the 0-transfer baseline, after hits


@dataclass
class TeamReport:
    baseline: object  # Selection: best XI/captain with no transfers
    optimal: object  # Selection: unconstrained optimal squad (wildcard view)
    rating: float  # 0-100, current squad vs optimal
    plans: list  # TransferPlan for n = 1..max_transfers
    recommended: object  # the TransferPlan worth making, or None


def evaluate_team(
    players,
    current_ids,
    bank=0.0,
    free_transfers=1,
    max_transfers=2,
    bench_weight=0.1,
):
    """Rate an existing squad and suggest the best transfers.

    ``current_ids`` are the 15 element ids of the current squad. The budget
    for any new squad is the current squad's combined price plus ``bank``
    (current price is used as an approximation of sell price, since the FPL
    API does not expose purchase prices for other managers' teams).
    """
    by_id = {p.id: p for p in players}
    missing = [pid for pid in current_ids if pid not in by_id]
    if missing:
        raise ValueError(f"Squad contains unknown player ids: {missing}")

    budget = sum(by_id[pid].price for pid in current_ids) + bank

    baseline = pick_team(
        players,
        budget=budget,
        bench_weight=bench_weight,
        current_ids=current_ids,
        max_transfers=0,
    )
    optimal = pick_team(players, budget=budget, bench_weight=bench_weight)
    rating = round(100.0 * baseline.projected_points / optimal.projected_points, 1)

    current_set = set(current_ids)
    plans = []
    for n in range(1, max_transfers + 1):
        selection = pick_team(
            players,
            budget=budget,
            bench_weight=bench_weight,
            current_ids=current_ids,
            max_transfers=n,
        )
        new_ids = {p.id for p in selection.squad}
        moved = len(current_set - new_ids)
        hit_cost = max(0, moved - free_transfers) * HIT_COST
        plans.append(
            TransferPlan(
                n_transfers=moved,
                # Sort both sides by position then score so zip() pairs each
                # outgoing player with an incoming player of the same position.
                players_out=sorted(
                    (by_id[pid] for pid in current_set - new_ids),
                    key=lambda p: (p.position, -p.score),
                ),
                players_in=sorted(
                    (by_id[pid] for pid in new_ids - current_set),
                    key=lambda p: (p.position, -p.score),
                ),
                selection=selection,
                gross_points=selection.projected_points,
                hit_cost=hit_cost,
                net_gain=round(
                    selection.projected_points - hit_cost - baseline.projected_points, 1
                ),
            )
        )

    recommended = None
    for plan in plans:
        if plan.n_transfers == 0:
            continue
        # Free moves just need to gain; paid moves must clear the margin.
        threshold = HIT_MARGIN if plan.hit_cost else 0.0
        if plan.net_gain > threshold and (
            recommended is None or plan.net_gain > recommended.net_gain
        ):
            recommended = plan

    return TeamReport(
        baseline=baseline,
        optimal=optimal,
        rating=rating,
        plans=plans,
        recommended=recommended,
    )
