from collections import Counter

import pytest

from fpl_picker import scoring
from fpl_picker.optimizer import MAX_PER_CLUB, SQUAD_SHAPE, XI_MAX, XI_MIN, pick_team


@pytest.fixture(scope="module")
def players(snapshot):
    return scoring.score_players(snapshot, horizon=5)


def test_selection_obeys_all_fpl_rules(players):
    selection = pick_team(players, budget=100.0)

    assert len(selection.squad) == 15
    assert len(selection.starting_xi) == 11
    assert len(selection.bench) == 4
    assert selection.total_cost <= 100.0

    positions = Counter(p.position for p in selection.squad)
    assert dict(positions) == SQUAD_SHAPE

    clubs = Counter(p.team_id for p in selection.squad)
    assert max(clubs.values()) <= MAX_PER_CLUB

    xi_positions = Counter(p.position for p in selection.starting_xi)
    for pos in SQUAD_SHAPE:
        assert XI_MIN[pos] <= xi_positions.get(pos, 0) <= XI_MAX[pos]

    xi_ids = {p.id for p in selection.starting_xi}
    squad_ids = {p.id for p in selection.squad}
    assert xi_ids <= squad_ids
    assert selection.captain.id in xi_ids
    assert selection.vice_captain.id in xi_ids
    assert selection.captain.id != selection.vice_captain.id
    # Bench is ordered GK first.
    assert selection.bench[0].position == "GK"


def test_captain_is_best_starter(players):
    selection = pick_team(players, budget=100.0)
    best = max(selection.starting_xi, key=lambda p: p.score)
    assert selection.captain.id == best.id


def test_lock_and_exclude(players):
    target = players[0]
    without = pick_team(players, budget=100.0, excluded=[target.id])
    assert target.id not in {p.id for p in without.squad}

    cheap = min(players, key=lambda p: (p.score, p.price))
    locked = pick_team(players, budget=100.0, locked=[cheap.id])
    assert cheap.id in {p.id for p in locked.squad}


def test_infeasible_budget_raises(players):
    with pytest.raises(ValueError):
        pick_team(players, budget=10.0)


def test_tighter_budget_never_beats_looser(players):
    rich = pick_team(players, budget=100.0)
    poor = pick_team(players, budget=80.0)
    assert poor.total_cost <= 80.0
    assert poor.projected_points <= rich.projected_points
